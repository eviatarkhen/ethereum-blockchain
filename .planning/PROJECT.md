# EduEthereum — Simplified Ethereum Blockchain

## What This Is

A simplified, single-node Ethereum blockchain implementation in Python, built for learning. It covers the core Ethereum concepts — accounts, transactions, blocks, EVM execution, smart contracts, and Merkle Patricia Tries — with code designed to be stepped through with a debugger. Not a production system; a teaching tool.

## Core Value

A developer can set breakpoints and trace the complete lifecycle of a transaction — from creation through EVM execution to state update and block inclusion — understanding exactly how Ethereum works at each step.

## Requirements

### Validated

- Keccak-256 hashing (eth-hash with pycryptodome backend) -- Phase 1
- ECDSA key generation, signing, and recovery (eth-keys) -- Phase 1
- Ethereum address derivation from public key -- Phase 1
- RLP encoding/decoding (from-scratch implementation) -- Phase 1

### Active

- [ ] Account model with balances, nonces, and contract storage
- [ ] Transaction creation, signing, and validation
- [ ] Block structure with headers and transaction lists
- [ ] EVM with ~20-30 core opcodes (stack, memory, storage, flow control)
- [ ] Smart contract deployment and function calls
- [ ] State transitions (applying transactions to world state)
- [ ] Pre-built example contracts (counter, simple token) in bytecode
- [ ] Python scenario scripts for guided exploration (transfer, deploy, call contract)
- [ ] Clear, readable code with meaningful variable names for debugger inspection

### Out of Scope

- Networking/P2P — single node only, focus on internals
- Full EVM (140+ opcodes) — only core ~20-30 needed for learning
- Proof of Stake / consensus — simple block creation, no consensus complexity
- Solidity compiler — use hardcoded bytecode examples instead
- JSON-RPC API — interact via Python scripts directly
- Gas optimization — implement gas conceptually but skip optimization edge cases
- Interactive REPL — scenario scripts are sufficient

## Context

- The Ethereum Yellow Paper (Gavin Wood) is included in the repo as reference
- Target audience: the developer building this (self-learning)
- Python chosen for readability and easy debugging (breakpoints, inspect variables)
- Single-node eliminates networking complexity, keeping focus on blockchain internals
- Hardcoded example contracts avoid needing a compiler while still demonstrating smart contract flows

## Constraints

- **Language**: Python — readability and debugger-friendly
- **Scope**: ~3-5K lines — solid foundation without becoming overwhelming
- **Dependencies**: Minimal external dependencies — core crypto libs only
- **No networking**: Single-node architecture

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Python over Rust/Go | Debugger-friendly, readable, fast to build | Confirmed |
| Single node | Eliminates P2P complexity, focus on core concepts | Confirmed |
| Hardcoded contracts over compiler | Avoids compiler complexity, still shows full EVM flow | — Pending |
| Scenario scripts over REPL | Guided learning paths, easy to set breakpoints | — Pending |
| eth-hash[pycryptodome] for Keccak-256 | Eliminates Keccak vs SHA-3 confusion, portable backend | Validated Phase 1 |
| eth-keys NativeECCBackend for ECDSA | Pure Python, ideal for debugger stepping | Validated Phase 1 |
| From-scratch RLP over pyrlp | Educational value -- specification is simple enough to implement | Validated Phase 1 |
| MPT deferred to v2 | Dict-backed world state sufficient for v1 learning | — Pending |

---
*Last updated: 2026-02-19 after Phase 1*
