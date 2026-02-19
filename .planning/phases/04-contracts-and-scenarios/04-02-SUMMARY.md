---
phase: 04-contracts-and-scenarios
plan: 02
subsystem: scenarios
tags: [evm, scenario, transactions, breakpoints, contracts, state-transition]

# Dependency graph
requires:
  - phase: 04-contracts-and-scenarios
    plan: 01
    provides: COUNTER_RUNTIME_BYTECODE, TOKEN_RUNTIME_BYTECODE, ABI encoding helpers, compute_contract_address
  - phase: 03-evm-and-state
    provides: EVM execution, WorldState, apply_transaction, Block creation
  - phase: 01-crypto-and-encoding
    provides: generate_key_pair, sign_transaction, keccak256, RLP encoding
provides:
  - scenarios/01_eth_transfer.py: End-to-end ETH transfer with sign/apply/mine lifecycle
  - scenarios/02_counter.py: Counter contract deploy + increment + getCount scenario
  - scenarios/03_token.py: SimpleToken deploy + transfer + balanceOf scenario
affects:
  - Developers stepping through transactions in a debugger

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Minimal init code builder (PUSH1/CODECOPY/RETURN 12-byte header + runtime_bytecode)
    - Manual constructor storage init for simplified CREATE (no init code execution)
    - BREAKPOINT annotations at every major EVM state transition step

key-files:
  created:
    - scenarios/01_eth_transfer.py
    - scenarios/02_counter.py
    - scenarios/03_token.py
  modified:
    - src/ethereum/contracts/counter.py
    - src/ethereum/contracts/token.py

key-decisions:
  - "build_init_code helper: 12-byte PUSH1/CODECOPY/RETURN header + runtime bytecode as CREATE transaction data"
  - "Manual storage init in token scenario: set_storage(contract, int(deployer), INITIAL_SUPPLY) since simplified CREATE has no constructor execution"
  - "DIV operand order fix: PUSH32(2^224) must precede CALLDATALOAD so that CALLDATALOAD result is on TOP for DIV"

patterns-established:
  - "Scenario script structure: constants -> keygen -> genesis state -> genesis block -> transactions -> block packaging -> assertions -> summary"
  - "Build init code inline in scenario scripts for educational clarity"
  - "decode_uint256(data) helper to decode 32-byte ABI return values from contract calls"

requirements-completed: [LEARN-01, LEARN-02, LEARN-03]

# Metrics
duration: 8min
completed: 2026-02-19
---

# Phase 4 Plan 2: Contracts and Scenarios Summary

**Three end-to-end scenario scripts (ETH transfer, Counter contract, SimpleToken contract) with BREAKPOINT annotations, using all Phase 1-3 modules for sign/apply/mine lifecycle demonstration**

## Performance

- **Duration:** 8 min
- **Started:** 2026-02-19T11:44:20Z
- **Completed:** 2026-02-19T11:52:00Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments

- `01_eth_transfer.py`: Generates two key pairs, creates genesis state (1 ETH sender, 0 recipient), signs legacy transaction, applies state transition (21,000 gas), mines block #1, verifies sender decreased and recipient received 0.1 ETH
- `02_counter.py`: Deploys Counter with init code wrapping COUNTER_RUNTIME_BYTECODE, calls increment() (verifies storage[0]=1), calls getCount() (decodes 32-byte return), mines block containing all 3 transactions
- `03_token.py`: Deploys SimpleToken, manually sets deployer initial supply in storage, calls balanceOf() twice, calls transfer(recipient, 1000), verifies token conservation (deployer 999,000 + recipient 1,000 = INITIAL_SUPPLY)
- DIV operand order bug fixed in counter.py and token.py: PUSH32(2^224) moved before CALLDATALOAD so EVM DIV computes calldata_word // 2^224 correctly
- 19 BREAKPOINT annotations across all three scripts covering every major lifecycle step

## Task Commits

Each task was committed atomically:

1. **Task 1: ETH transfer scenario** - `12e005f` (feat)
2. **Task 2: Counter/token scenarios + bytecode DIV fix** - `d447cc2` (feat)

## Files Created/Modified

- `scenarios/01_eth_transfer.py` - 233 lines, 5 BREAKPOINT annotations
- `scenarios/02_counter.py` - 299 lines, 6 BREAKPOINT annotations
- `scenarios/03_token.py` - 391 lines, 8 BREAKPOINT annotations
- `src/ethereum/contracts/counter.py` - Fixed DIV operand order (PUSH32 before CALLDATALOAD)
- `src/ethereum/contracts/token.py` - Fixed DIV operand order (same pattern)

## Decisions Made

- `build_init_code` helper: 12-byte header (PUSH1/PUSH1/CODECOPY/PUSH1/PUSH1/RETURN) followed by runtime bytecode. This is the minimal CREATE init code pattern that copies runtime code to memory and returns it.
- Manual token storage init: `world_state.set_storage(contract_addr, int.from_bytes(deployer_addr, 'big'), INITIAL_SUPPLY)` with a clear `# SIMPLIFIED:` comment explaining real Solidity constructors run init code to set this.
- Both counter and token scenario scripts share the same `build_init_code` implementation (copied inline for standalone readability).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed DIV operand order in COUNTER_RUNTIME_BYTECODE and TOKEN_RUNTIME_BYTECODE**
- **Found during:** Task 2 (increment() call returned `execution failed`)
- **Issue:** CALLDATALOAD was pushed first, PUSH32(2^224) second. EVM DIV pops `a` (top = 2^224) then `b` (second = calldata_word), computes `2^224 // calldata_word = 0`. Selector was always 0, causing REVERT on every call.
- **Fix:** Moved PUSH32(2^224) before PUSH1/CALLDATALOAD so CALLDATALOAD result is on top when DIV executes. Result: `calldata_word // 2^224 = selector` (correct).
- **Files modified:** `src/ethereum/contracts/counter.py`, `src/ethereum/contracts/token.py`
- **Commit:** `d447cc2`
- **Tests:** All 30 existing contract tests still pass after fix.

## Issues Encountered

- Discovered that the DIV-based selector extraction bug was not caught by existing tests because tests only checked bytecode structure and encoding helpers (not live EVM execution). The fix is self-evident from EVM stack semantics: the divisor must be pushed before the dividend.

## User Setup Required

None — no external service configuration required. Run with `PYTHONPATH=src python3 scenarios/NN_name.py`.

## Next Phase Readiness

- Phase 4 is complete: contract bytecode (04-01) and scenario scripts (04-02) both done
- All three scenarios run end-to-end from project root
- BREAKPOINT annotations enable step-through debugging of every major state transition
- No blockers identified

## Self-Check: PASSED

All 3 scenario files confirmed on disk. Both task commits (12e005f, d447cc2) confirmed in git log.

---
*Phase: 04-contracts-and-scenarios*
*Completed: 2026-02-19*
