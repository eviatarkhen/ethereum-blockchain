# Phase 2: State and Data Structures - Research

**Researched:** 2026-02-19
**Domain:** Ethereum account model, world state, transaction structure, block structure (Python dataclasses)
**Confidence:** HIGH

## Summary

Phase 2 builds the data layer that sits between Phase 1's crypto/encoding primitives and Phase 3's EVM execution engine. The official Ethereum execution-specs (ethereum/execution-specs, Frontier fork) provides the canonical Python reference implementation using `@dataclass` throughout. Our simplified version drops the Merkle Patricia Trie (deferred to v2) in favor of dict-backed state, drops PoW/PoS fields from block headers, and uses legacy (pre-EIP-1559) transactions only.

The key architectural insight from the execution-specs is the separation of concerns: `fork_types.py` defines Account + type aliases, `state.py` provides functional-style state operations (get/set/modify), `transactions.py` defines Transaction + signing/recovery, and `blocks.py` defines Header + Block. This maps cleanly to our module structure under `src/ethereum/`.

**Primary recommendation:** Follow the execution-specs pattern of `@dataclass` with functional helper functions, simplified to use `dict[bytes, Account]` for world state instead of tries, and integrating directly with the Phase 1 `keccak256`, `rlp_encode`/`rlp_decode`, and `eth-keys` primitives.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **Minimal block header**: parent_hash, block_number, timestamp, state_root placeholder -- no gas_used, difficulty, or other fields

### Claude's Discretion
- Account model design: EOA vs contract account distinction, balance/nonce types, storage representation, dataclass vs plain class
- World state operations: genesis initialization approach, rollback/snapshot support timing, API style, state root placeholder
- Transaction structure: transaction format (legacy only vs EIP-1559), signed/unsigned relationship, signing API, contract address derivation timing
- Block and chain linking: genesis block creation, validation on append, block hashing approach

**Guiding principles:**
1. Debugger readability -- structures should display clearly when stepping through code
2. Educational value -- show how Ethereum works, not just mimic it
3. Phase 1 integration -- use crypto/encoding primitives where it demonstrates the protocol

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| STATE-01 | Account model with balance, nonce, code hash, and storage | Account dataclass pattern from execution-specs; single class for both EOA and contract |
| STATE-02 | Dict-backed world state with get/set/update operations | Functional state operations (get_account, set_account, modify_state) adapted for dict backend |
| STATE-03 | Genesis state initialization with pre-funded accounts | Factory function that creates WorldState with pre-funded accounts from a config dict |
| TX-01 | Transaction structure (nonce, to, value, data, gas, signature) | Transaction dataclass with unsigned fields + v,r,s signature components |
| TX-02 | Transaction signing and sender recovery | RLP-encode unsigned fields, keccak256 hash, sign with eth-keys, recover sender from v,r,s |
| BLOCK-01 | Block structure (header with parent hash, state root, tx list) | Simplified Header dataclass (4 fields per user decision) + Block with header + tx list |
| BLOCK-02 | Block creation / simplified mining (no PoW/PoS) | Factory function that assembles block from transactions, no mining computation |
| BLOCK-03 | Chain management (append block, validate chain) | Blockchain class/functions that validate parent_hash linkage on append |
</phase_requirements>

## Standard Stack

### Core (Already Installed from Phase 1)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| eth-keys | 0.7.0 | ECDSA signing, public key recovery | Official Ethereum Foundation library for secp256k1 |
| eth-hash[pycryptodome] | 0.7.1 | Keccak-256 hashing | Official Ethereum Foundation hash library |
| Python dataclasses | stdlib | Data structure definitions | Standard Python pattern matching execution-specs |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Our rlp module | Phase 1 | Transaction/block RLP encoding | Serialization for signing hash and block hash |
| Our hashing module | Phase 1 | keccak256() | Address derivation, signing hash, block hash |
| Our keys module | Phase 1 | sign_message, recover_public_key | Transaction signing and sender recovery |

### No New Dependencies Needed
Phase 2 builds entirely on Phase 1 primitives plus Python stdlib. No new pip packages required.

## Architecture Patterns

