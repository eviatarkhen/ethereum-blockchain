"""Dict-backed Ethereum world state.

The world state maps 20-byte Ethereum addresses to Account objects.
This is the central data structure that the EVM reads from and writes to
during transaction execution.

# SIMPLIFIED: Uses plain dict instead of Merkle Patricia Trie.
# Real Ethereum stores accounts in an MPT for O(log n) membership proofs
# and deterministic state root computation.
# The state_root_placeholder method provides a deterministic hash
# but not a real MPT root — that's deferred to v2.
"""

import copy

from ethereum.crypto.hashing import keccak256
from ethereum.encoding.rlp import rlp_encode, int_to_rlp_bytes
from ethereum.state.account import Account, EMPTY_ACCOUNT


class WorldState:
    """Dict-backed Ethereum world state.

    Maps 20-byte addresses to Account objects. Provides get/set/modify
    operations that the EVM and state transition function use.

    Usage:
        state = WorldState()
        state.set_account(address, Account(balance=1000))
        account = state.get_account(address)
    """

    def __init__(self):
        self._accounts: dict[bytes, Account] = {}

    def get_account(self, address: bytes) -> Account:
        """Get account at address, or EMPTY_ACCOUNT if not found.

        Args:
            address: 20-byte Ethereum address.

        Returns:
            Account at address, or EMPTY_ACCOUNT sentinel if no account exists.
        """
        return self._accounts.get(address, EMPTY_ACCOUNT)

    def set_account(self, address: bytes, account: Account) -> None:
        """Set account at address.

        Args:
            address: 20-byte Ethereum address.
            account: Account to store.
        """
        self._accounts[address] = account

    def account_exists(self, address: bytes) -> bool:
        """Check if address has an account in state.

        Args:
            address: 20-byte Ethereum address.

        Returns:
            True if an account exists at address, False otherwise.
        """
        return address in self._accounts

    def get_balance(self, address: bytes) -> int:
        """Get balance of address (0 if account not found).

        Convenience method — equivalent to get_account(address).balance.

        Args:
            address: 20-byte Ethereum address.

        Returns:
            Account balance in wei, or 0 if account doesn't exist.
        """
        return self.get_account(address).balance

    def modify_account(self, address: bytes, modifier) -> None:
        """Apply a modifier function to the account at address.

        If the account doesn't exist, creates a deep copy of EMPTY_ACCOUNT first.
        The modifier function receives the account and mutates it in-place.

        Args:
            address: 20-byte Ethereum address.
            modifier: Callable that takes an Account and modifies it.

        Example:
            def increment_nonce(account):
                account.nonce += 1
            state.modify_account(address, increment_nonce)
        """
        account = copy.deepcopy(self.get_account(address))
        modifier(account)
        self.set_account(address, account)

    def snapshot(self) -> dict[bytes, Account]:
        """Take a deep copy of the current state for potential rollback.

        Used by the state transition function before executing a transaction.
        If execution fails (out-of-gas, revert), the state can be restored
        to this snapshot.

        Returns:
            Deep copy of the accounts dictionary.
        """
        return copy.deepcopy(self._accounts)

    def revert(self, snapshot: dict[bytes, Account]) -> None:
        """Restore state from a previous snapshot.

        Replaces the entire accounts dictionary with the snapshot.
        Used when a transaction fails and state must be rolled back.

        Args:
            snapshot: Previously captured state from snapshot().
        """
        self._accounts = snapshot

    def add_balance(self, address: bytes, amount: int) -> None:
        """Add to account balance. Creates account if it doesn't exist.

        Args:
            address: 20-byte Ethereum address.
            amount: Wei to add.
        """
        self.modify_account(address, lambda a: setattr(a, 'balance', a.balance + amount))

    def deduct_balance(self, address: bytes, amount: int) -> None:
        """Deduct from account balance.

        Args:
            address: 20-byte Ethereum address.
            amount: Wei to deduct.

        Raises:
            ValueError: If balance would go negative.
        """
        account = self.get_account(address)
        if account.balance < amount:
            raise ValueError(
                f"Cannot deduct {amount} from balance {account.balance}"
            )
        self.modify_account(address, lambda a: setattr(a, 'balance', a.balance - amount))

    def increment_nonce(self, address: bytes) -> None:
        """Increment account nonce by 1.

        Args:
            address: 20-byte Ethereum address.
        """
        self.modify_account(address, lambda a: setattr(a, 'nonce', a.nonce + 1))

    def transfer(self, sender: bytes, recipient: bytes, amount: int) -> None:
        """Transfer value from sender to recipient.

        Creates recipient account if it doesn't exist.

        Args:
            sender: 20-byte sender address.
            recipient: 20-byte recipient address.
            amount: Wei to transfer.
        """
        if amount == 0:
            return
        self.deduct_balance(sender, amount)
        self.add_balance(recipient, amount)

    def set_code(self, address: bytes, code: bytes) -> None:
        """Set contract code at address.

        Args:
            address: 20-byte contract address.
            code: Runtime bytecode.
        """
        self.modify_account(address, lambda a: setattr(a, 'code', code))

    def get_storage(self, address: bytes, key: int) -> int:
        """Get a storage value for an account.

        Args:
            address: 20-byte contract address.
            key: Storage slot key (uint256).

        Returns:
            Storage value, or 0 if not set.
        """
        account = self.get_account(address)
        return account.storage.get(key, 0)

    def set_storage(self, address: bytes, key: int, value: int) -> None:
        """Set a storage value for an account.

        Args:
            address: 20-byte contract address.
            key: Storage slot key (uint256).
            value: Value to store (uint256).
        """
        def _set_storage(a):
            a.storage[key] = value
        self.modify_account(address, _set_storage)

    def state_root_placeholder(self) -> bytes:
        """Compute a deterministic 32-byte hash of the current state.

        Returns keccak256 of sorted, RLP-encoded account data.
        Same state always produces the same hash; different states
        produce different hashes.

        # SIMPLIFIED: Not a real MPT root. Just keccak256 of sorted account data.
        # Real Ethereum computes this from the Merkle Patricia Trie, which
        # enables O(log n) proofs of account existence and state.

        Returns:
            32-byte deterministic hash of the world state.
        """
        if not self._accounts:
            return keccak256(b"")

        items = []
        for addr in sorted(self._accounts.keys()):
            acct = self._accounts[addr]
            items.append(rlp_encode([
                addr,
                int_to_rlp_bytes(acct.nonce),
                int_to_rlp_bytes(acct.balance),
                acct.code,
            ]))
        return keccak256(b"".join(items))


def create_genesis_state(alloc: dict[bytes, int]) -> WorldState:
    """Create a genesis world state with pre-funded accounts.

    This is how Ethereum initializes its state at network launch.
    The genesis allocation specifies which addresses start with ETH.

    Args:
        alloc: Mapping of 20-byte address to initial balance (in wei).

    Returns:
        WorldState with pre-funded accounts (nonce=0, no code, no storage).
    """
    state = WorldState()
    for address, balance in alloc.items():
        state.set_account(address, Account(balance=balance))
    return state
