# Architecture Research

**Domain:** Educational Ethereum Blockchain (Python, single-node)
**Researched:** 2026-02-19
**Confidence:** HIGH — grounded in Ethereum Yellow Paper, py-evm reference implementation, and ethereum.org official documentation.

## Standard Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Scenario Layer                                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐   │
│  │  transfer.py │  │  deploy.py   │  │  call_contract.py        │   │
│  └──────┬───────┘  └──────┬───────┘  └──────────┬───────────────┘   │
└─────────┼────────────────┼───────────────────────┼───────────────────┘
          │                │                       │
┌─────────▼────────────────▼───────────────────────▼───────────────────┐
│                        Blockchain Orchestration                       │
│  ┌────────────────────────────────────────────────────────────────┐   │
│  │  Blockchain  (apply_block, mine_block, get_block_by_hash)      │   │
│  └───────────────────────────┬────────────────────────────────────┘   │
└──────────────────────────────┼────────────────────────────────────────┘
                               │
┌──────────────────────────────▼────────────────────────────────────────┐
│                        Execution Layer                                 │
│  ┌──────────────────────┐   ┌───────────────────────────────────────┐  │
│  │  Transaction Engine  │   │  EVM                                  │  │
│  │  apply_transaction() │──▶│  execute_bytecode()                   │  │
│  │  validate_tx()       │   │  Stack, Memory, Storage, PC, Gas      │  │
│  └──────────────────────┘   └───────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────────┘
                               │
┌──────────────────────────────▼────────────────────────────────────────┐
│                        State Layer                                     │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────────┐  │
│  │  WorldState      │  │  Account         │  │  Block               │  │
│  │  state_root      │  │  balance, nonce  │  │  header, txs         │  │
│  │  get/set account │  │  code, storage   │  │  receipts            │  │
│  └──────────────────┘  └──────────────────┘  └──────────────────────┘  │
└────────────────────────────────────────────────────────────────────────┘
                               │
┌──────────────────────────────▼────────────────────────────────────────┐
│                        Data Structures Layer                           │
│  ┌──────────────────────────┐   ┌──────────────────────────────────┐   │
│  │  MerklePatriciaTrie      │   │  RLP                             │   │
│  │  insert, get, root_hash  │   │  encode(), decode()              │   │
│  └──────────────────────────┘   └──────────────────────────────────┘   │
└────────────────────────────────────────────────────────────────────────┘
                               │
┌──────────────────────────────▼────────────────────────────────────────┐
│                        Crypto Primitives Layer                         │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────────┐  │
│  │  keccak256()     │  │  secp256k1 sign  │  │  address_from_key()  │  │
│  └──────────────────┘  └──────────────────┘  └──────────────────────┘  │
└────────────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Typical Implementation |
|-----------|----------------|------------------------|
| Scenario Scripts | Entry points for guided learning; create keypairs, build transactions, run flows | Plain Python scripts, no framework |
| Blockchain | Chain of blocks; tracks canonical chain; mines new blocks; applies block-level state transitions | `Blockchain` class with block list and world state |
| Transaction Engine | Validates and applies individual transactions; charges gas; calls EVM for contract interactions | `apply_transaction(state, tx)` pure function matching Yellow Paper Υ(σ,T)→σ' |
| EVM | Executes bytecode on a stack machine; 256-bit words; stack depth 1024; tracks gas; dispatches opcodes | `EVM` class with stack, memory, storage, PC, gas counter |
| WorldState | Canonical account map; produces `stateRoot` by hashing account trie; holds all EOA and contract state | Wraps MerklePatriciaTrie; exposes `get_account`, `set_account` |
| Account | Holds balance, nonce, code_hash, storage_root; distinguishes EOA from contract | Simple dataclass |
| Block | Header (parent_hash, state_root, tx_root, receipt_root, number, timestamp, gas_limit) + transaction list | Dataclass + RLP serialization |
| Transaction | Signed payload: from, to, value, data, gas_limit, gas_price, nonce; ECDSA signature | Dataclass + signing helpers |
| MerklePatriciaTrie | Modified Radix-16 trie with Merkle hashing; produces a deterministic root from key-value pairs; used for state, transactions, and receipts | Custom Python class; branch/extension/leaf nodes |
| RLP | Recursive Length Prefix encoding; serializes all Ethereum data structures for hashing and storage | `rlp_encode`, `rlp_decode` pure functions |
| Crypto Primitives | keccak256 hashing; secp256k1 keypair generation, signing, and verification; address derivation | Thin wrappers over `pysha3` / `coincurve` or `py_ecc` |

