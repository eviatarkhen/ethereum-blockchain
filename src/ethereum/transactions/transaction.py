"""Ethereum legacy (Type 0) transaction structure.

Transactions are the atomic units that move Ethereum's state machine.
Each transaction specifies what the sender wants to do (transfer ETH,
deploy contract, call contract) and includes an ECDSA signature that
proves the sender authorized it.

The signing flow demonstrates how Phase 1 crypto primitives secure
transactions:
1. RLP-encode the unsigned fields (nonce, gas_price, gas, to, value, data)
2. Keccak-256 hash the RLP encoding to get the signing hash
3. ECDSA sign the hash with the sender's private key
4. Store signature as v, r, s on the transaction

Sender recovery reverses this: recompute the signing hash, then use
ECDSA recovery with v, r, s to get the public key, then derive the address.

# SIMPLIFIED: Legacy format only (pre-EIP-1559).
# Real Ethereum supports Type 0 (legacy), Type 1 (EIP-2930 access lists),
# and Type 2 (EIP-1559 dynamic fees).
# Legacy format is sufficient for educational purposes.
"""

from dataclasses import dataclass

from eth_keys import keys as eth_keys

from ethereum.crypto.hashing import keccak256
from ethereum.encoding.rlp import rlp_encode, int_to_rlp_bytes


@dataclass
class Transaction:
    """Ethereum legacy (Type 0) transaction.

    Contains the six unsigned fields that define the transaction intent,
    plus v, r, s signature components produced by ECDSA signing.

    Attributes:
        nonce: Sender's transaction count (prevents replay).
        gas_price: Price per gas unit in wei.
        gas: Maximum gas units this transaction may consume.
        to: Recipient address (20 bytes), or b"" for contract creation.
        value: ETH to transfer in wei.
        data: Calldata (for calls) or init code (for contract creation).
        v: Signature recovery id (27 or 28 for legacy, 0 when unsigned).
        r: ECDSA r component (0 when unsigned).
        s: ECDSA s component (0 when unsigned).
    """
    nonce: int
    gas_price: int
    gas: int
    to: bytes
    value: int
    data: bytes

    # Signature components (0 when unsigned)
    v: int = 0
    r: int = 0
    s: int = 0

    @property
    def is_signed(self) -> bool:
        """Check if transaction has been signed (v, r, s are non-zero)."""
        return self.v != 0 and self.r != 0 and self.s != 0


def signing_hash(tx: Transaction) -> bytes:
    """Compute the hash of unsigned transaction fields for ECDSA signing.

    The signing hash is keccak256(RLP([nonce, gas_price, gas, to, value, data])).
    This is what gets signed — the signature (v, r, s) is NOT included.

    This follows the Ethereum Yellow Paper: the sender signs over the
    transaction intent (what they want to do), not the signature itself.

    Args:
        tx: Transaction (signed or unsigned — only unsigned fields are used).

    Returns:
        32-byte keccak256 hash of RLP-encoded unsigned fields.
    """
    unsigned_fields = [
        int_to_rlp_bytes(tx.nonce),
        int_to_rlp_bytes(tx.gas_price),
        int_to_rlp_bytes(tx.gas),
        tx.to,
        int_to_rlp_bytes(tx.value),
        tx.data,
    ]
    return keccak256(rlp_encode(unsigned_fields))


def sign_transaction(tx: Transaction, private_key) -> Transaction:
    """Sign a transaction with a private key.

    Creates a NEW Transaction with the v, r, s fields populated.
    The original transaction is not modified.

    Uses sign_msg_hash (NOT sign_msg) because we pre-hash with keccak256.
    sign_msg would double-hash, producing an unrecoverable signature.

    Args:
        tx: Unsigned transaction (v=0, r=0, s=0).
        private_key: eth-keys PrivateKey object.

    Returns:
        New Transaction with ECDSA signature (v, r, s).
    """
    tx_hash = signing_hash(tx)
    signature = private_key.sign_msg_hash(tx_hash)

    return Transaction(
        nonce=tx.nonce,
        gas_price=tx.gas_price,
        gas=tx.gas,
        to=tx.to,
        value=tx.value,
        data=tx.data,
        v=signature.v + 27,   # Legacy: recovery id 0/1 -> 27/28
        r=signature.r,
        s=signature.s,
    )


def recover_sender(tx: Transaction) -> bytes:
    """Recover the sender's 20-byte address from a signed transaction.

    Recomputes the signing hash, then uses ECDSA recovery with v, r, s
    to get the public key, then derives the Ethereum address.

    This is how Ethereum nodes verify who sent a transaction without
    requiring the sender to include their address explicitly — it's
    recovered from the signature.

    Args:
        tx: Signed transaction (v, r, s must be valid).

    Returns:
        20-byte sender address as bytes.

    Raises:
        ValueError: If transaction is unsigned or signature is invalid.
    """
    if not tx.is_signed:
        raise ValueError("Cannot recover sender from unsigned transaction")

    tx_hash = signing_hash(tx)

    # Convert v back to recovery id (27/28 -> 0/1)
    recovery_id = tx.v - 27

    # Reconstruct signature from v, r, s components
    signature = eth_keys.Signature(
        vrs=(recovery_id, tx.r, tx.s)
    )

    # Recover public key from signature and signing hash
    public_key = signature.recover_public_key_from_msg_hash(tx_hash)

    # Derive address: last 20 bytes of keccak256(uncompressed public key)
    return public_key.to_canonical_address()
