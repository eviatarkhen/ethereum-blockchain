# Phase 4: Contracts and Scenarios - Research

**Researched:** 2026-02-19
**Domain:** EVM bytecode contracts, ABI encoding, transaction signing, scenario scripting
**Confidence:** HIGH (core EVM/ABI specs), MEDIUM (bytecode construction patterns), HIGH (Python tooling)

## Summary

Phase 4 is the capstone phase that ties together everything built in Phases 1-3. It has two distinct deliverables: (1) hardcoded bytecode for a Counter and a SimpleToken contract, and (2) three scenario scripts that drive the full transaction lifecycle — ETH transfer, contract deployment, and contract interaction. No Solidity compiler is needed; the REQUIREMENTS.md explicitly lists Solidity compiler as out-of-scope. Both contracts will be supplied as hand-crafted Python `bytes` literals annotated with opcode comments for clarity.

The primary complexity in Phase 4 is not the contracts themselves — they are simple — but the integration surface: the scenario scripts must correctly construct and sign transactions (EIP-155), compute contract addresses deterministically (CREATE formula), encode ABI calldata (4-byte selector + padded args), and interpret return data from CALL. All of these have precise, well-specified rules that must be implemented correctly for the EVM to execute them.

The educational goal — a developer can set a breakpoint anywhere and inspect EVM state — is already satisfied by Phase 3's EVM implementation. Phase 4's job is to give developers meaningful things to step through: end-to-end scenario flows with clear narrative comments guiding what to look for at each step.

**Primary recommendation:** Write the scenario scripts as standalone Python files in `scenarios/` that import from `src/ethereum/`. Each script runs top-to-bottom with no framework, creating accounts, signing transactions, calling the EVM, and printing final state. This maximizes debugger step-through value and requires zero extra infrastructure.

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| CNTR-01 | Hardcoded counter contract (increment, get count) | Hand-crafted EVM bytecode using PUSH1, SLOAD, SSTORE, CALLDATALOAD, JUMPI, JUMPDEST, RETURN. Function dispatcher pattern required. See Architecture Patterns section. |
| CNTR-02 | Hardcoded simple token contract (transfer, balance check) | Same bytecode pattern but with two storage slots per address (mapped via keccak of address+slot). Requires SHA3 opcode (0x20) for mapping key derivation. See Architecture Patterns section. |
| LEARN-01 | Scenario script: simple ETH transfer end-to-end | Requires: signed legacy transaction, EIP-155 v computation, state transition function from Phase 3. No contract code involved. See Code Examples section. |
| LEARN-02 | Scenario script: deploy and interact with counter contract | Requires: CREATE transaction (empty `to`), contract address derivation (keccak(RLP([sender, nonce]))[12:]), then CALL transaction with ABI-encoded function selector. |
| LEARN-03 | Scenario script: deploy and interact with token contract | Same deploy pattern as LEARN-02 plus multiple CALL transactions (transfer, balanceOf). Requires ABI encoding for (address, uint256) arguments. |
</phase_requirements>

---

## Standard Stack

### Core (no new dependencies needed)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| eth-hash | >=0.7.0 | keccak256 for ABI selector derivation, contract address derivation | Already in requirements.txt; correct keccak (not SHA-3) |
| eth-keys | >=0.7.0 | ECDSA signing for transactions | Already in requirements.txt |
| Python stdlib | 3.x | `int.to_bytes()`, `bytes.hex()`, `struct.pack()` for ABI encoding | No extra deps needed for uint256 padding |

### No New Dependencies Required

Phase 4 needs no additional PyPI packages. Everything required — keccak256, ECDSA signing, RLP encoding — was built in Phase 1 and is already available.

**ABI encoding** for simple types (uint256, address) is trivial with stdlib:
- `address` argument: `bytes.fromhex(addr_hex).rjust(32, b'\x00')`
- `uint256` argument: `n.to_bytes(32, 'big')`
- Function selector: `keccak256(b"functionName(type1,type2)")[:4]`

