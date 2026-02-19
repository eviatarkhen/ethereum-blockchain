"""Tests for RLP (Recursive Length Prefix) encoding and decoding.

Tests all five encoding rules from the Ethereum Yellow Paper Appendix B,
plus critical edge cases (integer zero, nested lists, round-trips).
"""

from ethereum.encoding.rlp import rlp_encode, rlp_decode, int_to_rlp_bytes


# === ENCODING TESTS ===


class TestRLPEncodeSingleByte:
    """Rule 1: Single byte 0x00-0x7f encodes as itself."""

    def test_single_byte_low(self):
        assert rlp_encode(b'\x00') == b'\x00'

    def test_single_byte_mid(self):
        assert rlp_encode(b'\x42') == b'\x42'

    def test_single_byte_max(self):
        assert rlp_encode(b'\x7f') == b'\x7f'


class TestRLPEncodeShortString:
    """Rule 2: String 0-55 bytes: prefix 0x80 + len, then string."""

    def test_empty_string(self):
        assert rlp_encode(b'') == b'\x80'

    def test_single_byte_above_0x7f(self):
        """Single byte >= 0x80 needs the length prefix."""
        assert rlp_encode(b'\x80') == b'\x81\x80'

    def test_short_string(self):
        # "ethereum" = 8 bytes, prefix = 0x80 + 8 = 0x88
        assert rlp_encode(b'ethereum') == b'\x88ethereum'

    def test_55_byte_string(self):
        """Maximum length for short string encoding."""
        data = b'a' * 55
        encoded = rlp_encode(data)
        assert encoded[0] == 0x80 + 55  # 0xb7
        assert encoded[1:] == data


class TestRLPEncodeLongString:
    """Rule 3: String >55 bytes: prefix 0xb7 + len_of_len, then len, then string."""

    def test_56_byte_string(self):
        data = b'b' * 56
        encoded = rlp_encode(data)
        assert encoded[0] == 0xb8  # 0xb7 + 1 (len fits in 1 byte)
        assert encoded[1] == 56
        assert encoded[2:] == data

    def test_256_byte_string(self):
        data = b'c' * 256
        encoded = rlp_encode(data)
        assert encoded[0] == 0xb9  # 0xb7 + 2 (len needs 2 bytes)
        assert int.from_bytes(encoded[1:3], 'big') == 256
        assert encoded[3:] == data


class TestRLPEncodeShortList:
    """Rule 4: List 0-55 bytes total: prefix 0xc0 + total_len, then items."""

    def test_empty_list(self):
        assert rlp_encode([]) == b'\xc0'

    def test_list_of_strings(self):
        # ["cat", "dog"]
        encoded = rlp_encode([b'cat', b'dog'])
        # cat: 0x83 + "cat" = 4 bytes
        # dog: 0x83 + "dog" = 4 bytes
        # total payload: 8 bytes
        # prefix: 0xc0 + 8 = 0xc8
        assert encoded == b'\xc8\x83cat\x83dog'


class TestRLPEncodeNestedList:
    """Nested structures."""

    def test_nested_empty_list(self):
        # [[]] = 0xc1 0xc0
        assert rlp_encode([[]]) == b'\xc1\xc0'

    def test_deeply_nested(self):
        # [[[]]] = 0xc2 0xc1 0xc0
        assert rlp_encode([[[]]]) == b'\xc2\xc1\xc0'

    def test_mixed_list(self):
        # [b'cat', [b'dog']] should encode correctly
        result = rlp_encode([b'cat', [b'dog']])
        # Verify it round-trips
        decoded = rlp_decode(result)
        assert decoded == [b'cat', [b'dog']]


class TestRLPEncodeIntegerEdgeCases:
    """Integer encoding helper -- critical edge case: 0 = empty bytes."""

    def test_zero_to_bytes(self):
        """Integer 0 MUST encode as empty byte string."""
        assert int_to_rlp_bytes(0) == b''

    def test_zero_encodes_as_0x80(self):
        """Integer 0 -> b'' -> 0x80."""
        assert rlp_encode(int_to_rlp_bytes(0)) == b'\x80'

    def test_one_to_bytes(self):
        assert int_to_rlp_bytes(1) == b'\x01'

    def test_127_single_byte(self):
        """127 fits in single byte, encodes as itself."""
        assert rlp_encode(int_to_rlp_bytes(127)) == b'\x7f'

    def test_128_needs_prefix(self):
        """128 = 0x80 as byte, needs length prefix."""
        assert rlp_encode(int_to_rlp_bytes(128)) == b'\x81\x80'

    def test_256_two_bytes(self):
        assert int_to_rlp_bytes(256) == b'\x01\x00'

    def test_no_leading_zeros(self):
        """Big-endian with no leading zeros."""
        result = int_to_rlp_bytes(1)
        assert result == b'\x01'  # Not b'\x00\x01'


# === DECODING TESTS ===


class TestRLPDecode:
    """Decoding tests -- verify decode reverses encode."""

    def test_decode_empty_string(self):
        assert rlp_decode(b'\x80') == b''

    def test_decode_single_byte(self):
        assert rlp_decode(b'\x42') == b'\x42'

    def test_decode_short_string(self):
        assert rlp_decode(b'\x88ethereum') == b'ethereum'

    def test_decode_empty_list(self):
        assert rlp_decode(b'\xc0') == []

    def test_decode_nested_list(self):
        assert rlp_decode(b'\xc1\xc0') == [[]]

    def test_decode_list_of_strings(self):
        assert rlp_decode(b'\xc8\x83cat\x83dog') == [b'cat', b'dog']


# === ROUND-TRIP TESTS ===


class TestRLPRoundTrip:
    """Encode then decode should return original data."""

    def test_roundtrip_empty_string(self):
        assert rlp_decode(rlp_encode(b'')) == b''

    def test_roundtrip_short_string(self):
        assert rlp_decode(rlp_encode(b'hello world')) == b'hello world'

    def test_roundtrip_long_string(self):
        data = b'x' * 100
        assert rlp_decode(rlp_encode(data)) == data

    def test_roundtrip_empty_list(self):
        assert rlp_decode(rlp_encode([])) == []

    def test_roundtrip_nested_list(self):
        data = [b'cat', [b'dog', b'fish'], b'']
        assert rlp_decode(rlp_encode(data)) == data

    def test_roundtrip_integer_zero(self):
        """Critical: 0 round-trips through empty bytes."""
        zero_bytes = int_to_rlp_bytes(0)
        encoded = rlp_encode(zero_bytes)
        decoded = rlp_decode(encoded)
        assert decoded == b''  # 0 -> b'' -> encode -> decode -> b''

    def test_roundtrip_deeply_nested(self):
        data = [[[b'deep']]]
        assert rlp_decode(rlp_encode(data)) == data

    def test_roundtrip_complex_structure(self):
        """Structure resembling a simplified transaction."""
        tx_like = [
            int_to_rlp_bytes(0),       # nonce
            int_to_rlp_bytes(21000),   # gas
            b'\xde\xad' * 10,          # to address (20 bytes)
            int_to_rlp_bytes(1000),    # value
            b'',                        # data
        ]
        decoded = rlp_decode(rlp_encode(tx_like))
        assert decoded[0] == b''               # nonce 0 = empty bytes
        assert decoded[2] == b'\xde\xad' * 10  # address preserved
        assert decoded[4] == b''               # empty data preserved
