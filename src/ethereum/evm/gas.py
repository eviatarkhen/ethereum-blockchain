"""EVM gas costs and constants.

Gas is Ethereum's mechanism for metering computation. Every opcode
has a cost, and transactions specify a gas limit. If execution exceeds
the limit, the transaction is reverted.

# SIMPLIFIED: Flat gas costs per opcode. Real Ethereum has dynamic costs:
# - SSTORE: EIP-2200 three-value model (2200/5000/20000 depending on current/new value)
# - SLOAD: EIP-2929 cold/warm (2100 cold, 100 warm)
# - CALL: EIP-2929 cold/warm + value transfer + new account costs
# - Memory: Quadratic cost (3 * words + words^2 / 512)
# - SHA3: 30 + 6 per 32-byte word
# - EXP: 10 + 50 per byte of exponent
# All simplified costs are marked with comments explaining real behavior.
"""

from ethereum.evm.opcodes import *

# === Constants ===
MAX_UINT256 = 2**256 - 1
"""Maximum value for a 256-bit unsigned integer."""

MOD_VALUE = 2**256
"""Modulus for 256-bit arithmetic. All EVM arithmetic wraps at this value."""

MAX_STACK_DEPTH = 1024
"""Maximum stack depth. Real Ethereum also uses 1024."""

INTRINSIC_GAS_TX = 21000
"""Base gas cost for any transaction.

This is the minimum gas required for a transaction to be valid,
even if it does nothing. Covers signature verification and state access.
"""

GAS_ZERO_BYTE = 4
"""Gas cost per zero byte of calldata.

Zero bytes are cheaper because they compress well in RLP encoding
and are common in ABI-encoded data (padding).
"""

GAS_NON_ZERO_BYTE = 16
"""Gas cost per non-zero byte of calldata.

Non-zero bytes are more expensive because they take more space
in the transaction data.
"""

GAS_CREATE = 32000
"""Gas cost for CREATE opcode (contract deployment)."""

GAS_SSTORE = 5000
"""Gas cost for SSTORE opcode.

# SIMPLIFIED: Flat 5000 gas for any SSTORE operation.
# Real Ethereum (EIP-2200) uses a three-value model:
# - 2200 gas: value unchanged (no-op)
# - 5000 gas: zero -> non-zero (first write)
# - 20000 gas: non-zero -> non-zero (modify existing)
# - With refund up to 1/5 of gas used for clearing to zero.
"""

GAS_SLOAD = 100
"""Gas cost for SLOAD opcode.

# SIMPLIFIED: Flat 100 gas for any SLOAD.
# Real Ethereum (EIP-2929) uses cold/warm model:
# - 2100 gas: first access to a storage slot (cold)
# - 100 gas: subsequent accesses in same transaction (warm)
"""

GAS_CALL_BASE = 100
"""Base gas cost for CALL opcode.

# SIMPLIFIED: Flat 100 gas base cost.
# Real Ethereum (EIP-2929) charges:
# - 2600 gas for cold address access
# - 100 gas for warm address access
# - 9000 extra for value transfer to new account
# - 25000 extra for creating new account with value
"""

GAS_CODE_DEPOSIT = 200
"""Gas per byte for storing contract code after CREATE.

This is the cost of permanently storing the runtime bytecode.
"""


# === Gas Cost Table ===
# Maps opcode -> gas cost. Used by EVM._consume_gas().

GAS_COSTS: dict[int, int] = {
    # Stop and arithmetic
    OP_STOP: 0,
    OP_ADD: 3,
    OP_MUL: 5,
    OP_SUB: 3,
    OP_DIV: 5,
    OP_MOD: 5,
    OP_EXP: 10,       # SIMPLIFIED: Flat 10. Real: 10 + 50 * byte_length(exponent)

    # Comparison
    OP_LT: 3,
    OP_GT: 3,
    OP_EQ: 3,
    OP_ISZERO: 3,

    # Bitwise
    OP_AND: 3,
    OP_OR: 3,
    OP_NOT: 3,

    # Hashing
    OP_SHA3: 30,       # SIMPLIFIED: Flat 30. Real: 30 + 6 * ceil(size / 32)

    # Environment
    OP_ADDRESS: 2,
    OP_CALLER: 2,
    OP_CALLVALUE: 2,
    OP_CALLDATALOAD: 3,
    OP_CALLDATASIZE: 2,
    OP_CALLDATACOPY: 3,  # SIMPLIFIED: Flat 3. Real: 3 + 3 * ceil(size / 32)
    OP_CODESIZE: 2,
    OP_CODECOPY: 3,    # SIMPLIFIED: Flat 3. Real: 3 + 3 * ceil(size / 32)

    # Stack, memory, storage
    OP_POP: 2,
    OP_MLOAD: 3,       # SIMPLIFIED: Flat 3. Real: 3 + memory expansion cost
    OP_MSTORE: 3,      # SIMPLIFIED: Flat 3. Real: 3 + memory expansion cost
    OP_MSTORE8: 3,     # SIMPLIFIED: Flat 3. Real: 3 + memory expansion cost
    OP_SLOAD: GAS_SLOAD,
    OP_SSTORE: GAS_SSTORE,

    # Flow control
    OP_JUMP: 8,
    OP_JUMPI: 10,
    OP_MSIZE: 2,
    OP_GAS: 2,
    OP_JUMPDEST: 1,

    # Contract
    OP_CREATE: GAS_CREATE,
    OP_CALL: GAS_CALL_BASE,

    # Return
    OP_RETURN: 0,
    OP_REVERT: 0,
    OP_INVALID: 0,     # Consumes ALL remaining gas (handled specially)
}

# All PUSHn opcodes cost 3 gas
for i in range(32):
    GAS_COSTS[OP_PUSH1 + i] = 3

# All DUPn opcodes cost 3 gas
for i in range(16):
    GAS_COSTS[OP_DUP1 + i] = 3

# All SWAPn opcodes cost 3 gas
for i in range(16):
    GAS_COSTS[OP_SWAP1 + i] = 3


def calculate_intrinsic_gas(data: bytes) -> int:
    """Calculate the intrinsic gas cost of a transaction.

    Intrinsic gas = base cost + per-byte calldata cost.

    This is the minimum gas a transaction must provide, consumed before
    any EVM execution begins. Ensures even failed transactions pay for
    the cost of signature verification and state updates.

    Args:
        data: Transaction calldata (or init code for contract creation).

    Returns:
        Intrinsic gas cost in gas units.

    # SIMPLIFIED: No EIP-2930 access list cost.
    # SIMPLIFIED: No CREATE cost differential (real Ethereum charges
    # 53000 base for contract creation vs 21000 for regular tx).
    """
    gas = INTRINSIC_GAS_TX

    for byte in data:
        if byte == 0:
            gas += GAS_ZERO_BYTE
        else:
            gas += GAS_NON_ZERO_BYTE

    return gas
