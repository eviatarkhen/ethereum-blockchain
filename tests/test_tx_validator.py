"""Tests for transaction validation in Yellow Paper order."""

import os
import pytest
from eth_keys import keys as eth_keys

from ethereum.state.account import Account
from ethereum.state.world_state import WorldState
from ethereum.transactions.transaction import Transaction, sign_transaction
from ethereum.core.tx_validator import validate_transaction, calculate_intrinsic_gas
from ethereum.core.exceptions import (
    InvalidNonce,
    InsufficientBalance,
    ExceedsBlockGasLimit,
    IntrinsicGasTooLow,
    InvalidSignature,
)


# === Test helpers ===


def _make_key():
    """Generate a private key and derive address."""
    private_key = eth_keys.PrivateKey(os.urandom(32))
    address = private_key.public_key.to_canonical_address()
    return private_key, address


def _make_world_state(accounts: dict) -> WorldState:
    """Create WorldState with given address -> Account mapping."""
    ws = WorldState()
    for addr, account in accounts.items():
        ws.set_account(addr, account)
    return ws


def _make_signed_tx(private_key, nonce=0, to=b"\x02" * 20, value=0,
                    data=b"", gas_limit=21000, gas_price=1):
    """Create and sign a transaction."""
    tx = Transaction(
        nonce=nonce,
        gas_price=gas_price,
        gas=gas_limit,
        to=to,
        value=value,
        data=data,
    )
    return sign_transaction(tx, private_key)


# === Validation Order Tests ===


def test_valid_transaction_returns_sender():
    """Valid transaction passes all checks and returns sender address."""
    key, sender = _make_key()
    ws = _make_world_state({sender: Account(balance=1_000_000, nonce=0)})
    tx = _make_signed_tx(key, nonce=0, value=100, gas_limit=21000, gas_price=1)

    result = validate_transaction(tx, ws, block_gas_limit=10_000_000)
    assert result == sender


def test_invalid_nonce_rejected():
    """Wrong nonce raises InvalidNonce."""
    key, sender = _make_key()
    ws = _make_world_state({sender: Account(balance=1_000_000, nonce=5)})
    tx = _make_signed_tx(key, nonce=3, gas_limit=21000)

    with pytest.raises(InvalidNonce) as exc_info:
        validate_transaction(tx, ws, block_gas_limit=10_000_000)
    assert exc_info.value.expected == 5
    assert exc_info.value.got == 3


def test_insufficient_balance_rejected():
    """Balance < value + gas*gasPrice raises InsufficientBalance."""
    key, sender = _make_key()
    ws = _make_world_state({sender: Account(balance=100, nonce=0)})
    tx = _make_signed_tx(key, nonce=0, value=50, gas_limit=21000, gas_price=1)
    # Total cost = 50 + 21000 = 21050 > 100

    with pytest.raises(InsufficientBalance) as exc_info:
        validate_transaction(tx, ws, block_gas_limit=10_000_000)
    assert exc_info.value.required == 21050
    assert exc_info.value.available == 100


def test_exceeds_block_gas_limit_rejected():
    """Gas limit exceeding block gas limit raises ExceedsBlockGasLimit."""
    key, sender = _make_key()
    ws = _make_world_state({sender: Account(balance=100_000_000, nonce=0)})
    tx = _make_signed_tx(key, nonce=0, gas_limit=20_000_000)

    with pytest.raises(ExceedsBlockGasLimit) as exc_info:
        validate_transaction(tx, ws, block_gas_limit=10_000_000)
    assert exc_info.value.tx_gas == 20_000_000
    assert exc_info.value.block_limit == 10_000_000


def test_intrinsic_gas_too_low_rejected():
    """Gas limit below intrinsic gas raises IntrinsicGasTooLow."""
    key, sender = _make_key()
    ws = _make_world_state({sender: Account(balance=1_000_000, nonce=0)})
    tx = _make_signed_tx(key, nonce=0, gas_limit=100)

    with pytest.raises(IntrinsicGasTooLow) as exc_info:
        validate_transaction(tx, ws, block_gas_limit=10_000_000)
    assert exc_info.value.required == 21000
    assert exc_info.value.provided == 100


def test_validation_order_nonce_before_balance():
    """Nonce checked before balance (Yellow Paper order).

    If nonce is wrong AND balance is insufficient, InvalidNonce
    should be raised first — not InsufficientBalance.
    """
    key, sender = _make_key()
    ws = _make_world_state({sender: Account(balance=0, nonce=5)})
    tx = _make_signed_tx(key, nonce=0, value=1000, gas_limit=21000, gas_price=1)

    with pytest.raises(InvalidNonce):  # NOT InsufficientBalance
        validate_transaction(tx, ws, block_gas_limit=10_000_000)


def test_unsigned_transaction_rejected():
    """Unsigned transaction raises InvalidSignature."""
    tx = Transaction(
        nonce=0, gas_price=1, gas=21000,
        to=b"\x02" * 20, value=0, data=b"",
    )
    ws = _make_world_state({})

    with pytest.raises(InvalidSignature):
        validate_transaction(tx, ws, block_gas_limit=10_000_000)


# === Intrinsic Gas Tests ===


def test_intrinsic_gas_empty():
    """Empty calldata costs just the base 21000."""
    assert calculate_intrinsic_gas(b"") == 21000


def test_intrinsic_gas_zero_bytes():
    """Zero bytes cost 4 gas each."""
    assert calculate_intrinsic_gas(b"\x00\x00") == 21000 + 8


def test_intrinsic_gas_non_zero_bytes():
    """Non-zero bytes cost 16 gas each."""
    assert calculate_intrinsic_gas(b"\x01\x02") == 21000 + 32


def test_intrinsic_gas_mixed():
    """Mixed zero and non-zero bytes."""
    assert calculate_intrinsic_gas(b"\x00\x01") == 21000 + 4 + 16
