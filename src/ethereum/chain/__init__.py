"""Ethereum block and blockchain management.

Provides block structure, block hashing, genesis creation,
and chain management with validation.
"""

from ethereum.chain.block import (
    Header,
    Block,
    block_hash,
    create_genesis_block,
    create_block,
    GENESIS_PARENT_HASH,
)
from ethereum.chain.blockchain import Blockchain

__all__ = [
    "Header",
    "Block",
    "block_hash",
    "create_genesis_block",
    "create_block",
    "GENESIS_PARENT_HASH",
    "Blockchain",
]
