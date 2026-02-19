# Phase 1: Crypto and Encoding - Research

**Researched:** 2026-02-19
**Domain:** Ethereum cryptographic primitives and RLP encoding in Python
**Confidence:** HIGH

## Summary

Phase 1 implements the zero-dependency foundation layer: Keccak-256 hashing, ECDSA key pair generation and signing, Ethereum address derivation, and RLP encoding/decoding. All four components have mature, well-maintained official Ethereum Foundation Python libraries that should be used as backends rather than hand-rolling cryptographic code.

The critical pitfall in this domain is the Keccak-256 vs SHA-3 confusion: Python's `hashlib.sha3_256` implements the FIPS 202 standard which differs from the pre-standardization Keccak-256 used by Ethereum. Using the wrong hash function silently produces incorrect results everywhere. The `eth-hash` library with the `pycryptodome` backend eliminates this risk entirely.

**Primary recommendation:** Use eth-hash[pycryptodome] for Keccak-256, eth-keys with NativeECCBackend for ECDSA (pure Python, no C dependencies, ideal for educational stepping), and implement RLP from scratch for maximum learning value since the specification is simple and self-contained.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
(none explicitly locked)

### Claude's Discretion
- User indicated crypto is not a primary learning interest -- keep it minimal and functional
- RLP implementation approach (pyrlp vs from-scratch): Claude decides based on learning value vs time trade-off
- Code organization: Claude decides file structure for crypto utilities
- Verification approach: Claude picks appropriate test vectors
- Wrapper style around eth-hash and eth-keys: Claude decides level of abstraction
- All decisions should prioritize: minimal code, correct results, readable for debugger stepping

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| CRYPT-01 | Keccak-256 hashing using eth-hash (not hashlib.sha3_256) | eth-hash 0.7.1 with pycryptodome backend; auto-import via `from eth_hash.auto import keccak` |
| CRYPT-02 | ECDSA key pair generation and transaction signing | eth-keys with NativeECCBackend; `PrivateKey.sign_msg()` and `Signature.recover_public_key_from_msg()` |
| CRYPT-03 | RLP encoding/decoding for transactions and blocks | From-scratch implementation following Yellow Paper Appendix B; pyrlp 4.1.0 available as reference/fallback |
| CRYPT-04 | Ethereum address derivation from public key | eth-keys `PublicKey.to_canonical_address()` returns 20-byte address; Keccak-256 of uncompressed public key, take last 20 bytes |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| eth-hash | 0.7.1 | Keccak-256 hashing | Official Ethereum Foundation library; eliminates Keccak vs SHA-3 confusion |
| pycryptodome | (dependency) | eth-hash backend | Recommended backend; supports pypy3; more portable than pysha3 |
| eth-keys | 0.6.x | ECDSA key ops, signing, address derivation | Official Ethereum Foundation library; pure Python NativeECCBackend available |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pyrlp (rlp) | 4.1.0 | RLP encoding/decoding | Reference implementation; use if from-scratch RLP proves too time-consuming |
| eth-utils | 5.x | Utility functions (keccak shortcut, address formatting) | Optional convenience; eth-hash + eth-keys cover all Phase 1 needs directly |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| eth-hash[pycryptodome] | eth-hash[pysha3] | pysha3 requires C compilation; pycryptodome is pure Python wheel |
| eth-keys NativeECCBackend | eth-keys CoinCurveECCBackend | CoinCurve is faster but requires C library; NativeECCBackend is better for educational stepping |
| From-scratch RLP | pyrlp 4.1.0 | pyrlp handles edge cases automatically but hides the encoding logic; from-scratch teaches RLP deeply |

**Installation:**
```bash
pip install "eth-hash[pycryptodome]" eth-keys
```

## Architecture Patterns

### Recommended Project Structure
```
src/
  ethereum/
    crypto/
      __init__.py          # Re-exports: keccak256, sign, verify, derive_address
      hashing.py           # Keccak-256 wrapper around eth-hash
      keys.py              # ECDSA key generation, signing, recovery, address derivation
    encoding/
      __init__.py          # Re-exports: rlp_encode, rlp_decode
      rlp.py               # RLP encode/decode implementation
tests/
  test_hashing.py          # Keccak-256 test vectors
  test_keys.py             # ECDSA signing, recovery, address derivation tests
  test_rlp.py              # RLP round-trip and edge case tests
```

### Pattern 1: Thin Wrapper Over eth-hash
**What:** Expose a single `keccak256(data: bytes) -> bytes` function that wraps eth-hash
**When to use:** All hashing operations throughout the project
**Example:**
```python
# Source: https://eth-hash.readthedocs.io/en/latest/quickstart.html
from eth_hash.auto import keccak

def keccak256(data: bytes) -> bytes:
    """Keccak-256 hash. NOT the same as hashlib.sha3_256 (FIPS 202)."""
    # SIMPLIFIED: We always hash in one call; eth-hash also supports incremental hashing
    return keccak(data)
```

