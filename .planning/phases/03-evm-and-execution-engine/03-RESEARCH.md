# Phase 3: EVM and Execution Engine - Research

**Researched:** 2026-02-19
**Domain:** Ethereum Virtual Machine implementation, gas metering, transaction validation, and state transitions in Python
**Confidence:** HIGH

## Summary

Phase 3 builds the core execution engine: a stack-based virtual machine that reads bytecode, executes opcodes, tracks gas, validates transactions, and applies state transitions. The key constraint is **contract-driven opcode selection** -- only implement opcodes that Counter (increment/get) and SimpleToken (transfer/balanceOf) contracts actually need. This keeps the scope to roughly 25 opcodes rather than the full 140+.

The implementation breaks down into four major subsystems: (1) the EVM stack machine with opcodes, (2) gas metering and enforcement, (3) transaction validation in Yellow Paper order, and (4) the state transition function that ties everything together. Contract deployment via CREATE is included in this phase so Phase 4 only writes scenario scripts.

**Primary recommendation:** Build the EVM as a single `EVM` class with an `execute()` method containing a while-loop dispatcher. Use one handler function per opcode for maximum debugger stepping clarity. Use a flat gas cost dictionary with `# SIMPLIFIED:` annotations. Implement full state rollback on out-of-gas via snapshot/revert pattern on the world state.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **Contract-driven selection**: Only include opcodes required by Counter and SimpleToken. Every opcode must have a concrete reason to exist.
- **Contract deployment (CREATE)**: Included in Phase 3 so Phase 4 focuses only on scenario scripts.
- **Out-of-gas behavior**: Full rollback expected (Ethereum spec correctness).

### Claude's Discretion
- Unsupported opcodes: raise `UnsupportedOpcode` error or treat as INVALID halt
- Code organization: one function per opcode vs grouped handlers -- optimize for debugger stepping
- CALL-family opcodes: determine based on what Counter and SimpleToken actually need
- Execution tracing approach: structured trace, print logging, or debugger-only variables
- Step mode: `step()` API vs continuous execution with breakpoint-friendly code
- SIMPLIFIED markers: code comments only vs also in trace output
- Execution results: summary object vs raw outcome
- SSTORE gas: flat cost vs two-tier. Mark deviation with `# SIMPLIFIED:`
- Gas cost structure: dictionary table vs hardcoded constants
- Intrinsic gas: full calculation (21000 + calldata bytes) vs flat 21000
- Error types: custom exception classes per failure vs single exception with reason
- State transition: unified `apply_transaction()` vs separate transfer/contract paths
- Validation logging: step-by-step log vs debugger-only inspection

### Deferred Ideas (OUT OF SCOPE)
None
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| EVM-01 | Stack machine with ~20 core opcodes | ~25 opcodes needed for Counter + SimpleToken; see opcode analysis below |
| EVM-02 | Gas metering (simplified -- track and enforce gas limit) | Flat gas cost dictionary; intrinsic gas 21000 + calldata; out-of-gas triggers full rollback |
| EVM-03 | CREATE opcode for contract deployment | Store bytecode at keccak256-derived address; return runtime code from constructor |
| EVM-04 | CALL opcode for contract function calls | Needed for inter-contract calls; SimpleToken needs at minimum basic CALL |
| TX-03 | Transaction validation (nonce, balance, gas limit) | Yellow Paper Section 6: signature -> nonce -> balance >= value + gas*gasPrice -> intrinsic gas |
| STATE-04 | State transition function (apply tx to world state) | `apply_transaction()` orchestrates validation -> EVM execution -> state commit or rollback |
| LEARN-04 | `# SIMPLIFIED:` comment convention | Every deviation from real Ethereum gets annotated; ~15-20 simplifications expected |
| LEARN-05 | Readable code with meaningful variable names | Descriptive names like `program_counter`, `gas_remaining`, `execution_stack` for debugger inspection |
</phase_requirements>

## Opcode Analysis: What Counter and SimpleToken Need

### Counter Contract (increment / get count)
A minimal counter stores a single uint256 in storage slot 0 and exposes `increment()` and `getCount()`.

**Solidity equivalent:**
```solidity
contract Counter {
    uint256 count;
    function increment() public { count += 1; }
    function getCount() public view returns (uint256) { return count; }
}
```

