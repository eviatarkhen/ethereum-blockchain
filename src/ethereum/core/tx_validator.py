"""Transaction validation in Yellow Paper order.

Validates transactions in the exact order specified by the
Ethereum Yellow Paper Section 6. This ordering is important:
Ethereum nodes reject transactions at the first failure point.

Validation order:
1. Recover sender from signature (proves authorization)
2. Verify nonce (prevents replay, ensures ordering)
3. Check balance (can sender afford this transaction?)
4. Check block gas limit (fits in this block?)
5. Check intrinsic gas (meets minimum gas requirement?)

# SIMPLIFIED: No EIP-155 chain ID in signature.
# Real Ethereum includes chain ID to prevent cross-chain replay attacks.
# SIMPLIFIED: No EIP-1559 base fee / priority fee.
# SIMPLIFIED: No EIP-2930 access lists.
"""

from ethereum.transactions.transaction import Transaction, recover_sender as _recover_sender
from ethereum.core.exceptions import (
    InvalidSignature,
    InvalidNonce,
    InsufficientBalance,
    ExceedsBlockGasLimit,
    IntrinsicGasTooLow,
)


def calculate_intrinsic_gas(data: bytes) -> int:
    """Calculate the intrinsic gas cost of a transaction.

    Intrinsic gas = 21000 base + 4 per zero byte + 16 per non-zero byte.

    This is the minimum gas a transaction must provide, consumed before
    any EVM execution begins.

    Args:
        data: Transaction calldata (or init code for contract creation).

    Returns:
        Intrinsic gas cost in gas units.

    # SIMPLIFIED: No EIP-2930 access list cost.
    # SIMPLIFIED: No CREATE cost differential (real: 53000 vs 21000).
    """
    gas = 21000

    for byte_val in data:
        if byte_val == 0:
            gas += 4   # Zero byte: 4 gas
        else:
            gas += 16  # Non-zero byte: 16 gas

    return gas


def validate_transaction(tx: Transaction, world_state, block_gas_limit: int) -> bytes:
    """Validate a transaction per Yellow Paper Section 6.

    Checks in order (stops at first failure):
    1. Signature is valid and sender can be recovered
    2. Sender nonce matches transaction nonce
    3. Sender balance >= value + gas_limit * gas_price
    4. Transaction gas_limit <= block gas limit
    5. Intrinsic gas <= transaction gas_limit

    This is the gateway to execution: only transactions that pass
    all five checks are allowed to modify state.

    Args:
        tx: Signed transaction to validate.
        world_state: Current world state (for nonce and balance checks).
        block_gas_limit: Maximum gas allowed in the current block.

    Returns:
        20-byte sender address (recovered from signature).

    Raises:
        InvalidSignature: Signature invalid or sender unrecoverable.
        InvalidNonce: Transaction nonce doesn't match account nonce.
        InsufficientBalance: Can't cover value + gas cost.
        ExceedsBlockGasLimit: Gas limit exceeds block limit.
        IntrinsicGasTooLow: Gas limit below intrinsic gas.
    """
    # Step 1: Recover sender from signature
    try:
        sender_address = _recover_sender(tx)
    except Exception as e:
        raise InvalidSignature(reason=str(e))

    # Step 2: Nonce check
    sender_account = world_state.get_account(sender_address)
    if sender_account.nonce != tx.nonce:
        raise InvalidNonce(expected=sender_account.nonce, got=tx.nonce)

    # Step 3: Balance check
    # Total cost = value to transfer + maximum gas cost
    total_cost = tx.value + (tx.gas * tx.gas_price)
    if sender_account.balance < total_cost:
        raise InsufficientBalance(required=total_cost, available=sender_account.balance)

    # Step 4: Block gas limit check
    if tx.gas > block_gas_limit:
        raise ExceedsBlockGasLimit(tx_gas=tx.gas, block_limit=block_gas_limit)

    # Step 5: Intrinsic gas check
    intrinsic = calculate_intrinsic_gas(tx.data)
    if tx.gas < intrinsic:
        raise IntrinsicGasTooLow(required=intrinsic, provided=tx.gas)

    return sender_address
