"""State transition function — the core of Ethereum.

The state transition function takes a transaction and the current
world state, and produces the new world state after applying the
transaction. This is the single most important function in Ethereum:
it defines how the state machine evolves.

Flow:
1. Validate transaction (Yellow Paper order)
2. Snapshot state for potential rollback
3. Deduct upfront gas cost from sender
4. Increment sender nonce
5. Execute (value transfer, contract call, or contract creation)
6. On failure: revert to snapshot (but keep nonce + gas consumption)
7. Refund unused gas to sender

# SIMPLIFIED: No gas refund mechanism for SSTORE clears.
# SIMPLIFIED: No coinbase/validator reward.
# SIMPLIFIED: No EIP-1559 base fee burning.
"""

from dataclasses import dataclass

from ethereum.core.tx_validator import validate_transaction, calculate_intrinsic_gas
from ethereum.evm.vm import EVM, ExecutionContext, ExecutionResult
from ethereum.evm.exceptions import OutOfGas, EVMError


@dataclass
class TransactionResult:
    """Result of applying a transaction to world state.

    Attributes:
        success: True if execution completed without revert/error.
        return_data: Bytes returned by the executed code.
        gas_used: Total gas consumed by the transaction.
        gas_remaining: Gas refunded to sender.
        error: Error description if failed, None if success.
        contract_address: Address of created contract (if CREATE), None otherwise.
    """
    success: bool
    return_data: bytes
    gas_used: int
    gas_remaining: int
    error: str | None = None
    contract_address: bytes | None = None


def apply_transaction(tx, world_state, block_gas_limit: int) -> TransactionResult:
    """Apply a signed transaction to world state.

    This is THE state transition function. It takes the current state
    and a transaction, and produces the new state.

    On success: state changes are committed, unused gas refunded.
    On failure: state is reverted to pre-transaction snapshot,
    but nonce still increments and gas is consumed.

    Set a breakpoint at the top of this function to trace the
    complete lifecycle of a transaction.

    Args:
        tx: Signed transaction to apply.
        world_state: Current world state (will be modified in place).
        block_gas_limit: Maximum gas allowed in current block.

    Returns:
        TransactionResult with execution details.
    """
    # === Step 1: Validate ===
    # This raises on failure — invalid transactions never touch state.
    sender = validate_transaction(tx, world_state, block_gas_limit)

    # === Step 2: Snapshot for rollback ===
    state_snapshot = world_state.snapshot()

    # Calculate costs upfront
    upfront_gas_cost = tx.gas * tx.gas_price
    intrinsic_gas = calculate_intrinsic_gas(tx.data)
    gas_for_execution = tx.gas - intrinsic_gas

    try:
        # === Step 3: Deduct upfront gas cost ===
        # Sender pays for ALL gas upfront. Unused gas is refunded later.
        world_state.deduct_balance(sender, upfront_gas_cost)

        # === Step 4: Increment sender nonce ===
        world_state.increment_nonce(sender)

        # === Step 5: Execute ===
        if tx.to == b"":
            # Contract creation (to == empty bytes)
            # Placeholder — full CREATE in Plan 03-03
            result = _execute_create(tx, sender, world_state, gas_for_execution)
        elif world_state.get_account(tx.to).code:
            # Contract call (recipient has code)
            result = _execute_contract_call(tx, sender, world_state, gas_for_execution)
        else:
            # Simple value transfer (recipient is EOA or empty)
            result = _execute_value_transfer(tx, sender, world_state, gas_for_execution)

        # === Step 6: Handle failure ===
        if not result.success:
            # Revert ALL state changes from execution
            world_state.revert(state_snapshot)
            # Re-apply nonce increment and gas deduction (these survive revert)
            world_state.deduct_balance(sender, upfront_gas_cost)
            world_state.increment_nonce(sender)
            # All gas consumed on failure
            gas_remaining = 0
            gas_used = tx.gas
        else:
            gas_remaining = result.gas_remaining
            gas_used = tx.gas - gas_remaining

        # === Step 7: Refund unused gas ===
        # # SIMPLIFIED: No gas refund cap (real Ethereum caps at 1/5 of gas used).
        gas_refund = gas_remaining * tx.gas_price
        if gas_refund > 0:
            world_state.add_balance(sender, gas_refund)

        return TransactionResult(
            success=result.success,
            return_data=result.return_data,
            gas_used=gas_used,
            gas_remaining=gas_remaining,
            error=None if result.success else "execution failed",
            contract_address=getattr(result, 'contract_address', None),
        )

    except (OutOfGas, EVMError) as e:
        # EVM exception during execution — revert and consume all gas
        world_state.revert(state_snapshot)
        world_state.deduct_balance(sender, upfront_gas_cost)
        world_state.increment_nonce(sender)
        return TransactionResult(
            success=False,
            return_data=b"",
            gas_used=tx.gas,
            gas_remaining=0,
            error=str(e),
        )

    except Exception as e:
        # Unexpected error — revert and consume all gas
        world_state.revert(state_snapshot)
        world_state.deduct_balance(sender, upfront_gas_cost)
        world_state.increment_nonce(sender)
        return TransactionResult(
            success=False,
            return_data=b"",
            gas_used=tx.gas,
            gas_remaining=0,
            error=f"unexpected error: {e}",
        )