No `eth-abi` library is needed for the simple types used by Counter and SimpleToken.

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Hand-crafted bytecode | `solcx` + pysolc | Requires compiler toolchain install; adds complexity; out-of-scope per REQUIREMENTS.md |
| Stdlib int.to_bytes for ABI | `eth-abi` library | eth-abi handles complex types (tuples, dynamic arrays) — overkill for uint256 and address |
| Standalone scenario scripts | pytest fixtures | Pytest fixtures are better for assertion-based testing; scenarios are demonstration scripts, not test suites |

**Installation:** No new packages. Verify existing requirements work:
```bash
pip install -r requirements.txt
```

---

## Architecture Patterns

### Recommended Project Structure

```
src/
├── ethereum/
│   ├── contracts/
│   │   ├── __init__.py
│   │   ├── counter.py        # COUNTER_BYTECODE bytes literal + ABI helpers
│   │   └── token.py          # TOKEN_BYTECODE bytes literal + ABI helpers
│   └── ...                   # existing crypto/, encoding/ modules

scenarios/
├── 01_eth_transfer.py         # LEARN-01: end-to-end ETH transfer
├── 02_counter.py              # LEARN-02: deploy + interact with Counter
└── 03_token.py                # LEARN-03: deploy + interact with SimpleToken
```

The `scenarios/` directory sits at the project root (sibling to `src/` and `tests/`). Scenario scripts are run directly with `python scenarios/01_eth_transfer.py`, not through pytest.

### Pattern 1: Hardcoded Contract Bytecode

**What:** The contract is expressed as a Python `bytes` literal with inline comments explaining each opcode.

**When to use:** Both CNTR-01 and CNTR-02. No Solidity compiler needed.

The contract bytecode has two parts that must be handled correctly:

**1. Init code (deployment code):** Executed once during CREATE. Its job is to copy the runtime code into memory and RETURN it so the EVM stores it at the contract address.

**2. Runtime code:** The actual contract logic, stored permanently after deployment.

For hardcoded contracts, the simplest approach is to supply ONLY the runtime code as the `data` field in the deployment transaction, and implement CREATE in Phase 3's EVM to store `msg.data` directly as the contract code (skipping the CODECOPY init code dance). Mark this with `# SIMPLIFIED:`.

**Example: Counter runtime bytecode (conceptual structure):**
```python
# src/ethereum/contracts/counter.py
# Source: manual construction per EVM opcode reference (ethervm.io)

# Counter contract logic:
#   increment() -> storage[0] += 1
#   getCount()  -> return storage[0]
#
# Function selectors (keccak256 of signature, first 4 bytes):
#   increment() = keccak256(b"increment()")[:4]
#   getCount()  = keccak256(b"getCount()")[:4]
#
# Dispatch pattern: read first 4 bytes of calldata, compare to selectors, JUMPI

COUNTER_RUNTIME_BYTECODE = bytes([
    # Function dispatcher: load calldata[0:32], extract top 4 bytes
    0x60, 0x00,  # PUSH1 0x00  -- offset 0 into calldata
    0x35,        # CALLDATALOAD  -- load 32 bytes from calldata[0]
    0x60, 0xe0,  # PUSH1 0xe0  -- 224 = 256 - 32 bits
    0x1c,        # SHR          -- shift right 224 bits -> 4-byte selector in low bits
    # ... compare against increment() selector, JUMPI to increment handler
    # ... compare against getCount() selector, JUMPI to getCount handler
    # ... REVERT if no match
])

# ABI encoding helpers
def encode_call(function_name: str, arg_types: list, args: list) -> bytes:
    """Encode a function call as EVM calldata.

    selector = keccak256(b"functionName(type1,type2)")[:4]
    calldata = selector + abi_encode(args)

    # SIMPLIFIED: Only handles uint256 and address types.
    """
    from src.ethereum.crypto.hashing import keccak256
    sig = f"{function_name}({','.join(arg_types)})".encode()
    selector = keccak256(sig)[:4]
    encoded_args = b""
    for arg, typ in zip(args, arg_types):
        if typ == "uint256":
            encoded_args += arg.to_bytes(32, 'big')
        elif typ == "address":
            encoded_args += bytes.fromhex(arg.lstrip("0x")).rjust(32, b'\x00')
    return selector + encoded_args
```

