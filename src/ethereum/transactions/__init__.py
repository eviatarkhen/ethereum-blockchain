"""Ethereum transaction structure and signing.

Provides the Transaction dataclass and functions for signing
transactions and recovering the sender address.
"""

from ethereum.transactions.transaction import (
    Transaction,
    sign_transaction,
    recover_sender,
    signing_hash,
)

__all__ = ["Transaction", "sign_transaction", "recover_sender", "signing_hash"]
