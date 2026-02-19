"""Blockchain chain management.

The Blockchain stores an ordered sequence of blocks and validates
chain integrity. Every block (except genesis) must reference the
hash of its predecessor, forming an unbroken cryptographic chain.

# SIMPLIFIED: No fork choice, no difficulty adjustment, no reorgs.
# Real Ethereum has a fork choice rule (LMD GHOST + Casper FFG)
# that selects the canonical chain from competing forks.
# This is a single linear chain for educational purposes.
"""

from typing import List

from ethereum.chain.block import Block, block_hash


class Blockchain:
    """Simple blockchain that validates chain integrity.

    Stores blocks in order and validates parent_hash linkage
    on every append. The chain always starts with a genesis block.

    Usage:
        genesis = create_genesis_block(state_root)
        chain = Blockchain(genesis)
        chain.append_block(next_block)
        assert chain.validate_chain()
    """

    def __init__(self, genesis: Block):
        """Initialize blockchain with a genesis block.

        Args:
            genesis: The genesis block (number=0, parent_hash=0x00*32).
        """
        self._blocks: List[Block] = [genesis]
        self._block_hashes: List[bytes] = [block_hash(genesis)]

    @property
    def latest(self) -> Block:
        """Get the latest (head) block in the chain."""
        return self._blocks[-1]

    @property
    def height(self) -> int:
        """Get the current chain height (latest block number)."""
        return self.latest.header.number

    def append_block(self, block: Block) -> bytes:
        """Append a block to the chain after validation.

        Validates two properties:
        1. Block's parent_hash matches the hash of the current latest block
        2. Block's number is exactly latest.number + 1

        Args:
            block: Block to append.

        Returns:
            Hash of the appended block (32 bytes).

        Raises:
            ValueError: If parent_hash doesn't match or block number is wrong.
        """
        expected_parent_hash = self._block_hashes[-1]
        if block.header.parent_hash != expected_parent_hash:
            raise ValueError(
                f"Invalid parent hash: expected {expected_parent_hash.hex()}, "
                f"got {block.header.parent_hash.hex()}"
            )

        expected_number = self.height + 1
        if block.header.number != expected_number:
            raise ValueError(
                f"Invalid block number: expected {expected_number}, "
                f"got {block.header.number}"
            )

        new_hash = block_hash(block)
        self._blocks.append(block)
        self._block_hashes.append(new_hash)
        return new_hash

    def get_block_by_number(self, number: int) -> Block:
        """Get a block by its block number.

        Args:
            number: Block number (0 = genesis).

        Returns:
            Block at the given number.

        Raises:
            IndexError: If block number is out of range.
        """
        if number < 0 or number >= len(self._blocks):
            raise IndexError(
                f"Block number {number} out of range "
                f"(0-{len(self._blocks) - 1})"
            )
        return self._blocks[number]

    def validate_chain(self) -> bool:
        """Validate the entire chain's parent_hash linkage.

        Checks that each block's parent_hash matches the hash
        of the previous block, forming an unbroken chain from
        genesis to head.

        Returns:
            True if chain is valid, False if any link is broken.
        """
        for i in range(1, len(self._blocks)):
            expected_parent = block_hash(self._blocks[i - 1])
            if self._blocks[i].header.parent_hash != expected_parent:
                return False
        return True