## Recommended Project Structure

```
ethereum/
├── crypto/
│   ├── __init__.py
│   ├── hash.py          # keccak256 wrapper
│   ├── keys.py          # secp256k1 keypair, sign, verify
│   └── address.py       # derive address from public key
│
├── encoding/
│   ├── __init__.py
│   └── rlp.py           # RLP encode / decode
│
├── trie/
│   ├── __init__.py
│   ├── nodes.py         # BranchNode, ExtensionNode, LeafNode
│   └── trie.py          # MerklePatriciaTrie (insert, get, root_hash)
│
├── state/
│   ├── __init__.py
│   ├── account.py       # Account dataclass
│   └── world_state.py   # WorldState: account map + stateRoot
│
├── core/
│   ├── __init__.py
│   ├── transaction.py   # Transaction dataclass, sign(), validate()
│   ├── block.py         # Block + BlockHeader dataclasses
│   └── blockchain.py    # Blockchain: mine_block, apply_block, chain history
│
├── evm/
│   ├── __init__.py
│   ├── opcodes.py       # Opcode dispatch table and implementations
│   ├── evm.py           # EVM class: stack, memory, storage, PC, gas
│   └── gas.py           # Gas cost constants
│
├── execution/
│   ├── __init__.py
│   └── apply_transaction.py  # apply_transaction(world_state, tx) → receipt
│
├── contracts/
│   ├── __init__.py
│   ├── counter.py       # Hardcoded Counter contract bytecode + ABI
│   └── token.py         # Hardcoded SimpleToken bytecode + ABI
│
└── scenarios/
    ├── 01_transfer_eth.py        # Guided: send ETH between accounts
    ├── 02_deploy_counter.py      # Guided: deploy contract, inspect state
    ├── 03_call_counter.py        # Guided: call increment, read value
    ├── 04_token_transfer.py      # Guided: token mint + transfer flow
    └── 05_full_block.py          # Guided: multiple txs in one block
```

### Structure Rationale

- **crypto/:** No dependencies on other modules. Built first. Everything else depends on it.
- **encoding/:** RLP is dependency-free and needed by trie, block, and transaction serialization.
- **trie/:** Depends only on crypto (keccak256). No state or EVM knowledge.
- **state/:** Depends on trie and encoding. Represents pure account data, no execution logic.
- **core/:** Block and Transaction depend on crypto, encoding, and state. Blockchain ties blocks to state.
- **evm/:** Depends on state (reads/writes account storage). No block or chain knowledge.
- **execution/:** Glue layer; calls EVM and updates world_state. Depends on everything below it.
- **contracts/:** Pure data (bytecode bytes + helper to encode calldata). No runtime dependencies.
- **scenarios/:** Top-level scripts that import and exercise all layers. Designed for breakpoints.

## Architectural Patterns

### Pattern 1: Pure State Transition Functions

**What:** Core execution logic is expressed as pure functions `apply_transaction(state, tx) -> (new_state, receipt)` and `apply_block(state, block) -> new_state`, matching the Yellow Paper's Υ(σ,T)=σ' formulation. No hidden mutation, no side effects beyond the returned state.

**When to use:** Everywhere in the execution and blockchain layers.

**Trade-offs:** Slightly more verbose than mutation-in-place; dramatically better for debugging because every intermediate state is inspectable and the function signature documents what changes.

**Example:**
```python
def apply_transaction(world_state: WorldState, tx: Transaction) -> tuple[WorldState, Receipt]:
    """
    Yellow Paper Section 6: Υ(σ, T) → σ'
    Breakpoint here to inspect pre/post state.
    """
    new_state = world_state.copy()
    sender = new_state.get_account(tx.sender)
    # 1. validate nonce + balance
    # 2. deduct upfront gas cost
    # 3. execute (EVM or value transfer)
    # 4. refund remaining gas
    # 5. pay miner fee
    return new_state, receipt
```

### Pattern 2: EVM as an Isolated Execution Context

**What:** The EVM class holds a self-contained execution context: `stack`, `memory`, `storage`, `pc` (program counter), `gas_remaining`, and `returndata`. It does not directly modify WorldState — it accepts the account's current storage snapshot on entry and returns mutations on exit.

**When to use:** EVM execution of contract calls and deployments.

