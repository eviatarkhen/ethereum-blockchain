# Plan 03-02 Summary: Transaction Validation and State Transition

## What was built

Implemented transaction validation in Yellow Paper Section 6 order and the state transition function with snapshot/revert for atomic execution.

## Files created/modified

- `src/ethereum/core/__init__.py` — Package re-exports
- `src/ethereum/core/exceptions.py` — InvalidSignature, InvalidNonce, InsufficientBalance, ExceedsBlockGasLimit, IntrinsicGasTooLow
- `src/ethereum/core/tx_validator.py` — validate_transaction() with 5 checks in Yellow Paper order, calculate_intrinsic_gas()
- `src/ethereum/core/state_transition.py` — apply_transaction(), TransactionResult, _execute_value_transfer(), _execute_contract_call(), _execute_create() (stub)
- `src/ethereum/state/world_state.py` — Added snapshot(), revert(), add_balance(), deduct_balance(), increment_nonce(), transfer(), set_code(), get_storage(), set_storage()
- `tests/test_tx_validator.py` — 11 tests for validation order and intrinsic gas
- `tests/test_state_transition.py` — 9 tests for value transfer, contract calls, gas accounting

## Key decisions

- Validation order matches Yellow Paper exactly: signature -> nonce -> balance -> block gas -> intrinsic gas
- State snapshot/revert uses deepcopy (simple and correct for dict-backed state)
- On failure: nonce still increments, all gas consumed, state changes reverted
- Transaction field is `tx.gas` (not `tx.gas_limit`) matching the Transaction dataclass

## Test results

20 tests passed (11 + 9)
