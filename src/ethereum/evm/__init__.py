"""Ethereum Virtual Machine (EVM).

Stack-based virtual machine that executes bytecode with ~25 opcodes,
tracks gas consumption, and enforces gas limits.

# SIMPLIFIED: ~25 opcodes vs ~140+ in real Ethereum.
# Only implements opcodes needed for Counter and SimpleToken contracts.
"""

from ethereum.evm.vm import EVM, ExecutionContext, ExecutionResult
from ethereum.evm.exceptions import (
    EVMError,
    OutOfGas,
    StackUnderflow,
    StackOverflow,
    InvalidJumpDestination,
    InvalidOpcode,
    Revert,
)

__all__ = [
    "EVM",
    "ExecutionContext",
    "ExecutionResult",
    "EVMError",
    "OutOfGas",
    "StackUnderflow",
    "StackOverflow",
    "InvalidJumpDestination",
    "InvalidOpcode",
    "Revert",
]
