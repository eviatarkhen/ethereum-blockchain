# EduEthereum — Simplified Ethereum Blockchain

## What This Is

A simplified, single-node Ethereum blockchain implementation in Python, built for learning. It covers the core Ethereum concepts — accounts, transactions, blocks, EVM execution, and smart contracts — with code designed to be stepped through with a debugger. v1.0 shipped with 8,037 lines of Python across 49 files, including 3 runnable scenario scripts that demonstrate complete transaction lifecycles. Not a production system; a teaching tool.

## Core Value

A developer can set breakpoints and trace the complete lifecycle of a transaction — from creation through EVM execution to state update and block inclusion — understanding exactly how Ethereum works at each step.

## Requirements

### Validated (v1.0)

- Keccak-256 hashing (eth-hash with pycryptodome backend) — v1.0
- ECDSA key generation, signing, and recovery (eth-keys) — v1.0
- Ethereum address derivation from public key — v1.0
- RLP encoding/decoding (from-scratch implementation) — v1.0
- Account model with balances, nonces, and contract storage — v1.0
- Transaction creation, signing, and validation — v1.0
- Block structure with headers and transaction lists — v1.0
- EVM with ~25 core opcodes (stack, memory, storage, flow control) — v1.0
- Smart contract deployment (CREATE) and function calls (CALL) — v1.0
- State transitions (applying transactions to world state) — v1.0
- Pre-built example contracts (counter, simple token) in bytecode — v1.0
- Python scenario scripts for guided exploration (transfer, deploy, call contract) — v1.0
- Clear, readable code with meaningful variable names for debugger inspection — v1.0

### Active

None — planning for next milestone not started.

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
| Hardcoded contracts over compiler | Avoids compiler complexity, still shows full EVM flow | Validated Phase 4 |
| Scenario scripts over REPL | Guided learning paths, easy to set breakpoints | Validated Phase 4 |
| eth-hash[pycryptodome] for Keccak-256 | Eliminates Keccak vs SHA-3 confusion, portable backend | Validated Phase 1 |
| eth-keys NativeECCBackend for ECDSA | Pure Python, ideal for debugger stepping | Validated Phase 1 |
| From-scratch RLP over pyrlp | Educational value -- specification is simple enough to implement | Validated Phase 1 |
| MPT deferred to v2 | Dict-backed world state sufficient for v1 learning | Confirmed — v1 complete without MPT |
| DIV-based selector extraction | SHR opcode not in Phase 3 EVM; DIV(calldata, 2^224) works | Validated Phase 4 |
| Simplified storage mapping | address as storage key directly; avoids SHA3 opcode requirement | Validated Phase 4 |

---
*Last updated: 2026-02-19 after Phase 4 — v1 milestone complete*
