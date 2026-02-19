# Stack Research

**Domain:** Educational Ethereum blockchain implementation in Python
**Researched:** 2026-02-19
**Confidence:** MEDIUM-HIGH (core crypto libraries HIGH; MPT and EVM strategy MEDIUM)

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Python | 3.12.x | Implementation language | 3.12 is the current stable LTS-equivalent; 3.13 is newest but some eth ecosystem packages lag on compatibility. 3.12 hits the sweet spot of modern features (structural pattern matching, improved error messages) and broad library support. |
| pytest | 9.0.x | Test runner | De facto standard for Python testing. Fixtures, parametrize, and plain `assert` make blockchain scenario tests readable. No alternatives worth considering for this scale. |
| eth-hash | 0.7.1 | Keccak-256 hashing | The Ethereum Foundation's own keccak wrapper. Provides `from eth_hash.auto import keccak` — one line, correct algorithm (not SHA-3). Critical for address derivation, block hashes, state root computation. Released Jan 2025. |
| eth-keys | 0.7.0 | secp256k1 ECDSA | Ethereum Foundation library implementing secp256k1 private/public keys, ECDSA signatures with recovery (`{r, s, v}`), and address derivation. Uses coincurve (libsecp256k1 bindings) under the hood for C-speed. Correct Ethereum signature semantics out of the box. |
| rlp (pyrlp) | 4.1.0 | RLP encoding/decoding | The Ethereum Foundation's RLP library. Version 4.1.0 released Feb 2025. Python <4, >=3.8 compatible. Defines sedes (serializable types) that map cleanly onto Block, Transaction, and Header data classes. Required for block hashing and wire format compliance. |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| eth-utils | 5.3.1 | Ethereum-specific utilities | Address checksumming (EIP-55), hex encoding/decoding, unit conversions (wei/gwei/ether). Use everywhere you need to display or compare addresses. Aug 2025 release. |
| coincurve | 21.0.0 | libsecp256k1 Python bindings | Required transitively by eth-keys. Install explicitly to pin the version. Provides the underlying C-library performance for ECDSA operations. Mar 2025 release. |
| eth-account | 0.13.7 | Transaction signing utilities | Optional — only needed if you want high-level transaction signing helpers that handle EIP-155 (replay protection) automatically. For a pure educational build, eth-keys alone is sufficient; add eth-account if scenario scripts feel low-level. Apr 2025 release. |
| pytest-cov | latest | Coverage reporting | Shows which EVM opcode branches and state transition paths are tested. Use during later phases when opcode coverage matters. |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| Python stdlib `dataclasses` | Block, Transaction, Account data models | No external dependency. Use `@dataclass(frozen=True)` for immutable types (transactions, block headers) and regular `@dataclass` for mutable state (world state, EVM stack). Zero overhead for debugging — all fields visible in the debugger. |
| Python stdlib `struct` | Low-level byte packing | For EVM memory/stack word (256-bit) operations. Use `int.to_bytes()` and `int.from_bytes()` — cleaner than struct for 32-byte Ethereum words. |
| Python stdlib `logging` | Execution tracing | Configure per-module loggers so scenario scripts can toggle `DEBUG` for step-by-step EVM trace without modifying code. Ideal for educational use. |
| Python debugger (pdb/debugpy) | Breakpoint-driven exploration | The entire point of this project. No configuration needed — Python's built-in debugger works with all IDE debuggers (VS Code, PyCharm) via `debugpy`. |
| uv or pip + venv | Dependency management | `uv` is the modern fast alternative to pip; either works. Use a `requirements.txt` pinned to exact versions for reproducibility. |

## Installation

```bash
# Create virtual environment
python3.12 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# Core Ethereum crypto/encoding libraries
pip install eth-hash[pycryptodome]==0.7.1 eth-keys==0.7.0 rlp==4.1.0

# Supporting utilities
pip install eth-utils==5.3.1 coincurve==21.0.0

# Development / testing
pip install pytest==9.0.2 pytest-cov

# Optional: high-level signing helpers
# pip install eth-account==0.13.7
```

