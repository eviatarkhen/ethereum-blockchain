"""Tests for Ethereum transaction structure, signing, and sender recovery.

Tests the Transaction dataclass, signing_hash function, sign_transaction,
and recover_sender — the complete transaction lifecycle.
"""

import os
import pytest
from eth_keys import keys as eth_keys

from ethereum.transactions.transaction import (
    Transaction,
    signing_hash,
    sign_transaction,
    recover_sender,
)
from ethereum.crypto.keys import generate_key_pair, private_key_to_address


# Test constants
ADDR_BOB = b"\x02" * 20
ADDR_EMPTY = b""  # Contract creation


def _make_unsigned_tx(**overrides):
    """Helper to create unsigned transactions with defaults."""
    defaults = dict(
        nonce=0,
        gas_price=1,
        gas=21000,
        to=ADDR_BOB,
        value=1000000,
        data=b"",
    )
    defaults.update(overrides)
    return Transaction(**defaults)


class TestTransactionCreation:
    """Test Transaction dataclass creation."""

    def test_create_with_all_fields(self):
        """Transaction stores all 9 fields correctly."""
        tx = Transaction(
            nonce=5,
            gas_price=20,
            gas=21000,
            to=ADDR_BOB,
            value=1000,
            data=b"\xab\xcd",
            v=27,
            r=123456,
            s=789012,
        )
        assert tx.nonce == 5
        assert tx.gas_price == 20
        assert tx.gas == 21000
        assert tx.to == ADDR_BOB
        assert tx.value == 1000
        assert tx.data == b"\xab\xcd"
        assert tx.v == 27
        assert tx.r == 123456
        assert tx.s == 789012

    def test_unsigned_transaction_defaults(self):
        """Unsigned transaction has v=0, r=0, s=0."""
        tx = _make_unsigned_tx()
        assert tx.v == 0
        assert tx.r == 0
        assert tx.s == 0

    def test_is_signed_false_when_unsigned(self):
        """is_signed returns False for unsigned transaction."""
        tx = _make_unsigned_tx()
        assert tx.is_signed is False

    def test_is_signed_true_when_signed(self):
        """is_signed returns True when v, r, s are all non-zero."""
        tx = Transaction(
            nonce=0, gas_price=1, gas=21000, to=ADDR_BOB,
            value=0, data=b"", v=27, r=1, s=1,
        )
        assert tx.is_signed is True

    def test_contract_creation_transaction(self):
        """Contract creation has to=b'' (empty bytes)."""
        tx = _make_unsigned_tx(to=b"", data=b"\x60\x00")
        assert tx.to == b""
        assert tx.data == b"\x60\x00"


class TestSigningHash:
    """Test signing_hash function."""

    def test_returns_32_bytes(self):
        """signing_hash returns a 32-byte hash."""
        tx = _make_unsigned_tx()
        h = signing_hash(tx)
        assert len(h) == 32
        assert isinstance(h, bytes)

    def test_deterministic(self):
        """Same transaction always produces the same hash."""
        tx1 = _make_unsigned_tx()
        tx2 = _make_unsigned_tx()
        assert signing_hash(tx1) == signing_hash(tx2)

    def test_changes_with_nonce(self):
        """Different nonce produces different hash."""
        tx1 = _make_unsigned_tx(nonce=0)
        tx2 = _make_unsigned_tx(nonce=1)
        assert signing_hash(tx1) != signing_hash(tx2)

    def test_changes_with_value(self):
        """Different value produces different hash."""
        tx1 = _make_unsigned_tx(value=1000)
        tx2 = _make_unsigned_tx(value=2000)
        assert signing_hash(tx1) != signing_hash(tx2)

    def test_changes_with_to(self):
        """Different recipient produces different hash."""
        tx1 = _make_unsigned_tx(to=b"\x01" * 20)
        tx2 = _make_unsigned_tx(to=b"\x02" * 20)
        assert signing_hash(tx1) != signing_hash(tx2)

    def test_changes_with_gas(self):
        """Different gas limit produces different hash."""
        tx1 = _make_unsigned_tx(gas=21000)
        tx2 = _make_unsigned_tx(gas=50000)
        assert signing_hash(tx1) != signing_hash(tx2)

    def test_ignores_signature(self):
        """Signing hash doesn't include v, r, s."""
        tx_unsigned = _make_unsigned_tx()
        tx_with_sig = Transaction(
            nonce=0, gas_price=1, gas=21000, to=ADDR_BOB,
            value=1000000, data=b"", v=27, r=999, s=888,
        )
        assert signing_hash(tx_unsigned) == signing_hash(tx_with_sig)

    def test_contract_creation_hash(self):
        """Contract creation transaction (to=b'') produces valid hash."""
        tx = _make_unsigned_tx(to=b"", data=b"\x60\x00")
        h = signing_hash(tx)
        assert len(h) == 32

    def test_zero_value_nonce_handled(self):
        """Transaction with nonce=0 and value=0 produces valid hash."""
        tx = _make_unsigned_tx(nonce=0, value=0)
        h = signing_hash(tx)
        assert len(h) == 32


