"""EVM byte-addressable memory.

Memory is a byte array that expands dynamically as needed.
All access is word-aligned to 32-byte boundaries for expansion.

EVM memory is volatile — it exists only during a single execution
context and is discarded when execution completes.

# SIMPLIFIED: No quadratic gas cost for memory expansion.
# Real Ethereum charges: 3 * num_words + num_words^2 / 512
# This means accessing high memory offsets becomes exponentially
# expensive, preventing denial-of-service via memory allocation.
# Our implementation charges a flat cost per access (in gas.py).
"""


class Memory:
    """Byte-addressable, word-aligned expandable EVM memory.

    Memory starts empty (size 0) and expands to the nearest 32-byte
    word boundary whenever an access exceeds the current size.
    Expansion fills new bytes with zeros.

    All operations are designed for debugger stepping — each method
    does one clear thing with descriptive variable names.
    """

    def __init__(self):
        self._data = bytearray()

    def _expand_to(self, offset: int, size: int) -> None:
        """Expand memory if access goes beyond current size.

        Memory always expands to the next 32-byte word boundary.
        New bytes are zero-filled.

        Args:
            offset: Start position of the access.
            size: Number of bytes being accessed.
        """
        if size == 0:
            return
        needed = offset + size
        if needed > len(self._data):
            # Round up to next 32-byte word boundary
            new_size = ((needed + 31) // 32) * 32
            self._data.extend(b"\x00" * (new_size - len(self._data)))

    def load(self, offset: int) -> int:
        """Load a 32-byte word from memory as a uint256.

        Reads 32 bytes starting at offset and interprets them as
        a big-endian unsigned 256-bit integer.

        Args:
            offset: Byte offset to start reading from.

        Returns:
            256-bit unsigned integer value.

        Stack effect: Used by MLOAD opcode.
        """
        self._expand_to(offset, 32)
        word_bytes = self._data[offset:offset + 32]
        return int.from_bytes(word_bytes, "big")

    def store(self, offset: int, value: int) -> None:
        """Store a uint256 as a 32-byte big-endian word.

        Writes the value as 32 bytes starting at offset.
        If value is smaller than 32 bytes, it is left-padded with zeros.

        Args:
            offset: Byte offset to start writing at.
            value: 256-bit unsigned integer to store.

        Stack effect: Used by MSTORE opcode.
        """
        self._expand_to(offset, 32)
        self._data[offset:offset + 32] = value.to_bytes(32, "big")

    def store8(self, offset: int, value: int) -> None:
        """Store a single byte at offset.

        Only the least significant byte of value is stored.

        Args:
            offset: Byte offset to write at.
            value: Value whose least significant byte is stored.

        Stack effect: Used by MSTORE8 opcode.
        """
        self._expand_to(offset, 1)
        self._data[offset] = value & 0xFF

    def read_range(self, offset: int, size: int) -> bytes:
        """Read an arbitrary byte range from memory.

        Used by SHA3 (to hash memory regions), RETURN (to return data),
        REVERT (to return error data), and CALLDATACOPY/CODECOPY.

        Args:
            offset: Start byte offset.
            size: Number of bytes to read.

        Returns:
            Bytes from memory[offset:offset+size].
        """
        if size == 0:
            return b""
        self._expand_to(offset, size)
        return bytes(self._data[offset:offset + size])

    def write_range(self, offset: int, data: bytes) -> None:
        """Write arbitrary bytes to memory.

        Used by CALLDATACOPY, CODECOPY, and CALL return data copy.

        Args:
            offset: Start byte offset.
            data: Bytes to write.
        """
        if len(data) == 0:
            return
        self._expand_to(offset, len(data))
        self._data[offset:offset + len(data)] = data

    def size(self) -> int:
        """Current memory size in bytes.

        Memory size is always a multiple of 32 (word-aligned).

        Returns:
            Current memory size.
        """
        return len(self._data)
