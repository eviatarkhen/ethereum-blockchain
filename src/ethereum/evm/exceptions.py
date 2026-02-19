"""EVM exception classes.

Each exception type represents a specific EVM error condition.
All exceptions store their arguments as attributes so a developer
can inspect them in the debugger at the point of failure.

Usage:
    try:
        evm.execute()
    except OutOfGas as e:
        print(f"Needed {e.needed} gas, had {e.remaining}")
"""


class EVMError(Exception):
    """Base exception for all EVM errors.

    All EVM-specific exceptions inherit from this class so callers
    can catch any EVM error with a single except clause.
    """
    pass


class OutOfGas(EVMError):
    """Raised when an opcode costs more gas than is remaining.

    This is the most common execution failure. When this occurs,
    the entire transaction is reverted (state changes undone),
    but the gas is still consumed.

    Attributes:
        needed: Gas cost of the opcode that failed.
        remaining: Gas remaining when the opcode was attempted.
    """

    def __init__(self, needed: int, remaining: int):
        self.needed = needed
        self.remaining = remaining
        super().__init__(
            f"Out of gas: needed {needed}, only {remaining} remaining"
        )


class StackUnderflow(EVMError):
    """Raised when an opcode tries to pop more items than the stack has.

    For example, ADD needs 2 items but the stack is empty.

    Attributes:
        needed: Number of items the opcode requires.
        actual: Number of items actually on the stack.
    """

    def __init__(self, needed: int, actual: int):
        self.needed = needed
        self.actual = actual
        super().__init__(
            f"Stack underflow: need {needed} items, have {actual}"
        )


class StackOverflow(EVMError):
    """Raised when pushing would exceed the maximum stack depth (1024).

    Attributes:
        max_depth: Maximum allowed stack depth (1024).
    """

    def __init__(self, max_depth: int = 1024):
        self.max_depth = max_depth
        super().__init__(
            f"Stack overflow: maximum depth {max_depth} exceeded"
        )


class InvalidJumpDestination(EVMError):
    """Raised when JUMP/JUMPI targets a position without JUMPDEST.

    The EVM requires every jump target to be marked with a JUMPDEST
    opcode (0x5B). This prevents jumping into the middle of a PUSH
    instruction's data bytes.

    Attributes:
        destination: The invalid jump target (program counter value).
    """

    def __init__(self, destination: int):
        self.destination = destination
        super().__init__(
            f"Invalid jump destination: 0x{destination:04x} ({destination}) "
            f"is not a JUMPDEST"
        )


class InvalidOpcode(EVMError):
    """Raised when the EVM encounters an unsupported opcode.

    Attributes:
        opcode: The unsupported opcode byte.
        pc: Program counter where the invalid opcode was found.
    """

    def __init__(self, opcode: int, pc: int):
        self.opcode = opcode
        self.pc = pc
        super().__init__(
            f"Invalid opcode: 0x{opcode:02X} at PC={pc}"
        )


class Revert(EVMError):
    """Raised when execution hits the REVERT opcode.

    REVERT stops execution, returns data, and reverts state changes,
    but refunds remaining gas (unlike INVALID which consumes all gas).

    Attributes:
        return_data: Data returned by the REVERT opcode.
    """

    def __init__(self, return_data: bytes = b""):
        self.return_data = return_data
        super().__init__(
            f"Execution reverted (return_data: {len(return_data)} bytes)"
        )
