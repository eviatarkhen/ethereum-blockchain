# Feature Research

**Domain:** Educational Ethereum blockchain implementation (Python, single-node, debugger-oriented)
**Researched:** 2026-02-19
**Confidence:** MEDIUM — core Ethereum protocol features are HIGH confidence (Yellow Paper, EELS); educational tool feature patterns are MEDIUM confidence (multiple comparable projects surveyed)

## Feature Landscape

### Table Stakes (Users Expect These)

Features a learner expects to find. Missing any of these leaves the learning tool incomplete — the learner cannot trace a full transaction lifecycle.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Account model (EOA + contract) | Ethereum fundamentals cannot be demonstrated without the two-account distinction; nonce, balance, code hash, storage root are all observable at breakpoints | LOW | 4 fields per account: nonce, balance, storage_root, code_hash. EOA has empty code. Contract account has bytecode and storage trie. |
| Private key / address derivation | Learner needs to understand where addresses come from; ECDSA secp256k1 + keccak160 of public key is core Ethereum | LOW | Use `eth_keys` library. No need to implement secp256k1 from scratch — that obscures rather than teaches. |
| Transaction structure (type 0) | Every tutorial shows from/to/value/data/nonce/gas; without this nothing else runs | LOW | Legacy transaction format. Cover gasPrice, gasLimit, value, data. Skip EIP-1559 type 2 — adds complexity without teaching the core concept. |
| Transaction signing and validation | ECDSA signing and recovery of sender is how Ethereum proves ownership; it must be traceable | MEDIUM | Use `eth_keys`. Validate: nonce match, sufficient balance, signature valid. |
| State transition function | Applying a transaction to world state is the conceptual core of a blockchain | MEDIUM | Pre-state → transaction → post-state. Nonce increment, balance deduction, EVM call or contract creation, gas refund. |
| EVM execution engine (core opcodes) | Without EVM, smart contracts are unreachable; no EVM = half the ecosystem unexplained | HIGH | ~20-30 opcodes: arithmetic (ADD, SUB, MUL, DIV, MOD), comparison (LT, GT, EQ, ISZERO), stack (PUSH1-PUSH32, POP, DUP1-DUP16, SWAP1-SWAP16), memory (MLOAD, MSTORE, MSTORE8), storage (SLOAD, SSTORE), flow (JUMP, JUMPI, PC, JUMPDEST, STOP, RETURN, REVERT), context (CALLER, CALLVALUE, CALLDATALOAD, CALLDATASIZE, CODESIZE, CODECOPY). |
| EVM machine state (stack, memory, storage) | These are the three data regions the learner must observe; without them EVM steps are a black box | MEDIUM | Stack: 1024-item max, 256-bit words. Memory: volatile byte array. Storage: persistent 256→256 mapping per contract. |
| Gas accounting | Gas is how Ethereum bounds execution; every opcode carries a cost that must be visible | MEDIUM | Implement static gas costs per opcode. Deduct from gas limit on each opcode. Raise OOG exception when exhausted. Skip dynamic/access-list gas tiers — they add noise without teaching the model. |
| Block structure (header + transactions) | Blocks are the unit of finality; learner needs to see how transactions are batched and committed | LOW | Header: parent_hash, state_root, transactions_root, number, timestamp, gas_limit, gas_used. Body: list of transactions. |
| Block creation (mine a block) | Completes the lifecycle: transactions become canonical once in a block | LOW | No PoW difficulty adjustment needed. Simple block sealing with incrementing block number and timestamp. |
| World state (mapping address → account) | The accumulation of all accounts IS the blockchain state; it must exist and be inspectable | LOW | In-memory dict is fine. Merkle Patricia Trie gives it cryptographic structure later. |
| RLP encoding / decoding | RLP is how Ethereum serializes every data structure; needed for transaction hashing, block hashing, trie values | MEDIUM | Implement from scratch or use `rlp` PyPI library. Implementing from scratch takes ~150 lines and teaches the encoding model. |
| Keccak-256 hashing | Used everywhere: address derivation, transaction hash, block hash, trie node keys | LOW | Use `pysha3` or `pycryptodome`. Do not implement from scratch. |
| Merkle Patricia Trie (state trie) | State root is how blocks commit to the full account state; this closes the cryptographic loop | HIGH | Most complex single component. Implement the 4 node types: blank, leaf, extension, branch. Use modified hex-prefix encoding. State trie maps keccak256(address) → RLP(account). Transaction trie and receipt trie are lower priority — state trie alone teaches the concept. |
| Contract deployment (CREATE) | Without deploy, the learner cannot see how contracts come into existence | MEDIUM | CREATE opcode: take init bytecode from transaction data, run it in EVM, store returned bytecode at computed address. Address = keccak256(RLP([sender, nonce]))[12:]. |
| Contract function call (CALL) | Without calling contracts, deployed bytecode is inert | MEDIUM | CALL opcode: load callee bytecode, create child EVM context, pass calldata, receive return value. Transfer value. Handle revert vs success. |
| Hardcoded example contracts (counter + token) | Without runnable examples the learner has nothing to step through | LOW | Counter: stores a uint256, has increment() and get(). Token: balances mapping, transfer(). Provide as hex bytecode strings with annotated disassembly comments in source. |
| Python scenario scripts | Guided walkthroughs are the primary learning interface; without them the learner has no entry point | LOW | Minimum: (1) ETH transfer between accounts, (2) deploy counter contract, (3) call increment, (4) verify state change. Each script should have comments pointing learner to functions worth setting breakpoints on. |
| Readable code with debugger-friendly naming | The entire tool's value proposition depends on this; if variable names are `s`, `t`, `h` the learning value collapses | LOW (ongoing discipline) | Variable names must match Yellow Paper concepts: `gas_remaining`, `program_counter`, `world_state`, `call_stack`. No abbreviations in public interfaces. |