### Pattern 2: Simplified CREATE — Runtime Code Direct Storage

**What:** Instead of executing init code, the EVM's CREATE handler stores `msg.data` directly as the contract's runtime code.

**Why it's the right simplification:** Full init code support requires implementing CODECOPY and the constructor call frame. For hardcoded contracts, the init code would simply copy the runtime bytes and return them — adding 15-20 bytes of boilerplate opcodes to every contract. Skipping this makes bytecode simpler to write, read, and explain.

**How to implement:**
```python
# In Phase 3's EVM CREATE handler:
# SIMPLIFIED: Skip init code execution. Store msg.data directly as contract code.
# Real Ethereum executes init code which returns the runtime code to store.
world_state[new_contract_addr]['code'] = transaction.data
```

This must be a decision made during Phase 3 EVM planning and implementation. If Phase 3 already chose to execute init code, then the counter/token bytecode must include proper init code preamble.

### Pattern 3: Contract Address Derivation (CREATE)

**What:** After deploying a contract, the scenario script needs to know the address where the contract was stored.

**Formula (HIGH confidence — from EIP spec and multiple sources):**
```python
# Source: EIP-155, RareSkills post on address derivation
from src.ethereum.crypto.hashing import keccak256
from src.ethereum.encoding.rlp import rlp_encode, int_to_rlp_bytes

def compute_contract_address(sender_address: bytes, nonce: int) -> bytes:
    """Compute the address of a contract deployed with CREATE.

    address = keccak256(RLP([sender_address, nonce]))[12:]

    Edge cases:
    - nonce == 0: RLP encodes as 0x80 (empty string)
    - nonce 1-127: RLP encodes as the single byte (e.g. 0x01)
    - nonce >= 128: RLP encodes with length prefix

    # SIMPLIFIED: Real Ethereum initializes new contract nonce to 1 (EIP-161).
    # This implementation uses 0 for simplicity.
    """
    encoded = rlp_encode([sender_address, int_to_rlp_bytes(nonce)])
    return keccak256(encoded)[12:]
```

### Pattern 4: EIP-155 Transaction Signing

**What:** Legacy transaction signing with chain ID replay protection.

**Fields for signing (9-field structure):**
```python
# Source: EIP-155 specification
def sign_transaction(tx_fields: dict, private_key, chain_id: int = 1) -> dict:
    """Sign a transaction using EIP-155 replay protection.

    Signing hash = keccak256(RLP([nonce, gasPrice, gasLimit, to, value, data, chainId, 0, 0]))

    v in signed tx = {0, 1} + CHAIN_ID * 2 + 35

    # SIMPLIFIED: Only supports legacy (Type 0) transactions.
    # Real Ethereum also supports EIP-2930 (Type 1) and EIP-1559 (Type 2).
    """
    from src.ethereum.encoding.rlp import rlp_encode, int_to_rlp_bytes
    from src.ethereum.crypto.hashing import keccak256

    unsigned_fields = [
        int_to_rlp_bytes(tx_fields['nonce']),
        int_to_rlp_bytes(tx_fields['gas_price']),
        int_to_rlp_bytes(tx_fields['gas_limit']),
        tx_fields['to'],           # bytes20 or b'' for contract creation
        int_to_rlp_bytes(tx_fields['value']),
        tx_fields['data'],         # b'' for ETH transfer
        int_to_rlp_bytes(chain_id),
        b'',  # 0 as empty bytes
        b'',  # 0 as empty bytes
    ]
    signing_hash = keccak256(rlp_encode(unsigned_fields))
    signature = private_key.sign_msg_hash(signing_hash)

    # v encodes chain_id and recovery bit
    v = signature.v + chain_id * 2 + 35

    return {**tx_fields, 'v': v, 'r': int.from_bytes(signature.r, 'big'), 's': int.from_bytes(signature.s, 'big')}
```

