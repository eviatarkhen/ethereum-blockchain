"""ABI encoding helpers for Ethereum function calls.

# SIMPLIFIED: Only handles uint256 and address types. Real ABI encoding supports
# tuples, dynamic arrays, bytes, string.
"""

from ethereum.crypto.hashing import keccak256


def compute_selector(signature: str) -> bytes:
    """Compute the 4-byte function selector from a canonical function signature.

    Args:
        signature: Canonical function signature string, e.g. "increment()" or
                   "transfer(address,uint256)".

    Returns:
        First 4 bytes of keccak256(signature).

    Example:
        compute_selector("increment()") == bytes.fromhex("d09de08a")
    """
    return keccak256(signature.encode())[:4]


def encode_uint256(value: int) -> bytes:
    """ABI-encode a uint256 value as a 32-byte big-endian word.

    Args:
        value: Non-negative integer less than 2**256.

    Returns:
        32-byte big-endian representation of value.

    Raises:
        ValueError: If value is negative or >= 2**256.
    """
    if value < 0:
        raise ValueError(f"uint256 cannot be negative, got {value}")
    if value >= 2 ** 256:
        raise ValueError(f"uint256 overflow: {value} >= 2**256")
    return value.to_bytes(32, 'big')


def encode_address(addr: bytes) -> bytes:
    """ABI-encode an Ethereum address as a 32-byte left-zero-padded word.

    Args:
        addr: 20-byte Ethereum address.

    Returns:
        32-byte value: 12 zero bytes + 20 address bytes.

    Raises:
        ValueError: If addr is not exactly 20 bytes.
    """
    if len(addr) != 20:
        raise ValueError(f"address must be 20 bytes, got {len(addr)}")
    return addr.rjust(32, b'\x00')


def encode_call(selector: bytes, *args: bytes) -> bytes:
    """Assemble ABI calldata from a selector and pre-encoded 32-byte arguments.

    Args:
        selector: 4-byte function selector.
        *args: Pre-encoded 32-byte argument words (each must already be 32 bytes).

    Returns:
        Concatenated selector + all argument words.
    """
    return selector + b''.join(args)