### Differentiators (Competitive Advantage)

Features not expected by default but that elevate this above a generic blockchain toy. These are the properties that make this implementation specifically excellent for learning.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Annotated disassembly alongside bytecode | Learner sees both raw hex and human-readable opcode sequence side-by-side; bridges compile output to EVM behavior | LOW | A `disassemble(bytecode)` utility that prints offset, hex, mnemonic, operand. ~50 lines. Major learning accelerator. |
| Step-by-step EVM trace output | Printing stack/memory/storage/PC/gas after each opcode gives the learner a paper trail to correlate with debugger state | LOW | A `verbose` mode flag on the EVM. Print state after each opcode cycle. Can be toggled per-scenario. |
| Yellow Paper section references in comments | Direct links from code to Yellow Paper sections (e.g., `# Yellow Paper §6.2 — Transaction Validity`) lets the learner triangulate between spec and implementation | LOW (notation discipline) | No runtime cost. High learning value. Differentiates from random GitHub blockchain toy. |
| Token transfer scenario with balance verification | Demonstrates the full EVM path: SLOAD, arithmetic, SSTORE, re-entrancy guard pattern — without needing Solidity | MEDIUM | Requires SLOAD, SSTORE, CALLER, CALLVALUE, ADD, SUB, LT, REVERT in the opcode set. Explicit prerequisite on storage opcodes. |
| Trie proof generation (get_proof) | Allows learner to verify that a specific account state is committed in a block's state root — closes the Merkle cryptographic loop | HIGH | Implement inclusion proof: path from leaf to root. Learner can verify state integrity manually. Significant complexity but teaches the most important structural insight. |
| Execution receipts (gas used, status, logs) | Shows what Ethereum actually records per transaction; learner can see why receipts exist | MEDIUM | Status (0/1), cumulative gas used, log entries from LOG0-LOG4 opcodes. Needed to understand the receipts trie later. |
| Inline documentation explaining WHY (not just WHAT) | Most implementations document what code does; this one should explain why Ethereum designed it this way | LOW (writing effort) | Each module should open with a paragraph explaining the design rationale, not just a list of what functions do. |

### Anti-Features (Commonly Requested, Often Problematic)