### Recommended Project Structure
```
src/ethereum/
├── crypto/              # Phase 1 (exists)
│   ├── hashing.py       # keccak256
│   └── keys.py          # ECDSA operations
├── encoding/            # Phase 1 (exists)
│   └── rlp.py           # RLP encode/decode
├── state/               # Phase 2 NEW
│   ├── __init__.py
│   ├── account.py       # Account dataclass, EMPTY_ACCOUNT
│   └── world_state.py   # WorldState class with get/set/modify
├── transactions/        # Phase 2 NEW
│   ├── __init__.py
│   └── transaction.py   # Transaction dataclass, signing, recovery
└── chain/               # Phase 2 NEW
    ├── __init__.py
    ├── block.py          # Header, Block dataclasses
    └── blockchain.py     # Blockchain class, chain validation
```

### Pattern 1: Dataclass with Functional Helpers
**What:** Define data as `@dataclass`, operations as standalone functions
**When to use:** All Phase 2 data structures
**Why:** Matches execution-specs style, excellent debugger inspection, clear separation of data and behavior

```python
# Source: ethereum/execution-specs frontier/fork_types.py
@dataclass
class Account:
    nonce: int
    balance: int
    code: bytes
    storage: dict[bytes, int]  # SIMPLIFIED: dict instead of storage trie

EMPTY_ACCOUNT = Account(nonce=0, balance=0, code=b"", storage={})

def get_account(state: dict, address: bytes) -> Account:
    return state.get(address, EMPTY_ACCOUNT)
```

### Pattern 2: Unsigned-then-Signed Transaction Flow
**What:** Transaction stores all fields including v,r,s. Signing produces these from unsigned fields.
**When to use:** Transaction creation and signing
**Why:** Matches Ethereum protocol -- the signing hash is computed over (nonce, gas_price, gas, to, value, data) only, then v,r,s are appended.

```python
# Source: ethereum/execution-specs frontier/transactions.py
def signing_hash(tx: Transaction) -> bytes:
    """Hash of unsigned transaction fields for signing."""
    return keccak256(rlp_encode([
        int_to_rlp_bytes(tx.nonce),
        int_to_rlp_bytes(tx.gas_price),
        int_to_rlp_bytes(tx.gas),
        tx.to,
        int_to_rlp_bytes(tx.value),
        tx.data,
    ]))

def recover_sender(tx: Transaction) -> bytes:
    """Recover sender address from signed transaction."""
    # v is 27 or 28 in legacy transactions
    # public_key = ecrecover(signing_hash, v, r, s)
    # address = keccak256(public_key)[12:32]
```

### Pattern 3: Dict-Backed World State
**What:** Use `dict[bytes, Account]` as the state backend, with functional get/set/modify operations
**When to use:** All state operations in Phase 2
**Why:** Defers MPT to v2, provides O(1) lookups, simple to debug

```python
# SIMPLIFIED: Dict instead of Merkle Patricia Trie
# Real Ethereum uses MPT for state root computation
class WorldState:
    def __init__(self):
        self._accounts: dict[bytes, Account] = {}

    def get_account(self, address: bytes) -> Account:
        return self._accounts.get(address, EMPTY_ACCOUNT)

    def set_account(self, address: bytes, account: Account) -> None:
        self._accounts[address] = account
```

### Anti-Patterns to Avoid
- **Storing signature in a separate object:** Keep v,r,s on the Transaction itself (matches protocol, simpler debugging)
- **Using inheritance for EOA vs Contract accounts:** Single Account class with empty code for EOAs (matches execution-specs)
- **Mutable state without clear APIs:** Always go through get/set/modify functions, never mutate accounts in-place outside those functions
- **Computing real state root with dict backend:** Use a placeholder hash (keccak256 of serialized accounts or a dummy value) since real state roots require MPT

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| ECDSA signing | Custom elliptic curve math | eth-keys library (Phase 1) | Cryptographic correctness requires audited implementation |
| Keccak-256 | hashlib.sha3_256 | eth-hash library (Phase 1) | SHA-3 != Keccak-256; silent corruption |
| RLP encoding | JSON or pickle serialization | Our rlp.py (Phase 1) | Protocol requires RLP specifically |
| Address derivation | Manual byte slicing of raw key | keys.py derive_address (Phase 1) | eth-keys handles public key format internally |

**Key insight:** Phase 2 should maximize reuse of Phase 1 primitives. Every hash, signature, and encoding operation should call the existing modules.

## Common Pitfalls

