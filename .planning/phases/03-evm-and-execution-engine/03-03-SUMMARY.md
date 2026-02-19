# Plan 03-03 Summary: CREATE and CALL Opcodes

## What was built

Implemented CREATE opcode for contract deployment and CALL opcode for inter-contract calls, replacing the stubs from Plan 03-01.

## Files created/modified

- `src/ethereum/core/address.py` — compute_contract_address(sender, nonce) using keccak256(rlp([sender, nonce]))[12:]
- `src/ethereum/core/__init__.py` — Added compute_contract_address re-export
- `src/ethereum/core/state_transition.py` — Replaced _execute_create() stub with full implementation
- `src/ethereum/evm/vm.py` — Replaced _op_create() and _op_call() stubs with full implementations
- `tests/test_create.py` — 11 tests for address computation and contract deployment
- `tests/test_call.py` — 8 tests for inter-contract calls

## Key decisions

- Contract address is deterministic: keccak256(rlp([sender, nonce]))[12:]
- CREATE runs init code in a child EVM; return data becomes runtime code stored at computed address
- CALL forwards requested gas (capped at remaining), executes target code, persists storage on success
- CALL to EOA (no code) is just a value transfer, pushes 1 (success)
- Out-of-gas in callee pushes 0 on caller's stack; caller continues execution
- Gas forwarded to CALL tests must be sufficient for SSTORE (5000 gas); used PUSH2 for larger amounts
- No CREATE2, DELEGATECALL, or STATICCALL (annotated with SIMPLIFIED)

## Test results

19 tests passed (11 create + 8 call)
Full suite: 295 tests passed