**Trade-offs:** Requires the caller (apply_transaction) to merge storage mutations back into WorldState, adding a step; but the EVM stays testable in isolation — you can call `evm.run(bytecode, calldata)` without any blockchain context.

**Example:**
```python
class EVM:
    def __init__(self, bytecode: bytes, calldata: bytes, storage: dict, gas: int):
        self.stack: list[int] = []
        self.memory: bytearray = bytearray()
        self.storage: dict = storage.copy()  # snapshot, not reference
        self.pc: int = 0
        self.gas: int = gas

    def run(self) -> bytes:
        """Execute until STOP/RETURN/REVERT. Breakpoint any opcode dispatch."""
        while self.pc < len(self.bytecode):
            opcode = self.bytecode[self.pc]
            self._dispatch(opcode)
        return self.returndata
```

### Pattern 3: Hardcoded Contract Bytecode with ABI Helpers

**What:** Instead of compiling Solidity, store contract bytecode as Python `bytes` literals. Provide a helper `encode_call(selector, *args)` to construct calldata from known 4-byte selectors and ABI-encoded arguments.

**When to use:** All example contracts (Counter, SimpleToken).

**Trade-offs:** Brittle if bytecode needs to change; but perfectly stable for a fixed learning tool and avoids the entire Solidity/compiler dependency chain.

**Example:**
```python
# contracts/counter.py
COUNTER_BYTECODE = bytes.fromhex("608060405234801561001057...")

# Function selectors (keccak256 of ABI signature, first 4 bytes)
SELECTOR_INCREMENT = bytes.fromhex("d09de08a")  # increment()
SELECTOR_GET_COUNT = bytes.fromhex("a87d942c")  # getCount()

def call_increment() -> bytes:
    return SELECTOR_INCREMENT  # no args

def call_get_count() -> bytes:
    return SELECTOR_GET_COUNT  # no args
```

### Pattern 4: Trie-Backed State with Explicit Root Hashing

**What:** WorldState wraps a MerklePatriciaTrie. After every account mutation, the trie can produce a deterministic `state_root` via `trie.root_hash()`. This root is stored in block headers. For the educational build, the trie can initially be simplified (Python dict) with the real MPT added later.

**When to use:** WorldState and block header construction.

**Trade-offs:** The full MPT is moderately complex to implement correctly (branch/extension/leaf nodes + hex-prefix encoding). Defer full MPT to a dedicated phase; use a simple dict-backed state first so EVM and transaction logic can be built and tested immediately.

## Data Flow

### Transaction Lifecycle

```
Scenario Script
    │ creates keypair, builds Transaction(from, to, value, data, gas_limit, nonce)
    │ signs with private key (secp256k1)
    ▼
Blockchain.submit_transaction(tx)
    │ validates signature, nonce, balance
    │ adds to pending tx pool
    ▼
Blockchain.mine_block()
    │ selects pending txs
    │ calls apply_block(world_state, block_candidate)
    ▼
apply_block(world_state, block)
    │ iterates transactions
    │ calls apply_transaction(world_state, tx) for each
    ▼
apply_transaction(world_state, tx)
    │ deducts upfront gas from sender
    │ if tx.to is contract → calls EVM
    │ if tx.to is EOA → value transfer only
    ▼
EVM.run(bytecode, calldata, storage_snapshot, gas)
    │ dispatches opcodes: PUSH, ADD, SSTORE, SLOAD, ...
    │ charges gas per opcode
    │ on RETURN → returns output bytes + storage mutations
    ▼
apply_transaction merges EVM storage mutations into world_state
    │ refunds unused gas to sender
    │ pays miner fee to coinbase
    │ produces Receipt(tx_hash, gas_used, logs, status)
    ▼
apply_block accumulates receipts
    │ computes transactions_root (MPT of all txs)
    │ computes receipts_root (MPT of all receipts)
    │ finalizes block header with state_root
    ▼
Blockchain appends finalized Block to chain
    │ updates canonical head
    ▼
Scenario Script inspects final state
    (world_state.get_account(addr).balance, storage values, etc.)
```

### Key Data Flows

1. **Value transfer:** `Transaction(value) → apply_transaction → sender.balance -= value + gas_cost, recipient.balance += value`

2. **Contract deployment:** `Transaction(to=None, data=init_bytecode) → EVM runs init code → returns runtime bytecode → stored at newly created contract address → WorldState updated`