### Pattern 5: Scenario Script Structure

**What:** Each scenario script is a standalone Python file with no test framework. It prints state at key points to show progression.

**When to use:** LEARN-01, LEARN-02, LEARN-03.

**Example structure (LEARN-02 counter scenario):**
```python
# scenarios/02_counter.py
"""
Scenario: Deploy and interact with Counter contract.

Set breakpoints at any print() or # BREAKPOINT comment to inspect state.

Execution flow:
  1. Genesis state created with funded account
  2. Deploy transaction: CREATE counter contract
  3. State updated: counter deployed at computed address
  4. Call transaction: increment()
  5. State updated: counter storage[0] == 1
  6. Call transaction: getCount()
  7. Return value decoded: count == 1
"""

import sys
sys.path.insert(0, '.')

from src.ethereum.crypto.keys import generate_key_pair, private_key_to_address
from src.ethereum.contracts.counter import COUNTER_RUNTIME_BYTECODE, encode_call

# -- Setup genesis state --
private_key, public_key = generate_key_pair()
sender_address = private_key_to_address(private_key)

# BREAKPOINT: world_state, sender_address, private_key visible here
world_state = {
    sender_address: {'balance': 10**18, 'nonce': 0, 'code': b'', 'storage': {}}
}

# -- Step 1: Deploy counter contract --
deploy_tx = sign_transaction({
    'nonce': 0,
    'gas_price': 10**9,
    'gas_limit': 100_000,
    'to': b'',           # empty = contract creation
    'value': 0,
    'data': COUNTER_RUNTIME_BYTECODE,
}, private_key)

# BREAKPOINT: deploy_tx fields, bytecode content visible here
world_state, receipt = apply_transaction(world_state, deploy_tx, block_context)
contract_address = compute_contract_address(sender_address, nonce=0)

print(f"Counter deployed at: {contract_address.hex()}")
# ... (similar pattern for increment and getCount calls)
```

### Pattern 6: SimpleToken Storage Layout

**What:** Solidity-style storage mapping for balances.

In Solidity, `mapping(address => uint256) public balances` stores each balance at storage slot `keccak256(abi.encode(address, slot_number))`. For hardcoded bytecode, use the same convention so the implementation is correct and educational.

**Storage key derivation:**
```python
# Source: Ethereum Yellow Paper / Solidity storage layout docs
# For mapping at slot 0: storage_key = keccak256(abi.encode(address, 0))
# abi.encode(address, slot) = address.rjust(32, b'\x00') + (0).to_bytes(32, 'big')

def mapping_key(address: bytes, slot: int) -> int:
    """Compute storage slot for mapping(address => uint256) at given slot index."""
    from src.ethereum.crypto.hashing import keccak256
    encoded = address.rjust(32, b'\x00') + slot.to_bytes(32, 'big')
    key_bytes = keccak256(encoded)
    return int.from_bytes(key_bytes, 'big')
```

This requires the SHA3 opcode (0x20) in the EVM, which must be confirmed as implemented in Phase 3. If SHA3 was not included, the token contract must use a simpler storage layout (direct address-indexed slots without keccak) with a `# SIMPLIFIED:` note.

### Anti-Patterns to Avoid

