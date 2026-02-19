"""ECDSA key operations for Ethereum.

Uses eth-keys library with NativeECCBackend (pure Python).
Provides key generation, message signing, public key recovery,
and Ethereum address derivation on the secp256k1 curve.

Address derivation: last 20 bytes of Keccak-256(uncompressed public key).
eth-keys handles the public key format internally.
"""
import os
from eth_keys import keys


def generate_key_pair():
    """Generate a new ECDSA key pair on the secp256k1 curve.

    Returns:
        Tuple of (PrivateKey, PublicKey).

    # SIMPLIFIED: Uses os.urandom for randomness.
    # Production Ethereum clients use additional entropy sources.
    """
    private_key = keys.PrivateKey(os.urandom(32))
    return private_key, private_key.public_key


def sign_message(private_key, message: bytes):
    """Sign a message with a private key.

    Args:
        private_key: The signer's private key.
        message: Raw message bytes (will be hashed internally by eth-keys).

    Returns:
        Signature object with v, r, s components.

    Note: This uses sign_msg() which hashes the message internally.
    For transaction signing (where you hash the RLP-encoded tx yourself),
    use private_key.sign_msg_hash(hash) directly instead.
    """
    return private_key.sign_msg(message)


def recover_public_key(message: bytes, signature):
    """Recover the signer's public key from a message and signature.

    Args:
        message: The original message that was signed.
        signature: The signature to recover from.

    Returns:
        PublicKey of the signer.
    """
    return signature.recover_public_key_from_msg(message)


def derive_address(public_key) -> bytes:
    """Derive a 20-byte Ethereum address from a public key.

    The address is the last 20 bytes of keccak256(uncompressed_public_key).
    eth-keys handles the public key format internally.

    Args:
        public_key: An eth-keys PublicKey object.

    Returns:
        20-byte Ethereum address as bytes.
    """
    return public_key.to_canonical_address()


def private_key_to_address(private_key) -> bytes:
    """Convenience: derive Ethereum address directly from private key.

    Args:
        private_key: An eth-keys PrivateKey object.

    Returns:
        20-byte Ethereum address as bytes.
    """
    return derive_address(private_key.public_key)
