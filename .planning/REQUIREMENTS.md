# Requirements: EduEthereum

**Defined:** 2026-02-19
**Core Value:** A developer can set breakpoints and trace the complete lifecycle of a transaction — from creation through EVM execution to state update and block inclusion.

## v1 Requirements

### Crypto & Encoding

- [x] **CRYPT-01**: Keccak-256 hashing using eth-hash (not hashlib.sha3_256)
- [x] **CRYPT-02**: ECDSA key pair generation and transaction signing
- [x] **CRYPT-03**: RLP encoding/decoding for transactions and blocks
- [x] **CRYPT-04**: Ethereum address derivation from public key

### State

- [x] **STATE-01**: Account model with balance, nonce, code hash, and storage
- [x] **STATE-02**: Dict-backed world state with get/set/update operations
- [x] **STATE-03**: Genesis state initialization with pre-funded accounts
- [ ] **STATE-04**: State transition function (apply transaction to world state)

### EVM

- [ ] **EVM-01**: Stack machine with ~20 core opcodes (arithmetic, comparison, stack, memory, storage, flow control)
- [ ] **EVM-02**: Gas metering (simplified — track and enforce gas limit)
- [ ] **EVM-03**: CREATE opcode for contract deployment
- [ ] **EVM-04**: CALL opcode for contract function calls

### Transactions

- [x] **TX-01**: Transaction structure (nonce, to, value, data, gas, signature)
- [x] **TX-02**: Transaction signing and sender recovery
- [ ] **TX-03**: Transaction validation (nonce check, balance check, gas limit)

### Blocks

- [x] **BLOCK-01**: Block structure (header with parent hash, state root, tx list)
- [x] **BLOCK-02**: Block creation / simplified mining (no PoW/PoS)
- [x] **BLOCK-03**: Chain management (append block, validate chain)

### Contracts

- [x] **CNTR-01**: Hardcoded counter contract (increment, get count)
- [x] **CNTR-02**: Hardcoded simple token contract (transfer, balance check)

### Learning Interface

- [ ] **LEARN-01**: Scenario script: simple ETH transfer end-to-end
- [ ] **LEARN-02**: Scenario script: deploy and interact with counter contract
- [ ] **LEARN-03**: Scenario script: deploy and interact with token contract
- [ ] **LEARN-04**: `# SIMPLIFIED:` comment convention marking all deviations from real Ethereum
- [ ] **LEARN-05**: Readable code with meaningful variable names for debugger inspection

## v2 Requirements

### Merkle Patricia Trie

- **MPT-01**: Full MPT implementation (branch, extension, leaf nodes)
- **MPT-02**: Hex-prefix encoding for trie keys
- **MPT-03**: State root computation replacing dict-backed state
- **MPT-04**: Separate tries (world state, storage, transactions)

### Enhanced Learning

- **ELEARN-01**: Execution trace mode (log each opcode step)
- **ELEARN-02**: Annotated bytecode disassembler utility

## Out of Scope

| Feature | Reason |
|---------|--------|
| Networking / P2P | Single node only — focus on internals |
| Full EVM (140+ opcodes) | Only ~20 needed for learning scenarios |
| Proof of Work / Proof of Stake | Consensus adds complexity without teaching core concepts |
| Solidity compiler | Hardcoded bytecode examples are sufficient |
| JSON-RPC API | Direct Python script interaction is simpler for debugging |
| Gas optimization / EIP-2929 | Simplified gas model is enough for learning |
| DELEGATECALL / STATICCALL | Complex context-switching; defer |
| LOG opcodes / event system | Not needed for counter/token scenarios |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| CRYPT-01 | Phase 1 | Complete |
| CRYPT-02 | Phase 1 | Complete |
| CRYPT-03 | Phase 1 | Complete |
| CRYPT-04 | Phase 1 | Complete |
| STATE-01 | Phase 2 | Complete |
| STATE-02 | Phase 2 | Complete |
| STATE-03 | Phase 2 | Complete |
| TX-01 | Phase 2 | Complete |
| TX-02 | Phase 2 | Complete |
| BLOCK-01 | Phase 2 | Complete |
| BLOCK-02 | Phase 2 | Complete |
| BLOCK-03 | Phase 2 | Complete |
| EVM-01 | Phase 3 | Pending |
| EVM-02 | Phase 3 | Pending |
| EVM-03 | Phase 3 | Pending |
| EVM-04 | Phase 3 | Pending |
| TX-03 | Phase 3 | Pending |
| STATE-04 | Phase 3 | Pending |
| LEARN-04 | Phase 3 | Pending |
| LEARN-05 | Phase 3 | Pending |
| CNTR-01 | Phase 4 | Complete |
| CNTR-02 | Phase 4 | Complete |
| LEARN-01 | Phase 4 | Pending |
| LEARN-02 | Phase 4 | Pending |
| LEARN-03 | Phase 4 | Pending |

**Coverage:**
- v1 requirements: 25 total
- Mapped to phases: 25
- Unmapped: 0

---
*Requirements defined: 2026-02-19*
*Last updated: 2026-02-19 after roadmap creation — all 25 requirements mapped*
