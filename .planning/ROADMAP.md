# Roadmap: EduEthereum

## Overview

Build a simplified, single-node Ethereum blockchain in Python that a developer can step through with a debugger to understand the complete transaction lifecycle. The build follows the strict dependency order mandated by the Ethereum protocol: cryptographic primitives first, then state data structures, then the EVM and execution engine, then contracts and scenario scripts. Each phase delivers a coherent, independently testable layer before the next begins.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Crypto and Encoding** - Keccak-256, ECDSA, address derivation, and RLP — the zero-dependency foundation everything else depends on
- [ ] **Phase 2: State and Data Structures** - Account model, world state, transaction structure, and block structure — the data layer that enables EVM execution
- [ ] **Phase 3: EVM and Execution Engine** - Stack machine with ~25 opcodes, gas metering, state transition function, and code standards for debuggability
- [ ] **Phase 4: Contracts and Scenarios** - Hardcoded example contracts and guided scenario scripts that deliver the complete learning experience

## Phase Details

### Phase 1: Crypto and Encoding
**Goal**: The cryptographic primitives and encoding layer are correct and verified against known test vectors
**Depends on**: Nothing (first phase)
**Requirements**: CRYPT-01, CRYPT-02, CRYPT-03, CRYPT-04
**Success Criteria** (what must be TRUE):
  1. `keccak256(b"")` returns `c5d2460186f7233c927e7db2dcc703c0e500b653ca82273b7bfad8045d85a470` — the canonical empty-input vector
  2. A generated key pair can sign a message and the signature can recover the original address
  3. An Ethereum address can be derived from a public key and matches the expected 20-byte, 0x-prefixed format
  4. RLP encode/decode round-trips correctly for integers, byte strings, and nested lists, including the `0 encodes as 0x80` edge case
**Plans**: TBD

### Phase 2: State and Data Structures
**Goal**: The account model, world state, transaction structure, and block structure exist as correct Python dataclasses with genesis initialization
**Depends on**: Phase 1
**Requirements**: STATE-01, STATE-02, STATE-03, TX-01, TX-02, BLOCK-01, BLOCK-02, BLOCK-03
**Success Criteria** (what must be TRUE):
  1. A genesis world state can be initialized with pre-funded accounts and queried by address
  2. A transaction can be created, signed with a private key, and the original sender address recovered from the signature
  3. A block can be created with a header (parent hash, state root placeholder, timestamp) and a list of signed transactions
  4. The blockchain can append a new block and validate that the chain links correctly via parent hashes
**Plans**: TBD

### Phase 3: EVM and Execution Engine
**Goal**: The EVM executes bytecode correctly against real world state, gas is tracked and enforced, and all code is written to the readability and annotation standard
**Depends on**: Phase 2
**Requirements**: EVM-01, EVM-02, EVM-03, EVM-04, TX-03, STATE-04, LEARN-04, LEARN-05
**Success Criteria** (what must be TRUE):
  1. The EVM stack machine executes arithmetic, comparison, stack manipulation, memory, storage, and flow control opcodes correctly with mod 2^256 on all arithmetic
  2. A transaction that exceeds the gas limit raises an out-of-gas exception and leaves state unchanged
  3. A transaction is validated in the correct Yellow Paper order (signature, nonce, balance, intrinsic gas) before any state mutation occurs
  4. The state transition function applies a value transfer transaction to world state, updating sender and recipient balances and incrementing sender nonce
  5. Every intentional deviation from real Ethereum is marked with a `# SIMPLIFIED:` comment, and all variable names are meaningful for debugger inspection
**Plans**: TBD

### Phase 4: Contracts and Scenarios
**Goal**: A developer can run scenario scripts that demonstrate the full transaction lifecycle — ETH transfer, contract deployment, and contract interaction — and set breakpoints at any step
**Depends on**: Phase 3
**Requirements**: CNTR-01, CNTR-02, LEARN-01, LEARN-02, LEARN-03
**Success Criteria** (what must be TRUE):
  1. Running the ETH transfer scenario script produces a confirmed transaction in a mined block with updated sender and recipient balances
  2. Running the counter scenario script deploys the counter contract, calls increment, and reads back the updated count — all traceable via debugger
  3. Running the token scenario script deploys the token contract, transfers tokens between accounts, and confirms the updated balances
  4. A developer can set a breakpoint anywhere in a scenario script and inspect the full EVM state (stack, memory, storage, program counter, gas remaining) at that point
**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Crypto and Encoding | 0/? | Not started | - |
| 2. State and Data Structures | 0/? | Not started | - |
| 3. EVM and Execution Engine | 0/? | Not started | - |
| 4. Contracts and Scenarios | 0/? | Not started | - |