3. **Contract call:** `Transaction(to=contract_addr, data=calldata) → apply_transaction loads contract code from WorldState → EVM runs code → SLOAD/SSTORE mutates storage snapshot → mutations merged back to WorldState`

4. **Block finalization:** `All tx receipts → receipts MPT → receipts_root; world_state.trie → state_root; all txs → transactions MPT → txs_root; these three roots go into BlockHeader`

## Build Order (Component Dependencies)

This ordering ensures each layer only depends on what is already built. The sequence maps directly to phases.

```
1. Crypto Primitives
   └─ No dependencies
   └─ Produces: keccak256, keypair, sign, verify, address derivation

2. RLP Encoding
   └─ Depends on: nothing
   └─ Produces: rlp_encode, rlp_decode

3. Account + Transaction Data Models
   └─ Depends on: crypto (for address type), RLP (for serialization)
   └─ Produces: Account dataclass, Transaction dataclass + sign/validate

4. Merkle Patricia Trie
   └─ Depends on: crypto (keccak256), RLP (node encoding)
   └─ Produces: MerklePatriciaTrie with root_hash

5. WorldState
   └─ Depends on: Account, MerklePatriciaTrie
   └─ Produces: WorldState.get_account, set_account, state_root

6. EVM
   └─ Depends on: WorldState (reads storage), crypto (keccak256 opcode)
   └─ Produces: EVM.run() with stack, memory, storage, gas

7. Transaction Execution (apply_transaction)
   └─ Depends on: EVM, WorldState, Transaction
   └─ Produces: apply_transaction(state, tx) → (new_state, receipt)

8. Block + Blockchain
   └─ Depends on: apply_transaction, WorldState, Block/BlockHeader, MPT
   └─ Produces: mine_block(), apply_block(), canonical chain

9. Contracts (hardcoded bytecode + ABI helpers)
   └─ Depends on: crypto (selector = keccak256[:4])
   └─ Can be built in parallel with EVM (phase 6)

10. Scenario Scripts
    └─ Depends on: everything above
    └─ Produces: runnable learning exercises
```

## Anti-Patterns

### Anti-Pattern 1: Building EVM Before State

**What people do:** Implement EVM bytecode dispatch first because it's the most exciting part.

**Why it's wrong:** EVM depends on WorldState (SLOAD/SSTORE access account storage). Without a working state model, EVM tests are untestable in realistic conditions and require mocking that creates false confidence.

**Do this instead:** Build Account, WorldState, and a minimal dict-backed state first. EVM can then be tested end-to-end with real state reads/writes from day one.

### Anti-Pattern 2: Mutable Global World State

**What people do:** Store world state as a module-level dict mutated directly during transaction execution.

**Why it's wrong:** Makes it impossible to reason about the state before and after a transaction. Debugging is very hard because partial failures leave state corrupted. Failed transactions can't be rolled back.

**Do this instead:** Pass state explicitly to `apply_transaction` and return a new state. Copy-on-write for educational codebases at this scale (< 5K lines) is perfectly fast enough.

### Anti-Pattern 3: Full MPT From Day One

**What people do:** Insist on implementing the complete Modified Merkle Patricia Trie (with proper hex-prefix encoding, branch/extension/leaf nodes) before any other code can run.

**Why it's wrong:** MPT is the most implementation-intensive data structure in Ethereum. It blocks all progress on accounts, EVM, and transactions — the parts that best demonstrate Ethereum concepts.

**Do this instead:** Use a plain Python dict as the initial state backing store. Build the real MPT in a dedicated phase after EVM and basic transactions are working. The `state_root` can initially be `keccak256(rlp_encode(sorted(state.items())))` as a placeholder.

### Anti-Pattern 4: Mixing EVM Context Into Block/Blockchain Classes

**What people do:** Put EVM execution logic directly inside a `Block.execute()` method or `Blockchain.process_transaction()`.

**Why it's wrong:** Destroys testability. The EVM becomes impossible to test without constructing a full Block. Block becomes responsible for knowing about stack machines.

**Do this instead:** `Blockchain` calls `apply_block(state, block)`, which calls `apply_transaction(state, tx)`, which calls `EVM.run(bytecode, calldata)`. Each level is independently testable.

### Anti-Pattern 5: Opaque Bytecode in Scenario Scripts

**What people do:** Embed raw hex bytecode strings in scenario scripts with no explanation of what they do.

**Why it's wrong:** The educational value is lost. A learner stepping through the debugger sees `0x6080604052...` with no idea what opcode it represents.

