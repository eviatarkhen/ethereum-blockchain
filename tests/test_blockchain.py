"""Tests for Ethereum blockchain chain management.

Tests the Blockchain class: genesis initialization, block append
with validation, get_block_by_number, and chain validation.
"""

import pytest
from ethereum.chain.block import (
    Header,
    Block,
    block_hash,
    create_genesis_block,
    create_block,
)
from ethereum.chain.blockchain import Blockchain
from ethereum.crypto.hashing import keccak256
from ethereum.transactions.transaction import Transaction


# Test constants
STATE_ROOT_A = keccak256(b"state_a")
STATE_ROOT_B = keccak256(b"state_b")
STATE_ROOT_C = keccak256(b"state_c")


class TestBlockchainInit:
    """Test Blockchain initialization."""

    def test_starts_with_genesis(self):
        """Blockchain starts with the genesis block."""
        genesis = create_genesis_block(STATE_ROOT_A)
        chain = Blockchain(genesis)
        assert chain.latest == genesis

    def test_initial_height_zero(self):
        """Initial chain height is 0 (genesis only)."""
        genesis = create_genesis_block(STATE_ROOT_A)
        chain = Blockchain(genesis)
        assert chain.height == 0


class TestAppendBlock:
    """Test Blockchain.append_block validation."""

    def test_append_valid_block(self):
        """Appending a valid block succeeds and increments height."""
        genesis = create_genesis_block(STATE_ROOT_A)
        chain = Blockchain(genesis)
        block1 = create_block(genesis, [], STATE_ROOT_B, timestamp=100)
        chain.append_block(block1)
        assert chain.height == 1
        assert chain.latest == block1

    def test_append_returns_block_hash(self):
        """append_block returns the hash of the appended block."""
        genesis = create_genesis_block(STATE_ROOT_A)
        chain = Blockchain(genesis)
        block1 = create_block(genesis, [], STATE_ROOT_B, timestamp=100)
        result_hash = chain.append_block(block1)
        assert result_hash == block_hash(block1)
        assert len(result_hash) == 32

    def test_rejects_wrong_parent_hash(self):
        """Block with wrong parent_hash is rejected."""
        genesis = create_genesis_block(STATE_ROOT_A)
        chain = Blockchain(genesis)
        bad_block = Block(
            header=Header(
                parent_hash=b"\xff" * 32,  # Wrong parent hash
                number=1,
                timestamp=100,
                state_root=STATE_ROOT_B,
            )
        )
        with pytest.raises(ValueError, match="Invalid parent hash"):
            chain.append_block(bad_block)

    def test_rejects_wrong_block_number(self):
        """Block with wrong number is rejected."""
        genesis = create_genesis_block(STATE_ROOT_A)
        chain = Blockchain(genesis)
        bad_block = Block(
            header=Header(
                parent_hash=block_hash(genesis),
                number=5,  # Should be 1
                timestamp=100,
                state_root=STATE_ROOT_B,
            )
        )
        with pytest.raises(ValueError, match="Invalid block number"):
            chain.append_block(bad_block)

    def test_chain_of_three_blocks(self):
        """Three blocks can be appended to form a chain."""
        genesis = create_genesis_block(STATE_ROOT_A)
        chain = Blockchain(genesis)

        block1 = create_block(genesis, [], STATE_ROOT_B, timestamp=100)
        chain.append_block(block1)

        block2 = create_block(block1, [], STATE_ROOT_C, timestamp=200)
        chain.append_block(block2)

        assert chain.height == 2
        assert chain.latest == block2

    def test_append_with_transactions(self):
        """Block with transactions can be appended."""
        genesis = create_genesis_block(STATE_ROOT_A)
        chain = Blockchain(genesis)
        tx = Transaction(nonce=0, gas_price=1, gas=21000,
                         to=b"\x02" * 20, value=1000, data=b"",
                         v=27, r=123, s=456)
        block1 = create_block(genesis, [tx], STATE_ROOT_B, timestamp=100)
        chain.append_block(block1)
        assert len(chain.latest.transactions) == 1


class TestGetBlockByNumber:
    """Test Blockchain.get_block_by_number."""

    def test_get_genesis(self):
        """get_block_by_number(0) returns genesis block."""
        genesis = create_genesis_block(STATE_ROOT_A)
        chain = Blockchain(genesis)
        assert chain.get_block_by_number(0) == genesis

    def test_get_subsequent_block(self):
        """get_block_by_number returns the correct block."""
        genesis = create_genesis_block(STATE_ROOT_A)
        chain = Blockchain(genesis)
        block1 = create_block(genesis, [], STATE_ROOT_B, timestamp=100)
        chain.append_block(block1)
        assert chain.get_block_by_number(1) == block1

    def test_get_negative_number_raises(self):
        """Negative block number raises IndexError."""
        genesis = create_genesis_block(STATE_ROOT_A)
        chain = Blockchain(genesis)
        with pytest.raises(IndexError):
            chain.get_block_by_number(-1)

    def test_get_too_high_number_raises(self):
        """Block number beyond chain height raises IndexError."""
        genesis = create_genesis_block(STATE_ROOT_A)
        chain = Blockchain(genesis)
        with pytest.raises(IndexError):
            chain.get_block_by_number(5)


class TestValidateChain:
    """Test Blockchain.validate_chain."""

    def test_genesis_only_valid(self):
        """Single-block chain (genesis only) is valid."""
        genesis = create_genesis_block(STATE_ROOT_A)
        chain = Blockchain(genesis)
        assert chain.validate_chain() is True

    def test_valid_chain(self):
        """Chain of properly linked blocks validates."""
        genesis = create_genesis_block(STATE_ROOT_A)
        chain = Blockchain(genesis)
        block1 = create_block(genesis, [], STATE_ROOT_B, timestamp=100)
        chain.append_block(block1)
        block2 = create_block(block1, [], STATE_ROOT_C, timestamp=200)
        chain.append_block(block2)
        assert chain.validate_chain() is True

    def test_corrupted_chain_detected(self):
        """Chain with corrupted parent_hash is detected as invalid."""
        genesis = create_genesis_block(STATE_ROOT_A)
        chain = Blockchain(genesis)
        block1 = create_block(genesis, [], STATE_ROOT_B, timestamp=100)
        chain.append_block(block1)

        # Corrupt the internal block's parent_hash (simulate data corruption)
        chain._blocks[1].header.parent_hash = b"\xff" * 32
        assert chain.validate_chain() is False

    def test_validate_long_chain(self):
        """Validate works on chains with many blocks."""
        genesis = create_genesis_block(STATE_ROOT_A)
        chain = Blockchain(genesis)
        parent = genesis
        for i in range(10):
            state_root = keccak256(f"state_{i}".encode())
            block = create_block(parent, [], state_root, timestamp=100 * (i + 1))
            chain.append_block(block)
            parent = block
        assert chain.height == 10
        assert chain.validate_chain() is True
