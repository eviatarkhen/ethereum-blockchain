---
phase: 04-contracts-and-scenarios
plan: 01
subsystem: contracts
tags: [evm, bytecode, abi, keccak256, rlp, solidity]

# Dependency graph
requires:
  - phase: 01-crypto-and-encoding
    provides: keccak256 for selector computation and RLP encoding for address derivation
provides:
  - COUNTER_RUNTIME_BYTECODE: 88-byte hand-crafted EVM bytecode for Counter contract
  - TOKEN_RUNTIME_BYTECODE: 112-byte hand-crafted EVM bytecode for SimpleToken contract
  - compute_selector: 4-byte keccak256 function selector computation
  - encode_uint256, encode_address, encode_call: ABI encoding primitives
  - compute_contract_address: keccak256(RLP([sender, nonce]))[12:] derivation
  - encode_increment, encode_get_count, encode_transfer, encode_balance_of: calldata helpers
affects:
  - 04-contracts-and-scenarios (plan 02, scenario scripts use these artifacts)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - DIV-based 4-byte selector extraction from CALLDATALOAD (no SHR opcode available)
    - Simplified direct-address storage mapping (address as storage key, no SHA3 opcode)
    - Hardcoded bytes() literals with per-opcode inline comments for human-readable bytecode
    - ABI encoding: 32-byte left-zero-padded address, big-endian uint256

key-files:
  created:
    - src/ethereum/contracts/__init__.py
    - src/ethereum/contracts/abi.py
    - src/ethereum/contracts/address.py
    - src/ethereum/contracts/counter.py
    - src/ethereum/contracts/token.py
    - tests/test_contracts.py
  modified: []

key-decisions:
  - "DIV-based selector extraction: PUSH32(2^224)/DIV used instead of SHR because opcodes.py does not define SHR (0x1c)"
  - "Simplified storage mapping: balance[address] stored at storage[int(address)] to avoid SHA3 opcode requirement"
  - "contracts/address.py is temporary home for compute_contract_address; should consolidate to core/address.py if Phase 3 creates it"

patterns-established:
  - "Bytecode layout table as docstring: offset, size, instruction, notes for each opcode"
  - "DECISION comments in bytecode files explaining opcode availability tradeoffs"
  - "SIMPLIFIED comments marking deviations from production Ethereum behavior"

requirements-completed: [CNTR-01, CNTR-02]

# Metrics
duration: 5min
completed: 2026-02-19
---

# Phase 4 Plan 1: Contracts and Scenarios Summary

**Hand-crafted Counter (88 bytes) and SimpleToken (112 bytes) EVM bytecode with DIV-based function dispatch, ABI encoding utilities, and keccak256+RLP contract address derivation**

## Performance

- **Duration:** 5 min
- **Started:** 2026-02-19T11:35:29Z
- **Completed:** 2026-02-19T11:41:28Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- ABI encoding primitives: compute_selector (keccak256[:4]), encode_uint256 (32-byte big-endian), encode_address (12-zero-pad + 20-byte address), encode_call (selector + args)
- compute_contract_address implements keccak256(RLP([sender, nonce]))[12:] with correct nonce=0 edge case (encodes as empty bytes -> 0x80 in RLP)
- Counter bytecode: 88-byte DIV-based dispatcher routing to increment() and getCount() handlers with correct JUMPDEST offsets (0x3f=63, 0x4b=75)
- SimpleToken bytecode: 112-byte dispatcher routing to transfer() (with balance check + REVERT at 0x5c=92) and balanceOf() handlers
- 30 tests all passing: selectors, ABI encoding, address derivation, bytecode structure, calldata helpers

## Task Commits

Each task was committed atomically:

1. **Task 1: ABI encoding utilities and contract address derivation** - `1819147` (feat)
2. **Task 2: Counter and Token bytecode with encoding helpers and tests** - `190cf76` (feat)

**Plan metadata:** (docs commit below)

## Files Created/Modified
- `src/ethereum/contracts/__init__.py` - Package init with module docstring
- `src/ethereum/contracts/abi.py` - compute_selector, encode_uint256, encode_address, encode_call
- `src/ethereum/contracts/address.py` - compute_contract_address using keccak256 + RLP
- `src/ethereum/contracts/counter.py` - COUNTER_RUNTIME_BYTECODE (88 bytes), encode_increment, encode_get_count
- `src/ethereum/contracts/token.py` - TOKEN_RUNTIME_BYTECODE (112 bytes), INITIAL_SUPPLY, encode_transfer, encode_balance_of
- `tests/test_contracts.py` - 30 tests covering all contract functionality

## Decisions Made
- DIV-based selector extraction chosen over SHR because opcodes.py (Phase 3 EVM) does not define SHR (0x1c). PUSH32(2^224)/DIV right-shifts 224 bits to extract the 4-byte selector.
- Simplified storage mapping for token: balance[addr] at storage[int(addr)] avoids requiring the SHA3 opcode. Documented with SIMPLIFIED comment.
- contracts/address.py is the initial home for compute_contract_address; should consolidate to core/address.py if Phase 3 creates that module.

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered
- 2^224 byte representation needed careful verification: `(2**224).to_bytes(32, 'big')` = `0x00000001` followed by 28 zero bytes (not `0x00000000_00000001`). Fixed before committing.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness
- All contract artifacts ready for scenario scripts (plan 04-02)
- Both bytecode constants are importable and contain verified function selectors
- ABI encoding helpers produce correct calldata for all four contract functions
- No blockers identified

## Self-Check: PASSED

All 7 created files confirmed on disk. Both task commits (1819147, 190cf76) confirmed in git log.

---
*Phase: 04-contracts-and-scenarios*
*Completed: 2026-02-19*
