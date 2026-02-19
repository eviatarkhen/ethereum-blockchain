"""Keccak-256 hashing for Ethereum.

Uses eth-hash library with pycryptodome backend.
NOT the same as hashlib.sha3_256 (FIPS 202 SHA-3).

The Keccak-256 hash function is used throughout Ethereum for:
- Address derivation (last 20 bytes of public key hash)
- Transaction hashing
- State trie keys
- Block hashing
"""
from eth_hash.auto import keccak


def keccak256(data: bytes) -> bytes:
    """Compute Keccak-256 hash of input data.

    Args:
        data: Arbitrary bytes to hash.

    Returns:
        32-byte hash digest.

    # SIMPLIFIED: We always hash in one call.
    # Real Ethereum clients may use incremental hashing for large inputs.
    """
    return keccak(data)
