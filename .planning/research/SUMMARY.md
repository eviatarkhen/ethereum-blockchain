# Project Research Summary

**Project:** Educational Ethereum Blockchain Implementation in Python
**Domain:** Single-node, debugger-oriented Ethereum protocol implementation
**Researched:** 2026-02-19
**Confidence:** MEDIUM-HIGH

## Executive Summary

This project is an educational Python implementation of the Ethereum protocol designed to make the full transaction lifecycle inspectable via a debugger. Research confirms there is a well-defined build order grounded in the Ethereum Yellow Paper: cryptographic primitives first, then encoding (RLP), then state data structures, then execution (EVM), then block assembly, then scenario scripts. The key insight from all four research streams is that the dependency graph is strict — you cannot test EVM without state, cannot produce correct block hashes without correct RLP, and cannot demonstrate anything meaningful without a working keccak-256 wrapper using the correct algorithm (not Python's built-in SHA3). The Ethereum Foundation's own Python libraries (eth-hash, eth-keys, rlp/pyrlp, eth-utils) provide the correct cryptographic primitives without implementing the full protocol for you, which is exactly the gap this project fills.

The recommended approach is a 5-phase build in strict dependency order, deferring the Merkle Patricia Trie (the most complex single component) until after the EVM and transaction execution are working end-to-end. The architecture should use pure state transition functions (`apply_transaction(state, tx) -> (new_state, receipt)`) matching the Yellow Paper formulation, an isolated EVM class that receives a storage snapshot and returns mutations rather than mutating world state directly, and in-memory Python dicts for all state storage. No P2P networking, no JSON-RPC API, no Solidity compiler, no consensus mechanism — these would triple the codebase without improving the learning outcome. Hardcoded bytecode contracts with annotated disassembly and guided scenario scripts are the delivery mechanism.

The primary risks are cryptographic correctness (keccak vs SHA-3 confusion silently corrupts all hashes), EVM arithmetic overflow (Python integers are unbounded, EVM requires mod 2^256 on all arithmetic), and RLP edge cases (the integer `0` encodes as `0x80`, not `0x00`). All three risks are preventable by building a test vector verification suite in the first phase before any other component is wired together. The Merkle Patricia Trie introduces additional implementation complexity (four distinct node types, hex-prefix encoding, 32-byte inline/hash threshold) that warrants its own phase with dedicated pitfall mitigations.

## Key Findings

### Recommended Stack

The Ethereum Foundation's Python library suite provides all necessary primitives without the abstraction overhead of a full client. Python 3.12 (not 3.13, which has trailing compatibility gaps) is the target version. The stack is intentionally minimal: five libraries plus pytest, all from the Ethereum Foundation or closely related projects.

**Core technologies:**
- **Python 3.12** — implementation language; 3.12 is stable LTS-equivalent with full Ethereum library support
- **eth-hash 0.7.1 + pycryptodome backend** — correct keccak-256 (not SHA-3); use `from eth_hash.auto import keccak`
- **eth-keys 0.7.0** — secp256k1 ECDSA signing/verification with correct Ethereum signature semantics (r, s, v)
- **rlp (pyrlp) 4.1.0** — Ethereum Foundation RLP library; sedes map cleanly onto Block/Transaction dataclasses
- **eth-utils 5.3.1** — EIP-55 address checksumming, hex conversions, unit conversions
- **pytest 9.0.x** — test runner; parametrize and fixtures make opcode and state tests readable
- **Python stdlib only** — dataclasses for data models, dict for world state, logging for EVM trace; no database

**What NOT to use:** `py-evm` (archived September 2025), `web3.py` (RPC client, wrong layer), `hashlib.sha3_256` (wrong algorithm — silent data corruption), `pyethash` (PoW-specific, removed), any database (LevelDB, RocksDB — hide trie structure, complicate setup).

See `.planning/research/STACK.md` for full version compatibility matrix and installation commands.

### Expected Features

The MVP delivers a complete transaction lifecycle traceable step-by-step in a Python debugger. The feature set is deliberately constrained to ~25-30 opcodes, two example contracts, and four scenario scripts. Full opcode coverage (140+ opcodes), Solidity compilation, P2P networking, JSON-RPC, and consensus mechanisms are explicitly out of scope.

**Must have (table stakes for v1):**
- keccak-256 and ECDSA wrappers — every other component depends on these
- Account model (nonce, balance, code, storage) — EOA vs contract distinction
- RLP encode/decode — required for transaction hashing, block hashing, trie values
- Transaction structure (type 0 legacy) + signing + sender recovery
- World state (in-memory dict, address -> Account)
- State transition function: validate tx, deduct gas, apply EVM or value transfer
- EVM machine state: stack (1024 items, 256-bit words), memory (volatile bytearray), storage (256->256 per contract)
- EVM core opcodes: ~25-30 covering arithmetic, comparison, stack ops, memory ops, storage ops, flow control, call context
- Gas accounting (static costs per opcode, OOG exception)
- Contract deployment (CREATE opcode: run init bytecode, derive address, store runtime bytecode)
- Contract function call (CALL opcode: load bytecode, pass calldata, handle REVERT)
- Block structure (header + transaction list) + simple sealing
- Hardcoded example contracts: Counter (increment/get) and SimpleToken (transfer/balanceOf) as annotated bytecode
- Four scenario scripts: ETH transfer, deploy counter, call increment, token transfer
- Annotated disassembly utility: `disassemble(bytecode)` printing offset/hex/mnemonic/operand

**Should have (v1.x after core validated):**
- Merkle Patricia Trie (state trie) — closes the cryptographic loop; state root in block headers
- EVM verbose/trace mode — per-opcode state dump (stack, memory, storage, PC, gas)
- Execution receipts (status, gas used, logs)
- Yellow Paper section references in all module docstrings
- Transaction trie root (low cost once MPT exists)

**Defer (v2+):**
- Trie inclusion proof generation — highest complexity, not needed for transaction tracing
- EIP-1559 type 2 transactions — adds fee market mechanics without teaching core concepts
- Additional example contracts (auction, voting)

See `.planning/research/FEATURES.md` for full dependency graph and comparable implementation analysis.

### Architecture Approach

The architecture is a strict 6-layer stack: Crypto Primitives -> Data Structures (RLP + MPT) -> State (Account + WorldState) -> Execution (EVM + apply_transaction) -> Chain (Block + Blockchain) -> Scenarios. Each layer depends only on layers below it. The EVM is isolated: it receives a storage snapshot and returns mutations — it never directly touches WorldState. State transition is a pure function matching the Yellow Paper's Υ(σ,T)=σ' formulation. All state lives in-memory Python dicts. No side effects, no global mutable state.

**Major components:**
1. **Crypto Primitives** (`crypto/`) — keccak256 wrapper, secp256k1 keypair/sign/verify, address derivation; zero dependencies
2. **RLP Encoding** (`encoding/rlp.py`) — standalone encode/decode; needed by trie, block, and transaction hashing
3. **Merkle Patricia Trie** (`trie/`) — BranchNode, ExtensionNode, LeafNode + MerklePatriciaTrie; depends only on crypto + RLP
4. **State** (`state/`) — Account dataclass + WorldState wrapping the MPT; exposes get_account/set_account
5. **EVM** (`evm/`) — opcode dispatch table (dict: byte -> handler), EVM class with stack/memory/storage/PC/gas; depends on state
6. **Execution** (`execution/apply_transaction.py`) — glue: calls EVM, merges storage mutations, produces receipts
7. **Core** (`core/`) — Transaction, Block, BlockHeader dataclasses + Blockchain chain management
8. **Contracts** (`contracts/`) — hardcoded bytecode bytes + ABI selector helpers; pure data, no runtime deps
9. **Scenarios** (`scenarios/`) — top-level learning scripts; entry points for breakpoint-driven exploration

See `.planning/research/ARCHITECTURE.md` for full project structure, data flow diagrams, and architectural patterns.

### Critical Pitfalls

Research identified 6 critical pitfalls that cause rewrites or silently produce incorrect Ethereum state, plus 10 moderate/minor pitfalls.

1. **Keccak-256 vs SHA-3 confusion** — `hashlib.sha3_256` produces FIPS SHA-3, not Ethereum keccak; every hash will be wrong silently. Prevention: use `eth_hash.auto.keccak`; add test `keccak256("") == "c5d246..."` in Phase 1 before building anything else.

2. **Python integers are not 256-bit** — EVM arithmetic requires `% (2**256)` on every result; Python int grows unbounded. Prevention: apply modular arithmetic in every arithmetic opcode from day one; test `ADD(2**256-1, 1) == 0`.

3. **RLP encoding edge cases** — integer `0` encodes as `0x80` (empty string), not `0x00`; strings >55 bytes need length-of-length prefix. Prevention: test against official Ethereum RLP test vectors before connecting RLP to any other component.

4. **JUMPDEST validation ignores PUSH immediates** — naive scan for `0x5B` includes PUSH data bytes as valid jump targets. Prevention: build JUMPDEST set by skipping N immediate bytes after each PUSH_N opcode.

5. **Four Merkle Patricia Tries conflated** — world state trie, per-account storage trie, transaction trie, receipt trie have different keys/values; mixing them produces wrong state roots. Prevention: implement each as a named separate instance; account's `storage_root` is a bytes32 hash, not a dict.

6. **Transaction validation order wrong** — Yellow Paper specifies: signature valid -> nonce matches -> balance sufficient -> intrinsic gas check -> then state mutation. Checking out of order allows invalid transactions to partially modify state. Prevention: implement validation as a pure function returning a validated object before any mutation.

See `.planning/research/PITFALLS.md` for full pitfall catalog including 10 moderate/minor pitfalls with detection tests.

## Implications for Roadmap

Based on the dependency graph from ARCHITECTURE.md and feature priorities from FEATURES.md, research strongly recommends a 5-phase build in strict dependency order. The Merkle Patricia Trie is deliberately placed in Phase 4 (not Phase 1) to unblock EVM development. This is the single most important structural decision: building MPT first blocks all other progress, but deferring it past Phase 3 means scenarios lack state root integrity.

### Phase 1: Crypto and Encoding Foundation

**Rationale:** Everything else depends on keccak-256 and RLP. These are the only zero-dependency components. The keccak pitfall (wrong algorithm) must be caught here with a test vector check before any other code is written. This phase has no architecture risk but has the highest correctness risk if skipped or rushed.

**Delivers:** `crypto/hash.py` (keccak256), `crypto/keys.py` (secp256k1 keypair, sign, verify, recover), `crypto/address.py` (address derivation), `encoding/rlp.py` (encode/decode), test suite covering known keccak and RLP vectors.

**Addresses:** Table stakes — keccak-256, ECDSA wrappers, RLP encode/decode.

**Avoids:** Pitfall 1 (SHA-3 vs keccak), Pitfall 3 (RLP edge cases), Pitfall 15 (float for ETH values established here as int-wei convention).

**Research flag:** Standard patterns; no additional research needed.

### Phase 2: State Data Structures (Account and WorldState)

**Rationale:** EVM cannot be built without state (SLOAD/SSTORE need a real storage model). WorldState with a simple dict backing store unblocks all EVM and transaction work immediately. The real MPT backing store is deferred to Phase 4 — this is the key anti-pattern avoidance identified in ARCHITECTURE.md.

**Delivers:** `state/account.py` (Account dataclass: nonce, balance, code_hash, storage_root), `state/world_state.py` (WorldState with dict-backed get_account/set_account + placeholder state_root), Transaction and Block dataclasses in `core/`.

**Addresses:** Account model, world state, transaction structure, block structure.

**Avoids:** Pitfall 15 (integer wei), Anti-Pattern 3 (Full MPT from day one), Anti-Pattern 2 (mutable global state).

**Research flag:** Standard patterns; Yellow Paper sections 4 and 6 are the spec.

### Phase 3: EVM and Transaction Execution

**Rationale:** This is the core of the project. With state in place, the EVM can be built and tested end-to-end against real state reads/writes. The opcode dispatch table (dict: byte -> handler) scales cleanly. apply_transaction as a pure function is the architectural centerpiece. Contracts and scenario scripts follow immediately after EVM is working.

**Delivers:** `evm/opcodes.py` (~25-30 opcodes), `evm/evm.py` (EVM class with stack/memory/storage/PC/gas), `evm/gas.py` (static cost constants), `execution/apply_transaction.py` (pure state transition), `contracts/counter.py` + `contracts/token.py` (hardcoded bytecode + ABI helpers), disassembly utility, all four scenario scripts.

**Addresses:** EVM machine state, gas accounting, contract deployment (CREATE), contract call (CALL), hardcoded example contracts, scenario scripts, annotated disassembly.

**Avoids:** Pitfall 2 (mod 2^256 on all arithmetic), Pitfall 4 (JUMPDEST validation), Pitfall 6 (transaction validation order), Pitfall 13 (bytes vs int type conventions), Pitfall 16 (PC advance order), Anti-Pattern 1 (EVM before state — state is already done), Anti-Pattern 4 (EVM mixed into Block class).

**Research flag:** NEEDS deeper research during planning. EVM opcode semantics (especially CALL gas forwarding, SSTORE gas, memory expansion formula) have multiple EIP-layered rules. Recommend reviewing `evm.codes` and wolflo/evm-opcodes gas.md before planning opcode implementations.

### Phase 4: Merkle Patricia Trie

**Rationale:** MPT is the most implementation-intensive single component (~200-400 lines), with its own pitfall cluster (hex-prefix encoding, 32-byte inline threshold, four distinct trie types). It is deferred until after EVM works so its complexity cannot block the core learning path. Once complete, WorldState upgrades from dict-backing to MPT-backing, and block headers gain real state roots.

**Delivers:** `trie/nodes.py` (BranchNode, ExtensionNode, LeafNode), `trie/trie.py` (MerklePatriciaTrie with insert/get/root_hash), WorldState upgraded to MPT backing, block headers with real state_root, transactions_root, receipts_root.

**Addresses:** Merkle Patricia Trie (state trie), state root in block headers.

**Avoids:** Pitfall 5 (four tries conflated), Pitfall 9 (hex-prefix encoding), Pitfall 10 (32-byte inline threshold), Anti-Pattern 3 (MPT built too early, blocking everything else).

**Research flag:** NEEDS deeper research during planning. MPT hex-prefix encoding, node inlining rules, and the separation of world state trie from per-account storage trie are all sources of subtle bugs. Recommend referencing Ethereum official MPT docs and ethereum/tests RLP test vectors before implementation.

### Phase 5: Polish, Tracing, and Documentation

**Rationale:** Once all core components work, the educational value multiplier features are low-cost additions: verbose EVM trace mode, execution receipts, Yellow Paper section references in all docstrings, SIMPLIFICATIONS.md documenting all intentional deviations. This phase requires no new architecture work and no external research.

**Delivers:** EVM verbose/trace mode (per-opcode state dump), execution receipts (status, gas_used, logs), Yellow Paper section references in all module docstrings, `SIMPLIFICATIONS.md` documenting every intentional deviation from the protocol spec.

**Addresses:** EVM trace output, execution receipts, inline documentation explaining WHY (differentiator), Yellow Paper annotation pass.

**Avoids:** Pitfall 11 (simplifications not marked as simplifications — this is the phase to formally document all of them).

**Research flag:** Standard patterns; no additional research needed.

### Phase Ordering Rationale

- **Crypto before everything:** keccak-256 and RLP have zero dependencies and are prerequisites for every other component. A bug here corrupts the entire system silently.
- **State before EVM:** EVM opcodes SLOAD/SSTORE require a working storage model. Building EVM without state forces mocking that creates false confidence (ARCHITECTURE.md Anti-Pattern 1).
- **EVM before MPT:** MPT is complex and self-contained. Deferring it lets EVM and transactions be built and validated with a simpler dict-backed state. This is the critical sequencing insight — confirmed by all four research files independently.
- **MPT as its own phase:** The hex-prefix encoding, four-trie separation, and 32-byte threshold pitfalls are dense enough to warrant isolation in their own phase with dedicated testing before integration.
- **Polish last:** Trace mode, receipts, and annotation are value multipliers that require working core code — they cannot be built first and shouldn't be attempted until Phase 3 is complete.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 3 (EVM):** CALL gas forwarding (EIP-150 63/64 rule), SSTORE gas (EIP-2200 three-value formula), memory expansion (quadratic formula). Reference: `evm.codes`, wolflo/evm-opcodes/gas.md, Yellow Paper Appendix H.
- **Phase 4 (MPT):** Hex-prefix encoding four cases, 32-byte inline/hash threshold, per-account storage trie separation from world state trie. Reference: Ethereum official MPT docs, ethereum/tests RLP test vectors.

Phases with standard patterns (skip research-phase):
- **Phase 1 (Crypto + RLP):** Well-documented; just use eth-hash and pyrlp libraries; test against known vectors.
- **Phase 2 (State):** Yellow Paper sections 4 and 6 are the complete spec; dict-backed WorldState is straightforward.
- **Phase 5 (Polish):** No new architecture; annotation and documentation work.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Core libraries (eth-hash, eth-keys, rlp, eth-utils) are Ethereum Foundation official; versions verified on PyPI Feb-Aug 2025. py-evm archival date confirmed from official Ethereum Foundation post. |
| Features | MEDIUM-HIGH | Table stakes features from Yellow Paper and EELS are HIGH confidence. Educational feature patterns (scenario scripts, annotated bytecode) are MEDIUM based on comparable project survey. |
| Architecture | HIGH | Grounded in Yellow Paper state transition formulas, py-evm module organization, and official Ethereum documentation. Pure function pattern and EVM isolation are well-validated by reference implementations. |
| Pitfalls | MEDIUM-HIGH | Cryptographic pitfalls (keccak, RLP) are HIGH confidence from official sources. EVM pitfalls (JUMPDEST, mod 2^256) are HIGH from spec + multiple tutorial postmortems. MPT pitfalls are MEDIUM from official docs + implementation guides. |

**Overall confidence:** MEDIUM-HIGH

### Gaps to Address

- **EVM opcode gas costs in detail:** Static gas costs for all ~30 implemented opcodes need to be confirmed against evm.codes or Yellow Paper Appendix G before Phase 3 planning. The EIP-2929 warm/cold access list gas rules add complexity that may need a simplification decision.
- **Hardcoded contract bytecode source:** The Counter and SimpleToken bytecode need to be sourced or compiled once and locked. The research recommends pre-compiled bytecode strings; the actual bytecode generation (compile a Solidity contract once offline, extract bytecode) is not detailed and should be addressed in Phase 3 planning.
- **SSTORE EIP-2200 complexity decision:** The three-value SSTORE gas formula (original, current, new values) with warm/cold access is significantly complex. A simplification to a flat gas cost with a `# SIMPLIFIED:` comment may be the right call — this decision should be made explicitly during Phase 3 planning.
- **eth-keys version confidence:** STACK.md notes eth-keys 0.7.0 and eth-utils 5.3.1 versions came from search results (PyPI page returned JS error during research). Verify these versions against PyPI directly before installation.

## Sources

### Primary (HIGH confidence)
- [Ethereum Yellow Paper](https://ethereum.github.io/yellowpaper/paper.pdf) — state transition functions, EVM spec, account structure, block header fields
- [ethereum/execution-specs](https://github.com/ethereum/execution-specs) — current reference Python EVM (replaced py-evm Sep 2025)
- [EVM Codes](https://www.evm.codes/) — authoritative opcode reference with gas costs
- [Ethereum MPT Documentation](https://ethereum.org/developers/docs/data-structures-and-encoding/patricia-merkle-trie/) — trie structure, four trie types
- [Ethereum RLP Documentation](https://ethereum.org/developers/docs/data-structures-and-encoding/rlp/) — encoding spec
- [PyPI: rlp 4.1.0](https://pypi.org/project/rlp/) — Ethereum Foundation RLP library
- [PyPI: eth-hash 0.7.1](https://pypi.org/project/eth-hash/) — Ethereum Foundation keccak wrapper
- [PyPI: coincurve 21.0.0](https://pypi.org/project/coincurve/) — libsecp256k1 bindings
- [EIP-150](https://eips.ethereum.org/EIPS/eip-150) — CALL gas forwarding 63/64 rule
- [EIP-2200](https://eips.ethereum.org/EIPS/eip-2200) — SSTORE net gas metering
- [Snakecharmers: py-evm archival](https://snakecharmers.ethereum.org/sunsetting-support-for-py-evm/) — py-evm archived Sep 8, 2025

### Secondary (MEDIUM confidence)
- [wolflo/evm-opcodes gas.md](https://github.com/wolflo/evm-opcodes/blob/main/gas.md) — gas cost details, cross-referenced with Yellow Paper
- [py-evm GitHub (archived)](https://github.com/ethereum/py-evm) — module organization patterns, opcode abstraction
- [pyethereum (archived)](https://github.com/ethereum/pyethereum) — pure function apply_transaction pattern
- [pythereum](https://github.com/gablg1/pythereum) — minimal educational implementation analysis
- [EVM-Simulator (thesis)](https://github.com/tanmaster/EVM-Simulator) — step-by-step trace as high-value differentiator

### Tertiary (LOW confidence)
- "Building Ethereum from scratch in 10 minutes" (Medium) — build order intuition only; single source

---
*Research completed: 2026-02-19*
*Ready for roadmap: yes*