Features that seem like good ideas but would harm the learning goal or violate scope.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| P2P networking / gossip protocol | Blockchain implies network; devs instinctively add it | Doubles the codebase. Forces learner to understand libp2p or asyncio before they understand blocks. Obscures what matters. Single-node teaches all the same internals. | Single-node architecture. Scenario scripts replace peer interaction. |
| Solidity / Vyper compiler integration | Real contracts are written in Solidity; learner wants to write their own | Compiler is a 100K+ LOC independent project. EVM learning does not require a compiler. Hardcoded bytecode with annotated disassembly teaches the same concepts and is debuggable. | Pre-compiled bytecode strings with inline disassembly annotations. |
| Full 140+ opcode coverage | "Complete" sounds better than "partial" | ~110 of the 140 opcodes cover edge cases (CREATE2, SELFDESTRUCT, TLOAD/TSTORE, BLOBHASH, access lists). Implementing them all dilutes focus and inflates codebase to unreadable size. | Implement the ~25-30 opcodes the example contracts actually use. Stub the rest with `NotImplementedError` and a comment naming the opcode. |
| Proof of Work / Proof of Stake | Consensus is half of blockchain | Neither PoW nor PoS teaches transaction lifecycle, EVM, or state. They are a separate domain. PoW requires mining loop. PoS requires validator set management. Both derail the focus. | Simple `seal_block()` that increments block number and timestamps without any puzzle. |
| JSON-RPC API (eth_sendTransaction, eth_call, etc.) | Makes it "real" Ethereum-compatible | Adds HTTP server, request routing, ABI encoding layers. Learner must navigate API surface before reaching the code that matters. All learning value exists in the Python layer directly. | Python function calls in scenario scripts. Direct method invocations are more debuggable than HTTP requests. |
| Gas optimization and EIP-1559 fee market | Modern Ethereum uses EIP-1559; type 2 transactions | Fee market mechanics (base fee, priority fee, BASEFEE opcode) are protocol detail that obscures the core gas model. Legacy type 0 transactions are simpler and teach the same gas accounting concept. | Implement legacy gasPrice × gasLimit. Add a comment noting EIP-1559 exists and where it differs. |
| LevelDB / RocksDB persistent storage | Production clients use LevelDB for trie storage | Introduces a database dependency that complicates setup and hides the trie structure behind key-value abstraction. In-memory dict makes every node visible in the debugger. | In-memory dict for all state. Optional pickle-based dump/load for session persistence is sufficient. |
| Interactive REPL (IPython / custom shell) | Sounds interactive and educational | REPLs are harder to debug because state is implicit. Scenario scripts are files — learner can set breakpoints, re-run, inspect, version-control their exploration. | Python scenario scripts run from the command line. Simpler, more reproducible, fully debuggable. |
| EVM test suite compliance (ethereum/tests) | Validates correctness against 10K+ test vectors | The test suite targets production EVM behavior across all hardforks. Running it requires complete opcode coverage and hardfork switching logic. It fights the 3-5K line constraint and punishes the educational shortcuts that make the code readable. | A small hand-written test suite (~20 tests) covering the scenarios the example contracts actually exercise. |

## Feature Dependencies

```
[ECDSA / keccak-256]
    └──required-by──> [Account address derivation]
    └──required-by──> [Transaction signing]
    └──required-by──> [Block hashing]
    └──required-by──> [Merkle Patricia Trie node keys]

[RLP encoding]
    └──required-by──> [Transaction hashing]
    └──required-by──> [Block hashing]
    └──required-by──> [Merkle Patricia Trie leaf/extension/branch values]
    └──required-by──> [Contract address derivation (CREATE)]

[Account model]
    └──required-by──> [World state]
    └──required-by──> [Transaction validation (nonce, balance check)]

[World state]
    └──required-by──> [State transition function]
    └──required-by──> [Merkle Patricia Trie (state trie roots)]

[EVM machine state (stack, memory, storage)]
    └──required-by──> [EVM execution engine (opcodes)]

[EVM execution engine]
    └──required-by──> [Contract deployment (CREATE)]
    └──required-by──> [Contract function call (CALL)]
    └──required-by──> [Hardcoded example contracts]

[Transaction structure + signing]
    └──required-by──> [State transition function]

[State transition function]
    └──required-by──> [Block creation]

[Block creation]
    └──required-by──> [Python scenario scripts]

[Contract deployment (CREATE)]
    └──required-by──> [Python scenario scripts (deploy + call)]

[Merkle Patricia Trie]
    └──required-by──> [State root in block header]
    └──required-by──> [Trie proof generation] (differentiator, optional)

[Annotated disassembly utility]
    └──enhances──> [Hardcoded example contracts] (makes bytecode readable)
    └──enhances──> [EVM execution engine] (makes opcode trace human-readable)

[EVM trace output (verbose mode)]
    └──enhances──> [Python scenario scripts] (turns scripts into guided walkthroughs)
```