Note on `eth-hash[pycryptodome]`: eth-hash is a thin wrapper — it requires you to install a backend. `pycryptodome` is the recommended backend for keccak-256 and has no C compilation issues across platforms.

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| Python stdlib `dataclasses` | `attrs` | If you need slot-based classes for memory optimization at scale; unnecessary here |
| Python stdlib `dataclasses` | Pydantic | If you need JSON schema validation or API serialization; adds overhead and complexity for a debugger-focused educational codebase |
| `eth-keys` | Raw `coincurve` directly | If you need full libsecp256k1 API surface (Schnorr, ECDH); eth-keys is sufficient for Ethereum ECDSA and cleaner API |
| `rlp` (pyrlp) | `eth-rlp` | eth-rlp adds higher-level sedes on top of pyrlp; fine to use, but the base rlp library is simpler and more transparent for learning |
| Build MPT from scratch | `ethereum-merkle-patricia-trie` (PyPI) | If you don't want to implement trie internals; but that library is classified as inactive and requires LevelDB. Building from scratch better serves the educational goal. |
| Build MPT from scratch | `popzxc/merkle-patricia-trie` (GitHub) | Small pure-Python MPT library; acceptable if MPT implementation is out of scope, but lacks maintenance activity |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `py-evm` (ethereum/py-evm) | Archived by Ethereum Foundation on Sep 8, 2025. Read-only, no further updates. Was the main Python EVM — now explicitly replaced by execution-specs for production use. | Build EVM from scratch (the educational goal) using opcode references from ethereum.org and evm.codes |
| `web3.py` | This is an RPC client for connecting to running Ethereum nodes, not for implementing one. Wrong abstraction layer for this project. | Direct Python implementation using eth-keys, eth-hash, rlp |
| `pyethash` | Removed from py-evm explicitly in 2025. Proof-of-work specific; Ethereum moved to PoS. No relevance to this project. | Not needed — skip PoW entirely |
| `pycryptodome` (standalone) | Fine as eth-hash backend, but don't use it directly for keccak. Using it directly bypasses eth-hash's consistent interface. | `eth-hash[pycryptodome]` — same package, correct interface |
| `hashlib.sha3_256` | SHA3-256 (NIST standard) is NOT keccak-256. Ethereum uses the pre-standardization keccak variant. This is a critical subtle bug that breaks all hashes silently. | `eth_hash.auto.keccak` |
| `random` module | Cryptographically insecure. Using it for key generation produces predictable private keys. | `os.urandom()` or eth-keys key generation |
| LevelDB / RocksDB | Heavyweight storage backends. This is a single-node educational project — in-memory dicts are sufficient and debugger-friendly. | Python `dict` for world state |

## Stack Patterns by Variant

**For EVM opcode implementation:**
- Use a Python `dict` mapping opcode byte values to handler functions
- Each handler takes `(stack, memory, storage, pc)` and returns new pc
- Makes it trivially easy to set breakpoints on specific opcode execution

**For world state storage:**
- Use `dict[str, Account]` keyed by checksummed address
- Wrap in a `WorldState` class with `apply_transaction()` method
- Avoids database complexity while keeping state transitions explicit

**For block/transaction data structures:**
- Use `@dataclass(frozen=True)` — immutable after creation, serializable, all fields visible in debugger
- Implement `__bytes__()` on each for RLP encoding entry point

**For MPT (Merkle Patricia Trie):**
- Build from scratch using four node types: blank, leaf, extension, branch
- Use Python `dict` for the backing store (no LevelDB)
- Key insight: Yellow Paper Appendix D defines the spec precisely; this is ~200-300 lines of Python

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| eth-keys==0.7.0 | coincurve>=13.0.0,<22.0.0 | eth-keys pins coincurve as a dependency; installing coincurve==21.0.0 explicitly keeps it in range |
| eth-hash==0.7.1 | pycryptodome>=3.6.6 or pysha3>=1.0.2 | Use pycryptodome backend; pysha3 has C extension compilation issues on newer Python |
| rlp==4.1.0 | Python >=3.8, <4 | Tested against 3.8-3.13 |
| eth-utils==5.3.1 | eth-hash>=0.5.0 | eth-utils imports from eth-hash internally |
| Python 3.12 | All above packages | All Ethereum Foundation Python packages support 3.12. Use 3.12 not 3.13 to avoid any trailing compatibility gaps. |

## Sources

- PyPI: https://pypi.org/project/rlp/ — rlp 4.1.0, Feb 2025 (HIGH confidence, official)
- PyPI: https://pypi.org/project/eth-hash/ — eth-hash 0.7.1, Jan 2025 (HIGH confidence, official)
- PyPI: https://pypi.org/project/coincurve/ — coincurve 21.0.0, Mar 2025 (HIGH confidence, official)
- WebSearch: eth-keys 0.7.0, eth-utils 5.3.1 current as of Aug 2025 (MEDIUM confidence — PyPI page returned JS error, version from search result)
- WebSearch: eth-account 0.13.7, Apr 2025 (MEDIUM confidence)
- https://snakecharmers.ethereum.org/sunsetting-support-for-py-evm/ — py-evm archival rationale (HIGH confidence, official Ethereum Foundation post)
- WebSearch: pytest 9.0.2, Dec 2025 release (MEDIUM confidence — PyPI page not directly fetched)
- https://py-evm.readthedocs.io/_/downloads/en/latest/pdf/ — py-evm archived Sep 8, 2025, last fork Prague (HIGH confidence, official docs)
- https://ethereum.org/developers/docs/programming-languages/python/ — Ethereum Python ecosystem overview (HIGH confidence, official)
- https://devguide.python.org/versions/ — Python version status (HIGH confidence, official)

---
*Stack research for: Educational Ethereum blockchain implementation in Python*
*Researched: 2026-02-19*