**Opcodes needed:**
- Flow: STOP, JUMPDEST, JUMP, JUMPI
- Stack: PUSH1-PUSH32 (PUSH1, PUSH2, PUSH4, PUSH32 sufficient), POP, DUP1, SWAP1
- Arithmetic: ADD, SUB, LT, GT, EQ, ISZERO
- Storage: SLOAD, SSTORE
- Memory: MSTORE, MLOAD, MSTORE8
- Calldata: CALLDATALOAD, CALLDATASIZE
- Return: RETURN, REVERT
- Context: CALLER (for access control if needed)

### SimpleToken Contract (transfer / balanceOf)
A token with mapping(address => uint256) balances, transfer(), and balanceOf().

**Solidity equivalent:**
```solidity
contract SimpleToken {
    mapping(address => uint256) balances;
    constructor(uint256 initialSupply) { balances[msg.sender] = initialSupply; }
    function transfer(address to, uint256 amount) public { ... }
    function balanceOf(address addr) public view returns (uint256) { return balances[addr]; }
}
```

**Additional opcodes needed (beyond Counter):**
- Hashing: SHA3 (Keccak-256 -- for mapping key computation: `keccak256(abi.encodePacked(key, slot))`)
- Comparison: AND, OR, NOT (for address masking and validation)
- Calldata: CALLDATASIZE (already listed), CALLDATACOPY
- Context: ADDRESS (contract's own address), CALLVALUE (check no ETH sent)
- Arithmetic: MUL (for slot calculation), DIV (unlikely but possible)

### Complete Opcode Set (~25 opcodes)

| Category | Opcodes | Count |
|----------|---------|-------|
| Arithmetic | ADD, SUB, MUL, DIV, MOD, EXP | 6 |
| Comparison | LT, GT, EQ, ISZERO | 4 |
| Bitwise | AND, OR, NOT | 3 |
| Hashing | SHA3 | 1 |
| Stack | POP, PUSH1-PUSH32, DUP1-DUP16, SWAP1-SWAP16 | 3 families |
| Memory | MLOAD, MSTORE, MSTORE8 | 3 |
| Storage | SLOAD, SSTORE | 2 |
| Flow | STOP, JUMP, JUMPI, JUMPDEST, RETURN, REVERT, INVALID | 7 |
| Calldata | CALLDATALOAD, CALLDATASIZE, CALLDATACOPY | 3 |
| Context | CALLER, CALLVALUE, ADDRESS, GAS | 4 |
| Contract | CREATE, CALL | 2 |

**Total: ~25 unique opcodes + PUSH/DUP/SWAP families**

### Opcodes Explicitly NOT Needed
- DELEGATECALL, STATICCALL, CALLCODE -- out of scope per requirements
- LOG0-LOG4 -- no event system needed
- BALANCE, EXTCODESIZE, EXTCODECOPY -- not needed for Counter/SimpleToken
- BLOCKHASH, COINBASE, TIMESTAMP, NUMBER, DIFFICULTY, GASLIMIT, CHAINID, SELFBALANCE -- block context not needed
- BYTE, SHL, SHR, SAR -- shift operations not needed for these contracts
- SIGNEXTEND, SDIV, SMOD, ADDMOD, MULMOD -- signed/modular arithmetic not needed
- RETURNDATASIZE, RETURNDATACOPY -- can simplify CALL without these
- SELFDESTRUCT -- deprecated, not needed
- PC, MSIZE, CODESIZE, CODECOPY -- can defer unless constructor needs CODECOPY

**Note on CODECOPY:** Constructor bytecode typically uses CODECOPY to return runtime code. This is needed for CREATE to work properly. Adding CODECOPY to the list.

**Revised total: ~26 opcodes + PUSH/DUP/SWAP families**

## Architecture Patterns

### Recommended Project Structure
```
src/
  ethereum/
    crypto/              # Phase 1 (exists)
    encoding/            # Phase 1 (exists)
    state/               # Phase 2 (will exist)
      __init__.py
      account.py         # Account dataclass
      world_state.py     # WorldState dict-backed store
    evm/                 # Phase 3 (NEW)
      __init__.py        # Re-exports: EVM, ExecutionResult
      opcodes.py         # Opcode constants (0x00-0xff hex values)
      gas.py             # Gas cost table and gas tracking
      vm.py              # EVM class with execute() loop
      exceptions.py      # OutOfGas, InvalidOpcode, StackUnderflow, etc.
    core/                # Phase 3 (NEW)
      __init__.py
      tx_validator.py    # Transaction validation (Yellow Paper order)
      state_transition.py # apply_transaction() orchestrator
tests/
  test_evm.py            # EVM opcode tests
  test_gas.py            # Gas metering tests
  test_tx_validator.py   # Transaction validation tests
  test_state_transition.py # End-to-end state transition tests
```

### Pattern 1: EVM Stack Machine
**What:** Single `EVM` class with a `while` loop reading opcodes from bytecode, dispatching to handler methods.
**When to use:** All bytecode execution.
**Why this pattern:** A developer can set a breakpoint at the top of the while loop and step through every opcode. Each handler is a separate method, so the debugger call stack shows exactly which opcode is executing.

```python
class EVM:
    """Ethereum Virtual Machine - simplified stack machine.

    # SIMPLIFIED: ~25 opcodes vs ~140 in real Ethereum.
    # Only implements opcodes needed for Counter and SimpleToken contracts.
    """

    def __init__(self, code: bytes, context: ExecutionContext):
        self.code = code
        self.program_counter = 0          # Current position in bytecode
        self.execution_stack = []          # Stack of 256-bit integers
        self.memory = bytearray()          # Byte-addressable memory
        self.storage = {}                  # Persistent key-value storage
        self.gas_remaining = context.gas   # Gas left to spend
        self.context = context             # Caller, value, calldata, etc.
        self.stopped = False
        self.return_data = b''
        self.reverted = False

    def execute(self) -> 'ExecutionResult':
        """Run bytecode until STOP, RETURN, REVERT, or out-of-gas.

        Set a breakpoint on the 'opcode = ...' line below to step
        through every instruction the EVM processes.
        """
        while not self.stopped and self.program_counter < len(self.code):
            # === BREAKPOINT HERE to trace every opcode ===
            opcode = self.code[self.program_counter]
            opcode_name = OPCODE_NAMES.get(opcode, f'UNKNOWN(0x{opcode:02x})')

            handler = self._get_handler(opcode)
            if handler is None:
                raise InvalidOpcode(opcode, self.program_counter)

            gas_cost = GAS_COSTS.get(opcode, 0)
            self._consume_gas(gas_cost)

            self.program_counter += 1
            handler()

        return ExecutionResult(
            success=not self.reverted,
            return_data=self.return_data,
            gas_used=self.context.gas - self.gas_remaining,
            gas_remaining=self.gas_remaining,
        )
```

### Pattern 2: Gas Cost Dictionary
**What:** A flat dictionary mapping opcode -> gas cost, with `# SIMPLIFIED:` annotations for deviations.
**When to use:** Gas calculation for every opcode.

```python
# SIMPLIFIED: Flat gas costs. Real Ethereum has dynamic costs for
# SSTORE (EIP-2200 three-value), CALL (EIP-150 forwarding),
# memory expansion, etc.
GAS_COSTS = {
    0x00: 0,      # STOP
    0x01: 3,      # ADD
    0x02: 3,      # MUL  (real: 5)
    0x03: 3,      # SUB
    0x04: 5,      # DIV
    0x06: 5,      # MOD
    0x10: 3,      # LT
    0x11: 3,      # GT
    0x14: 3,      # EQ
    0x15: 3,      # ISZERO
    0x16: 3,      # AND
    0x17: 3,      # OR
    0x19: 3,      # NOT
    0x20: 30,     # SHA3 (base cost; + 6 per word in real Ethereum)
    0x35: 3,      # CALLDATALOAD
    0x36: 2,      # CALLDATASIZE
    0x37: 3,      # CALLDATACOPY (base; + 3 per word in real)
    0x39: 3,      # CODECOPY (base; + 3 per word in real)
    0x50: 2,      # POP
    0x51: 3,      # MLOAD  (+ memory expansion)
    0x52: 3,      # MSTORE (+ memory expansion)
    0x53: 3,      # MSTORE8 (+ memory expansion)
    0x54: 100,    # SLOAD  # SIMPLIFIED: Real cost is 2100 cold / 100 warm (EIP-2929)
    0x55: 5000,   # SSTORE # SIMPLIFIED: Flat 5000. Real is 2200-20000 depending on value (EIP-2200)
    0x56: 8,      # JUMP
    0x57: 10,     # JUMPI
    0x5b: 1,      # JUMPDEST
    0x60: 3,      # PUSH1 (all PUSHn cost 3)
    0xf0: 32000,  # CREATE
    0xf1: 100,    # CALL  # SIMPLIFIED: Base cost. Real has memory expansion + value transfer + new account costs
    0xf3: 0,      # RETURN
    0xfd: 0,      # REVERT
    0xfe: 0,      # INVALID
}
```

### Pattern 3: Transaction Validation (Yellow Paper Order)
**What:** Validate transactions in the exact order specified by the Yellow Paper Section 6.
**Why this order matters:** Ethereum nodes reject transactions at the first failure point. The order is: well-formed signature -> valid nonce -> sufficient balance -> sufficient gas.

```python
def validate_transaction(tx, world_state, block_gas_limit):
    """Validate a transaction per Yellow Paper Section 6.

    Checks in order (stops at first failure):
    1. Signature is valid and sender can be recovered
    2. Sender nonce matches transaction nonce
    3. Sender balance >= value + gas_limit * gas_price
    4. Transaction gas_limit <= block gas limit
    5. Intrinsic gas <= transaction gas_limit

    # SIMPLIFIED: No EIP-1559 base fee / priority fee.
    # SIMPLIFIED: No access lists (EIP-2930).
    """
    # Step 1: Recover sender from signature
    sender_address = recover_sender(tx)

    # Step 2: Nonce check
    sender_account = world_state.get_account(sender_address)
    if sender_account.nonce != tx.nonce:
        raise InvalidNonce(expected=sender_account.nonce, got=tx.nonce)

    # Step 3: Balance check
    total_cost = tx.value + (tx.gas_limit * tx.gas_price)
    if sender_account.balance < total_cost:
        raise InsufficientBalance(required=total_cost, available=sender_account.balance)

    # Step 4: Block gas limit
    if tx.gas_limit > block_gas_limit:
        raise ExceedsBlockGasLimit(tx_gas=tx.gas_limit, block_limit=block_gas_limit)

    # Step 5: Intrinsic gas
    intrinsic = calculate_intrinsic_gas(tx)
    if tx.gas_limit < intrinsic:
        raise IntrinsicGasTooLow(required=intrinsic, provided=tx.gas_limit)

    return sender_address
```

### Pattern 4: State Transition with Snapshot/Revert
**What:** Take a snapshot of world state before execution, revert on failure.
**Why:** Out-of-gas must leave state unchanged. This is a critical Ethereum invariant.

```python
def apply_transaction(tx, world_state, block_gas_limit):
    """Apply a signed transaction to world state.

    This is the core state transition function.
    On success: state changes are committed, gas is consumed.
    On failure: state is reverted to pre-transaction snapshot.

    # SIMPLIFIED: No gas refund mechanism.
    # SIMPLIFIED: No coinbase reward for miner/validator.
    """
    # 1. Validate
    sender = validate_transaction(tx, world_state, block_gas_limit)

    # 2. Snapshot state for potential rollback
    state_snapshot = world_state.snapshot()

    # 3. Deduct upfront gas cost
    world_state.deduct_balance(sender, tx.gas_limit * tx.gas_price)
    world_state.increment_nonce(sender)

    # 4. Execute
    if tx.to is None:
        # Contract creation
        result = execute_create(tx, sender, world_state)
    else:
        # Message call (transfer or contract interaction)
        result = execute_call(tx, sender, world_state)

    # 5. Handle result
    if not result.success:
        world_state.revert(state_snapshot)
        # But nonce still increments and gas is consumed

    # 6. Refund unused gas
    gas_refund = result.gas_remaining * tx.gas_price
    world_state.add_balance(sender, gas_refund)

    return result
```

### Pattern 5: Contract Deployment via CREATE
**What:** CREATE opcode deploys a new contract by running constructor bytecode and storing the returned runtime code.
**How:**

```python
def execute_create(tx, sender, world_state):
    """Deploy a new contract.

    1. Compute contract address = keccak256(rlp([sender, nonce]))[12:]
    2. Create account at that address
    3. Run init code (constructor) -- the bytecode in tx.data
    4. Store return data as the contract's runtime code
    5. Charge gas for code storage (200 per byte)

    # SIMPLIFIED: No CREATE2. No init code size limit (EIP-3860).
    """
    contract_address = compute_contract_address(sender, world_state.get_nonce(sender) - 1)
    world_state.create_account(contract_address)

    if tx.value > 0:
        world_state.transfer(sender, contract_address, tx.value)

    # Run constructor
    evm = EVM(code=tx.data, context=ExecutionContext(
        caller=sender,
        address=contract_address,
        value=tx.value,
        data=b'',  # No calldata for constructor
        gas=tx.gas_limit - intrinsic_gas,
    ))
    result = evm.execute()

    if result.success and result.return_data:
        # return_data IS the runtime bytecode
        world_state.set_code(contract_address, result.return_data)

    return result
```

### Anti-Patterns to Avoid
- **Implementing all 140+ opcodes:** Only implement what Counter and SimpleToken need. Everything else is wasted effort.
- **Dynamic gas without annotation:** Every simplified gas cost must have a `# SIMPLIFIED:` comment explaining what the real cost model is.
- **Mutating state before validation completes:** All 5 validation steps must pass before any state change.
- **Forgetting mod 2^256:** All arithmetic results must be `% (2**256)`. Missing this causes overflow bugs.
- **Using Python lists as the EVM stack without a max depth:** Real EVM has a 1024-depth limit. Enforcing this prevents infinite recursion bugs.
- **Not reverting state on out-of-gas:** This is the most common correctness bug in toy EVM implementations.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Keccak-256 | Custom hash | `ethereum.crypto.keccak256` (Phase 1) | Already implemented and tested |
| Signature recovery | Custom ECDSA | `ethereum.crypto` (Phase 1) | Already implemented and tested |
| RLP encoding | New serializer | `ethereum.encoding.rlp` (Phase 1) | Already implemented and tested |
| Account/WorldState | New data layer | Phase 2 modules | Will exist before Phase 3 executes |

## Common Pitfalls

### Pitfall 1: Forgetting mod 2^256 on Arithmetic
**What goes wrong:** Python integers have unlimited precision. Without explicit modding, ADD(MAX_UINT256, 1) returns MAX_UINT256 + 1 instead of 0.
**Why it happens:** In C/Go/Rust, uint256 naturally overflows. Python doesn't.
**How to avoid:** Every arithmetic opcode handler must apply `% (2**256)` to the result. Define `MAX_UINT256 = 2**256 - 1` and `MOD_VALUE = 2**256` as constants.
**Warning signs:** Large number arithmetic produces values > 2^256.

### Pitfall 2: JUMP/JUMPI Destination Validation
**What goes wrong:** Jumping to an arbitrary position that doesn't contain JUMPDEST (0x5b).
**Why it happens:** EVM requires JUMPDEST at every valid jump target. Without validation, code can jump into the middle of a PUSH instruction's data.
**How to avoid:** Pre-scan bytecode for valid JUMPDEST positions before execution. Store as a set. Check on every JUMP/JUMPI.
**Warning signs:** Execution produces garbage results or infinite loops.

### Pitfall 3: Memory Expansion Gas Cost
**What goes wrong:** Accessing memory address 1,000,000 should cost gas proportional to the new memory size, but flat-cost implementations don't charge for it.
**Why it happens:** EVM memory is dynamically sized. Accessing a high offset expands memory and costs gas quadratically.
**How to avoid:** Track current memory size. On any memory access, if the access extends beyond current size, expand and charge gas. For the simplified model, at minimum charge a flat cost per 32-byte word of expansion.
**Warning signs:** Programs can allocate unlimited memory without running out of gas.

### Pitfall 4: SSTORE Nonce/Value Confusion
**What goes wrong:** SSTORE stores at the wrong slot because the stack order is confused (key is deeper than value on stack).
**Why it happens:** SSTORE pops the key first, then the value: `key = stack.pop(); value = stack.pop(); storage[key] = value`.
**How to avoid:** Document stack effects as comments on every opcode handler. Verify with a simple test: `PUSH1 42 PUSH1 0 SSTORE` should store 42 at slot 0.
**Warning signs:** Storage values end up in wrong slots.

### Pitfall 5: CREATE Address Calculation
**What goes wrong:** Contract address doesn't match expected value.
**Why it happens:** The address is `keccak256(rlp([sender_address, sender_nonce]))[12:]` -- the nonce must be the nonce BEFORE the transaction increments it, and both sender_address and nonce must be properly RLP-encoded.
**How to avoid:** Use the existing `rlp_encode` and `keccak256` from Phase 1. Test against a known vector.
**Warning signs:** Contract deployment succeeds but the contract can't be found at the expected address.

### Pitfall 6: Stack Order for Binary Operations
**What goes wrong:** SUB, DIV, and comparison operations produce wrong results because operand order is reversed.
**Why it happens:** EVM stack pops the first operand (a) then the second (b), and computes a op b. For `PUSH1 3 PUSH1 5 SUB`, 5 is on top, so it pops 5 then 3, computing 5 - 3 = 2.
**How to avoid:** Always test binary ops with asymmetric operands to catch order bugs. Document: `a = stack.pop(); b = stack.pop(); result = a - b` for SUB.
**Warning signs:** `5 - 3` gives `-2` (or 2^256 - 2 after mod) instead of 2.

## Gas Model Recommendation

Given Claude's discretion on gas model simplification, the recommended approach is:

1. **Intrinsic gas:** 21000 base + 4 per zero calldata byte + 16 per non-zero calldata byte. This is simple to implement and educationally valuable (shows why empty transactions still cost gas).
2. **SSTORE:** Flat 5000 gas with `# SIMPLIFIED: Real Ethereum uses EIP-2200 (2200 for no-change, 5000 for zero->non-zero, 20000 for non-zero->non-zero with refund logic)`.
3. **CALL:** Flat 100 gas base cost with `# SIMPLIFIED: Real Ethereum charges 2600 cold / 100 warm (EIP-2929) + value transfer costs`.
4. **Memory expansion:** Flat 3 gas per word of expansion with `# SIMPLIFIED: Real Ethereum charges quadratically: 3 * words + words^2 / 512`.
5. **No gas refund:** Skip the refund mechanism entirely with `# SIMPLIFIED: Real Ethereum refunds up to 1/5 of gas used for SSTORE clears`.

## SHA3 for Mapping Keys

SimpleToken uses `mapping(address => uint256)`. Solidity computes the storage slot for `balances[addr]` as:

```python
slot = keccak256(left_pad_32(addr) + left_pad_32(mapping_slot_number))
```

For `balances` at slot 0: `keccak256(pad32(addr) + pad32(0))`

The SHA3 opcode is critical for this. It reads from memory: `SHA3(offset, length)` computes `keccak256(memory[offset:offset+length])`.

## Code Examples

### Contract Address Computation
```python
from ethereum.crypto import keccak256
from ethereum.encoding.rlp import rlp_encode, int_to_rlp_bytes

def compute_contract_address(sender: bytes, nonce: int) -> bytes:
    """Compute the address for a newly deployed contract.

    address = keccak256(rlp([sender, nonce]))[12:]

    Args:
        sender: 20-byte sender address.
        nonce: Sender's nonce at time of deployment.

    Returns:
        20-byte contract address.
    """
    encoded = rlp_encode([sender, int_to_rlp_bytes(nonce)])
    return keccak256(encoded)[12:]  # Last 20 bytes
```

### Function Selector (ABI Dispatch)
```python
# Compiled Solidity uses the first 4 bytes of calldata as a function selector:
# selector = keccak256(b"increment()")[0:4]
# selector = keccak256(b"getCount()")[0:4]
# selector = keccak256(b"transfer(address,uint256)")[0:4]
# selector = keccak256(b"balanceOf(address)")[0:4]

# The compiled bytecode compares calldata[:4] against these selectors using:
# CALLDATALOAD(0) -> PUSH4 selector -> EQ -> JUMPI(handler)
```

### EVM Memory Model
```python
class Memory:
    """Byte-addressable, word-aligned expandable memory.

    # SIMPLIFIED: No quadratic gas cost for expansion.
    # Real Ethereum charges: 3 * num_words + num_words^2 / 512
    """
    def __init__(self):
        self._data = bytearray()

    def _expand_to(self, offset: int, size: int):
        """Expand memory if access goes beyond current size."""
        needed = offset + size
        if needed > len(self._data):
            # Expand to next 32-byte word boundary
            new_size = ((needed + 31) // 32) * 32
            self._data.extend(b'\x00' * (new_size - len(self._data)))

    def load(self, offset: int) -> int:
        """Load 32-byte word from memory as uint256."""
        self._expand_to(offset, 32)
        return int.from_bytes(self._data[offset:offset+32], 'big')

    def store(self, offset: int, value: int):
        """Store uint256 as 32-byte big-endian word."""
        self._expand_to(offset, 32)
        self._data[offset:offset+32] = value.to_bytes(32, 'big')

    def store8(self, offset: int, value: int):
        """Store single byte."""
        self._expand_to(offset, 1)
        self._data[offset] = value & 0xFF
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Flat SSTORE cost | EIP-2200 three-value model | Istanbul (Dec 2019) | We use flat cost with `# SIMPLIFIED:` |
| Flat CALL cost | EIP-2929 cold/warm access | Berlin (Apr 2021) | We use flat cost with `# SIMPLIFIED:` |
| Unlimited gas forwarding | EIP-150 (63/64 rule) | Tangerine Whistle (Oct 2016) | We use full remaining gas with `# SIMPLIFIED:` |
| No max init code size | EIP-3860 (48KB limit) | Shanghai (Apr 2023) | We skip the limit with `# SIMPLIFIED:` |
| Simple memory pricing | Quadratic memory cost | Always (Yellow Paper) | We use linear cost with `# SIMPLIFIED:` |

## Dependency on Phase 2

Phase 3 depends on these Phase 2 artifacts (must exist before execution):
- `Account` dataclass with `balance`, `nonce`, `code_hash`, `storage` fields
- `WorldState` with `get_account()`, `set_account()`, `snapshot()`, `revert()` methods
- `Transaction` dataclass with `nonce`, `to`, `value`, `data`, `gas_limit`, `gas_price`, signature fields
- `Block` structure (for block gas limit context)
- Signing/recovery integration with Phase 1 crypto

## Open Questions

1. **Exact bytecode for Counter and SimpleToken**
   - What we know: The opcodes needed can be derived from the Solidity source
   - What's unclear: Whether to hand-compile or use solc to get exact bytecode
   - Recommendation: Hand-compile minimal bytecode for Counter; use solc output as reference for SimpleToken. Phase 4 will provide the actual bytecode -- Phase 3 just needs the EVM to support the required opcodes.

2. **CALL depth limit**
   - What we know: Real Ethereum limits call depth to 1024
   - What's unclear: Whether Counter/SimpleToken will trigger any nested calls
   - Recommendation: Implement a call depth counter with limit 1024, but it likely won't be exercised by these simple contracts.

## Sources

### Primary (HIGH confidence)
- Ethereum Yellow Paper, Appendix H: EVM opcode definitions and gas costs
- Ethereum Yellow Paper, Section 6: Transaction validation order
- Ethereum Yellow Paper, Section 7: Contract creation
- [EIP-2200](https://eips.ethereum.org/EIPS/eip-2200): SSTORE gas cost changes (reference for `# SIMPLIFIED:` annotations)
- [EIP-150](https://eips.ethereum.org/EIPS/eip-150): Gas cost changes for IO-heavy operations
- [EIP-2929](https://eips.ethereum.org/EIPS/eip-2929): Cold/warm access lists

### Secondary (MEDIUM confidence)
- [py-evm](https://github.com/ethereum/py-evm): Reference Python implementation (official Ethereum Foundation)
- [evm.codes](https://www.evm.codes/): Interactive opcode reference with gas costs

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Opcode selection: HIGH -- derived directly from Counter and SimpleToken contract requirements
- Gas model: HIGH -- Yellow Paper provides canonical costs; simplifications are well-documented
- Architecture: HIGH -- standard interpreter pattern used by all EVM implementations
- Transaction validation: HIGH -- Yellow Paper Section 6 is explicit about order

**Research date:** 2026-02-19
**Valid until:** 2026-03-19 (stable domain; EVM spec changes infrequently)

## RESEARCH COMPLETE