def _execute_value_transfer(tx, sender: bytes, world_state,
                            gas_available: int) -> ExecutionResult:
    """Execute a simple ETH transfer (no contract code).

    Transfers tx.value from sender to recipient. Creates recipient
    account if it doesn't exist.

    Args:
        tx: Transaction with value to transfer.
        sender: 20-byte sender address.
        world_state: World state to modify.
        gas_available: Gas available after intrinsic cost.

    Returns:
        ExecutionResult (always success for simple transfers).
    """
    if tx.value > 0:
        # Create recipient if doesn't exist, then transfer
        world_state.transfer(sender, tx.to, tx.value)

    return ExecutionResult(
        success=True,
        return_data=b"",
        gas_used=0,  # No EVM execution gas for simple transfers
        gas_remaining=gas_available,
    )


def _execute_contract_call(tx, sender: bytes, world_state,
                           gas_available: int) -> ExecutionResult:
    """Execute a call to a contract (recipient has code).

    Transfers value, then runs the contract's bytecode in the EVM.

    Args:
        tx: Transaction calling the contract.
        sender: 20-byte sender address.
        world_state: World state to modify.
        gas_available: Gas available for EVM execution.

    Returns:
        ExecutionResult from EVM execution.
    """
    contract = world_state.get_account(tx.to)

    # Transfer value first
    if tx.value > 0:
        world_state.transfer(sender, tx.to, tx.value)

    # Set up execution context
    context = ExecutionContext(
        caller=sender,
        address=tx.to,
        value=tx.value,
        data=tx.data,
        gas=gas_available,
    )

    # Load contract storage as int->int dict
    contract_storage = dict(contract.storage)

    # Execute bytecode
    evm = EVM(
        code=contract.code,
        context=context,
        storage=contract_storage,
        world_state=world_state,
    )

    try:
        result = evm.execute()
    except OutOfGas:
        return ExecutionResult(
            success=False,
            return_data=b"",
            gas_used=gas_available,
            gas_remaining=0,
        )

    # If successful, persist storage changes
    if result.success:
        for key, value in evm.storage.items():
            world_state.set_storage(tx.to, key, value)

    return result


def _execute_create(tx, sender: bytes, world_state,
                    gas_available: int) -> ExecutionResult:
    """Execute contract creation (to is empty).

    Placeholder for Plan 03-03. Currently returns failure.

    # TODO: Full implementation in Plan 03-03.
    """
    return ExecutionResult(
        success=False,
        return_data=b"",
        gas_used=gas_available,
        gas_remaining=0,
    )
