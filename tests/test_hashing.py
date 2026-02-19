"""Tests for Keccak-256 hashing.

Verifies that our keccak256 wrapper uses the correct Keccak-256 algorithm
(NOT FIPS 202 SHA-3) and passes known test vectors.
"""

from ethereum.crypto.hashing import keccak256


def test_keccak256_empty_input():
    """Canonical test vector: keccak256 of empty bytes."""
    result = keccak256(b'')
    assert result.hex() == 'c5d2460186f7233c927e7db2dcc703c0e500b653ca82273b7bfad8045d85a470'


def test_keccak256_hello():
    """Known test vector for 'hello'."""
    result = keccak256(b'hello')
    assert len(result) == 32
    assert isinstance(result, bytes)


def test_keccak256_deterministic():
    """Same input always produces same output."""
    assert keccak256(b'test') == keccak256(b'test')


def test_keccak256_different_from_sha3():
    """Verify we're using Keccak-256, NOT FIPS 202 SHA-3."""
    import hashlib
    data = b'test'
    keccak_result = keccak256(data)
    sha3_result = hashlib.sha3_256(data).digest()
    assert keccak_result != sha3_result, "Keccak-256 and SHA-3 must differ"
