"""Tests for contract address computation and CREATE opcode."""

import os
import pytest
from eth_keys import keys as eth_keys

from ethereum.core.address import compute_contract_address
from ethereum.crypto.hashing import keccak256
from ethereum.encoding.rlp import rlp_encode, int_to_rlp_bytes
from ethereum.state.account import Account
from ethereum.state.world_state import WorldState
from ethereum.transactions.transaction import Transaction, sign_transaction
from ethereum.core.state_transition import apply_transaction
from ethereum.evm.vm import EVM, ExecutionContext, ExecutionResult
from ethereum.evm.opcodes import (
    OP_PUSH1, OP_MSTORE8, OP_RETURN, OP_STOP, OP_SSTORE,
    OP_PUSH20, OP_CREATE,
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


# === Address computation tests ===


def test_contract_address_deterministic():
    """Same sender + nonce always produces same address."""
    sender = b'\x01' * 20
    addr1 = compute_contract_address(sender, 0)
    addr2 = compute_contract_address(sender, 0)
    assert addr1 == addr2


def test_contract_address_is_20_bytes():
    """Contract address is exactly 20 bytes."""
    addr = compute_contract_address(b'\x01' * 20, 0)
    assert len(addr) == 20


def test_contract_address_different_nonce():
    """Different nonces produce different addresses."""
    sender = b'\x01' * 20
    addr0 = compute_contract_address(sender, 0)
    addr1 = compute_contract_address(sender, 1)
    assert addr0 != addr1


def test_contract_address_different_sender():
    """Different senders produce different addresses."""
    addr0 = compute_contract_address(b'\x01' * 20, 0)
    addr1 = compute_contract_address(b'\x02' * 20, 0)
    assert addr0 != addr1


def test_contract_address_matches_manual():
    """Address matches manual keccak256(rlp([sender, nonce]))[12:]."""
    sender = b'\xd6\x1b' + b'\x00' * 18
    nonce = 1
    encoded = rlp_encode([sender, int_to_rlp_bytes(nonce)])
    expected = keccak256(encoded)[12:]
    assert compute_contract_address(sender, nonce) == expected


def test_contract_address_nonce_zero():
    """Nonce 0 produces a valid address (RLP of 0 is empty bytes)."""
    sender = b'\xaa' * 20
    addr = compute_contract_address(sender, 0)
    # Manual check
    encoded = rlp_encode([sender, int_to_rlp_bytes(0)])
    expected = keccak256(encoded)[12:]
    assert addr == expected


# === CREATE via state transition tests ===


def test_create_via_state_transition():
    """apply_transaction with to=b'' deploys a contract."""
    key, sender = _make_key()
    ws = _make_world_state({
        sender: Account(balance=1_000_000, nonce=0),
    })

    # Init code: PUSH1 0x42 PUSH1 0 MSTORE8 PUSH1 1 PUSH1 0 RETURN
    # Returns 1 byte (0x42) as runtime code
    init_code = bytes([
        OP_PUSH1, 0x42, OP_PUSH1, 0, OP_MSTORE8,
        OP_PUSH1, 1, OP_PUSH1, 0, OP_RETURN,
    ])

    tx = _make_signed_tx(key, to=b"", value=0, data=init_code,
                         gas_limit=100000, gas_price=1, nonce=0)

    result = apply_transaction(tx, ws, block_gas_limit=10_000_000)

    assert result.success is True
    # Compute expected contract address (nonce=0 before tx increments it)
    contract_addr = compute_contract_address(sender, 0)
    assert result.contract_address == contract_addr
    contract_acct = ws.get_account(contract_addr)
    assert contract_acct.code == bytes([0x42])


def test_create_with_value_endows_contract():
    """CREATE with value transfers ETH to the new contract."""
    key, sender = _make_key()
    ws = _make_world_state({
        sender: Account(balance=1_000_000, nonce=0),
    })

    # Simple init code that returns empty runtime code
    init_code = bytes([OP_PUSH1, 0, OP_PUSH1, 0, OP_RETURN])

    tx = _make_signed_tx(key, to=b"", value=5000, data=init_code,
                         gas_limit=100000, gas_price=1, nonce=0)

    result = apply_transaction(tx, ws, block_gas_limit=10_000_000)

    assert result.success is True
    contract_addr = compute_contract_address(sender, 0)
    assert ws.get_account(contract_addr).balance == 5000


def test_create_out_of_gas_reverts():
    """CREATE with insufficient gas fails."""
    key, sender = _make_key()
    ws = _make_world_state({
        sender: Account(balance=1_000_000, nonce=0),
    })

    # Init code that tries to do a lot: store in many slots
    # Just make the gas too low for the init code to run
    init_code = bytes([
        OP_PUSH1, 42, OP_PUSH1, 0, OP_SSTORE,
        OP_PUSH1, 42, OP_PUSH1, 1, OP_SSTORE,
        OP_PUSH1, 42, OP_PUSH1, 2, OP_SSTORE,
        OP_PUSH1, 42, OP_PUSH1, 3, OP_SSTORE,
        OP_PUSH1, 42, OP_PUSH1, 4, OP_SSTORE,
        OP_PUSH1, 0, OP_PUSH1, 0, OP_RETURN,
    ])

    # Gas limit barely covers intrinsic gas, not enough for execution
    tx = _make_signed_tx(key, to=b"", value=0, data=init_code,
                         gas_limit=21500, gas_price=1, nonce=0)

    result = apply_transaction(tx, ws, block_gas_limit=10_000_000)

    assert result.success is False
    # Contract should NOT exist
    contract_addr = compute_contract_address(sender, 0)
    contract_acct = ws.get_account(contract_addr)
    assert contract_acct.code == b""


def test_create_nonce_increments():
    """Sender nonce increments after contract creation."""
    key, sender = _make_key()
    ws = _make_world_state({
        sender: Account(balance=1_000_000, nonce=0),
    })

    init_code = bytes([OP_PUSH1, 0, OP_PUSH1, 0, OP_RETURN])
    tx = _make_signed_tx(key, to=b"", value=0, data=init_code,
                         gas_limit=100000, gas_price=1, nonce=0)

    apply_transaction(tx, ws, block_gas_limit=10_000_000)
    assert ws.get_account(sender).nonce == 1


def test_create_returns_contract_address():
    """Transaction result includes the contract address."""
    key, sender = _make_key()
    ws = _make_world_state({
        sender: Account(balance=1_000_000, nonce=0),
    })

    init_code = bytes([OP_PUSH1, 0x99, OP_PUSH1, 0, OP_MSTORE8,
                       OP_PUSH1, 1, OP_PUSH1, 0, OP_RETURN])
    tx = _make_signed_tx(key, to=b"", value=0, data=init_code,
                         gas_limit=100000, gas_price=1, nonce=0)

    result = apply_transaction(tx, ws, block_gas_limit=10_000_000)

    assert result.contract_address is not None
    assert len(result.contract_address) == 20
    assert result.contract_address == compute_contract_address(sender, 0)
