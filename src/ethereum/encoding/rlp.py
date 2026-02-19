"""RLP (Recursive Length Prefix) encoding and decoding.

Implemented from scratch following the Ethereum Yellow Paper Appendix B.
RLP is the primary serialization format used throughout Ethereum for
transactions, blocks, and state data.

RLP supports two data types:
1. Byte strings (bytes)
2. Lists of byte strings and/or lists (recursive)

Integers are NOT a native RLP type. Use int_to_rlp_bytes() to convert
integers to big-endian bytes before encoding.

Encoding rules (Yellow Paper Appendix B):
- Single byte 0x00-0x7f: encodes as itself
- String 0-55 bytes: prefix 0x80 + len, then string
- String >55 bytes: prefix 0xb7 + len_of_len, then len, then string
- List 0-55 bytes total payload: prefix 0xc0 + total_len, then items
- List >55 bytes total payload: prefix 0xf7 + len_of_len, then len, then items

CRITICAL: Integer 0 encodes as empty byte string (0x80), not as b'\\x00'.
"""


def int_to_rlp_bytes(n: int) -> bytes:
    """Convert a non-negative integer to minimal big-endian bytes for RLP.

    Args:
        n: Non-negative integer.

    Returns:
        Minimal big-endian byte representation. Zero returns empty bytes b''.

    IMPORTANT: This is how Ethereum encodes integers in RLP.
    Zero has no digits in big-endian, so it becomes empty bytes.
    Empty bytes then encode as 0x80 in RLP.

    # SIMPLIFIED: No maximum integer size check.
    # Real Ethereum limits integers to 256 bits (32 bytes).
    """
    if n == 0:
        return b''
    # Calculate minimum number of bytes needed
    byte_length = (n.bit_length() + 7) // 8
    return n.to_bytes(byte_length, 'big')


def _encode_length(length: int) -> bytes:
    """Encode a length value as minimal big-endian bytes.

    Used for the "long string" and "long list" encoding rules
    where the length itself needs to be encoded in multiple bytes.

    Args:
        length: The length value to encode.

    Returns:
        Minimal big-endian bytes representing the length.
    """
    if length == 0:
        return b'\x00'
    byte_length = (length.bit_length() + 7) // 8
    return length.to_bytes(byte_length, 'big')


def rlp_encode(input_data) -> bytes:
    """RLP encode input data per Ethereum Yellow Paper Appendix B.

    Args:
        input_data: Either bytes (string) or list (recursive).

    Returns:
        RLP-encoded bytes.

    Raises:
        TypeError: If input_data is neither bytes nor list.
    """
    if isinstance(input_data, bytes):
        return _encode_string(input_data)
    elif isinstance(input_data, (list, tuple)):
        return _encode_list(input_data)
    else:
        raise TypeError(
            f"RLP can only encode bytes or lists, got {type(input_data).__name__}. "
            f"Use int_to_rlp_bytes() to convert integers first."
        )


def _encode_string(data: bytes) -> bytes:
    """Encode a byte string according to RLP rules.

    Rule 1: Single byte 0x00-0x7f -> encodes as itself
    Rule 2: String 0-55 bytes -> prefix (0x80 + len) + string
    Rule 3: String >55 bytes -> prefix (0xb7 + len_of_len) + len + string
    """
    length = len(data)

    # Rule 1: Single byte in range [0x00, 0x7f]
    if length == 1 and data[0] < 0x80:
        return data

    # Rule 2: Short string (0-55 bytes)
    if length <= 55:
        return bytes([0x80 + length]) + data

    # Rule 3: Long string (>55 bytes)
    len_bytes = _encode_length(length)
    return bytes([0xb7 + len(len_bytes)]) + len_bytes + data


def _encode_list(items) -> bytes:
    """Encode a list according to RLP rules.

    Rule 4: List with 0-55 bytes total payload -> prefix (0xc0 + total_len) + items
    Rule 5: List with >55 bytes total payload -> prefix (0xf7 + len_of_len) + len + items
    """
    # Recursively encode each item and concatenate
    payload = b''.join(rlp_encode(item) for item in items)
    payload_length = len(payload)

    # Rule 4: Short list (0-55 bytes total payload)
    if payload_length <= 55:
        return bytes([0xc0 + payload_length]) + payload

    # Rule 5: Long list (>55 bytes total payload)
    len_bytes = _encode_length(payload_length)
    return bytes([0xf7 + len(len_bytes)]) + len_bytes + payload


def rlp_decode(data: bytes):
    """RLP decode bytes back to the original data structure.

    Args:
        data: RLP-encoded bytes.

    Returns:
        Decoded data: either bytes (for strings) or list (for lists).

    # SIMPLIFIED: No streaming decode or maximum depth limit.
    # Real implementations guard against stack overflow from deeply nested lists.
    """
    result, consumed = _decode_item(data, 0)
    if consumed != len(data):
        raise ValueError(
            f"RLP decode error: {len(data) - consumed} trailing bytes after decoding"
        )
    return result


def _decode_item(data: bytes, offset: int):
    """Decode a single RLP item starting at offset.

    Args:
        data: Full RLP-encoded bytes.
        offset: Starting position in data.

    Returns:
        Tuple of (decoded_item, bytes_consumed).
        decoded_item is bytes for strings, list for lists.
    """
    if offset >= len(data):
        raise ValueError("RLP decode error: unexpected end of data")

    prefix = data[offset]

    # Rule 1: Single byte [0x00, 0x7f]
    if prefix < 0x80:
        return bytes([prefix]), offset + 1

    # Rule 2: Short string (0-55 bytes), prefix in [0x80, 0xb7]
    elif prefix <= 0xb7:
        str_len = prefix - 0x80
        start = offset + 1
        end = start + str_len
        if end > len(data):
            raise ValueError("RLP decode error: string length exceeds data")
        return data[start:end], end

    # Rule 3: Long string (>55 bytes), prefix in [0xb8, 0xbf]
    elif prefix <= 0xbf:
        len_of_len = prefix - 0xb7
        len_start = offset + 1
        len_end = len_start + len_of_len
        if len_end > len(data):
            raise ValueError("RLP decode error: length-of-length exceeds data")
        str_len = int.from_bytes(data[len_start:len_end], 'big')
        start = len_end
        end = start + str_len
        if end > len(data):
            raise ValueError("RLP decode error: long string exceeds data")
        return data[start:end], end

    # Rule 4: Short list (0-55 bytes payload), prefix in [0xc0, 0xf7]
    elif prefix <= 0xf7:
        list_len = prefix - 0xc0
        return _decode_list(data, offset + 1, list_len)

    # Rule 5: Long list (>55 bytes payload), prefix in [0xf8, 0xff]
    else:
        len_of_len = prefix - 0xf7
        len_start = offset + 1
        len_end = len_start + len_of_len
        if len_end > len(data):
            raise ValueError("RLP decode error: list length-of-length exceeds data")
        list_len = int.from_bytes(data[len_start:len_end], 'big')
        return _decode_list(data, len_end, list_len)


def _decode_list(data: bytes, start: int, list_len: int):
    """Decode a list payload of known length.

    Args:
        data: Full RLP-encoded bytes.
        start: Start of list payload (after prefix/length bytes).
        list_len: Total byte length of list payload.

    Returns:
        Tuple of (list_of_items, end_offset).
    """
    items = []
    end = start + list_len
    if end > len(data):
        raise ValueError("RLP decode error: list payload exceeds data")

    pos = start
    while pos < end:
        item, pos = _decode_item(data, pos)
        items.append(item)

    if pos != end:
        raise ValueError("RLP decode error: list items don't fill declared length")

    return items, end