class TestSignTransaction:
    """Test sign_transaction function."""

    def test_returns_signed_transaction(self):
        """sign_transaction returns a Transaction with v in {27, 28}."""
        private_key, _ = generate_key_pair()
        tx = _make_unsigned_tx()
        signed = sign_transaction(tx, private_key)
        assert signed.v in (27, 28)
        assert signed.r > 0
        assert signed.s > 0

    def test_preserves_unsigned_fields(self):
        """Signed transaction preserves all unsigned field values."""
        private_key, _ = generate_key_pair()
        tx = _make_unsigned_tx(nonce=5, gas_price=20, gas=50000,
                                value=9999, data=b"\xab")
        signed = sign_transaction(tx, private_key)
        assert signed.nonce == 5
        assert signed.gas_price == 20
        assert signed.gas == 50000
        assert signed.to == ADDR_BOB
        assert signed.value == 9999
        assert signed.data == b"\xab"

    def test_original_unchanged(self):
        """sign_transaction does not modify the original transaction."""
        private_key, _ = generate_key_pair()
        tx = _make_unsigned_tx()
        sign_transaction(tx, private_key)
        assert tx.v == 0
        assert tx.r == 0
        assert tx.s == 0

    def test_is_signed_after_signing(self):
        """Signed transaction reports is_signed = True."""
        private_key, _ = generate_key_pair()
        tx = _make_unsigned_tx()
        signed = sign_transaction(tx, private_key)
        assert signed.is_signed is True

    def test_different_keys_different_signatures(self):
        """Two different keys produce different signatures on same tx."""
        key1, _ = generate_key_pair()
        key2, _ = generate_key_pair()
        tx = _make_unsigned_tx()
        sig1 = sign_transaction(tx, key1)
        sig2 = sign_transaction(tx, key2)
        # r and s should differ (extremely unlikely to be same)
        assert (sig1.r, sig1.s) != (sig2.r, sig2.s)


class TestRecoverSender:
    """Test recover_sender function."""

    def test_recovers_correct_address(self):
        """recover_sender returns the signer's address."""
        private_key, _ = generate_key_pair()
        expected_address = private_key_to_address(private_key)
        tx = _make_unsigned_tx()
        signed = sign_transaction(tx, private_key)
        recovered = recover_sender(signed)
        assert recovered == expected_address

    def test_sign_recover_roundtrip(self):
        """Full round-trip: sign -> recover -> matches key's address."""
        private_key, public_key = generate_key_pair()
        address = public_key.to_canonical_address()
        tx = _make_unsigned_tx()
        signed = sign_transaction(tx, private_key)
        assert recover_sender(signed) == address

    def test_returns_20_bytes(self):
        """Recovered address is exactly 20 bytes."""
        private_key, _ = generate_key_pair()
        tx = _make_unsigned_tx()
        signed = sign_transaction(tx, private_key)
        recovered = recover_sender(signed)
        assert len(recovered) == 20
        assert isinstance(recovered, bytes)

    def test_fails_on_unsigned_transaction(self):
        """recover_sender raises ValueError for unsigned transaction."""
        tx = _make_unsigned_tx()
        with pytest.raises(ValueError, match="unsigned"):
            recover_sender(tx)

    def test_consistent_recovery(self):
        """Same signed transaction always recovers same address."""
        private_key, _ = generate_key_pair()
        tx = _make_unsigned_tx()
        signed = sign_transaction(tx, private_key)
        addr1 = recover_sender(signed)
        addr2 = recover_sender(signed)
        assert addr1 == addr2

    def test_contract_creation_signing_recovery(self):
        """Contract creation transaction (to=b'') can be signed and recovered."""
        private_key, _ = generate_key_pair()
        expected = private_key_to_address(private_key)
        tx = _make_unsigned_tx(to=b"", data=b"\x60\x00\x60\x00\xf3")
        signed = sign_transaction(tx, private_key)
        assert recover_sender(signed) == expected

    def test_different_keys_recover_different_senders(self):
        """Transactions signed by different keys recover different senders."""
        key1, _ = generate_key_pair()
        key2, _ = generate_key_pair()
        tx = _make_unsigned_tx()
        signed1 = sign_transaction(tx, key1)
        signed2 = sign_transaction(tx, key2)
        assert recover_sender(signed1) != recover_sender(signed2)