- **Using pytest for scenario scripts:** Scenarios are demonstration flows, not assertions. They should run as plain Python scripts so developers can add `import pdb; pdb.set_trace()` anywhere.
- **Hiding ABI encoding behind an opaque library:** The whole point is education — compute selectors explicitly with keccak256, pad args with `to_bytes(32, 'big')`, and add comments explaining why.
- **Realistic gas prices:** Use round numbers (e.g., `gas_price = 1`, `gas_limit = 100_000`) so the math is trivial and doesn't distract from the flow.
- **Complex token contract:** Do not implement ERC-20 approve/transferFrom — the REQUIREMENTS.md specifies only `transfer` and `balance check`. Keep it minimal.
- **Dynamic bytecode generation:** Do not generate bytecode programmatically at runtime. The bytecode must be a readable constant that a developer can inspect in the source file.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Keccak-256 for ABI selectors | Custom hash | `eth-hash` (already installed) | Already correct and tested in Phase 1 |
| ECDSA signing for transactions | Custom signing | `eth-keys` (already installed) | Already correct and tested in Phase 1 |
| RLP encoding for CREATE address | Custom encoder | Phase 1's `rlp.py` | Already implemented; nonce edge cases handled |
| uint256 ABI encoding | Custom encoder | stdlib `int.to_bytes(32, 'big')` | uint256 padding is a trivial one-liner |

**Key insight:** Phase 4 is almost entirely integration work, not new library work. The custom implementations are already built. The main new code is: (1) the bytecode constants themselves, (2) thin ABI encoding helpers for the 2-3 argument types needed, and (3) the scenario script flows.

---

## Common Pitfalls

### Pitfall 1: Init Code vs Runtime Code Confusion

**What goes wrong:** The deployment transaction `data` field is submitted as the init code + runtime code concatenated. If only the runtime code is sent (the simplified approach), the CREATE opcode must be aware of this deviation and store `data` directly instead of executing it.

**Why it happens:** Full Ethereum CREATE executes the `data` as a program (init code) and stores whatever that program RETURNs (the runtime code). If you skip init code execution, the entire `data` becomes the runtime code.

**How to avoid:** Make the decision explicit during Phase 3 EVM planning. Document which approach Phase 3 implemented so Phase 4 bytecode is authored correctly.

**Warning signs:** Contract deploys "successfully" (no revert) but calling it produces unexpected results — means the stored code is the init code wrapper, not the runtime code.

### Pitfall 2: Function Selector Computation Errors

**What goes wrong:** Wrong ABI signature format produces wrong 4-byte selector, causing every function call to hit the REVERT fallback.

**Why it happens:** The signature must be canonical: `increment()` not `increment(void)`, `uint256` not `uint`, no spaces after commas, no parameter names — only types.

**How to avoid:** Verify selectors against a known reference:
```python
# Verify these before using in bytecode
from src.ethereum.crypto.hashing import keccak256
assert keccak256(b"increment()")[:4].hex() == "d09de08a"
assert keccak256(b"getCount()")[:4].hex() == "a87d942c"
assert keccak256(b"transfer(address,uint256)")[:4].hex() == "a9059cbb"
assert keccak256(b"balanceOf(address)")[:4].hex() == "70a08231"
```

**Warning signs:** All function calls revert immediately. Check selector bytes in calldata against bytecode PUSH constants.

### Pitfall 3: EIP-155 v Computation

**What goes wrong:** Using `v = recovery_bit + 27` (pre-EIP-155) instead of `v = recovery_bit + chain_id * 2 + 35`. The transaction signature validates but sender recovery produces the wrong address.

**Why it happens:** eth-keys returns the raw recovery bit (0 or 1). The v value stored in the signed transaction is chain-ID-adjusted.

**How to avoid:** Use `v = signature.v + chain_id * 2 + 35` explicitly. With `chain_id = 1` (mainnet), `v` is either 37 or 38.

**Warning signs:** `recover_sender(signed_tx)` returns a random address instead of the sender's address.

### Pitfall 4: Contract Address Not Matching

**What goes wrong:** The scenario script computes the expected contract address but it doesn't match where the EVM stored the contract.

**Why it happens:** The RLP encoding of `nonce=0` uses the empty byte string `b''` (encoded as `0x80`), not `0x00`. This is a known edge case from Phase 1's `int_to_rlp_bytes(0) == b''`.

**How to avoid:** Use Phase 1's `int_to_rlp_bytes(nonce)` to encode the nonce — it already handles the `0 -> b''` case correctly. The Phase 3 EVM CREATE handler must use the same function for address derivation so both sides agree.

