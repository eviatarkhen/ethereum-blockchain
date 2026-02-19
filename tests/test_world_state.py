"""Tests for Ethereum world state.

Tests the WorldState class, genesis initialization, and state operations.
"""

import pytest
from ethereum.state.account import Account, EMPTY_ACCOUNT
from ethereum.state.world_state import WorldState, create_genesis_state
from ethereum.crypto.hashing import keccak256


# Test addresses (20 bytes each)
ADDR_ALICE = b"\x01" * 20
ADDR_BOB = b"\x02" * 20
ADDR_CHARLIE = b"\x03" * 20
ADDR_NONEXISTENT = b"\xff" * 20


class TestWorldStateBasic:
    """Test basic WorldState get/set operations."""

    def test_empty_state_returns_empty_account(self):
        """Getting a nonexistent address returns EMPTY_ACCOUNT."""
        state = WorldState()
        account = state.get_account(ADDR_NONEXISTENT)
        assert account == EMPTY_ACCOUNT
        assert account.balance == 0
        assert account.nonce == 0

    def test_set_then_get_account(self):
        """set_account followed by get_account returns the stored account."""
        state = WorldState()
        account = Account(balance=1000, nonce=5)
        state.set_account(ADDR_ALICE, account)
        retrieved = state.get_account(ADDR_ALICE)
        assert retrieved.balance == 1000
        assert retrieved.nonce == 5

    def test_set_overwrites_previous(self):
        """Setting account at same address overwrites the previous one."""
        state = WorldState()
        state.set_account(ADDR_ALICE, Account(balance=100))
        state.set_account(ADDR_ALICE, Account(balance=200))
        assert state.get_account(ADDR_ALICE).balance == 200

    def test_different_addresses_independent(self):
        """Accounts at different addresses are independent."""
        state = WorldState()
        state.set_account(ADDR_ALICE, Account(balance=100))
        state.set_account(ADDR_BOB, Account(balance=200))
        assert state.get_account(ADDR_ALICE).balance == 100
        assert state.get_account(ADDR_BOB).balance == 200


class TestAccountExists:
    """Test account_exists method."""

    def test_nonexistent_address(self):
        """account_exists returns False for address not in state."""
        state = WorldState()
        assert state.account_exists(ADDR_NONEXISTENT) is False

    def test_existing_address(self):
        """account_exists returns True for address in state."""
        state = WorldState()
        state.set_account(ADDR_ALICE, Account(balance=100))
        assert state.account_exists(ADDR_ALICE) is True


class TestGetBalance:
    """Test get_balance convenience method."""

    def test_balance_of_nonexistent(self):
        """Balance of nonexistent address is 0."""
        state = WorldState()
        assert state.get_balance(ADDR_NONEXISTENT) == 0

    def test_balance_of_funded_account(self):
        """Balance of funded account returns correct value."""
        state = WorldState()
        state.set_account(ADDR_ALICE, Account(balance=5000))
        assert state.get_balance(ADDR_ALICE) == 5000


class TestModifyAccount:
    """Test modify_account with callback function."""

    def test_modify_existing_account(self):
        """modify_account applies modifier to existing account."""
        state = WorldState()
        state.set_account(ADDR_ALICE, Account(balance=100, nonce=0))

        def increment_nonce(acct):
            acct.nonce += 1

        state.modify_account(ADDR_ALICE, increment_nonce)
        assert state.get_account(ADDR_ALICE).nonce == 1
        assert state.get_account(ADDR_ALICE).balance == 100  # preserved

    def test_modify_nonexistent_creates_account(self):
        """modify_account on nonexistent address creates from EMPTY_ACCOUNT."""
        state = WorldState()

        def set_balance(acct):
            acct.balance = 500

        state.modify_account(ADDR_ALICE, set_balance)
        assert state.get_account(ADDR_ALICE).balance == 500
        assert state.account_exists(ADDR_ALICE) is True

    def test_modify_does_not_affect_other_accounts(self):
        """Modifying one account doesn't affect others."""
        state = WorldState()
        state.set_account(ADDR_ALICE, Account(balance=100))
        state.set_account(ADDR_BOB, Account(balance=200))

        def double_balance(acct):
            acct.balance *= 2

        state.modify_account(ADDR_ALICE, double_balance)
        assert state.get_account(ADDR_ALICE).balance == 200
        assert state.get_account(ADDR_BOB).balance == 200  # unchanged


class TestGenesisState:
    """Test create_genesis_state factory function."""

    def test_genesis_with_prefunded_accounts(self):
        """Genesis creates accounts with specified balances."""
        alloc = {
            ADDR_ALICE: 1000000,
            ADDR_BOB: 2000000,
        }
        state = create_genesis_state(alloc)
        assert state.get_balance(ADDR_ALICE) == 1000000
        assert state.get_balance(ADDR_BOB) == 2000000

    def test_genesis_accounts_have_zero_nonce(self):
        """Genesis accounts start with nonce 0."""
        state = create_genesis_state({ADDR_ALICE: 1000})
        assert state.get_account(ADDR_ALICE).nonce == 0

    def test_genesis_accounts_have_no_code(self):
        """Genesis accounts start with empty code (EOAs)."""
        state = create_genesis_state({ADDR_ALICE: 1000})
        assert state.get_account(ADDR_ALICE).code == b""

    def test_genesis_queryable_by_address(self):
        """Genesis state can be queried by any address."""
        state = create_genesis_state({ADDR_ALICE: 1000})
        assert state.account_exists(ADDR_ALICE) is True
        assert state.account_exists(ADDR_NONEXISTENT) is False

    def test_genesis_empty_alloc(self):
        """Genesis with empty alloc creates empty state."""
        state = create_genesis_state({})
        assert state.get_balance(ADDR_ALICE) == 0


class TestStateRootPlaceholder:
    """Test state_root_placeholder deterministic hashing."""

    def test_returns_32_bytes(self):
        """state_root_placeholder returns a 32-byte hash."""
        state = WorldState()
        root = state.state_root_placeholder()
        assert len(root) == 32
        assert isinstance(root, bytes)

    def test_empty_state_deterministic(self):
        """Empty state always produces the same root."""
        state1 = WorldState()
        state2 = WorldState()
        assert state1.state_root_placeholder() == state2.state_root_placeholder()

    def test_same_state_same_root(self):
        """Same accounts produce the same root hash."""
        state1 = WorldState()
        state1.set_account(ADDR_ALICE, Account(balance=1000))

        state2 = WorldState()
        state2.set_account(ADDR_ALICE, Account(balance=1000))

        assert state1.state_root_placeholder() == state2.state_root_placeholder()

    def test_different_state_different_root(self):
        """Different accounts produce different root hashes."""
        state1 = WorldState()
        state1.set_account(ADDR_ALICE, Account(balance=1000))

        state2 = WorldState()
        state2.set_account(ADDR_ALICE, Account(balance=2000))

        assert state1.state_root_placeholder() != state2.state_root_placeholder()

    def test_root_changes_when_state_changes(self):
        """Root hash changes when state is modified."""
        state = WorldState()
        root_before = state.state_root_placeholder()

        state.set_account(ADDR_ALICE, Account(balance=1000))
        root_after = state.state_root_placeholder()

        assert root_before != root_after
