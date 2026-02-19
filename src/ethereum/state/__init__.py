"""Ethereum state data structures.

Provides the account model and world state that represent
Ethereum's state between transactions.
"""

from ethereum.state.account import Account, EMPTY_ACCOUNT
from ethereum.state.world_state import WorldState, create_genesis_state

__all__ = ["Account", "EMPTY_ACCOUNT", "WorldState", "create_genesis_state"]