### Pitfall 1: Sign-then-hash vs Hash-then-sign Confusion
**What goes wrong:** Signing the wrong data -- either signing raw transaction bytes instead of the RLP-encoded hash, or double-hashing
**Why it happens:** eth-keys `sign_msg()` internally hashes the message, but for transactions we need to hash the RLP encoding ourselves and use `sign_msg_hash()`
**How to avoid:** Use `private_key.sign_msg_hash(signing_hash)` where `signing_hash = keccak256(rlp_encode(unsigned_fields))`. The Phase 1 keys.py docstring already notes this distinction.
**Warning signs:** Recovered sender address doesn't match expected address

### Pitfall 2: Integer 0 in RLP Encoding
**What goes wrong:** Nonce 0 or value 0 encoded incorrectly in transaction RLP
**Why it happens:** Integer 0 must encode as empty bytes (0x80), not as b'\x00'
**How to avoid:** Always use `int_to_rlp_bytes()` from Phase 1's rlp.py, which correctly returns `b""` for 0
**Warning signs:** Transaction hash doesn't match expected value, signing hash differs between implementations

### Pitfall 3: Address Format Inconsistency
**What goes wrong:** Mixing 20-byte raw addresses with 0x-prefixed hex strings
**Why it happens:** Ethereum addresses appear in both formats across documentation
**How to avoid:** Standardize on 20-byte `bytes` internally (matching execution-specs `Address = Bytes20`). Convert to/from hex only at display boundaries.
**Warning signs:** KeyError on state lookup, address comparison failures

### Pitfall 4: Transaction `to` Field for Contract Creation
**What goes wrong:** Using `None` or empty string for contract creation transactions
**Why it happens:** Ethereum uses empty bytes `b""` for the `to` field in contract creation
**How to avoid:** Use `b""` (empty bytes) for contract creation, 20-byte address for value transfers. The execution-specs uses `Bytes0` type for this.
**Warning signs:** RLP encoding fails or produces wrong output for contract creation txs

### Pitfall 5: v Value in Legacy Transactions
**What goes wrong:** Using wrong v value (0/1 vs 27/28) in transaction signature
**Why it happens:** eth-keys returns v as 0 or 1, but legacy Ethereum transactions use v = 27 or 28
**How to avoid:** Add 27 to the recovery id from eth-keys: `v = signature.v + 27`. For recovery, subtract 27: `recovery_id = v - 27`
**Warning signs:** `recover_sender` fails or returns wrong address

### Pitfall 6: Genesis Block Special Cases
**What goes wrong:** Genesis block fails validation because it has no parent
**Why it happens:** Genesis block's parent_hash is conventionally all zeros (32 zero bytes)
**How to avoid:** Use `b'\x00' * 32` as genesis parent_hash, block_number = 0. Special-case genesis in chain validation.
**Warning signs:** Chain validation fails on first block

## Code Examples

### Account Creation and State Operations
```python
from dataclasses import dataclass

@dataclass
class Account:
    """Ethereum account state.

    Every address on Ethereum has an associated Account.
    EOAs have empty code; contract accounts have deployed bytecode.

    # SIMPLIFIED: Storage is a plain dict, not a Merkle Patricia Trie.
    # Real Ethereum computes a storage_root hash from the trie.
    """
    nonce: int = 0
    balance: int = 0
    code: bytes = b""
    storage: dict[bytes, int] = field(default_factory=dict)

    @property
    def code_hash(self) -> bytes:
        """Keccak-256 hash of the account's code."""
        return keccak256(self.code)

    @property
    def is_empty(self) -> bool:
        return self.nonce == 0 and self.balance == 0 and self.code == b""
```

### Transaction Signing Flow
```python
# 1. Create unsigned transaction
tx = Transaction(
    nonce=0,
    gas_price=1,
    gas=21000,
    to=recipient_address,  # 20-byte address
    value=1000000,
    data=b"",
    v=0, r=0, s=0  # placeholder before signing
)

# 2. Compute signing hash (RLP of unsigned fields, then keccak256)
unsigned_fields = [
    int_to_rlp_bytes(tx.nonce),
    int_to_rlp_bytes(tx.gas_price),
    int_to_rlp_bytes(tx.gas),
    tx.to,
    int_to_rlp_bytes(tx.value),
    tx.data,
]
tx_hash = keccak256(rlp_encode(unsigned_fields))

# 3. Sign with eth-keys (sign_msg_hash, NOT sign_msg)
signature = private_key.sign_msg_hash(tx_hash)

# 4. Create signed transaction
signed_tx = Transaction(
    nonce=tx.nonce, gas_price=tx.gas_price, gas=tx.gas,
    to=tx.to, value=tx.value, data=tx.data,
    v=signature.v + 27,  # Legacy: add 27 to recovery id
    r=signature.r,
    s=signature.s,
)

# 5. Recover sender
recovered_pub = signature.recover_public_key_from_msg_hash(tx_hash)
sender_address = keccak256(recovered_pub.to_bytes())[12:]  # Last 20 bytes
```

