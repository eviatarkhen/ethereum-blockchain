"""Ethereum Virtual Machine — stack-based bytecode executor.

The EVM reads bytecode one opcode at a time, dispatching to handler
methods that manipulate the stack, memory, and storage. Gas is consumed
before each opcode executes; if gas runs out, execution halts.

Set a breakpoint at the top of the execute() while loop to step through
every opcode the EVM processes. Each handler is a separate method so
the debugger call stack shows exactly which opcode is executing.

# SIMPLIFIED: ~25 opcodes vs ~140+ in real Ethereum.
# Only implements opcodes needed for Counter and SimpleToken contracts.
# CREATE and CALL opcodes are stubs — implemented in Plan 03-03.
"""

from dataclasses import dataclass

from ethereum.crypto.hashing import keccak256
from ethereum.evm.memory import Memory
from ethereum.evm.opcodes import *
from ethereum.evm.gas import GAS_COSTS, MOD_VALUE, MAX_UINT256, MAX_STACK_DEPTH
from ethereum.evm.exceptions import (
    OutOfGas,
    StackUnderflow,
    StackOverflow,
    InvalidJumpDestination,
    InvalidOpcode,
)


@dataclass
class ExecutionContext:
    """Context for a single EVM execution frame.

    Contains all the information the EVM needs from the outside world:
    who called, what address is executing, how much ETH was sent, etc.

    Attributes:
        caller: 20-byte address of the message sender (msg.sender).
        address: 20-byte address of the executing contract.
        value: Wei sent with this call (msg.value).
        data: Calldata bytes (the input to the contract).
        gas: Gas allocated for this execution.
    """
    caller: bytes
    address: bytes
    value: int
    data: bytes
    gas: int


@dataclass
class ExecutionResult:
    """Result of EVM execution.

    Returned by EVM.execute() to the caller (state transition function).

    Attributes:
        success: True if execution completed without revert/error.
        return_data: Bytes returned by RETURN opcode (or empty).
        gas_used: Total gas consumed during execution.
        gas_remaining: Gas left after execution.
    """
    success: bool
    return_data: bytes
    gas_used: int
    gas_remaining: int


