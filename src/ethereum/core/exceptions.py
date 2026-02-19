"""Transaction validation exception classes.

Each exception represents a specific validation failure in the
Yellow Paper Section 6 validation order. All exceptions store
their arguments as attributes for debugger inspection.
"""


class TransactionError(Exception):
    """Base exception for all transaction validation errors."""
    pass


class InvalidSignature(TransactionError):
    """Raised when transaction signature is invalid or sender cannot be recovered.

    This is the first check in Yellow Paper order.
    """

    def __init__(self, reason: str = ""):
        self.reason = reason
        super().__init__(f"Invalid transaction signature: {reason}" if reason else
                         "Invalid transaction signature")


class InvalidNonce(TransactionError):
    """Raised when transaction nonce doesn't match sender's account nonce.

    This is the second check in Yellow Paper order.
    Prevents transaction replay and ensures ordering.

    Attributes:
        expected: The sender's current account nonce.
        got: The nonce in the transaction.
    """

    def __init__(self, expected: int, got: int):
        self.expected = expected
        self.got = got
        super().__init__(
            f"Invalid nonce: expected {expected}, got {got}"
        )


class InsufficientBalance(TransactionError):
    """Raised when sender can't cover value + gas cost.

    This is the third check in Yellow Paper order.

    Attributes:
        required: Total cost (value + gas_limit * gas_price).
        available: Sender's current balance.
    """

    def __init__(self, required: int, available: int):
        self.required = required
        self.available = available
        super().__init__(
            f"Insufficient balance: need {required}, have {available}"
        )


class ExceedsBlockGasLimit(TransactionError):
    """Raised when transaction gas limit exceeds block gas limit.

    This is the fourth check in Yellow Paper order.

    Attributes:
        tx_gas: Transaction's gas limit.
        block_limit: Block's gas limit.
    """

    def __init__(self, tx_gas: int, block_limit: int):
        self.tx_gas = tx_gas
        self.block_limit = block_limit
        super().__init__(
            f"Transaction gas {tx_gas} exceeds block gas limit {block_limit}"
        )


class IntrinsicGasTooLow(TransactionError):
    """Raised when gas limit is below intrinsic gas cost.

    This is the fifth check in Yellow Paper order.
    Even empty transactions need at least 21000 gas.

    Attributes:
        required: Intrinsic gas cost.
        provided: Transaction's gas limit.
    """

    def __init__(self, required: int, provided: int):
        self.required = required
        self.provided = provided
        super().__init__(
            f"Intrinsic gas too low: need {required}, provided {provided}"
        )
