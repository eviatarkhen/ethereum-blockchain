# Phase 3: EVM and Execution Engine - Context

**Gathered:** 2026-02-19
**Status:** Ready for planning

<domain>
## Phase Boundary

Stack-based virtual machine that executes bytecode with ~25 opcodes, tracks and enforces gas, validates transactions in Yellow Paper order, and applies state transitions (value transfers and contract execution). All code is written for debugger stepping and annotated with `# SIMPLIFIED:` where it deviates from real Ethereum. Contract deployment (CREATE) is included here so Phase 4 only writes scenario scripts.

</domain>

<decisions>
## Implementation Decisions

### Opcode selection and grouping
- **Contract-driven selection**: Only include opcodes required by Counter and SimpleToken contracts. Every opcode must have a concrete reason to exist — no speculative additions.
- Unsupported opcodes: Claude's discretion on whether to raise a named `UnsupportedOpcode` error or treat as INVALID halt.
- Code organization: Claude's discretion on whether to use one function per opcode or grouped handler methods — optimize for debugger stepping.
- CALL-family opcodes: Claude determines based on what Counter and SimpleToken actually need.

### Debug/learning annotations
- Execution tracing approach: Claude's discretion — choose the method (structured trace, print logging, or debugger-only variables) that best serves the learning goal.
- Step mode: Claude's discretion on whether to offer a `step()` API or rely on continuous execution with breakpoint-friendly code.
- SIMPLIFIED markers in trace: Claude's discretion on whether deviations appear only as code comments or also in trace output.
- Execution results: Claude's discretion on whether to return a summary object or raw outcome.

### Gas model behavior
- SSTORE gas: Claude's discretion on simplification level (flat cost vs two-tier cold/warm). Mark deviation with `# SIMPLIFIED:`.
- Out-of-gas behavior: Claude's discretion — follow Ethereum spec correctness (full rollback expected).
- Gas cost structure: Claude's discretion on dictionary table vs hardcoded constants.
- Intrinsic gas: Claude's discretion on full calculation (21000 + calldata bytes) vs flat 21000.

### Transaction validation flow
- Error types: Claude's discretion on custom exception classes per failure vs single exception with reason.
- State transition code path: Claude's discretion on unified `apply_transaction()` vs separate transfer/contract paths.
- Validation logging: Claude's discretion on step-by-step validation log vs debugger-only inspection.
- Contract deployment (CREATE): Included in Phase 3 — the EVM and state transition function handle deployment so Phase 4 focuses on scenario scripts.

### Claude's Discretion
The user delegated most implementation details to Claude. Key constraint: all decisions should optimize for **debugger stepping and educational clarity**. The user cares about the learning experience — being able to set breakpoints and understand what's happening at each step. Technical choices (code structure, trace format, gas model specifics, error handling patterns) are Claude's to make within that constraint.

</decisions>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches. The overarching principle is: a developer should be able to set breakpoints and trace the complete lifecycle of a transaction through EVM execution.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 03-evm-and-execution-engine*
*Context gathered: 2026-02-19*
