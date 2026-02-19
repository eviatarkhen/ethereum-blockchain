"""Tests for ECDSA key operations and Ethereum address derivation.

Verifies key generation, message signing, public key recovery,
and address derivation using the secp256k1 curve.
"""

from ethereum.crypto.keys import (
    generate_key_pair,
    sign_message,
    recover_public_key,
    derive_address,
    private_key_to_address,
)


def test_generate_key_pair():
    """Key pair generation produces valid private and public keys."""
    private_key, public_key = generate_key_pair()
    assert private_key is not None
    assert public_key is not None
    # Private key is 32 bytes
    assert len(private_key.to_bytes()) == 32


def test_sign_and_recover():
    """Sign a message and recover the signer's public key."""
    private_key, public_key = generate_key_pair()
    message = b'test message for signing'
    signature = sign_message(private_key, message)
    recovered = recover_public_key(message, signature)
    assert recovered == public_key


def test_sign_different_messages_different_sigs():
    """Different messages produce different signatures."""
    private_key, _ = generate_key_pair()
    sig1 = sign_message(private_key, b'message one')
    sig2 = sign_message(private_key, b'message two')
    assert sig1 != sig2


def test_derive_address_length():
    """Ethereum address is exactly 20 bytes."""
    _, public_key = generate_key_pair()
    address = derive_address(public_key)
    assert len(address) == 20
    assert isinstance(address, bytes)


def test_derive_address_deterministic():
    """Same public key always derives same address."""
    _, public_key = generate_key_pair()
    addr1 = derive_address(public_key)
    addr2 = derive_address(public_key)
    assert addr1 == addr2


def test_private_key_to_address():
    """Convenience: private key -> address in one step."""
    private_key, public_key = generate_key_pair()
    address_from_priv = private_key_to_address(private_key)
    address_from_pub = derive_address(public_key)
    assert address_from_priv == address_from_pub


def test_address_hex_format():
    """Address can be formatted as 0x-prefixed hex string."""
    _, public_key = generate_key_pair()
    address = derive_address(public_key)
    hex_addr = '0x' + address.hex()
    assert hex_addr.startswith('0x')
    assert len(hex_addr) == 42  # 0x + 40 hex chars


def test_sign_msg_hash_for_transaction_signing():
    """sign_msg_hash works with pre-hashed 32-byte data (for transaction signing later)."""
    from ethereum.crypto.hashing import keccak256
    private_key, public_key = generate_key_pair()
    msg_hash = keccak256(b'transaction data')
    signature = private_key.sign_msg_hash(msg_hash)
    recovered = signature.recover_public_key_from_msg_hash(msg_hash)
    assert recovered == public_key
