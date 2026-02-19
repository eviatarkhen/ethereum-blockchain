"""Ethereum core transaction processing.

Provides transaction validation and the state transition function
that orchestrates validation, EVM execution, and state commit/rollback.
"""

from ethereum.core.address import compute_contract_address
from ethereum.core.tx_validator import validate_transaction, calculate_intrinsic_gas
from ethereum.core.state_transition import apply_transaction, TransactionResult
from ethereum.core.exceptions import (
    TransactionError,
    InvalidSignature,
    InvalidNonce,
    InsufficientBalance,
    ExceedsBlockGasLimit,
    IntrinsicGasTooLow,
)

__all__ = [
    "compute_contract_address",
    "validate_transaction",
    "calculate_intrinsic_gas",
    "apply_transaction",
    "TransactionResult",
    "TransactionError",
    "InvalidSignature",
    "InvalidNonce",
    "InsufficientBalance",
    "ExceedsBlockGasLimit",
    "IntrinsicGasTooLow",
]