### Pattern 2: Key Operations Wrapper
**What:** Wrap eth-keys PrivateKey/PublicKey into project-specific functions
**When to use:** Key generation, signing, verification, address derivation
**Example:**
```python
# Source: https://github.com/ethereum/eth-keys README
from eth_keys import keys
import os

def generate_key_pair():
    """Generate a new ECDSA key pair on the secp256k1 curve."""
    private_key = keys.PrivateKey(os.urandom(32))
    return private_key, private_key.public_key

def sign_message(private_key, message: bytes):
    """Sign a message, returning signature with recovery id (v, r, s)."""
    return private_key.sign_msg(message)

def recover_address(message: bytes, signature) -> bytes:
    """Recover the signer's Ethereum address from a message and signature."""
    public_key = signature.recover_public_key_from_msg(message)
    return public_key.to_canonical_address()

def derive_address(public_key) -> bytes:
    """Derive 20-byte Ethereum address from public key.

    Address = last 20 bytes of Keccak-256(uncompressed_public_key_bytes)
    """
    return public_key.to_canonical_address()
```

### Pattern 3: From-Scratch RLP
**What:** Implement RLP encoding/decoding per Yellow Paper Appendix B
**When to use:** All serialization for transactions and blocks
**Example:**
```python
def rlp_encode(input_data) -> bytes:
    """RLP encode per Ethereum Yellow Paper Appendix B.

    Rules:
    - Single byte 0x00-0x7f: encode as itself
    - String 0-55 bytes: 0x80 + len, then string
    - String >55 bytes: 0xb7 + len_of_len, then len, then string
    - List 0-55 bytes total: 0xc0 + total_len, then concatenated items
    - List >55 bytes total: 0xf7 + len_of_len, then len, then items

    IMPORTANT: Integer 0 encodes as empty byte string (0x80), not as 0x00
    """
    if isinstance(input_data, bytes):
        if len(input_data) == 1 and input_data[0] < 0x80:
            return input_data
        elif len(input_data) <= 55:
            return bytes([0x80 + len(input_data)]) + input_data
        else:
            len_bytes = _encode_length(len(input_data))
            return bytes([0xb7 + len(len_bytes)]) + len_bytes + input_data
    elif isinstance(input_data, list):
        payload = b''.join(rlp_encode(item) for item in input_data)
        if len(payload) <= 55:
            return bytes([0xc0 + len(payload)]) + payload
        else:
            len_bytes = _encode_length(len(payload))
            return bytes([0xf7 + len(len_bytes)]) + len_bytes + payload
```

### Anti-Patterns to Avoid
- **Using hashlib.sha3_256 for Keccak:** SHA-3 (FIPS 202) adds domain separation padding that Keccak-256 does not. Results differ silently.
- **Storing private keys as strings:** Always bytes. String conversion introduces encoding bugs.
- **Encoding integer 0 as b'\x00':** Integer 0 must encode as empty byte string (0x80). This is the most common RLP bug.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Keccak-256 | Custom hash function | eth-hash[pycryptodome] | Keccak vs SHA-3 confusion; cryptographic correctness |
| ECDSA secp256k1 | Custom elliptic curve math | eth-keys NativeECCBackend | Constant-time operations, proper nonce generation, security-critical |
| Address derivation | Manual keccak + slice | eth-keys PublicKey.to_canonical_address() | Handles edge cases in public key format |

**Key insight:** Cryptographic primitives must never be hand-rolled. The libraries handle constant-time comparisons, proper randomness, and curve-specific edge cases. RLP encoding, however, is pure data serialization with a simple spec and IS worth implementing from scratch for educational value.

## Common Pitfalls

### Pitfall 1: Keccak-256 vs SHA-3 (FIPS 202)
**What goes wrong:** Using `hashlib.sha3_256()` produces different output than Ethereum's Keccak-256 for the same input. Every hash, address, and signature in the system becomes silently wrong.
**Why it happens:** NIST modified Keccak when standardizing it as SHA-3, adding domain separation padding. The internal permutation is the same but the output differs.
**How to avoid:** Always use eth-hash. Never import hashlib for Keccak operations.
**Warning signs:** Address derivation produces wrong addresses; test vectors fail.

### Pitfall 2: RLP Integer Zero Encoding
**What goes wrong:** Integer 0 is encoded as `b'\x00'` (0x00) instead of empty byte string `b''` (0x80).
**Why it happens:** Natural assumption that 0 should encode as a zero byte. But RLP encodes integers as big-endian with no leading zeros, and zero has no digits.
**How to avoid:** Convert integers to bytes with `int.to_bytes()` using minimal length; `0.to_bytes(0, 'big')` returns `b''`. Special-case zero explicitly.
**Warning signs:** Transaction nonce=0 or value=0 produces different encoded output than expected.

### Pitfall 3: Public Key Format for Address Derivation
**What goes wrong:** Using the compressed (33-byte) public key instead of uncompressed (64-byte, without 0x04 prefix) when computing the address.
**Why it happens:** ECDSA public keys have multiple representations. Ethereum uses the uncompressed form minus the 0x04 prefix byte.
**How to avoid:** eth-keys handles this internally. If doing manually: `keccak256(uncompressed_pubkey_64_bytes)[-20:]`.
**Warning signs:** Derived address doesn't match known test vectors.

