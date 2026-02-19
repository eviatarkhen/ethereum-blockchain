# EduEthereum — Simplified Ethereum Blockchain

## What This Is

A simplified, single-node Ethereum blockchain implementation in Python, built for learning. It covers the core Ethereum concepts — accounts, transactions, blocks, EVM execution, smart contracts, and Merkle Patricia Tries — with code designed to be stepped through with a debugger. Not a production system; a teaching tool.

## Core Value

A developer can set breakpoints and trace the complete lifecycle of a transaction — from creation through EVM execution to state update and block inclusion — understanding exactly how Ethereum works at each step.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] Account model with balances, nonces, and contract storage
- [ ] Transaction creation, signing, and validation
- [ ] Block structure with headers and transaction lists
- [ ] EVM with ~20-30 core opcodes (stack, memory, storage, flow control)
- [ ] Smart contract deployment and function calls
- [ ] Merkle Patricia Trie for state storage and verification
- [ ] RLP encoding/decoding
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
| Python over Rust/Go | Debugger-friendly, readable, fast to build | — Pending |
| Single node | Eliminates P2P complexity, focus on core concepts | — Pending |
| Hardcoded contracts over compiler | Avoids compiler complexity, still shows full EVM flow | — Pending |
| Scenario scripts over REPL | Guided learning paths, easy to set breakpoints | — Pending |

---
*Last updated: 2026-02-19 after initialization*