### Block Hash Computation
```python
def compute_block_hash(header: Header) -> bytes:
    """Compute block hash from header fields.

    # SIMPLIFIED: Only hashing our minimal header fields.
    # Real Ethereum RLP-encodes all 15+ header fields.
    """
    header_fields = [
        header.parent_hash,
        int_to_rlp_bytes(header.number),
        int_to_rlp_bytes(header.timestamp),
        header.state_root,
    ]
    return keccak256(rlp_encode(header_fields))
```

### Genesis Initialization
```python
def create_genesis_state(alloc: dict[bytes, int]) -> WorldState:
    """Create genesis world state with pre-funded accounts.

    Args:
        alloc: Mapping of address (20 bytes) to initial balance (wei).

    Returns:
        WorldState with accounts initialized.
    """
    state = WorldState()
    for address, balance in alloc.items():
        account = Account(nonce=0, balance=balance, code=b"", storage={})
        state.set_account(address, account)
    return state
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| py-evm (archived Sep 2025) | execution-specs (active) | 2025 | Canonical Python reference is now execution-specs |
| rlp.Serializable classes | @dataclass with RLP helpers | execution-specs migration | Simpler, more Pythonic data structures |
| EIP-1559 (Type 2) default | Legacy (Type 0) still valid | EIP-2718 (2021) | Legacy format is simpler and sufficient for educational use |

**Deprecated/outdated:**
- py-evm repository: Archived September 2025, replaced by execution-specs
- pyrlp Serializable pattern: Replaced by plain dataclasses in execution-specs

## Open Questions

1. **State root placeholder approach**
   - What we know: Real state root requires MPT (deferred to v2). Need something for the block header.
   - What's unclear: Best placeholder value -- dummy constant, keccak256 of sorted accounts, or keccak256(b"")?
   - Recommendation: Use `keccak256(rlp_encode(sorted account data))` as a deterministic placeholder. Marks with `# SIMPLIFIED:` comment. This gives meaningful output (different state = different root) even without MPT.

2. **Snapshot/rollback in Phase 2 vs Phase 3**
   - What we know: The execution-specs State has begin_transaction/commit_transaction/rollback_transaction for EVM state changes.
   - What's unclear: Whether to build this now or defer to Phase 3.
   - Recommendation: Defer to Phase 3. Phase 2 only needs get/set/modify. Rollback is only needed when EVM execution fails mid-transaction.

3. **Contract address derivation**
   - What we know: Contract address = keccak256(rlp_encode([sender_address, sender_nonce]))[12:]. This is a simple formula.
   - What's unclear: Whether to include in Phase 2 or Phase 3.
   - Recommendation: Include as a utility function in Phase 2 (it's just crypto + RLP, no EVM needed) but actual contract creation logic belongs in Phase 3.

## Sources

### Primary (HIGH confidence)
- ethereum/execution-specs (Frontier fork) - Account, State, Transaction, Block dataclass definitions and full functional API
- ethereum.org/developers/docs/accounts - Account structure (4 fields: nonce, balance, codeHash, storageRoot)
- ethereum.org/developers/docs/transactions - Transaction fields, signing process, v/r/s recovery
- ethereum.org/developers/docs/blocks - Block header structure, execution payload

### Secondary (MEDIUM confidence)
- Phase 1 codebase (src/ethereum/) - Existing crypto and encoding modules, API patterns established

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - No new dependencies, all Phase 1 primitives verified working
- Architecture: HIGH - execution-specs provides canonical Python reference with @dataclass pattern
- Pitfalls: HIGH - Well-documented in execution-specs source and Ethereum documentation (v offset, RLP integer encoding, signing flow)

**Research date:** 2026-02-19
**Valid until:** 2026-03-19 (stable domain, Frontier-era data structures don't change)
