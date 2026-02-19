# Domain Pitfalls: Educational Ethereum Blockchain in Python

**Domain:** Educational single-node Ethereum implementation (Python)
**Researched:** 2026-02-19
**Confidence:** MEDIUM — core cryptographic pitfalls are HIGH (documented in multiple authoritative sources); EVM implementation pitfalls are MEDIUM (py-evm source + community documentation); educational design pitfalls are MEDIUM (HN community analysis + multiple tutorial post-mortems)

---

## Critical Pitfalls

Mistakes that cause rewrites, incorrect blockchain state, or fundamentally mislead learners.

---

### Pitfall 1: Keccak-256 vs SHA-3 Confusion

**What goes wrong:** Python's `hashlib` provides `sha3_256`, which produces FIPS 202 SHA-3 output. Ethereum uses the original Keccak-256, which uses slightly different padding. Using `hashlib.sha3_256` produces hashes that do not match Ethereum's address derivation, transaction hashes, or trie nodes.

**Why it happens:** Python's `hashlib.sha3_256` is named intuitively but produces the wrong output for Ethereum. Ethereum was designed before SHA-3 was standardized; the committee added padding tweaks that changed the output. The library `pysha3` provides the correct `keccak_256`, but is a non-obvious dependency.

**Consequences:** Every hash in the system is wrong. Addresses don't match, transaction hashes are invalid, Merkle Patricia Trie roots disagree with reference implementations. The errors are silent — the system "works" but produces incorrect output that a learner cannot verify against Ethereum tools.

**Prevention:** Use `pysha3` (which exposes `sha3.keccak_256`) or `pycryptodome` (which exposes `Crypto.Hash.keccak`). Never use `hashlib.sha3_256` for Ethereum. Add a test in Phase 1 that verifies the hash of a known input matches the expected Ethereum output (e.g., keccak256("") == "c5d2460186f7233c927e7db2dcc703c0e500b653ca82273b7bfad8045d85a470").

**Detection:** Cross-check your keccak output against a known Ethereum address derivation before building anything else. If address derivation is wrong, the hash function is wrong.

**Phase:** Crypto/accounts foundation (earliest phase). Must be fixed before any other component is built.

**Confidence:** HIGH — documented in Python Ethereum libraries (eth-hash, pysha3 issue trackers, PyCryptodome docs).

---

### Pitfall 2: Treating Python's Arbitrary-Precision Integers as "Safe" for EVM Arithmetic

**What goes wrong:** The EVM uses 256-bit unsigned integers with wraparound (modular) arithmetic. Python integers are unbounded — they silently grow past 2^256 without overflow. EVM arithmetic opcodes (ADD, MUL, SUB, EXP) must produce results modulo 2^256. Without explicit `% (2**256)`, every arithmetic operation in the EVM produces wrong results for large values.

**Why it happens:** Python's integers "just work" for most purposes, so the modular arithmetic requirement is easy to forget. The bug is invisible on small test values (where the result is well under 2^256) and only surfaces when testing with realistic values.

**Consequences:** Arithmetic opcodes produce incorrect results for overflow cases. Smart contracts that depend on overflow behavior (e.g., token calculations) silently produce wrong balances. Learners get a false impression that EVM arithmetic is unbounded.

**Prevention:** In every arithmetic opcode implementation, apply `% (2**256)` to the result before pushing to the stack. For signed operations (SDIV, SMOD), also implement correct two's complement interpretation. Create an opcode test that verifies `0xFFFF...FFFF + 1 == 0` (256-bit overflow wraps to 0).

**Detection:** Add a test: `ADD(2**256 - 1, 1) == 0`. If it returns `2**256`, the modular arithmetic is missing.

**Phase:** EVM opcodes implementation phase. Apply from the first opcode implemented.

**Confidence:** HIGH — documented in py-evm source and EVM specification; confirmed by multiple EVM tutorial authors noting Python-specific risk.

---

### Pitfall 3: RLP Encoding Edge Cases Silently Breaking the Entire System

**What goes wrong:** RLP (Recursive Length Prefix) encoding has multiple subtle edge cases: the single-byte range `[0x00, 0x7f]` encodes as itself (no length prefix), the integer `0` encodes as `0x80` (the empty byte string), and length fields for strings >55 bytes require a multi-byte big-endian length-of-length prefix. Mistakes in any of these produce encoding that differs from the reference, breaking transaction hashes, block hashes, and Merkle trie nodes.

