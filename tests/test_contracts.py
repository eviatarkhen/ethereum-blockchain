"""Tests for contract bytecode, ABI encoding, and address derivation.

Verifies:
- Function selectors match canonical Ethereum values
- ABI encoding produces correct 32-byte padded calldata
- Contract address derivation uses keccak256(RLP([sender, nonce]))[12:]
- Counter bytecode structure contains correct selector bytes
- Token bytecode structure contains correct selector bytes
- Helper functions produce correctly-sized calldata
"""
import pytest
from ethereum.contracts.abi import compute_selector, encode_uint256, encode_address, encode_call
from ethereum.contracts.address import compute_contract_address
from ethereum.contracts.counter import COUNTER_RUNTIME_BYTECODE, encode_increment, encode_get_count
from ethereum.contracts.token import TOKEN_RUNTIME_BYTECODE, encode_transfer, encode_balance_of
from ethereum.crypto.hashing import keccak256
from ethereum.encoding.rlp import rlp_encode, int_to_rlp_bytes


# ---------------------------------------------------------------------------
# Function selector tests
# ---------------------------------------------------------------------------

class TestComputeSelector:
    def test_increment_selector(self):
        """increment() selector must be d09de08a."""
        result = compute_selector("increment()")
        assert result == bytes.fromhex("d09de08a"), (
            f"Expected d09de08a, got {result.hex()}"
        )

    def test_get_count_selector(self):
        """getCount() selector must be a87d942c."""
        result = compute_selector("getCount()")
        assert result == bytes.fromhex("a87d942c"), (
            f"Expected a87d942c, got {result.hex()}"
        )

    def test_transfer_selector(self):
        """transfer(address,uint256) selector must be a9059cbb."""
        result = compute_selector("transfer(address,uint256)")
        assert result == bytes.fromhex("a9059cbb"), (
            f"Expected a9059cbb, got {result.hex()}"
        )

    def test_balance_of_selector(self):
        """balanceOf(address) selector must be 70a08231."""
        result = compute_selector("balanceOf(address)")
        assert result == bytes.fromhex("70a08231"), (
            f"Expected 70a08231, got {result.hex()}"
        )

    def test_selector_is_4_bytes(self):
        """All selectors are exactly 4 bytes."""
        for sig in ["increment()", "getCount()", "transfer(address,uint256)", "balanceOf(address)"]:
            result = compute_selector(sig)
            assert len(result) == 4, f"selector for {sig!r} is {len(result)} bytes, expected 4"


# ---------------------------------------------------------------------------
# ABI encoding tests
# ---------------------------------------------------------------------------

class TestEncodeUint256:
    def test_zero_is_32_zero_bytes(self):
        """encode_uint256(0) produces 32 zero bytes."""
        result = encode_uint256(0)
        assert result == b'\x00' * 32
        assert len(result) == 32

    def test_one_has_lsb_at_position_31(self):
        """encode_uint256(1) has 0x01 at byte position 31 (big-endian)."""
        result = encode_uint256(1)
        assert len(result) == 32
        assert result[31] == 0x01
        assert result[:31] == b'\x00' * 31

    def test_large_value(self):
        """encode_uint256 handles values up to 2^256 - 1."""
        max_val = 2 ** 256 - 1
        result = encode_uint256(max_val)
        assert result == b'\xff' * 32

    def test_negative_raises(self):
        """encode_uint256 raises ValueError for negative values."""
        with pytest.raises(ValueError):
            encode_uint256(-1)

    def test_overflow_raises(self):
        """encode_uint256 raises ValueError for values >= 2^256."""
        with pytest.raises(ValueError):
            encode_uint256(2 ** 256)


class TestEncodeAddress:
    def test_address_is_right_aligned(self):
        """encode_address pads with 12 zero bytes on the left."""
        addr = b'\x01' * 20
        result = encode_address(addr)
        assert len(result) == 32
        assert result[:12] == b'\x00' * 12
        assert result[12:] == addr

    def test_wrong_length_raises(self):
        """encode_address raises ValueError for non-20-byte input."""
        with pytest.raises(ValueError):
            encode_address(b'\x01' * 19)
        with pytest.raises(ValueError):
            encode_address(b'\x01' * 21)

    def test_zero_address(self):
        """encode_address of zero address produces 32 zero bytes."""
        result = encode_address(b'\x00' * 20)
        assert result == b'\x00' * 32


# ---------------------------------------------------------------------------
# Contract address derivation tests
# ---------------------------------------------------------------------------

