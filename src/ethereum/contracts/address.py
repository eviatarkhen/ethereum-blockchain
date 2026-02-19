"""Contract address derivation for Ethereum CREATE transactions.

NOTE: This is the initial home for compute_contract_address. If Phase 3 later
creates core/address.py, this function should be consolidated there and
contracts/address.py should re-export from core.
"""

from ethereum.crypto.hashing import keccak256
from ethereum.encoding.rlp import rlp_encode, int_to_rlp_bytes


def compute_contract_address(sender: bytes, nonce: int) -> bytes:
    """Derive the address of a contract created by sender at the given nonce.

    Formula: keccak256(rlp_encode([sender, int_to_rlp_bytes(nonce)]))[12:]

    The address is the last 20 bytes of the keccak256 hash of the RLP encoding
    of the list [sender_address, nonce].

    Args:
        sender: 20-byte address of the deployer account.
        nonce: Account nonce at the time of deployment (the nonce value used
               in the CREATE transaction). Must be a non-negative integer.

    Returns:
        20-byte contract address.

    Edge case — nonce=0:
        int_to_rlp_bytes(0) returns b'' (empty bytes).
        RLP encodes b'' as 0x80 (empty string marker).
        So the list [sender, b''] becomes 0xd5 + 0x94 + <20 bytes> + 0x80.

    Example:
        sender = bytes.fromhex("0000000000000000000000000000000000000001")
        compute_contract_address(sender, 0) == keccak256(rlp_encode([sender, b'']))[12:]
    """
    encoded = rlp_encode([sender, int_to_rlp_bytes(nonce)])
    return keccak256(encoded)[12:]