**Why it happens:** The RLP spec looks simple but has corner cases that only appear in specific value ranges. The `0` encoding (as empty bytes, not as `\x00`) is the most commonly missed. String vs. bytes type handling in Python 3 (where mixing `str` and `bytes` is a TypeError) adds another failure mode not present in reference implementations written for Python 2.

**Consequences:** Transaction hashes don't match Ethereum reference values. Block hashes are wrong. Trie root computation is wrong. The system is internally consistent but wrong relative to Ethereum — learners cannot validate their output against real Ethereum data.

**Prevention:** Build a standalone RLP module first. Write tests against known RLP vectors from the Ethereum test suite (https://github.com/ethereum/tests/tree/develop/RLPTests). Explicitly test: empty bytes (`0x80`), single byte below 0x80 (encodes as itself), integer 0 (encodes as `0x80`), strings of 1-55 bytes, strings of >55 bytes.

**Detection:** Run the official Ethereum RLP test vectors before connecting RLP to any other component.

**Phase:** RLP implementation phase (should be its own early phase, before anything that depends on hashing).

**Confidence:** HIGH — documented in Ethereum official docs, multiple Python RLP implementations, and implementation experience from py-evm.

---

### Pitfall 4: JUMPDEST Validation Ignoring PUSH Immediate Bytes

**What goes wrong:** The EVM's JUMP and JUMPI opcodes require the target to be a JUMPDEST opcode. Naive implementations scan for `0x5B` (JUMPDEST opcode byte) in the bytecode. But PUSH instructions (PUSH1 through PUSH32) are followed by N immediate data bytes that may contain `0x5B`. A naive scanner treats those data bytes as valid JUMPDEST locations, allowing jumps to illegal positions inside PUSH data.

**Why it happens:** The EVM program counter advances over PUSH operand bytes, but a pre-scan to build the valid JUMPDEST set must also skip those bytes. Forgetting this means the JUMPDEST set is larger than it should be, enabling malformed control flow.

**Consequences:** Contracts that rely on security properties of JUMPDEST validation behave incorrectly. A learner stepping through bytecode observes jumps landing inside data, which is confusing and wrong. Any contract that uses JUMPDEST inside PUSH data for some reason would "succeed" when it should revert.

**Prevention:** Build the valid JUMPDEST set by iterating through bytecode once, tracking the program counter properly: when you see a PUSH1-PUSH32 opcode (0x60-0x7f), advance the counter by (opcode - 0x5f) additional bytes to skip the immediate data.

**Detection:** Test with bytecode containing `0x5B` as a PUSH1 immediate: `PUSH1 0x5B JUMP`. The jump should fail (no valid JUMPDEST), not succeed.

**Phase:** EVM control flow opcodes phase.

**Confidence:** HIGH — specified in the Ethereum Yellow Paper and EVM spec; confirmed in EIP-3690 (JUMPDEST Table) discussion.

---

### Pitfall 5: Merkle Patricia Trie — Conflating the Four Data Structures

**What goes wrong:** Ethereum maintains four distinct tries that developers conflate:
1. **World State Trie** — maps address → account state (nonce, balance, storageRoot, codeHash)
2. **Account Storage Trie** — per-contract, maps storage slot → value (referenced by `storageRoot` in account state)
3. **Transaction Trie** — per-block, maps transaction index → RLP-encoded transaction
4. **Receipt Trie** — per-block, maps transaction index → RLP-encoded receipt

Implementations often mix keys and values between these tries, or store contract storage directly in the world state trie instead of in a separate per-account storage trie.

**Why it happens:** The relationship between world state and storage is easy to misread: the world state trie stores the *hash* of each contract's storage trie root, not the storage data itself. This indirection is easy to miss.

**Consequences:** State root computation is wrong. Any scenario that updates contract storage produces an incorrect block hash. Debugger walkthroughs show wrong state.

**Prevention:** Implement each trie as a separate instance with clearly named keys/values. In the account dataclass, make `storage_root` explicitly a bytes32 hash (not a dict). Write a test that deploys a contract, writes to storage, and verifies the block's state root changes correctly.

**Phase:** Merkle Patricia Trie implementation phase and state transition phase.

**Confidence:** HIGH — confirmed in Ethereum official docs and multiple architectural explainers.

---

### Pitfall 6: Transaction Validation Order (Nonce and Balance Checked Wrong)

**What goes wrong:** The Ethereum Yellow Paper specifies a precise validation order for transactions. A common mistake is to check nonce before verifying the signature, or to deduct gas cost before checking sender balance, or to apply state changes before fully validating the transaction. This results in scenarios where invalid transactions partially modify state.

**Why it happens:** Validation and execution feel like one flow, and implementations build them as one function. The required order (signature valid → nonce matches → sender can cover gas → intrinsic gas check → deduct upfront gas → execute → refund) is easy to implement out of order.

**Consequences:** An invalid transaction may increment a nonce, deduct partial fees, or modify account state before being rejected. Educational scenarios step through incorrect state transitions, misleading learners about Ethereum's transaction atomicity.

**Prevention:** Implement validation as a separate, explicit step that returns a validated transaction object before any state mutation occurs. Validate in this order: (1) signature validity, (2) nonce == sender.nonce, (3) sender.balance >= gas_limit * gas_price + value, (4) intrinsic gas <= gas_limit. Only then begin execution and state mutation.

**Detection:** Test: submit a transaction with a valid signature but insufficient balance. Confirm that sender nonce is not incremented and no state changes occur.

**Phase:** Transaction processing phase.

**Confidence:** MEDIUM — Yellow Paper specifies the order; validation order bugs are a documented class of issues in educational implementations (HN analysis of blockchain tutorials).

---

## Moderate Pitfalls

---

### Pitfall 7: EVM Gas Accounting — Memory Expansion Formula Applied Incrementally Not Cumulatively

**What goes wrong:** Memory expansion gas is calculated on the *cumulative* memory size, not on the delta. The formula is:

```
memory_cost(n) = (n^2 / 512) + (3 * n)   where n = memory_size_in_words
```

The gas charge for any memory-touching opcode is `memory_cost(new_size) - memory_cost(old_size)`. Implementations that apply `3 * words_added` on each operation (linear delta) instead of the quadratic cumulative formula are wrong once memory exceeds the linear range (~724 bytes).

**Prevention:** Keep a single `memory_size_words` state variable. On every memory access, compute the new required size in words, then charge `memory_cost(new_size) - memory_cost(current_size)` before updating `memory_size_words`.

**Detection:** Test MSTORE at offset 800 from a fresh state. The gas charge should include the quadratic penalty; a linear-only implementation will undercharge.

**Phase:** EVM opcodes — memory operations.

**Confidence:** MEDIUM — gas formula is in the Yellow Paper; the incremental-vs-cumulative mistake is a known implementation class error in EVM from scratch courses.

---

### Pitfall 8: CALL Gas Forwarding — Forgetting the "All But One 64th" Rule (EIP-150)

**What goes wrong:** When a CALL opcode requests more gas than available, the EVM does not forward exactly what was requested. Per EIP-150, the actual gas forwarded is:

```
gas_sent = min(requested_gas, remaining_gas - (remaining_gas // 64))
```

Implementations that simply forward `min(requested_gas, remaining_gas)` are wrong after EIP-150 (Tangerine Whistle fork, 2016).

**Prevention:** For any CALL family opcode (CALL, CALLCODE, DELEGATECALL, STATICCALL), apply the 63/64 rule. Since this is a simplified implementation, document clearly which fork rules are implemented and which are not.

**Detection:** Test a CALL that requests more gas than available. Verify the callee receives `remaining - remaining//64` gas, not the full remaining amount.

**Phase:** EVM — CALL opcode implementation.

**Confidence:** MEDIUM — documented in EIP-150 and gas accounting references (wolflo/evm-opcodes).

---

### Pitfall 9: Hex-Prefix Encoding Errors in MPT Nodes

**What goes wrong:** Merkle Patricia Trie leaf and extension nodes encode their partial path with a hex-prefix that encodes two bits of flag: (1) leaf vs. extension, (2) odd vs. even path length. Getting the first nibble wrong (e.g., using `0x20` for extension nodes, or not padding even-length paths) produces trie nodes that hash incorrectly, making the trie root wrong.

**Why it happens:** The dual-purpose encoding is non-obvious. The flag nibble encodes:
- `0` (0000) = extension, even
- `1` (0001) = extension, odd
- `2` (0010) = leaf, even
- `3` (0011) = leaf, odd

Implementations often hard-code one case or conflate leaf/extension flags.

**Prevention:** Implement hex-prefix encoding as a standalone function with four explicit test cases (one per flag combination). Test round-trip: encode a known path, decode it, verify the path and node type match.

**Phase:** Merkle Patricia Trie implementation.

**Confidence:** MEDIUM — documented in Ethereum official MPT spec and multiple implementation guides.

---

### Pitfall 10: Inline vs. Hash References in MPT (The 32-Byte Threshold)

**What goes wrong:** In a Merkle Patricia Trie, nodes are referenced by their keccak256 hash only if `len(rlp.encode(node)) >= 32`. Smaller nodes are embedded (inlined) directly in their parent node. Implementations that always hash node references produce different trie roots than Ethereum's reference implementation.

**Prevention:** Before storing a node reference, check `len(rlp.encode(node))`. If < 32, embed the RLP-encoded node directly. If >= 32, store `keccak256(rlp.encode(node))`.

**Phase:** Merkle Patricia Trie implementation. Depends on RLP encoding being correct first.

**Confidence:** MEDIUM — specified in Ethereum official MPT documentation.

---

### Pitfall 11: Not Marking Simplifications as Simplifications

**What goes wrong:** Educational shortcuts (simplified gas rules, omitting EIP-155 chain ID in signing, skipping receipt generation, implementing only pre-EIP-1559 transaction types) are implemented without clear comments. A learner reading the code assumes it is correct Ethereum behavior and forms wrong mental models.

**Why it happens:** Developers building the system know the shortcuts are simplifications, but don't document them. The HN analysis of educational blockchain implementations specifically identified this as a recurring failure mode: "bad examples aren't clearly marked as bad."

**Consequences:** The educational purpose is undermined. Learners build incorrect mental models that they have to unlearn later.

**Prevention:** Add a `# SIMPLIFIED:` comment at every deliberate deviation from the Yellow Paper. Add a top-level `SIMPLIFICATIONS.md` listing every intentional shortcut with a reference to what the real implementation does differently.

**Phase:** Applies to all phases. Establish the convention in Phase 1 and enforce it throughout.

**Confidence:** MEDIUM — confirmed by HN community analysis of educational blockchain implementations.

---

### Pitfall 12: EVM SSTORE Gas — Dirty/Clean/Warm/Cold State Is Per-Transaction

**What goes wrong:** EVM gas for SSTORE depends on three values: the original value (at transaction start), the current value (most recent write in this transaction), and the new value. "Warm" vs "cold" access also applies. Implementations that only track "current vs. new" miss the original-value comparison and compute wrong gas and wrong refunds.

**Prevention:** For SSTORE, maintain an "original storage values" snapshot at the start of each transaction. During execution, the gas formula requires all three values: `original`, `current`, and `new`. Keep the access list (warm/cold) as a set of (address, slot) pairs, reset at the start of each transaction.

**Phase:** EVM storage opcodes (SLOAD/SSTORE); also affects transaction execution frame.

**Confidence:** MEDIUM — documented in EIP-2200 (net gas metering) and EIP-2929 (cold/warm access costs).

---

## Minor Pitfalls

---

### Pitfall 13: `bytes` vs `int` Inconsistency in Python Leads to Silent Bugs

**What goes wrong:** EVM stack values are 256-bit integers. EVM memory is a byte array. Addresses are 20-byte values. Python code that mixes `int` and `bytes` representations without explicit conversion produces wrong output. For example, pushing an address to the stack requires zero-padding it from 20 to 32 bytes, then interpreting as int. Forgetting the padding is silent — no exception, just wrong values.

**Prevention:** Define clear type conventions: stack holds Python `int` (always mod 2^256), memory is `bytearray`, storage keys/values are Python `int`. Write explicit conversion helpers (`int_to_bytes32`, `bytes32_to_int`, `address_to_int`). Use Python type hints throughout.

**Phase:** Applies from the first EVM phase.

**Confidence:** MEDIUM — Python-specific, confirmed by multiple EVM from scratch tutorial authors.

---

### Pitfall 14: Block Hash Covers the Wrong Fields

**What goes wrong:** Ethereum block headers contain specific fields in a specific RLP-encoded order. Educational implementations commonly include too many fields (e.g., transaction list data directly in the header instead of the transactions root hash), too few fields (missing the receipts root, logs bloom, etc.), or wrong types for fields (timestamp as Python datetime instead of Unix int).

**Prevention:** Define the block header dataclass against the Yellow Paper's field list. Hash the block header as `keccak256(rlp.encode(header_fields))` where `header_fields` contains only the header (not the transaction list). Verify your genesis block hash matches a reference.

**Phase:** Block structure phase.

**Confidence:** MEDIUM — commonly wrong in tutorial implementations; Yellow Paper is the authoritative spec.

---

### Pitfall 15: Floating-Point Used for ETH/Wei Values

**What goes wrong:** Some educational implementations represent ETH values as floating-point (1.5 ETH) rather than integer wei (1500000000000000000 wei). Floating-point arithmetic produces precision errors that don't exist in Ethereum.

**Prevention:** All balance and value fields are Python `int` in wei. Never use float for any monetary value. Document at the top of the accounts module: "All values in wei (integer)."

**Phase:** Accounts/state phase (earliest).

**Confidence:** MEDIUM — documented in HN blockchain implementation reviews; confirmed in Ethereum developer documentation.

---

### Pitfall 16: EVM Program Counter Advances Before or After Opcode Dispatch

**What goes wrong:** The EVM program counter points to the current opcode during execution. After execution, it advances to the next instruction (past any PUSH immediate bytes). Implementations that advance the PC before dispatch (or forget to advance past PUSH immediates) produce wrong program counter values during debugger stepping — exactly the wrong behavior for an educational tool.

**Prevention:** The dispatch loop should: (1) read opcode at PC, (2) if PUSH_N, read N bytes at PC+1 as immediate, (3) execute opcode, (4) advance PC by 1 + N (where N=0 for non-PUSH). Test by stepping through a PUSH1 PUSH2 sequence and verifying PC values.

**Phase:** EVM core dispatch loop.

**Confidence:** MEDIUM — common in educational EVM implementations; directly observable when using a debugger.

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| Crypto/accounts foundation | Wrong keccak (using hashlib sha3) | Add keccak256 self-test against known vector before any other code |
| RLP encoding | Integer 0 encodes as `0x80` not `0x00`; Python str vs bytes confusion | Test against Ethereum official RLP test vectors before connecting to anything else |
| Transaction processing | Validation order wrong; nonce checked before signature | Implement validation as pure function returning validated object; no state mutation in validation path |
| EVM core dispatch | PC advances wrong for PUSH instructions; no mod 2^256 on arithmetic | PUSH N advances PC by N+1; add mod to every arithmetic opcode |
| EVM memory ops | Memory expansion charged as linear delta instead of quadratic cumulative | Track `memory_size_words` as state; charge `cost(new) - cost(old)` |
| EVM storage ops | SSTORE gas wrong; missing original-value snapshot | Snapshot original storage at transaction start; implement all three-value SSTORE gas branches |
| EVM control flow | JUMPDEST set includes bytes inside PUSH immediates | Build JUMPDEST set by properly skipping PUSH immediate bytes |
| Merkle Patricia Trie | Hex-prefix flag wrong; inline vs hash reference wrong | Test four hex-prefix cases; test the 32-byte threshold for inline embedding |
| MPT + state | Four tries conflated; storageRoot used as direct storage | Separate world state trie, per-account storage trie, tx trie into distinct named instances |
| Block construction | Block header hashes transaction list directly instead of tx root | Block header contains `transactions_root` hash; transaction list is separate |
| All phases | Simplifications not marked | Establish `# SIMPLIFIED:` convention in Phase 1; document all deviations |

---

## Sources

- [Ethereum Yellow Paper (Shanghai Version, Feb 2025)](https://ethereum.github.io/yellowpaper/paper.pdf) — HIGH confidence
- [Ethereum MPT Documentation](https://ethereum.org/developers/docs/data-structures-and-encoding/patricia-merkle-trie/) — HIGH confidence
- [Ethereum RLP Documentation](https://ethereum.org/developers/docs/data-structures-and-encoding/rlp/) — HIGH confidence
- [wolflo/evm-opcodes gas.md](https://github.com/wolflo/evm-opcodes/blob/main/gas.md) — MEDIUM confidence (community-maintained, cross-referenced with Yellow Paper)
- [EIP-150: Gas cost changes for IO-heavy operations](https://eips.ethereum.org/EIPS/eip-150) — HIGH confidence
- [EIP-2200: Structured Definitions for Net Gas Metering](https://eips.ethereum.org/EIPS/eip-2200) — HIGH confidence
- [EIP-2929: Gas cost increases for state access opcodes](https://eips.ethereum.org/EIPS/eip-2929) — HIGH confidence
- [Show HN: Educational blockchain Python — HN comments](https://news.ycombinator.com/item?id=15945490) — MEDIUM confidence (community analysis)
- [eth-hash PyPI](https://pypi.org/project/eth-hash/) — HIGH confidence (official Ethereum Foundation library)
- [PyCryptodome Keccak docs](https://pycryptodome.readthedocs.io/en/latest/src/hash/keccak.html) — HIGH confidence
- [py-evm GitHub (archived)](https://github.com/ethereum/py-evm) — MEDIUM confidence (archived but historically authoritative Python EVM)
- [ethereum/execution-specs](https://github.com/ethereum/execution-specs) — HIGH confidence (current reference Python EVM)
