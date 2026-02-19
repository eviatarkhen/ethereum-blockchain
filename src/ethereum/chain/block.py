"""Ethereum block structure.

A Block is a single link in the chain that is Ethereum. Each Block contains
a Header and zero or more transactions. The Header contains metadata like
the block number, parent block hash, timestamp, and state root.

Together, blocks form a cryptographically secure journal recording the
history of all state transitions since genesis.

# SIMPLIFIED: Minimal header with 4 fields instead of 15+ in real Ethereum.
# Real headers include: ommers_hash, coinbase, transactions_root,
# receipt_root, bloom, difficulty, gas_limit, gas_used, extra_data,
# mix_digest, nonce. We keep only what's needed for chain linking
# and state tracking — per user decision.
# SIMPLIFIED: No ommers (uncle blocks), no receipts, no logs.
"""

from dataclasses import dataclass, field
from typing import List

from ethereum.crypto.hashing import keccak256
from ethereum.encoding.rlp import rlp_encode, int_to_rlp_bytes
from ethereum.transactions.transaction import Transaction


GENESIS_PARENT_HASH = b"\x00" * 32
"""Parent hash for the genesis block (32 zero bytes).

The genesis block has no parent, so by convention its parent_hash
is all zeros.
"""


@dataclass
class Header:
    """Minimal Ethereum block header.

    Contains only the essential fields for chain linking and state tracking.

    Attributes:
        parent_hash: Hash of the parent block's header (32 bytes).
                     Creates the chain linkage.
        number: Block height in the chain (0 for genesis).
        timestamp: Unix timestamp of block creation.
        state_root: Hash representing the world state after this block
                    (32 bytes). Placeholder until MPT in v2.

    # SIMPLIFIED: Only 4 fields instead of 15+ in real Ethereum.
    # Missing fields: ommers_hash, coinbase, transactions_root,
    # receipt_root, bloom, difficulty, gas_limit, gas_used,
    # extra_data, mix_digest, nonce.
    """
    parent_hash: bytes
    number: int
    timestamp: int
    state_root: bytes


@dataclass
class Block:
    """Ethereum block containing a header and transactions.

    A block bundles transactions that have been applied to the state.
    The header's parent_hash links to the previous block, forming the chain.

    Attributes:
        header: Block header with metadata.
        transactions: List of signed transactions in this block.

    # SIMPLIFIED: No ommers (uncle blocks), no receipts.
    # Real Ethereum blocks also contain ommer headers and
    # generate transaction receipts during execution.
    """
    header: Header
    transactions: List[Transaction] = field(default_factory=list)


def block_hash(block: Block) -> bytes:
    """Compute block hash from header fields.

    The block hash uniquely identifies a block and is used as the
    parent_hash in the next block, creating the chain linkage.

    This is keccak256(RLP([parent_hash, number, timestamp, state_root])).

    Args:
        block: Block to compute hash for.

    Returns:
        32-byte keccak256 hash of RLP-encoded header fields.

    # SIMPLIFIED: Only hashing our 4 minimal header fields.
    # Real Ethereum RLP-encodes all 15+ header fields.
    """
    header_fields = [
        block.header.parent_hash,
        int_to_rlp_bytes(block.header.number),
        int_to_rlp_bytes(block.header.timestamp),
        block.header.state_root,
    ]
    return keccak256(rlp_encode(header_fields))


def create_genesis_block(state_root: bytes, timestamp: int = 0) -> Block:
    """Create the genesis (first) block of the chain.

    The genesis block has no parent (parent_hash is 32 zero bytes),
    block number 0, and no transactions. It represents the initial
    state of the blockchain.

    Args:
        state_root: Hash representing the initial world state.
        timestamp: Genesis timestamp (default 0).

    Returns:
        Genesis Block with empty transaction list.
    """
    header = Header(
        parent_hash=GENESIS_PARENT_HASH,
        number=0,
        timestamp=timestamp,
        state_root=state_root,
    )
    return Block(header=header, transactions=[])


def create_block(
    parent: Block,
    transactions: List[Transaction],
    state_root: bytes,
    timestamp: int,
) -> Block:
    """Create a new block linked to a parent block.

    Sets parent_hash to the hash of the parent block and
    increments block number by 1.

    Args:
        parent: The previous block in the chain.
        transactions: Signed transactions to include in this block.
        state_root: World state root hash after applying transactions.
        timestamp: Block timestamp (Unix seconds).

    Returns:
        New Block linked to parent via parent_hash.
    """
    header = Header(
        parent_hash=block_hash(parent),
        number=parent.header.number + 1,
        timestamp=timestamp,
        state_root=state_root,
    )
    return Block(header=header, transactions=transactions)
