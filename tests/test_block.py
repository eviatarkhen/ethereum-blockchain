"""Tests for Ethereum block structure.

Tests Header and Block dataclasses, block_hash computation,
genesis block creation, and create_block factory.
"""

import pytest
from ethereum.chain.block import (
    Header,
    Block,
    block_hash,
    create_genesis_block,
    create_block,
    GENESIS_PARENT_HASH,
)
from ethereum.transactions.transaction import Transaction
from ethereum.crypto.hashing import keccak256


# Test constants
STATE_ROOT_A = keccak256(b"state_a")
STATE_ROOT_B = keccak256(b"state_b")
PARENT_HASH = keccak256(b"parent")


class TestHeaderCreation:
    """Test Header dataclass creation."""

    def test_header_with_all_fields(self):
        """Header stores parent_hash, number, timestamp, state_root."""
        header = Header(
            parent_hash=PARENT_HASH,
            number=1,
            timestamp=1000000,
            state_root=STATE_ROOT_A,
        )
        assert header.parent_hash == PARENT_HASH
        assert header.number == 1
        assert header.timestamp == 1000000
        assert header.state_root == STATE_ROOT_A

    def test_header_has_exactly_four_fields(self):
        """Header has only the 4 minimal fields per user decision."""
        header = Header(
            parent_hash=PARENT_HASH,
            number=0,
            timestamp=0,
            state_root=STATE_ROOT_A,
        )
        # Verify only expected fields exist
        fields = {f.name for f in header.__dataclass_fields__.values()}
        assert fields == {"parent_hash", "number", "timestamp", "state_root"}


class TestBlockCreation:
    """Test Block dataclass creation."""

    def test_block_with_header_and_transactions(self):
        """Block stores header and transaction list."""
        header = Header(
            parent_hash=PARENT_HASH,
            number=1,
            timestamp=1000,
            state_root=STATE_ROOT_A,
        )
        tx = Transaction(nonce=0, gas_price=1, gas=21000,
                         to=b"\x02" * 20, value=1000, data=b"")
        block = Block(header=header, transactions=[tx])
        assert block.header == header
        assert len(block.transactions) == 1

    def test_block_with_empty_transactions(self):
        """Block can be created with no transactions."""
        header = Header(
            parent_hash=PARENT_HASH,
            number=0,
            timestamp=0,
            state_root=STATE_ROOT_A,
        )
        block = Block(header=header)
        assert block.transactions == []

    def test_block_default_empty_transactions(self):
        """Block defaults to empty transaction list."""
        header = Header(
            parent_hash=PARENT_HASH,
            number=0,
            timestamp=0,
            state_root=STATE_ROOT_A,
        )
        block = Block(header=header)
        assert block.transactions == []


class TestBlockHash:
    """Test block_hash computation."""

    def test_returns_32_bytes(self):
        """block_hash returns a 32-byte hash."""
        genesis = create_genesis_block(STATE_ROOT_A)
        h = block_hash(genesis)
        assert len(h) == 32
        assert isinstance(h, bytes)

    def test_deterministic(self):
        """Same block always produces the same hash."""
        block1 = create_genesis_block(STATE_ROOT_A, timestamp=100)
        block2 = create_genesis_block(STATE_ROOT_A, timestamp=100)
        assert block_hash(block1) == block_hash(block2)

    def test_changes_with_parent_hash(self):
        """Different parent_hash produces different block hash."""
        header1 = Header(parent_hash=b"\x00" * 32, number=1,
                         timestamp=100, state_root=STATE_ROOT_A)
        header2 = Header(parent_hash=b"\x01" * 32, number=1,
                         timestamp=100, state_root=STATE_ROOT_A)
        b1 = Block(header=header1)
        b2 = Block(header=header2)
        assert block_hash(b1) != block_hash(b2)

    def test_changes_with_number(self):
        """Different block number produces different hash."""
        header1 = Header(parent_hash=PARENT_HASH, number=1,
                         timestamp=100, state_root=STATE_ROOT_A)
        header2 = Header(parent_hash=PARENT_HASH, number=2,
                         timestamp=100, state_root=STATE_ROOT_A)
        assert block_hash(Block(header=header1)) != block_hash(Block(header=header2))

    def test_changes_with_timestamp(self):
        """Different timestamp produces different hash."""
        header1 = Header(parent_hash=PARENT_HASH, number=1,
                         timestamp=100, state_root=STATE_ROOT_A)
        header2 = Header(parent_hash=PARENT_HASH, number=1,
                         timestamp=200, state_root=STATE_ROOT_A)
        assert block_hash(Block(header=header1)) != block_hash(Block(header=header2))

    def test_changes_with_state_root(self):
        """Different state_root produces different hash."""
        header1 = Header(parent_hash=PARENT_HASH, number=1,
                         timestamp=100, state_root=STATE_ROOT_A)
        header2 = Header(parent_hash=PARENT_HASH, number=1,
                         timestamp=100, state_root=STATE_ROOT_B)
        assert block_hash(Block(header=header1)) != block_hash(Block(header=header2))


