"""Tests for state transition function."""

import os
import pytest
from eth_keys import keys as eth_keys

from ethereum.state.account import Account
from ethereum.state.world_state import WorldState
from ethereum.transactions.transaction import Transaction, sign_transaction
from ethereum.core.state_transition import apply_transaction
from ethereum.evm.opcodes import OP_PUSH1, OP_SSTORE, OP_STOP, OP_JUMPDEST, OP_JUMP


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


# === Value Transfer Tests ===


def test_value_transfer_updates_balances():
    """Simple ETH transfer: sender balance decreases, recipient increases."""
    key, sender = _make_key()
    recipient = b"\x02" * 20
    ws = _make_world_state({
        sender: Account(balance=1_000_000, nonce=0),
        recipient: Account(balance=500, nonce=0),
    })
    tx = _make_signed_tx(key, to=recipient, value=1000,
                         gas_limit=21000, gas_price=1, nonce=0)

    result = apply_transaction(tx, ws, block_gas_limit=10_000_000)

    assert result.success is True
    sender_acct = ws.get_account(sender)
    recipient_acct = ws.get_account(recipient)
    # Sender loses: value (1000) + gas_used * gas_price (21000)
    assert sender_acct.balance == 1_000_000 - 1000 - 21000
    # Recipient gains exactly the value
    assert recipient_acct.balance == 500 + 1000


def test_value_transfer_increments_nonce():
    """Sender nonce increments after successful transfer."""
    key, sender = _make_key()
    recipient = b"\x02" * 20
    ws = _make_world_state({
        sender: Account(balance=1_000_000, nonce=0),
        recipient: Account(balance=0, nonce=0),
    })
    tx = _make_signed_tx(key, to=recipient, value=100,
                         gas_limit=21000, gas_price=1, nonce=0)

    apply_transaction(tx, ws, block_gas_limit=10_000_000)
    assert ws.get_account(sender).nonce == 1


def test_gas_refund():
    """Unused gas is refunded to sender."""
    key, sender = _make_key()
    recipient = b"\x02" * 20
    ws = _make_world_state({
        sender: Account(balance=1_000_000, nonce=0),
        recipient: Account(balance=0, nonce=0),
    })
    tx = _make_signed_tx(key, to=recipient, value=0,
                         gas_limit=50000, gas_price=1, nonce=0)

    result = apply_transaction(tx, ws, block_gas_limit=10_000_000)

    # For a simple transfer, only intrinsic gas is consumed
    sender_balance = ws.get_account(sender).balance
    # gas_used should be just intrinsic (21000), rest refunded
    assert result.gas_used == 21000
    assert sender_balance == 1_000_000 - 21000


def test_transfer_to_new_account_creates_it():
    """Sending to a non-existent account creates it."""
    key, sender = _make_key()
    new_addr = b"\x05" * 20
    ws = _make_world_state({
        sender: Account(balance=1_000_000, nonce=0),
    })
    tx = _make_signed_tx(key, to=new_addr, value=1000,
                         gas_limit=21000, gas_price=1, nonce=0)

    result = apply_transaction(tx, ws, block_gas_limit=10_000_000)

    assert result.success is True
    assert ws.get_account(new_addr).balance == 1000


def test_result_gas_accounting():
    """gas_used + gas_remaining = gas_limit."""
    key, sender = _make_key()
    recipient = b"\x02" * 20
    ws = _make_world_state({
        sender: Account(balance=1_000_000, nonce=0),
        recipient: Account(balance=0, nonce=0),
    })
    tx = _make_signed_tx(key, to=recipient, value=0,
                         gas_limit=50000, gas_price=1, nonce=0)

    result = apply_transaction(tx, ws, block_gas_limit=10_000_000)

    assert result.gas_used + result.gas_remaining == 50000


# === Contract Call Tests ===


def test_contract_call_executes_bytecode():
    """Calling a contract with code executes its bytecode."""
    key, sender = _make_key()
    contract = b"\x03" * 20
    # Bytecode: PUSH1 42 PUSH1 0 SSTORE STOP (store 42 at slot 0)
    code = bytes([OP_PUSH1, 42, OP_PUSH1, 0, OP_SSTORE, OP_STOP])
    ws = _make_world_state({
        sender: Account(balance=1_000_000, nonce=0),
        contract: Account(balance=0, nonce=0, code=code),
    })
    tx = _make_signed_tx(key, to=contract, value=0,
                         gas_limit=100000, gas_price=1, nonce=0)

    result = apply_transaction(tx, ws, block_gas_limit=10_000_000)

    assert result.success is True
    # Storage should have been updated
    assert ws.get_storage(contract, 0) == 42


def test_out_of_gas_reverts_value_transfer():
    """Out-of-gas during contract execution reverts state but consumes gas."""
    key, sender = _make_key()
    contract = b"\x03" * 20
    # Infinite loop bytecode: JUMPDEST PUSH1 0 JUMP
    code = bytes([OP_JUMPDEST, OP_PUSH1, 0, OP_JUMP])
    ws = _make_world_state({
        sender: Account(balance=1_000_000, nonce=0),
        contract: Account(balance=0, nonce=0, code=code),
    })
    tx = _make_signed_tx(key, to=contract, value=500,
                         gas_limit=30000, gas_price=1, nonce=0)

    result = apply_transaction(tx, ws, block_gas_limit=10_000_000)

    assert result.success is False
    # Contract balance should NOT have increased (reverted)
    assert ws.get_account(contract).balance == 0
    # Sender nonce still increments
    assert ws.get_account(sender).nonce == 1
    # Sender loses all gas (30000)
    assert ws.get_account(sender).balance == 1_000_000 - 30000


def test_contract_call_with_value():
    """Contract call with value transfers ETH and executes code."""
    key, sender = _make_key()
    contract = b"\x03" * 20
    code = bytes([OP_STOP])
    ws = _make_world_state({
        sender: Account(balance=1_000_000, nonce=0),
        contract: Account(balance=0, nonce=0, code=code),
    })
    tx = _make_signed_tx(key, to=contract, value=5000,
                         gas_limit=100000, gas_price=1, nonce=0)

    result = apply_transaction(tx, ws, block_gas_limit=10_000_000)

    assert result.success is True
    assert ws.get_account(contract).balance == 5000


def test_multiple_transactions_sequential():
    """Two transactions from same sender execute correctly."""
    key, sender = _make_key()
    recipient = b"\x02" * 20
    ws = _make_world_state({
        sender: Account(balance=1_000_000, nonce=0),
        recipient: Account(balance=0, nonce=0),
    })

    # First tx
    tx1 = _make_signed_tx(key, to=recipient, value=100,
                          gas_limit=21000, gas_price=1, nonce=0)
    result1 = apply_transaction(tx1, ws, block_gas_limit=10_000_000)
    assert result1.success is True

    # Second tx (nonce incremented)
    tx2 = _make_signed_tx(key, to=recipient, value=200,
                          gas_limit=21000, gas_price=1, nonce=1)
    result2 = apply_transaction(tx2, ws, block_gas_limit=10_000_000)
    assert result2.success is True

    assert ws.get_account(sender).nonce == 2
    assert ws.get_account(recipient).balance == 300
