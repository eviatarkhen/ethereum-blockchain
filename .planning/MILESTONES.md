# Milestones

## v1.0 EduEthereum MVP (Shipped: 2026-02-19)

**Phases completed:** 4 phases, 10 plans
**Lines of code:** 8,037 Python across 49 files
**Git commits:** 12 feat commits

**Key accomplishments:**
1. Keccak-256 hashing and ECDSA key operations with correct keccak (not SHA-3) via eth-hash
2. From-scratch RLP encode/decode per Yellow Paper Appendix B including integer zero edge case
3. Account model, world state, transaction signing/recovery, block structure, and blockchain chain validation
4. EVM stack machine with ~25 opcodes, gas metering, CREATE/CALL for contract deployment and calls
5. Hand-crafted Counter (88 bytes) and SimpleToken (112 bytes) bytecode with DIV-based function dispatch
6. Three end-to-end scenario scripts (ETH transfer, counter, token) with 19 BREAKPOINT annotations for debugger step-through

**Delivered:** A developer can set breakpoints and trace the complete lifecycle of a transaction — from key generation through signing, EVM execution, contract interaction, to block inclusion.

---