class TestGenesisBlock:
    """Test create_genesis_block factory."""

    def test_genesis_parent_hash_is_zeros(self):
        """Genesis block has parent_hash of 32 zero bytes."""
        genesis = create_genesis_block(STATE_ROOT_A)
        assert genesis.header.parent_hash == b"\x00" * 32
        assert genesis.header.parent_hash == GENESIS_PARENT_HASH

    def test_genesis_block_number_zero(self):
        """Genesis block has number 0."""
        genesis = create_genesis_block(STATE_ROOT_A)
        assert genesis.header.number == 0

    def test_genesis_empty_transactions(self):
        """Genesis block has no transactions."""
        genesis = create_genesis_block(STATE_ROOT_A)
        assert genesis.transactions == []

    def test_genesis_state_root(self):
        """Genesis block stores the provided state root."""
        genesis = create_genesis_block(STATE_ROOT_A)
        assert genesis.header.state_root == STATE_ROOT_A

    def test_genesis_default_timestamp(self):
        """Genesis block defaults to timestamp 0."""
        genesis = create_genesis_block(STATE_ROOT_A)
        assert genesis.header.timestamp == 0

    def test_genesis_custom_timestamp(self):
        """Genesis block can have a custom timestamp."""
        genesis = create_genesis_block(STATE_ROOT_A, timestamp=1234567890)
        assert genesis.header.timestamp == 1234567890

    def test_genesis_hash_deterministic(self):
        """Same genesis parameters produce the same block hash."""
        g1 = create_genesis_block(STATE_ROOT_A, timestamp=100)
        g2 = create_genesis_block(STATE_ROOT_A, timestamp=100)
        assert block_hash(g1) == block_hash(g2)


class TestCreateBlock:
    """Test create_block factory."""

    def test_links_to_parent(self):
        """New block's parent_hash is the hash of the parent block."""
        genesis = create_genesis_block(STATE_ROOT_A)
        block = create_block(genesis, [], STATE_ROOT_B, timestamp=1000)
        assert block.header.parent_hash == block_hash(genesis)

    def test_increments_block_number(self):
        """New block's number is parent.number + 1."""
        genesis = create_genesis_block(STATE_ROOT_A)
        block = create_block(genesis, [], STATE_ROOT_B, timestamp=1000)
        assert block.header.number == 1

    def test_stores_transactions(self):
        """New block stores the provided transactions."""
        genesis = create_genesis_block(STATE_ROOT_A)
        tx = Transaction(nonce=0, gas_price=1, gas=21000,
                         to=b"\x02" * 20, value=1000, data=b"")
        block = create_block(genesis, [tx], STATE_ROOT_B, timestamp=1000)
        assert len(block.transactions) == 1
        assert block.transactions[0] == tx

    def test_chain_of_three_blocks(self):
        """Three blocks form a chain with correct linkage."""
        b0 = create_genesis_block(STATE_ROOT_A)
        b1 = create_block(b0, [], STATE_ROOT_B, timestamp=100)
        b2 = create_block(b1, [], STATE_ROOT_A, timestamp=200)
        assert b1.header.parent_hash == block_hash(b0)
        assert b2.header.parent_hash == block_hash(b1)
        assert b0.header.number == 0
        assert b1.header.number == 1
        assert b2.header.number == 2