class EVM:
    """Ethereum Virtual Machine — simplified stack machine.

    Executes bytecode by reading opcodes sequentially, dispatching to
    handler methods. The main execute() loop is designed for debugger
    stepping: set a breakpoint on the `opcode = ...` line to trace
    every instruction.

    # SIMPLIFIED: ~25 opcodes vs ~140+ in real Ethereum.
    # Only implements opcodes needed for Counter and SimpleToken contracts.

    Args:
        code: Bytecode to execute.
        context: Execution context (caller, address, value, calldata, gas).
        storage: Initial storage (dict of int -> int). Defaults to empty.
        world_state: Optional WorldState for CREATE/CALL opcodes.
    """

    def __init__(self, code: bytes, context: ExecutionContext,
                 storage: dict | None = None, world_state=None):
        self.code = code
        self.program_counter: int = 0
        self.execution_stack: list[int] = []
        self.memory = Memory()
        self.storage: dict[int, int] = storage if storage is not None else {}
        self.gas_remaining: int = context.gas
        self.context = context
        self.world_state = world_state

        # Execution state
        self.stopped: bool = False
        self.return_data: bytes = b""
        self.reverted: bool = False

        # Pre-scan for valid jump destinations
        self.valid_jumpdests: set[int] = self._find_jumpdests()

    def _find_jumpdests(self) -> set[int]:
        """Pre-scan bytecode for valid JUMPDEST positions.

        PUSH instructions embed data bytes in the code stream. Those
        data bytes might coincidentally equal 0x5B (JUMPDEST), but they
        are NOT valid jump targets. This scan skips PUSH data correctly.

        Returns:
            Set of valid JUMPDEST byte positions.
        """
        jumpdests = set()
        pc = 0
        while pc < len(self.code):
            opcode = self.code[pc]
            if opcode == OP_JUMPDEST:
                jumpdests.add(pc)
            # Skip PUSH data bytes
            if OP_PUSH1 <= opcode <= OP_PUSH32:
                push_size = opcode - OP_PUSH1 + 1
                pc += push_size
            pc += 1
        return jumpdests

    def _consume_gas(self, cost: int) -> None:
        """Consume gas for an opcode. Raise OutOfGas if insufficient.

        Args:
            cost: Gas units to consume.

        Raises:
            OutOfGas: If cost exceeds remaining gas.
        """
        if cost > self.gas_remaining:
            raise OutOfGas(needed=cost, remaining=self.gas_remaining)
        self.gas_remaining -= cost

    def _stack_pop(self) -> int:
        """Pop the top value from the execution stack.

        Returns:
            Top stack value as uint256.

        Raises:
            StackUnderflow: If stack is empty.
        """
        if len(self.execution_stack) == 0:
            raise StackUnderflow(needed=1, actual=0)
        return self.execution_stack.pop()

    def _stack_push(self, value: int) -> None:
        """Push a value onto the execution stack.

        Args:
            value: uint256 value to push.

        Raises:
            StackOverflow: If stack depth exceeds 1024.
        """
        if len(self.execution_stack) >= MAX_STACK_DEPTH:
            raise StackOverflow(max_depth=MAX_STACK_DEPTH)
        self.execution_stack.append(value)

    def _stack_peek(self, depth: int = 0) -> int:
        """Peek at a stack value without removing it.

        Args:
            depth: How deep to look (0 = top, 1 = second from top).

        Returns:
            Stack value at the specified depth.

        Raises:
            StackUnderflow: If depth exceeds stack size.
        """
        index = len(self.execution_stack) - 1 - depth
        if index < 0:
            raise StackUnderflow(needed=depth + 1, actual=len(self.execution_stack))
        return self.execution_stack[index]

    def execute(self) -> ExecutionResult:
        """Run bytecode until STOP, RETURN, REVERT, or out-of-gas.

        This is the main execution loop. Set a breakpoint on the line:
            opcode = self.code[self.program_counter]
        to step through every instruction.

        Returns:
            ExecutionResult with success status, return data, and gas info.
        """
        initial_gas = self.gas_remaining

        try:
            while not self.stopped and self.program_counter < len(self.code):
                # === BREAKPOINT HERE to trace every opcode ===
                opcode = self.code[self.program_counter]
                opcode_name = OPCODE_NAMES.get(opcode, f"UNKNOWN(0x{opcode:02x})")

                # Consume gas before execution
                gas_cost = GAS_COSTS.get(opcode)
                if gas_cost is None:
                    raise InvalidOpcode(opcode=opcode, pc=self.program_counter)

                # INVALID consumes ALL remaining gas
                if opcode == OP_INVALID:
                    self.gas_remaining = 0
                    self.stopped = True
                    self.reverted = True
                    break

                self._consume_gas(gas_cost)

                # Advance PC (handlers may further advance for PUSH data)
                self.program_counter += 1

                # Dispatch to handler
                self._dispatch(opcode)

        except OutOfGas:
            # Out of gas — execution failed, all gas consumed
            self.reverted = True
            self.gas_remaining = 0
            raise

        return ExecutionResult(
            success=not self.reverted,
            return_data=self.return_data,
            gas_used=initial_gas - self.gas_remaining,
            gas_remaining=self.gas_remaining,
        )

    def _dispatch(self, opcode: int) -> None:
        """Dispatch an opcode to its handler method.

        PUSHn, DUPn, and SWAPn are handled as ranges. All other
        opcodes have individual handler methods.

        Args:
            opcode: The opcode byte to dispatch.
        """
        # PUSHn: 0x60 - 0x7F
        if OP_PUSH1 <= opcode <= OP_PUSH32:
            push_size = opcode - OP_PUSH1 + 1
            self._op_push(push_size)
            return

        # DUPn: 0x80 - 0x8F
        if OP_DUP1 <= opcode <= OP_DUP16:
            depth = opcode - OP_DUP1
            self._op_dup(depth)
            return

        # SWAPn: 0x90 - 0x9F
        if OP_SWAP1 <= opcode <= OP_SWAP16:
            depth = opcode - OP_SWAP1 + 1
            self._op_swap(depth)
            return

        # Individual opcode handlers
        handlers = {
            OP_STOP: self._op_stop,
            OP_ADD: self._op_add,
            OP_MUL: self._op_mul,
            OP_SUB: self._op_sub,
            OP_DIV: self._op_div,
            OP_MOD: self._op_mod,
            OP_EXP: self._op_exp,
            OP_LT: self._op_lt,
            OP_GT: self._op_gt,
            OP_EQ: self._op_eq,
            OP_ISZERO: self._op_iszero,
            OP_AND: self._op_and,
            OP_OR: self._op_or,
            OP_NOT: self._op_not,
            OP_SHA3: self._op_sha3,
            OP_ADDRESS: self._op_address,
            OP_CALLER: self._op_caller,
            OP_CALLVALUE: self._op_callvalue,
            OP_CALLDATALOAD: self._op_calldataload,
            OP_CALLDATASIZE: self._op_calldatasize,
            OP_CALLDATACOPY: self._op_calldatacopy,
            OP_CODESIZE: self._op_codesize,
            OP_CODECOPY: self._op_codecopy,
            OP_POP: self._op_pop,
            OP_MLOAD: self._op_mload,
            OP_MSTORE: self._op_mstore,
            OP_MSTORE8: self._op_mstore8,
            OP_SLOAD: self._op_sload,
            OP_SSTORE: self._op_sstore,
            OP_JUMP: self._op_jump,
            OP_JUMPI: self._op_jumpi,
            OP_MSIZE: self._op_msize,
            OP_GAS: self._op_gas,
            OP_JUMPDEST: self._op_jumpdest,
            OP_CREATE: self._op_create,
            OP_CALL: self._op_call,
            OP_RETURN: self._op_return,
            OP_REVERT: self._op_revert,
        }

        handler = handlers.get(opcode)
        if handler is None:
            raise InvalidOpcode(opcode=opcode, pc=self.program_counter - 1)
        handler()

    # === Stop ===

    def _op_stop(self) -> None:
        """STOP (0x00): Halt execution successfully.

        Stack: [...] -> [...]  (no change)
        """
        self.stopped = True

    # === Arithmetic ===

    def _op_add(self) -> None:
        """ADD (0x01): Addition modulo 2^256.

        Stack: [a, b, ...] -> [(a + b) % 2^256, ...]
        """
        a = self._stack_pop()
        b = self._stack_pop()
        result = (a + b) % MOD_VALUE
        self._stack_push(result)

    def _op_mul(self) -> None:
        """MUL (0x02): Multiplication modulo 2^256.

        Stack: [a, b, ...] -> [(a * b) % 2^256, ...]
        """
        a = self._stack_pop()
        b = self._stack_pop()
        result = (a * b) % MOD_VALUE
        self._stack_push(result)

    def _op_sub(self) -> None:
        """SUB (0x03): Subtraction modulo 2^256.

        Stack: [a, b, ...] -> [(a - b) % 2^256, ...]

        Note: if a < b, the result wraps around (unsigned underflow).
        For example, SUB(3, 5) = 2^256 - 2.
        """
        a = self._stack_pop()
        b = self._stack_pop()
        result = (a - b) % MOD_VALUE
        self._stack_push(result)

    def _op_div(self) -> None:
        """DIV (0x04): Integer division.

        Stack: [a, b, ...] -> [a // b, ...]
        Division by zero returns 0 (EVM specification).
        """
        a = self._stack_pop()
        b = self._stack_pop()
        result = a // b if b != 0 else 0
        self._stack_push(result)

    def _op_mod(self) -> None:
        """MOD (0x06): Modulo.

        Stack: [a, b, ...] -> [a % b, ...]
        Modulo by zero returns 0 (EVM specification).
        """
        a = self._stack_pop()
        b = self._stack_pop()
        result = a % b if b != 0 else 0
        self._stack_push(result)

    def _op_exp(self) -> None:
        """EXP (0x0A): Exponentiation modulo 2^256.

        Stack: [a, b, ...] -> [(a ** b) % 2^256, ...]

        # SIMPLIFIED: Flat gas cost. Real Ethereum charges
        # 10 + 50 * byte_length(exponent) gas.
        """
        base = self._stack_pop()
        exponent = self._stack_pop()
        result = pow(base, exponent, MOD_VALUE)
        self._stack_push(result)

    # === Comparison ===

    def _op_lt(self) -> None:
        """LT (0x10): Less than comparison.

        Stack: [a, b, ...] -> [1 if a < b else 0, ...]
        """
        a = self._stack_pop()
        b = self._stack_pop()
        self._stack_push(1 if a < b else 0)

    def _op_gt(self) -> None:
        """GT (0x11): Greater than comparison.

        Stack: [a, b, ...] -> [1 if a > b else 0, ...]
        """
        a = self._stack_pop()
        b = self._stack_pop()
        self._stack_push(1 if a > b else 0)

    def _op_eq(self) -> None:
        """EQ (0x14): Equality comparison.

        Stack: [a, b, ...] -> [1 if a == b else 0, ...]
        """
        a = self._stack_pop()
        b = self._stack_pop()
        self._stack_push(1 if a == b else 0)

    def _op_iszero(self) -> None:
        """ISZERO (0x15): Is zero check.

        Stack: [a, ...] -> [1 if a == 0 else 0, ...]
        """
        a = self._stack_pop()
        self._stack_push(1 if a == 0 else 0)

    # === Bitwise ===

    def _op_and(self) -> None:
        """AND (0x16): Bitwise AND.

        Stack: [a, b, ...] -> [a & b, ...]
        """
        a = self._stack_pop()
        b = self._stack_pop()
        self._stack_push(a & b)

    def _op_or(self) -> None:
        """OR (0x17): Bitwise OR.

        Stack: [a, b, ...] -> [a | b, ...]
        """
        a = self._stack_pop()
        b = self._stack_pop()
        self._stack_push(a | b)

    def _op_not(self) -> None:
        """NOT (0x19): Bitwise NOT.

        Stack: [a, ...] -> [~a & MAX_UINT256, ...]

        NOT inverts all 256 bits. NOT(0) = MAX_UINT256.
        """
        a = self._stack_pop()
        self._stack_push(MAX_UINT256 - a)

    # === Hashing ===

    def _op_sha3(self) -> None:
        """SHA3 (0x20): Keccak-256 hash of memory region.

        Stack: [offset, size, ...] -> [hash, ...]

        Reads memory[offset:offset+size] and computes keccak256.
        Used by Solidity for mapping key computation.

        # SIMPLIFIED: Flat gas cost. Real Ethereum charges
        # 30 + 6 * ceil(size / 32) gas.
        """
        offset = self._stack_pop()
        size = self._stack_pop()
        data = self.memory.read_range(offset, size)
        hash_result = keccak256(data)
        self._stack_push(int.from_bytes(hash_result, "big"))

    # === Environment ===

    def _op_address(self) -> None:
        """ADDRESS (0x30): Get address of currently executing contract.

        Stack: [...] -> [address, ...]
        """
        self._stack_push(int.from_bytes(self.context.address, "big"))

    def _op_caller(self) -> None:
        """CALLER (0x33): Get caller address (msg.sender).

        Stack: [...] -> [caller, ...]

        In a direct transaction, this is the sender's EOA address.
        In a contract-to-contract call, this is the calling contract.
        """
        self._stack_push(int.from_bytes(self.context.caller, "big"))

    def _op_callvalue(self) -> None:
        """CALLVALUE (0x34): Get value sent with this call (msg.value).

        Stack: [...] -> [value, ...]
        """
        self._stack_push(self.context.value)

    def _op_calldataload(self) -> None:
        """CALLDATALOAD (0x35): Load 32 bytes from calldata.

        Stack: [offset, ...] -> [data, ...]

        Reads 32 bytes starting at offset from calldata. If offset + 32
        exceeds calldata length, the result is zero-padded on the right.
        """
        offset = self._stack_pop()
        calldata = self.context.data

        # Read 32 bytes, zero-padding if past end of calldata
        word = bytearray(32)
        for i in range(32):
            if offset + i < len(calldata):
                word[i] = calldata[offset + i]
            # else: stays 0x00 (zero-padded)

        self._stack_push(int.from_bytes(word, "big"))

    def _op_calldatasize(self) -> None:
        """CALLDATASIZE (0x36): Get size of calldata.

        Stack: [...] -> [size, ...]
        """
        self._stack_push(len(self.context.data))

    def _op_calldatacopy(self) -> None:
        """CALLDATACOPY (0x37): Copy calldata to memory.

        Stack: [destOffset, offset, size, ...] -> [...]

        Copies size bytes from calldata at offset to memory at destOffset.
        Zero-pads if reading past end of calldata.

        # SIMPLIFIED: Flat gas cost. Real: 3 + 3 * ceil(size / 32).
        """
        dest_offset = self._stack_pop()
        offset = self._stack_pop()
        size = self._stack_pop()

        if size == 0:
            return

        calldata = self.context.data
        data = bytearray(size)
        for i in range(size):
            if offset + i < len(calldata):
                data[i] = calldata[offset + i]

        self.memory.write_range(dest_offset, bytes(data))

    def _op_codesize(self) -> None:
        """CODESIZE (0x38): Get size of code running in current environment.

        Stack: [...] -> [size, ...]
        """
        self._stack_push(len(self.code))

    def _op_codecopy(self) -> None:
        """CODECOPY (0x39): Copy code to memory.

        Stack: [destOffset, offset, size, ...] -> [...]

        Used by constructors to copy runtime code for RETURN.

        # SIMPLIFIED: Flat gas cost. Real: 3 + 3 * ceil(size / 32).
        """
        dest_offset = self._stack_pop()
        offset = self._stack_pop()
        size = self._stack_pop()

        if size == 0:
            return

        data = bytearray(size)
        for i in range(size):
            if offset + i < len(self.code):
                data[i] = self.code[offset + i]

        self.memory.write_range(dest_offset, bytes(data))

    # === Stack Operations ===

    def _op_pop(self) -> None:
        """POP (0x50): Remove top of stack.

        Stack: [a, ...] -> [...]
        """
        self._stack_pop()

    def _op_push(self, n: int) -> None:
        """PUSHn (0x60-0x7F): Push n bytes from code onto stack.

        Reads n bytes immediately following the PUSH opcode in the
        bytecode and pushes them as a big-endian uint256.

        Stack: [...] -> [value, ...]
        """
        start = self.program_counter
        end = start + n
        # Read bytes from code, zero-pad if past end
        value_bytes = bytearray(n)
        for i in range(n):
            if start + i < len(self.code):
                value_bytes[i] = self.code[start + i]
        value = int.from_bytes(value_bytes, "big")
        self._stack_push(value)
        self.program_counter += n  # Skip past the data bytes

    def _op_dup(self, depth: int) -> None:
        """DUPn (0x80-0x8F): Duplicate the (depth+1)th stack item.

        DUP1 copies the top item, DUP2 copies the second item, etc.

        Stack: [..., a] -> [..., a, a]  (for DUP1)
        """
        value = self._stack_peek(depth)
        self._stack_push(value)

    def _op_swap(self, depth: int) -> None:
        """SWAPn (0x90-0x9F): Swap top item with the (depth+1)th item.

        SWAP1 swaps top two items, SWAP2 swaps top with third, etc.

        Stack: [a, ..., b] -> [b, ..., a]
        """
        top_index = len(self.execution_stack) - 1
        swap_index = top_index - depth
        if swap_index < 0:
            raise StackUnderflow(
                needed=depth + 1,
                actual=len(self.execution_stack),
            )
        self.execution_stack[top_index], self.execution_stack[swap_index] = (
            self.execution_stack[swap_index],
            self.execution_stack[top_index],
        )

    # === Memory ===

    def _op_mload(self) -> None:
        """MLOAD (0x51): Load 32-byte word from memory.

        Stack: [offset, ...] -> [value, ...]

        # SIMPLIFIED: No memory expansion gas cost.
        """
        offset = self._stack_pop()
        value = self.memory.load(offset)
        self._stack_push(value)

    def _op_mstore(self) -> None:
        """MSTORE (0x52): Store 32-byte word to memory.

        Stack: [offset, value, ...] -> [...]

        # SIMPLIFIED: No memory expansion gas cost.
        """
        offset = self._stack_pop()
        value = self._stack_pop()
        self.memory.store(offset, value)

    def _op_mstore8(self) -> None:
        """MSTORE8 (0x53): Store single byte to memory.

        Stack: [offset, value, ...] -> [...]
        Only the least significant byte of value is stored.

        # SIMPLIFIED: No memory expansion gas cost.
        """
        offset = self._stack_pop()
        value = self._stack_pop()
        self.memory.store8(offset, value)

    def _op_msize(self) -> None:
        """MSIZE (0x59): Get current memory size.

        Stack: [...] -> [size, ...]
        """
        self._stack_push(self.memory.size())

    # === Storage ===

    def _op_sload(self) -> None:
        """SLOAD (0x54): Load value from storage.

        Stack: [key, ...] -> [value, ...]

        Reads from persistent storage. Returns 0 for unset keys.

        # SIMPLIFIED: Flat 100 gas. Real: 2100 cold / 100 warm (EIP-2929).
        """
        key = self._stack_pop()
        value = self.storage.get(key, 0)
        self._stack_push(value)

    def _op_sstore(self) -> None:
        """SSTORE (0x55): Store value to storage.

        Stack: [key, value, ...] -> [...]

        Writes to persistent storage. This is how contracts save state
        between transactions.

        # SIMPLIFIED: Flat 5000 gas. Real Ethereum (EIP-2200) charges
        # 2200 for no-change, 5000 for zero->non-zero, 20000 for
        # non-zero->non-zero, with refund logic for clearing.
        """
        key = self._stack_pop()
        value = self._stack_pop()
        self.storage[key] = value

    # === Flow Control ===

    def _op_jump(self) -> None:
        """JUMP (0x56): Unconditional jump.

        Stack: [destination, ...] -> [...]

        Jumps to the given position in code. The destination must
        be a valid JUMPDEST position, otherwise execution fails.
        """
        destination = self._stack_pop()
        if destination not in self.valid_jumpdests:
            raise InvalidJumpDestination(destination=destination)
        self.program_counter = destination

    def _op_jumpi(self) -> None:
        """JUMPI (0x57): Conditional jump.

        Stack: [destination, condition, ...] -> [...]

        Jumps to destination if condition is non-zero.
        If condition is zero, execution continues to next opcode.
        """
        destination = self._stack_pop()
        condition = self._stack_pop()
        if condition != 0:
            if destination not in self.valid_jumpdests:
                raise InvalidJumpDestination(destination=destination)
            self.program_counter = destination

    def _op_gas(self) -> None:
        """GAS (0x5A): Get remaining gas.

        Stack: [...] -> [gas_remaining, ...]

        Returns gas remaining AFTER the GAS opcode's own cost
        has been consumed.
        """
        self._stack_push(self.gas_remaining)

    def _op_jumpdest(self) -> None:
        """JUMPDEST (0x5B): Mark a valid jump destination.

        Stack: [...] -> [...]  (no change)

        This opcode does nothing at execution time. It exists only
        to mark positions where JUMP/JUMPI are allowed to land.
        """
        pass  # No-op — exists only as a jump target marker

    # === Return ===

    def _op_return(self) -> None:
        """RETURN (0xF3): Return data and halt execution.

        Stack: [offset, size, ...] -> [...]

        Reads memory[offset:offset+size] as the return data and
        stops execution successfully.
        """
        offset = self._stack_pop()
        size = self._stack_pop()
        self.return_data = self.memory.read_range(offset, size)
        self.stopped = True

    def _op_revert(self) -> None:
        """REVERT (0xFD): Revert state and halt.

        Stack: [offset, size, ...] -> [...]

        Like RETURN but marks execution as failed. State changes
        from this execution context are reverted. Remaining gas
        IS refunded (unlike INVALID which consumes all gas).
        """
        offset = self._stack_pop()
        size = self._stack_pop()
        self.return_data = self.memory.read_range(offset, size)
        self.stopped = True
        self.reverted = True

    # === Contract Operations ===

    def _op_create(self) -> None:
        """CREATE (0xF0): Deploy a new contract.

        Stack: [value, offset, size, ...] -> [address, ...]

        Reads init code from memory, deploys a new contract, and pushes
        the new contract address on success (0 on failure).

        # SIMPLIFIED: No EIP-3860 init code size limit (48KB max).
        # SIMPLIFIED: Forward all remaining gas to init code.
        # Real Ethereum uses EIP-150 (63/64 rule).
        # SIMPLIFIED: No code deposit cost (200 gas per byte).
        """
        from ethereum.core.address import compute_contract_address

        value = self._stack_pop()
        offset = self._stack_pop()
        size = self._stack_pop()

        if self.world_state is None:
            self._stack_push(0)  # No world state, cannot create
            return

        # Read init code from memory
        init_code = self.memory.read_range(offset, size)

        # Compute contract address from current contract's address and nonce
        creator_account = self.world_state.get_account(self.context.address)
        contract_address = compute_contract_address(
            self.context.address, creator_account.nonce
        )

        # Increment creator's nonce
        self.world_state.increment_nonce(self.context.address)

        # Create the new account
        self.world_state.add_balance(contract_address, 0)

        # Transfer value if specified
        if value > 0:
            try:
                self.world_state.transfer(self.context.address, contract_address, value)
            except ValueError:
                self._stack_push(0)
                return

        # Run init code
        context = ExecutionContext(
            caller=self.context.address,
            address=contract_address,
            value=value,
            data=b"",
            gas=self.gas_remaining,
        )

        evm = EVM(
            code=init_code,
            context=context,
            storage={},
            world_state=self.world_state,
        )

        try:
            result = evm.execute()
        except OutOfGas:
            self._stack_push(0)
            return

        if result.success:
            # Store return data as runtime code
            self.world_state.set_code(contract_address, result.return_data)
            # Persist storage changes
            for key, val in evm.storage.items():
                self.world_state.set_storage(contract_address, key, val)
            # Deduct gas used by child, refund remaining
            self.gas_remaining -= result.gas_used
            # Push contract address as uint256
            self._stack_push(int.from_bytes(contract_address, "big"))
        else:
            self.gas_remaining -= result.gas_used
            self._stack_push(0)

    def _op_call(self) -> None:
        """CALL (0xF1): Call another contract.

        Stack: [gas, addr, value, argsOffset, argsLength, retOffset, retLength, ...]
               -> [success, ...]

        Calls the contract at addr with the given gas, value, and calldata.
        Writes return data to caller's memory. Pushes 1 on success, 0 on failure.

        # SIMPLIFIED: Forward exact requested gas (no EIP-150 63/64 rule).
        # SIMPLIFIED: No DELEGATECALL or STATICCALL.
        # SIMPLIFIED: No stipend (2300 gas) for value transfers.
        """
        gas = self._stack_pop()
        addr_int = self._stack_pop()
        value = self._stack_pop()
        args_offset = self._stack_pop()
        args_length = self._stack_pop()
        ret_offset = self._stack_pop()
        ret_length = self._stack_pop()

        if self.world_state is None:
            self._stack_push(0)
            return

        # Convert address from uint256 to 20-byte bytes
        target_address = addr_int.to_bytes(32, "big")[12:]

        # Cap gas at remaining
        forwarded_gas = min(gas, self.gas_remaining)

        # Read calldata from memory
        input_data = b""
        if args_length > 0:
            input_data = self.memory.read_range(args_offset, args_length)

        # Get target account
        target_account = self.world_state.get_account(target_address)

        # Transfer value first (before execution)
        if value > 0:
            try:
                self.world_state.transfer(self.context.address, target_address, value)
            except ValueError:
                self._stack_push(0)
                return

        # If target has no code (EOA), it's just a value transfer
        if not target_account.code:
            self.gas_remaining -= forwarded_gas  # Consume forwarded gas
            self.gas_remaining += forwarded_gas   # Refund all (no execution)
            self._stack_push(1)  # Success
            return

        # Execute target code
        context = ExecutionContext(
            caller=self.context.address,
            address=target_address,
            value=value,
            data=input_data,
            gas=forwarded_gas,
        )

        # Load target's storage
        target_storage = dict(target_account.storage)

        evm = EVM(
            code=target_account.code,
            context=context,
            storage=target_storage,
            world_state=self.world_state,
        )

        try:
            result = evm.execute()
        except OutOfGas:
            # Callee ran out of gas -- caller continues
            self.gas_remaining -= forwarded_gas  # All forwarded gas consumed
            self._stack_push(0)
            return

        if result.success:
            # Persist storage changes
            for key, val in evm.storage.items():
                self.world_state.set_storage(target_address, key, val)

            # Write return data to caller's memory
            if ret_length > 0 and result.return_data:
                write_data = result.return_data[:ret_length]
                # Pad if return data is shorter than ret_length
                if len(write_data) < ret_length:
                    write_data += b'\x00' * (ret_length - len(write_data))
                self.memory.write_range(ret_offset, write_data)

            # Deduct gas used, refund remaining
            self.gas_remaining -= result.gas_used
            self._stack_push(1)
        else:
            # Failed: consume all forwarded gas
            self.gas_remaining -= forwarded_gas
            self._stack_push(0)