class TestComputeContractAddress:
    def test_known_address_nonce_zero(self):
        """compute_contract_address matches independent keccak256(RLP([sender, b''])) computation."""
        sender = bytes.fromhex("0000000000000000000000000000000000000001")
        nonce = 0
        expected = keccak256(rlp_encode([sender, int_to_rlp_bytes(nonce)]))[12:]
        result = compute_contract_address(sender, nonce)
        assert result == expected
        assert len(result) == 20

    def test_known_address_nonce_one(self):
        """compute_contract_address with nonce=1 matches independent computation."""
        sender = bytes.fromhex("cafebabecafebabecafebabecafebabecafebabe")
        nonce = 1
        expected = keccak256(rlp_encode([sender, int_to_rlp_bytes(nonce)]))[12:]
        result = compute_contract_address(sender, nonce)
        assert result == expected
        assert len(result) == 20

    def test_different_nonces_produce_different_addresses(self):
        """Different nonces produce different contract addresses."""
        sender = b'\xab' * 20
        addr0 = compute_contract_address(sender, 0)
        addr1 = compute_contract_address(sender, 1)
        assert addr0 != addr1

    def test_returns_20_bytes(self):
        """Contract address is always exactly 20 bytes."""
        result = compute_contract_address(b'\x00' * 20, 0)
        assert len(result) == 20


# ---------------------------------------------------------------------------
# Counter bytecode tests
# ---------------------------------------------------------------------------

class TestCounterBytecode:
    def test_is_non_empty_bytes(self):
        """COUNTER_RUNTIME_BYTECODE is a non-empty bytes object."""
        assert isinstance(COUNTER_RUNTIME_BYTECODE, bytes)
        assert len(COUNTER_RUNTIME_BYTECODE) > 0

    def test_contains_increment_selector(self):
        """Counter bytecode embeds the increment() selector d09de08a."""
        inc_selector = bytes.fromhex("d09de08a")
        assert inc_selector in COUNTER_RUNTIME_BYTECODE, (
            f"increment selector d09de08a not found in Counter bytecode"
        )

    def test_contains_get_count_selector(self):
        """Counter bytecode embeds the getCount() selector a87d942c."""
        get_selector = bytes.fromhex("a87d942c")
        assert get_selector in COUNTER_RUNTIME_BYTECODE, (
            f"getCount selector a87d942c not found in Counter bytecode"
        )

    def test_encode_increment_returns_4_bytes(self):
        """encode_increment() returns exactly 4 bytes."""
        result = encode_increment()
        assert isinstance(result, bytes)
        assert len(result) == 4

    def test_encode_increment_is_correct_selector(self):
        """encode_increment() returns the increment() selector."""
        assert encode_increment() == bytes.fromhex("d09de08a")

    def test_encode_get_count_returns_4_bytes(self):
        """encode_get_count() returns exactly 4 bytes."""
        result = encode_get_count()
        assert isinstance(result, bytes)
        assert len(result) == 4


# ---------------------------------------------------------------------------
# Token bytecode tests
# ---------------------------------------------------------------------------

class TestTokenBytecode:
    def test_is_non_empty_bytes(self):
        """TOKEN_RUNTIME_BYTECODE is a non-empty bytes object."""
        assert isinstance(TOKEN_RUNTIME_BYTECODE, bytes)
        assert len(TOKEN_RUNTIME_BYTECODE) > 0

    def test_contains_transfer_selector(self):
        """Token bytecode embeds the transfer(address,uint256) selector a9059cbb."""
        transfer_selector = bytes.fromhex("a9059cbb")
        assert transfer_selector in TOKEN_RUNTIME_BYTECODE, (
            f"transfer selector a9059cbb not found in Token bytecode"
        )

    def test_contains_balance_of_selector(self):
        """Token bytecode embeds the balanceOf(address) selector 70a08231."""
        balance_selector = bytes.fromhex("70a08231")
        assert balance_selector in TOKEN_RUNTIME_BYTECODE, (
            f"balanceOf selector 70a08231 not found in Token bytecode"
        )

    def test_encode_transfer_returns_68_bytes(self):
        """encode_transfer(addr, amount) returns exactly 68 bytes (4 + 32 + 32)."""
        addr = b'\x01' * 20
        result = encode_transfer(addr, 1000)
        assert isinstance(result, bytes)
        assert len(result) == 68, f"Expected 68 bytes, got {len(result)}"

    def test_encode_balance_of_returns_36_bytes(self):
        """encode_balance_of(addr) returns exactly 36 bytes (4 + 32)."""
        addr = b'\x01' * 20
        result = encode_balance_of(addr)
        assert isinstance(result, bytes)
        assert len(result) == 36, f"Expected 36 bytes, got {len(result)}"

    def test_encode_transfer_selector_prefix(self):
        """encode_transfer calldata starts with the transfer selector."""
        addr = b'\x02' * 20
        result = encode_transfer(addr, 500)
        assert result[:4] == bytes.fromhex("a9059cbb")

    def test_encode_balance_of_selector_prefix(self):
        """encode_balance_of calldata starts with the balanceOf selector."""
        addr = b'\x03' * 20
        result = encode_balance_of(addr)
        assert result[:4] == bytes.fromhex("70a08231")