**Warning signs:** Contract address computed by script differs from what the EVM stores; all subsequent CALL transactions fail with "no code at address."

### Pitfall 5: SHA3 Opcode Not in Phase 3

**What goes wrong:** The SimpleToken contract requires SHA3 (opcode 0x20) to compute mapping storage keys. If Phase 3 did not implement SHA3, the token contract cannot use Solidity-style mappings.

**Why it happens:** SHA3 is sometimes omitted from "minimal" EVM implementations because it's not needed for arithmetic-only contracts.

**How to avoid:** If SHA3 is not available from Phase 3, use a simplified storage layout for the token: store balances at slot `int.from_bytes(address, 'big')` directly (not keccak-hashed). Mark with `# SIMPLIFIED:`. This avoids slot collision for most addresses.

**Warning signs:** Cannot verify that keccak-based mapping keys work; use simplified layout as fallback.

### Pitfall 6: Return Value Decoding

**What goes wrong:** The scenario script sends a CALL transaction for `getCount()` but doesn't know how to read the return value from the EVM output.

**Why it happens:** The EVM RETURN opcode writes to the output buffer. The Phase 3 execution result must expose `result.return_data` as bytes.

**How to avoid:** Decode return value explicitly:
```python
result = evm.call(world_state, call_tx, block_context)
count = int.from_bytes(result.return_data[:32], 'big')
print(f"Count: {count}")  # BREAKPOINT: count, result.return_data visible
```

---

## Code Examples

### ABI Encoding for Counter Calls
```python
# Source: ABI encoding spec (ethereum.org) + keccak256 from Phase 1
from src.ethereum.crypto.hashing import keccak256

# No arguments
def encode_increment() -> bytes:
    selector = keccak256(b"increment()")[:4]
    return selector  # no args

# No arguments, returns uint256
def encode_get_count() -> bytes:
    selector = keccak256(b"getCount()")[:4]
    return selector  # no args

# address + uint256 arguments
def encode_transfer(to_address: bytes, amount: int) -> bytes:
    selector = keccak256(b"transfer(address,uint256)")[:4]
    encoded_to = to_address.rjust(32, b'\x00')
    encoded_amount = amount.to_bytes(32, 'big')
    return selector + encoded_to + encoded_amount

# address argument
def encode_balance_of(address: bytes) -> bytes:
    selector = keccak256(b"balanceOf(address)")[:4]
    encoded_addr = address.rjust(32, b'\x00')
    return selector + encoded_addr
```

### Contract Address Derivation
```python
# Source: EIP spec + RareSkills (rareskills.io/post/ethereum-address-derivation)
from src.ethereum.crypto.hashing import keccak256
from src.ethereum.encoding.rlp import rlp_encode, int_to_rlp_bytes

def compute_contract_address(sender: bytes, nonce: int) -> bytes:
    """keccak256(RLP([sender, nonce]))[12:]"""
    # int_to_rlp_bytes(0) == b'' which RLP encodes to 0x80 -- correct per spec
    encoded = rlp_encode([sender, int_to_rlp_bytes(nonce)])
    return keccak256(encoded)[12:]
```

### Minimal Block Context for EVM
```python
# Block context dict — EVM opcodes (NUMBER, TIMESTAMP, COINBASE, etc.) read from here
# SIMPLIFIED: Fixed values, no real block header
block_context = {
    'number': 1,
    'timestamp': 1_700_000_000,
    'coinbase': b'\x00' * 20,
    'gas_limit': 10_000_000,
    'difficulty': 1,
    'chain_id': 1,
}
```