**Do this instead:** In `contracts/`, provide the bytecode alongside a comment listing the disassembled opcodes and what each section does (e.g., `# PUSH1 0x60  — push free memory pointer`). The scenario scripts import the named constant (`COUNTER_BYTECODE`) not a raw hex string.

## Integration Points

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| Scenario → Blockchain | Direct Python method calls | Scenarios import from `core.blockchain`; no abstraction layer needed |
| Blockchain → apply_transaction | Function call: `apply_transaction(state, tx)` | Pure function, no shared mutable state |
| apply_transaction → EVM | Instantiate `EVM(bytecode, calldata, storage, gas)` and call `run()` | EVM returns `(output_bytes, storage_mutations, gas_used, revert_flag)` |
| EVM → WorldState | EVM receives a storage snapshot dict on init; SLOAD reads from it; SSTORE writes to it | WorldState is NOT injected into EVM — only the specific contract's storage snapshot is passed |
| WorldState → MerklePatriciaTrie | `world_state.set_account()` updates trie; `world_state.state_root` calls `trie.root_hash()` | WorldState owns the trie instance |
| Transaction → Crypto | `tx.sign(private_key)` calls `crypto.keys.sign()`; `tx.recover_sender()` calls `crypto.keys.recover()` | One-way dependency: transactions use crypto, crypto knows nothing about transactions |

### External Libraries (Minimal)

| Library | Integration Point | Notes |
|---------|-------------------|-------|
| `pysha3` or `pycryptodome` | `crypto/hash.py` — keccak256 | Only stdlib `hashlib` doesn't include keccak256; one of these fills the gap |
| `coincurve` or `eth-keys` | `crypto/keys.py` — secp256k1 sign/verify | `coincurve` is a thin libsecp256k1 wrapper; most debugger-friendly option |
| No database | State lives in-memory Python dicts | Single-node, in-process; persistence not needed for the educational goal |

## Scalability Considerations

This is an educational single-node implementation. Scalability in the traditional sense is irrelevant. The relevant concern is **code complexity at scale** (more opcodes, more account types, more scenario scripts).

| Concern | Approach |
|---------|----------|
| Adding more opcodes | Opcode dispatch table (dict mapping byte → handler function) scales to 150 opcodes without structural change |
| Adding more contract examples | `contracts/` folder is self-contained; each new contract is a file with bytecode + selector constants |
| Introducing storage persistence | WorldState can add a `save(path)` / `load(path)` that serializes the trie to JSON or SQLite; nothing else changes |
| Replacing dict-backed state with real MPT | WorldState is the only class that changes; all callers use `get_account`/`set_account` interface |

## Sources

- Ethereum Yellow Paper (Gavin Wood) — state transition functions Υ, Π, Ω; EVM execution model; account structure: https://ethereum.github.io/yellowpaper/paper.pdf [HIGH confidence]
- ethereum.org EVM documentation — stack machine, memory, storage, opcodes, gas: https://ethereum.org/developers/docs/evm/ [HIGH confidence]
- ethereum.org Merkle Patricia Trie documentation — three trie types (state, transactions, receipts), block header roots: https://ethereum.org/developers/docs/data-structures-and-encoding/patricia-merkle-trie/ [HIGH confidence]
- py-evm reference implementation (Ethereum Foundation) — module organization, MiningChain, VM fork structure: https://github.com/ethereum/py-evm [HIGH confidence]
- pyethereum "maximally state-centric" architecture — apply_transaction / apply_block pure function pattern: https://github.com/ethereum/pyethereum [MEDIUM confidence — archived project]
- Lucas Saldanha Yellow Paper walkthrough — transaction execution step sequence: https://www.lucassaldanha.com/transaction-execution-ethereum-yellow-paper-walkthrough-4-7/ [MEDIUM confidence]
- QuickNode EVM architecture deep dive — opcode reference, stack depth 1024, gas metering: https://www.quicknode.com/guides/ethereum-development/smart-contracts/a-dive-into-evm-architecture-and-opcodes [MEDIUM confidence]
- "Building Ethereum from scratch in 10 minutes" — layered build order evidence: https://medium.com/brexeng/building-ethereum-from-scratch-in-10-minutes-fe74519ef8c8 [LOW confidence — single source, use for ordering intuition only]

---
*Architecture research for: Educational Ethereum Blockchain (Python, single-node)*
*Researched: 2026-02-19*