### Dependency Notes

- **RLP and keccak-256 are prerequisites for everything** — they must be Phase 1 work.
- **Account model before world state** — you cannot have a world state without knowing what an account is.
- **EVM machine state before opcodes** — opcodes manipulate stack/memory/storage; those regions must exist first.
- **State transition before block creation** — a block is just a container for validated state transitions.
- **Merkle Patricia Trie is a standalone module** — it does not depend on EVM or transactions, only on keccak-256 and RLP. It can be built in parallel with the EVM but must be complete before state roots appear in block headers.
- **Trie proof generation conflicts with simplicity goal** — it is the most complex single feature and should only be built if all table-stakes features are complete and time remains. It is a differentiator, not required.

## MVP Definition

### Launch With (v1)

Minimum viable product — what is needed to step through a complete transaction lifecycle in the debugger.

- [ ] keccak-256 and ECDSA wrappers — all hashing and signing flows through these
- [ ] Account model (nonce, balance, code, storage) — the data structure that makes Ethereum an account-based system
- [ ] RLP encode/decode — required to hash transactions and blocks
- [ ] Transaction structure: type 0 (legacy), signing, sender recovery
- [ ] World state: in-memory dict from address to account
- [ ] State transition function: validate tx, deduct gas, apply value transfer, call EVM or CREATE
- [ ] EVM engine: stack, memory, storage + 25-30 core opcodes (arithmetic, comparison, stack ops, memory ops, storage ops, flow control, call context)
- [ ] Gas accounting: per-opcode static costs, OOG exception
- [ ] Contract deployment (CREATE): run init bytecode, store runtime bytecode at derived address
- [ ] Contract call (CALL): load bytecode, pass calldata, return data, handle REVERT
- [ ] Block structure: header fields + transaction list + simple sealing
- [ ] Hardcoded example contracts: counter (increment/get) and token (transfer/balanceOf) as annotated bytecode strings
- [ ] Scenario scripts: ETH transfer, deploy counter, call increment, verify state (4 scripts)
- [ ] Annotated disassembly utility — essential for making bytecode readable in scenarios

### Add After Validation (v1.x)

Features to add once the core learning loop is verified to work.

- [ ] Merkle Patricia Trie — adds state root integrity to block headers; significant complexity, high payoff for understanding Ethereum's cryptographic design
- [ ] EVM trace / verbose mode — per-opcode state dump; makes debugging sessions self-documenting
- [ ] Execution receipts (status, gas used, logs) — required for the token transfer scenario to demonstrate LOG opcodes
- [ ] Transaction trie root — once MPT exists, computing the transactions_root for a block header is low additional cost
- [ ] Yellow Paper section references in all module docstrings — annotation pass after code is stable

### Future Consideration (v2+)

Features to defer until the v1 learning loop is validated and if scope permits.

- [ ] Trie inclusion proof generation — teaches the most advanced concept (Merkle proofs) but is complex and not needed for transaction tracing
- [ ] Additional example contracts (simple auction, voting) — broadens scenario coverage but requires more opcode coverage first
- [ ] EIP-1559 type 2 transactions — adds fee market mechanics for learners who want to understand modern Ethereum; needs BASEFEE opcode and fee logic

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| keccak-256 + ECDSA wrappers | HIGH | LOW | P1 |
| Account model | HIGH | LOW | P1 |
| RLP encode/decode | HIGH | MEDIUM | P1 |
| Transaction structure + signing | HIGH | LOW | P1 |
| World state (in-memory) | HIGH | LOW | P1 |
| State transition function | HIGH | MEDIUM | P1 |
| EVM machine state (stack/memory/storage) | HIGH | MEDIUM | P1 |
| EVM core opcodes (~25-30) | HIGH | HIGH | P1 |
| Gas accounting (static costs) | HIGH | LOW | P1 |
| Contract deployment (CREATE) | HIGH | MEDIUM | P1 |
| Contract call (CALL) | HIGH | MEDIUM | P1 |
| Block structure + sealing | HIGH | LOW | P1 |
| Hardcoded example contracts | HIGH | LOW | P1 |
| Scenario scripts (4 scenarios) | HIGH | LOW | P1 |
| Annotated disassembly utility | HIGH | LOW | P1 |
| Merkle Patricia Trie (state trie) | HIGH | HIGH | P2 |
| EVM trace / verbose mode | MEDIUM | LOW | P2 |
| Execution receipts | MEDIUM | MEDIUM | P2 |
| Transaction trie root | MEDIUM | LOW | P2 |
| Yellow Paper section annotations | MEDIUM | LOW | P2 |
| Trie inclusion proof generation | MEDIUM | HIGH | P3 |
| Additional example contracts | LOW | MEDIUM | P3 |
| EIP-1559 type 2 transactions | LOW | MEDIUM | P3 |