### Scenario Script Template (LEARN-01 ETH Transfer)
```python
#!/usr/bin/env python3
"""
Scenario 01: Simple ETH Transfer

Goal: Demonstrate the complete lifecycle of a value transfer transaction.
Set breakpoints at any BREAKPOINT comment to inspect state at that step.

Lifecycle:
  1. Create genesis state with funded sender
  2. Create and sign a transaction (EIP-155)
  3. Validate the transaction (nonce, balance, gas)
  4. Execute state transition (debit sender, credit recipient)
  5. Package transaction into a block
  6. Verify final balances
"""
import sys
sys.path.insert(0, '.')

from src.ethereum.crypto.keys import generate_key_pair, private_key_to_address
from src.ethereum.crypto.hashing import keccak256
from src.ethereum.encoding.rlp import rlp_encode, int_to_rlp_bytes
# from src.ethereum.state.world_state import WorldState          # Phase 2
# from src.ethereum.evm.transaction import sign_transaction       # Phase 3
# from src.ethereum.evm.execution import apply_transaction        # Phase 3
# from src.ethereum.evm.block import Block                        # Phase 2

CHAIN_ID = 1
GAS_PRICE = 10**9   # 1 gwei
GAS_LIMIT = 21_000  # exact intrinsic cost for value transfer

# -- 1. Genesis state --
sender_pk, sender_pub = generate_key_pair()
sender_addr = private_key_to_address(sender_pk)

recipient_pk, _ = generate_key_pair()
recipient_addr = private_key_to_address(recipient_pk)

world_state = {
    sender_addr:    {'balance': 10**18, 'nonce': 0, 'code': b'', 'storage': {}},
    recipient_addr: {'balance': 0,      'nonce': 0, 'code': b'', 'storage': {}},
}
# BREAKPOINT: world_state, sender_addr, recipient_addr

# -- 2. Create and sign transaction --
tx = sign_transaction({
    'nonce': 0,
    'gas_price': GAS_PRICE,
    'gas_limit': GAS_LIMIT,
    'to': recipient_addr,
    'value': 10**17,   # 0.1 ETH
    'data': b'',
}, private_key=sender_pk, chain_id=CHAIN_ID)
# BREAKPOINT: tx['v'], tx['r'], tx['s'], tx hash

# -- 3+4. Validate and execute state transition --
new_world_state, receipt = apply_transaction(world_state, tx, block_context)
# BREAKPOINT: new_world_state[sender_addr]['balance'], receipt.gas_used

# -- 5. Mine block --
block = Block(transactions=[tx], parent_hash=b'\x00'*32, state=new_world_state)
# BREAKPOINT: block.hash, block.number, block.transactions

# -- 6. Verify --
assert new_world_state[sender_addr]['balance'] < 10**18    # deducted
assert new_world_state[recipient_addr]['balance'] == 10**17
print("Scenario 01 complete: ETH transferred successfully")
print(f"  Sender balance:    {new_world_state[sender_addr]['balance']}")
print(f"  Recipient balance: {new_world_state[recipient_addr]['balance']}")
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Deploy Solidity via compiler | Hardcoded bytecode constants | v1 project decision | Eliminates toolchain dependency |
| Full ERC-20 (approve/transferFrom) | Minimal transfer + balanceOf only | v1 project decision | Reduces bytecode complexity |
| Real PoW mining | Simplified block creation (no PoW) | v1 project decision | Scenario scripts don't wait for mining |
| Init code + runtime code pattern | Simplified: store data directly as runtime | Phase 3 CONTEXT decision (Claude's discretion) | Bytecode is simpler but must be consistent |
| EIP-1559 (Type 2) transactions | Legacy (Type 0) EIP-155 transactions | v1 project decision | Simpler signing, fewer transaction fields |

**Deprecated/outdated:**
- Pre-EIP-155 signing (`v = {0,1} + 27`): Do not use. All signing must use EIP-155 with `chain_id = 1`.
- py-evm as reference: Archived Sep 2025 — can be read for inspiration but not installed or depended on.

---

## Open Questions

1. **Did Phase 3 implement SHA3 opcode (0x20)?**
   - What we know: Phase 3 CONTEXT.md says opcodes are "contract-driven" — only include what Counter and SimpleToken need.
   - What's unclear: The planning research noted SHA3 is needed for Solidity-style storage mappings in token contracts.
   - Recommendation: If SHA3 is absent, use a simplified token storage layout where `storage[int.from_bytes(addr, 'big')]` holds the balance. Mark with `# SIMPLIFIED:`. This avoids any slot collision for realistic 20-byte addresses since they are very sparse in a 256-bit space.

