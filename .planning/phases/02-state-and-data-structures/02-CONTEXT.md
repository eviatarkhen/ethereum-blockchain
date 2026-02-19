# Phase 2: State and Data Structures - Context

**Gathered:** 2026-02-19
**Status:** Ready for planning

<domain>
## Phase Boundary

Account model, world state, transaction structure, and block structure — the data layer that enables EVM execution. This phase delivers correct Python dataclasses with genesis initialization, transaction signing, and chain linking. Does NOT include EVM execution, gas computation, or contract logic.

</domain>

<decisions>
## Implementation Decisions

### Account model design
- Claude's discretion on EOA vs contract account distinction (single class vs subclasses)
- Claude's discretion on balance/nonce types (plain ints vs validated types)
- Claude's discretion on storage representation (plain dict vs wrapper class)
- Claude's discretion on data structure choice (dataclass vs plain class)

### World state operations
- Claude's discretion on genesis initialization approach (config dict vs hardcoded)
- Claude's discretion on whether to build rollback/snapshot support now or defer to Phase 3
- Claude's discretion on API style (method-based vs direct dict access)
- Claude's discretion on state root placeholder (simple hash vs dummy value)

### Transaction structure
- Claude's discretion on transaction format (legacy only vs EIP-1559)
- Claude's discretion on signed/unsigned transaction relationship (two classes vs single class)
- Claude's discretion on signing API (high-level helper vs direct primitives vs both)
- Claude's discretion on contract address derivation timing (Phase 2 vs Phase 3)

### Block and chain linking
- **Minimal block header**: parent_hash, block_number, timestamp, state_root placeholder — no gas_used, difficulty, or other fields
- Claude's discretion on genesis block creation (factory function vs regular constructor)
- Claude's discretion on whether Blockchain validates on append or just stores
- Claude's discretion on block hashing approach (RLP+keccak vs simpler)

### Claude's Discretion
The user has given Claude full discretion on nearly all implementation decisions for this phase. The guiding principles should be:
1. **Debugger readability** — structures should display clearly when stepping through code
2. **Educational value** — show how Ethereum works, not just mimic it
3. **Phase 1 integration** — use the crypto/encoding primitives built in Phase 1 where it demonstrates the protocol

</decisions>

<specifics>
## Specific Ideas

- Block header should be minimal (parent_hash, block_number, timestamp, state_root placeholder) — user explicitly chose simplicity over realism for header fields
- All other design decisions are open to standard approaches that best serve the educational/debugging goal

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 02-state-and-data-structures*
*Context gathered: 2026-02-19*