### Pitfall 4: eth-keys sign_msg vs sign_msg_hash
**What goes wrong:** Using `sign_msg_hash()` when you should use `sign_msg()` or vice versa.
**Why it happens:** `sign_msg(message)` internally hashes the message first; `sign_msg_hash(hash)` expects a pre-hashed 32-byte value.
**How to avoid:** For simplicity, use `sign_msg()` which handles hashing. Use `sign_msg_hash()` only when you've already computed the hash (e.g., for transaction signing where you hash the RLP-encoded transaction).
**Warning signs:** Signature verification fails; recovered address is wrong.

## Code Examples

### Keccak-256 Canonical Test Vector
```python
# Source: https://eth-hash.readthedocs.io/en/latest/quickstart.html
from eth_hash.auto import keccak

result = keccak(b'')
assert result.hex() == 'c5d2460186f7233c927e7db2dcc703c0e500b653ca82273b7bfad8045d85a470'
```

### ECDSA Key Generation, Signing, Recovery
```python
# Source: https://github.com/ethereum/eth-keys
from eth_keys import keys
import os

# Generate key pair
private_key = keys.PrivateKey(os.urandom(32))
public_key = private_key.public_key

# Sign a message
message = b'test message'
signature = private_key.sign_msg(message)

# Verify signature
assert signature.verify_msg(message, public_key)

# Recover public key from signature
recovered = signature.recover_public_key_from_msg(message)
assert recovered == public_key
```

### Address Derivation
```python
# Source: https://github.com/ethereum/eth-keys
from eth_keys import keys

private_key = keys.PrivateKey(b'\x01' * 32)
public_key = private_key.public_key

# 20-byte canonical address
address_bytes = public_key.to_canonical_address()  # bytes, length 20

# Checksum address string (ERC-55)
address_str = public_key.to_checksum_address()  # '0x...' format
```

### RLP Edge Cases
```python
# Source: https://ethereum.org/developers/docs/data-structures-and-encoding/rlp/

# Single byte (0x00-0x7f): encodes as itself
assert rlp_encode(b'\x42') == b'\x42'

# Empty string: encodes as 0x80
assert rlp_encode(b'') == b'\x80'

# Integer 0 -> empty byte string -> 0x80
assert rlp_encode(int_to_bytes(0)) == b'\x80'

# "ethereum" -> 0x88 + b'ethereum' (0x80 + 8 = 0x88)
assert rlp_encode(b'ethereum') == b'\x88ethereum'

# Empty list: 0xc0
assert rlp_encode([]) == b'\xc0'

# Nested list [[]]
assert rlp_encode([[]]) == b'\xc1\xc0'
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| hashlib.sha3_256 | eth-hash[pycryptodome] | Since Ethereum inception | SHA-3 != Keccak-256; always use eth-hash |
| pysha3 backend | pycryptodome backend | ~2023 | pycryptodome is more portable, no C compilation needed |
| eth-keys CoinCurve default | NativeECCBackend available | Available since early versions | Pure Python option ideal for educational use |

**Deprecated/outdated:**
- ethereum-keys: Renamed to eth-keys, no longer maintained under old name
- hashlib.sha3_256 for Ethereum: Was never correct for Ethereum, but this misconception persists

## Open Questions

1. **eth-keys exact latest version**
   - What we know: 0.6.x line, Python 3.8-3.13 support, released April 2025
   - What's unclear: Exact minor version (PyPI page returned JS error during research)
   - Recommendation: Pin to `eth-keys>=0.6.0` and verify on install; NativeECCBackend API is stable

## Sources

### Primary (HIGH confidence)
- [eth-hash PyPI](https://pypi.org/project/eth-hash/) - version 0.7.1, installation, backends
- [eth-hash quickstart](https://eth-hash.readthedocs.io/en/latest/quickstart.html) - API usage patterns
- [eth-keys GitHub](https://github.com/ethereum/eth-keys) - API documentation, signing, recovery, address derivation
- [pyrlp tutorial](https://pyrlp.readthedocs.io/en/latest/tutorial.html) - RLP encoding/decoding patterns
- [rlp PyPI](https://pypi.org/project/rlp/) - version 4.1.0, Python requirements
- [Ethereum RLP specification](https://ethereum.org/developers/docs/data-structures-and-encoding/rlp/) - canonical encoding rules, edge cases

### Secondary (MEDIUM confidence)
- [eth-keys PyPI](https://pypi.org/project/eth-keys/) - version info (page had rendering issues)

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - all libraries are official Ethereum Foundation, verified on PyPI and official docs
- Architecture: HIGH - simple wrapper pattern over well-documented APIs
- Pitfalls: HIGH - Keccak vs SHA-3 is extensively documented; RLP zero encoding is in the Yellow Paper spec

**Research date:** 2026-02-19
**Valid until:** 2026-03-19 (stable domain, libraries change infrequently)
