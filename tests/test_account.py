"""Tests for Ethereum account model.

Tests the Account dataclass, EMPTY_ACCOUNT sentinel, code_hash property,
and is_empty property.
"""

import pytest
from ethereum.state.account import Account, EMPTY_ACCOUNT
from ethereum.crypto.hashing import keccak256


class TestAccountCreation:
    """Test Account dataclass creation with explicit and default values."""

    def test_account_with_explicit_values(self):
        """Account stores nonce, balance, code, and storage."""
        account = Account(
            nonce=5,
            balance=1000,
            code=b"\x60\x00",
            storage={b"\x00" * 32: 42},
        )
        assert account.nonce == 5
        assert account.balance == 1000
        assert account.code == b"\x60\x00"
        assert account.storage == {b"\x00" * 32: 42}

    def test_account_default_values(self):
        """Account defaults to zero nonce, zero balance, empty code, empty storage."""
        account = Account()
        assert account.nonce == 0
        assert account.balance == 0
        assert account.code == b""
        assert account.storage == {}

    def test_account_partial_defaults(self):
        """Account can be created with only some fields specified."""
        account = Account(balance=5000)
        assert account.nonce == 0
        assert account.balance == 5000
        assert account.code == b""
        assert account.storage == {}


class TestEmptyAccount:
    """Test the EMPTY_ACCOUNT sentinel."""

    def test_empty_account_has_default_values(self):
        """EMPTY_ACCOUNT has all default field values."""
        assert EMPTY_ACCOUNT.nonce == 0
        assert EMPTY_ACCOUNT.balance == 0
        assert EMPTY_ACCOUNT.code == b""
        assert EMPTY_ACCOUNT.storage == {}

    def test_empty_account_equals_default_account(self):
        """EMPTY_ACCOUNT equals a freshly created default Account."""
        assert EMPTY_ACCOUNT == Account()

    def test_empty_account_is_empty(self):
        """EMPTY_ACCOUNT.is_empty returns True."""
        assert EMPTY_ACCOUNT.is_empty is True


class TestIsEmpty:
    """Test the is_empty property."""

    def test_default_account_is_empty(self):
        """Default account is empty."""
        assert Account().is_empty is True

    def test_account_with_balance_not_empty(self):
        """Account with non-zero balance is not empty."""
        assert Account(balance=1).is_empty is False

    def test_account_with_nonce_not_empty(self):
        """Account with non-zero nonce is not empty."""
        assert Account(nonce=1).is_empty is False

    def test_account_with_code_not_empty(self):
        """Account with code is not empty (contract account)."""
        assert Account(code=b"\x60\x00").is_empty is False

    def test_account_with_only_storage_is_empty(self):
        """Account with only storage is still considered empty (EIP-161)."""
        account = Account(storage={b"\x00" * 32: 42})
        assert account.is_empty is True


class TestCodeHash:
    """Test the code_hash property."""

    def test_empty_code_hash_matches_known_vector(self):
        """keccak256(b'') is the canonical empty code hash."""
        expected = bytes.fromhex(
            "c5d2460186f7233c927e7db2dcc703c0e500b653ca82273b7bfad8045d85a470"
        )
        assert Account().code_hash == expected

    def test_code_hash_uses_keccak256(self):
        """code_hash returns keccak256 of the code field."""
        code = b"\x60\x00\x60\x00\x52"  # PUSH1 0 PUSH1 0 MSTORE
        account = Account(code=code)
        assert account.code_hash == keccak256(code)

    def test_nonempty_code_hash_differs_from_empty(self):
        """Non-empty code hash differs from the empty code hash."""
        empty_hash = Account().code_hash
        nonempty_hash = Account(code=b"\x60\x00").code_hash
        assert nonempty_hash != empty_hash

    def test_code_hash_is_32_bytes(self):
        """code_hash always returns 32 bytes."""
        assert len(Account().code_hash) == 32
        assert len(Account(code=b"\xff" * 100).code_hash) == 32


class TestStorage:
    """Test account storage as plain dict."""

    def test_storage_set_and_get(self):
        """Storage can be set and retrieved."""
        account = Account()
        key = b"\x00" * 32
        account.storage[key] = 42
        assert account.storage[key] == 42

    def test_storage_default_for_missing_key(self):
        """Missing storage key returns default via dict.get."""
        account = Account()
        assert account.storage.get(b"\x00" * 32, 0) == 0

    def test_storage_multiple_keys(self):
        """Storage supports multiple independent keys."""
        account = Account()
        key1 = b"\x00" * 32
        key2 = b"\x01" + b"\x00" * 31
        account.storage[key1] = 100
        account.storage[key2] = 200
        assert account.storage[key1] == 100
        assert account.storage[key2] == 200
