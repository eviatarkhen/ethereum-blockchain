"""Ethereum account model.

An Account represents the state associated with an Ethereum address.
Externally-owned accounts (EOAs) have empty code; contract accounts
have deployed bytecode. Both types share the same dataclass.

The four fields match the Ethereum Yellow Paper account definition:
nonce, balance, codeHash (derived), storageRoot (simplified to dict).

# SIMPLIFIED: Storage is a plain dict, not a Merkle Patricia Trie.
# Real Ethereum computes a storage_root hash from a per-account trie.
# SIMPLIFIED: Single class for both EOA and contract accounts.
# The only distinction is whether code is empty.
"""

from dataclasses import dataclass, field

from ethereum.crypto.hashing import keccak256


@dataclass
class Account:
    """Ethereum account state.

    Every address on Ethereum has an associated Account.
    EOAs (externally-owned accounts) have empty code.
    Contract accounts have deployed bytecode in code field.

    Attributes:
        nonce: Number of transactions sent (EOA) or contracts created (contract).
        balance: Account balance in wei (1 ETH = 10^18 wei).
        code: EVM bytecode. Empty for EOAs.
        storage: Contract storage as key-value mapping.
    """
    nonce: int = 0
    balance: int = 0
    code: bytes = b""
    storage: dict[bytes, int] = field(default_factory=dict)

    @property
    def code_hash(self) -> bytes:
        """Keccak-256 hash of the account's code.

        For EOAs with no code, this is keccak256(b"") — the canonical
        empty hash: 0xc5d2460186f7233c927e7db2dcc703c0e500b653ca82273b7bfad8045d85a470
        """
        return keccak256(self.code)

    @property
    def is_empty(self) -> bool:
        """Check if account is empty (default state).

        An empty account has zero nonce, zero balance, and no code.
        Storage is not checked — an account with only storage is still
        considered empty per EIP-161.
        """
        return self.nonce == 0 and self.balance == 0 and self.code == b""


EMPTY_ACCOUNT = Account()
"""Sentinel representing a nonexistent or empty account.

Used as the default return value when querying an address
that has no account in the world state.
"""