**Priority key:**
- P1: Must have for launch (v1 — complete transaction lifecycle traceable in debugger)
- P2: Should have — add in v1.x once core works
- P3: Nice to have — future consideration if scope permits

## Comparable Implementation Analysis

| Feature | pythereum (200 LOC) | pychain (Flask API) | theluxaz/Python-EVM | EduEthereum (this project) |
|---------|---------------------|---------------------|---------------------|---------------------------|
| Account model | Yes (nonce, balance, code, storage) | No | No | Yes |
| Real EVM opcodes | No (Python eval) | No | Yes (~140 opcodes) | Yes (~25-30 opcodes) |
| Transaction signing | No | Yes (ECDSA) | No | Yes |
| Merkle Patricia Trie | No | Stage 2 (incomplete) | No | Yes (v1.x) |
| Gas accounting | No | No | Yes | Yes |
| Example contracts | No (Python eval strings) | No | No | Yes (hardcoded bytecode) |
| Scenario scripts | No | No | No | Yes |
| Debugger-oriented design | No | No | No | Yes |
| Yellow Paper alignment | Whitepaper only | Yellow Paper stated | Partial | Yellow Paper (spec in repo) |

The gap this project fills: the only educational Python implementation that combines real EVM opcodes, proper cryptography, Merkle Patricia Trie, pre-built example contracts, guided scenario scripts, and explicit debugger-oriented design in one coherent 3-5K line codebase.

## Sources

- [Ethereum Yellow Paper](https://ethereum.github.io/yellowpaper/paper.pdf) — HIGH confidence. Canonical source for all protocol data structures and EVM specification.
- [Ethereum Execution Layer Specifications (EELS)](https://github.com/ethereum/execution-specs) — HIGH confidence. Python reference implementation, prioritizes readability. Archived py-evm redirects here as of September 2025.
- [EVM Codes — Opcode Reference](https://www.evm.codes/) — HIGH confidence. Authoritative interactive opcode reference with gas costs.
- [Ethereum Developers — Merkle Patricia Trie](https://ethereum.org/developers/docs/data-structures-and-encoding/patricia-merkle-trie/) — HIGH confidence. Official documentation on trie structure and all four trie types.
- [Understanding the Yellow Paper's EVM Specifications](https://ethereum.org/developers/tutorials/yellow-paper-evm/) — MEDIUM confidence. Official Ethereum tutorial mapping Yellow Paper sections to EVM concepts.
- [pythereum — Simple Didactic Ethereum in ~200 LOC](https://github.com/gablg1/pythereum) — MEDIUM confidence. Confirms simplest-viable account+state+contract model; shows Python eval as a shortcut that avoids real opcode learning.
- [pychain — Educational Blockchain from First Principles](https://github.com/valzam/pychain) — MEDIUM confidence. Confirms transaction signing + Proof of Work as common table stakes; also shows Merkle trees as a Stage 2 (later) addition.
- [theluxaz/Python-EVM](https://github.com/theluxaz/Python-EVM) — MEDIUM confidence. Confirms ~140 opcode categories; validates that full opcode coverage is achievable in Python but exceeds educational scope.
- [EVM-Simulator (Bachelor's thesis)](https://github.com/tanmaster/EVM-Simulator) — MEDIUM confidence. Confirms step-by-step execution trace and memory/storage observation as high-value differentiators for learning.
- [py-evm Documentation (archived)](https://py-evm.readthedocs.io/en/latest/) — MEDIUM confidence. Shows production-grade opcode abstraction patterns; confirms gas decoupling from logic as useful educational pattern.

---
*Feature research for: Educational Ethereum blockchain implementation (Python, single-node, debugger-oriented)*
*Researched: 2026-02-19*
