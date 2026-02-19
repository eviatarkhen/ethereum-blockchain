"""Contract address computation.

New contract addresses are deterministically derived from the
deployer's address and nonce per the Yellow Paper.

address = keccak256(rlp([sender_address, sender_nonce]))[12:]

This means the address of a deployed contract is known before
deployment -- it depends only on who deploys and their nonce.

# SIMPLIFIED: No CREATE2 (salt-based deterministic deployment).
# Real Ethereum also supports CREATE2:
# keccak256(0xff + sender + salt + keccak256(init_code))[12:]
"""

from ethereum.crypto.hashing import keccak256
from ethereum.encoding.rlp import rlp_encode, int_to_rlp_bytes


def compute_contract_address(sender: bytes, nonce: int) -> bytes:
    """Compute the address for a newly deployed contract.

    address = keccak256(rlp([sender_address, sender_nonce]))[12:]

    The nonce is the sender's nonce at the time of deployment
    (before the transaction increments it).

    Args:
        sender: 20-byte deployer address.
        nonce: Deployer's nonce at deployment time.

    Returns:
        20-byte contract address.
    """
    encoded = rlp_encode([sender, int_to_rlp_bytes(nonce)])
    return keccak256(encoded)[12:]