2. **Did Phase 3 implement CREATE with init-code execution or direct storage?**
   - What we know: Phase 3 CONTEXT.md says "Contract deployment (CREATE) is included in Phase 3" but the exact implementation was left to Claude's discretion.
   - What's unclear: Whether to author bytecode with an init code preamble (CODECOPY + RETURN) or supply raw runtime code.
   - Recommendation: Check Phase 3 implementation before authoring bytecode. If Phase 3 stores `msg.data` directly (simplified approach), supply only runtime code. If Phase 3 executes init code, supply full creation bytecode with CODECOPY/RETURN header.

3. **Are CALLDATALOAD/CALLDATASIZE/SHR opcodes implemented in Phase 3?**
   - What we know: CALLDATALOAD (0x35), CALLDATASIZE (0x36), SHR (0x1c) are needed for function dispatch.
   - What's unclear: The ~25 opcode target may or may not include all three.
   - Recommendation: If SHR is absent, use a bitmask (AND + shift with MUL/DIV) as fallback for selector extraction. This is more opcodes but avoids needing SHR.

4. **What does `apply_transaction` return for contract creation — does it expose the new contract address?**
   - What we know: Phase 3 implements state transition but the exact return structure is Claude's discretion.
   - What's unclear: Whether `receipt.contract_address` is exposed, or whether the scenario script must compute the address independently.
   - Recommendation: Scenario scripts should compute the address using `compute_contract_address(sender, nonce)` independently rather than relying on the receipt, since this is more educational (shows how address derivation works).

---

## Sources

### Primary (HIGH confidence)
- EIP-155 specification (eips.ethereum.org/EIPS/eip-155) — EIP-155 signing, v computation formula, 9-field RLP structure
- RareSkills — Ethereum address derivation (rareskills.io/post/ethereum-address-derivation) — CREATE address formula, nonce=0 edge case, RLP prefix breakdown
- EtherVM opcode reference (ethervm.io) — opcode hex values: CALLDATALOAD 0x35, CALLDATASIZE 0x36, SLOAD 0x54, SSTORE 0x55, RETURN 0xf3, CREATE 0xf0, CALL 0xf1
- Project REQUIREMENTS.md — Solidity compiler out-of-scope, only transfer+balanceOf needed for token, no networking

### Secondary (MEDIUM confidence)
- RareSkills — Contract creation code (rareskills.io/post/ethereum-contract-creation-code) — init code vs runtime code structure, CODECOPY pattern, payable vs non-payable constructor shift
- Ethereumbook Chapter 13 (cypherpunks-core.github.io/ethereumbook/13evm.html) — execution context fields, gas intrinsic cost baseline (21000 gas)
- LearnEVM / Andrey Obruchkov (Medium) — calldata dispatch pattern using CALLDATALOAD + SHR + EQ + JUMPI

### Tertiary (LOW confidence — needs validation against Phase 3 implementation)
- SHA3 opcode availability: assumed based on Solidity mapping convention; needs Phase 3 confirmation
- CREATE handler behavior (init code vs direct): left to Phase 3 Claude's discretion; needs Phase 3 confirmation before bytecode is authored

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new dependencies needed; all required libraries were installed in Phase 1
- Architecture: HIGH — EVM/ABI specs are stable, precise, and verified against multiple authoritative sources
- Contract bytecode patterns: MEDIUM — structure is correct but exact opcode sequences depend on Phase 3 opcode support; 2 open questions need Phase 3 confirmation
- Pitfalls: HIGH — all pitfalls are grounded in specific, verifiable EVM/ABI rules

**Research date:** 2026-02-19
**Valid until:** 2026-05-19 (90 days — EVM spec is stable; only Phase 3 implementation details may shift)
