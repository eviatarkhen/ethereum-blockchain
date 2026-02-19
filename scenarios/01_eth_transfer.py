#!/usr/bin/env python3
"""ETH Transfer Scenario — Complete Transaction Lifecycle.

This script demonstrates the full lifecycle of an Ether transfer transaction:

  1. Create genesis world state with a funded sender and zero-balance recipient
  2. Create and sign a legacy (Type 0) transaction using ECDSA/secp256k1
  3. Validate and apply the state transition (Yellow Paper Section 6 order)
  4. Package the transaction into a block (block #1 linked to genesis block #0)
  5. Verify final balances: sender decreased, recipient received 0.1 ETH

Run from project root:
    PYTHONPATH=src python scenarios/01_eth_transfer.py

Set a breakpoint at any "# BREAKPOINT:" comment to inspect EVM state
(stack, memory, storage, pc, gas) in your debugger.

All values use round numbers for educational clarity.
"""

import time

from ethereum.crypto.keys import generate_key_pair, private_key_to_address
from ethereum.state.world_state import WorldState, create_genesis_state
from ethereum.state.account import Account
from ethereum.transactions.transaction import Transaction, sign_transaction
from ethereum.core.state_transition import apply_transaction
from ethereum.chain.block import (
    Block, Header, create_genesis_block, create_block, block_hash,
    GENESIS_PARENT_HASH,
)


# =============================================================================
# Constants
# =============================================================================

CHAIN_ID = 1          # Ethereum mainnet
GAS_PRICE = 1         # 1 wei per gas unit (round number for clarity)
GAS_LIMIT = 21_000    # Intrinsic gas cost for a simple ETH value transfer
BLOCK_GAS_LIMIT = 1_000_000  # Block gas limit for validation

ONE_ETH  = 10 ** 18   # 1 ETH in wei
TRANSFER_VALUE = ONE_ETH // 10  # 0.1 ETH in wei = 10^17 wei


def main():
    print("=" * 60)
    print("ETH Transfer Scenario")
    print("=" * 60)

    # =========================================================================
    # Step 1: Generate key pairs for sender and recipient
    # =========================================================================
    print("\n[1] Generating key pairs...")

    sender_private_key, sender_public_key = generate_key_pair()
    sender_addr = private_key_to_address(sender_private_key)

    recipient_private_key, recipient_public_key = generate_key_pair()
    recipient_addr = private_key_to_address(recipient_private_key)

    print(f"    Sender:    0x{sender_addr.hex()}")
    print(f"    Recipient: 0x{recipient_addr.hex()}")

    # =========================================================================
    # Step 2: Create genesis world state
    # =========================================================================
    print("\n[2] Creating genesis world state...")

    world_state = create_genesis_state({
        sender_addr:    ONE_ETH,  # Sender starts with 1 ETH (10^18 wei)
        recipient_addr: 0,        # Recipient starts with 0 wei
    })

    sender_initial_balance    = world_state.get_balance(sender_addr)
    recipient_initial_balance = world_state.get_balance(recipient_addr)

    print(f"    Sender balance:    {sender_initial_balance} wei ({sender_initial_balance / ONE_ETH} ETH)")
    print(f"    Recipient balance: {recipient_initial_balance} wei")

    # BREAKPOINT: world_state, sender_addr, recipient_addr visible.
    # Inspect: world_state._accounts to see all funded accounts.
    # Expected: sender has 10^18 wei, recipient has 0 wei, both nonce=0.

    # =========================================================================
    # Step 3: Create the genesis block (block #0 anchors the chain)
    # =========================================================================
    print("\n[3] Creating genesis block (block #0)...")

    genesis_state_root = world_state.state_root_placeholder()
    genesis_block = create_genesis_block(state_root=genesis_state_root, timestamp=0)
    genesis_hash = block_hash(genesis_block)

    print(f"    Genesis block hash: 0x{genesis_hash.hex()[:16]}...")
    print(f"    State root:         0x{genesis_state_root.hex()[:16]}...")

    # =========================================================================
    # Step 4: Build and sign the transaction
    # =========================================================================
    print("\n[4] Building and signing transaction...")

    # Unsigned transaction: send 0.1 ETH from sender to recipient
    unsigned_tx = Transaction(
        nonce=0,                  # Sender's first transaction
        gas_price=GAS_PRICE,      # 1 wei per gas
        gas=GAS_LIMIT,            # 21,000 gas limit for value transfer
        to=recipient_addr,        # Recipient's 20-byte address
        value=TRANSFER_VALUE,     # 0.1 ETH in wei
        data=b"",                 # No calldata for simple ETH transfer
    )

    # Sign with sender's private key (legacy format: v = recovery_id + 27)
    # Note: sign_transaction computes keccak256(RLP(unsigned_fields)) then ECDSA signs.
    signed_tx = sign_transaction(unsigned_tx, sender_private_key)

    print(f"    Nonce:     {signed_tx.nonce}")
    print(f"    Gas price: {signed_tx.gas_price} wei")
    print(f"    Gas limit: {signed_tx.gas}")
    print(f"    To:        0x{signed_tx.to.hex()}")
    print(f"    Value:     {signed_tx.value} wei ({signed_tx.value / ONE_ETH} ETH)")
    print(f"    v:         {signed_tx.v}  (recovery_id + 27)")
    print(f"    r:         0x{signed_tx.r:064x}")
    print(f"    s:         0x{signed_tx.s:064x}")

    # BREAKPOINT: signed_tx fields, v/r/s visible.
    # Inspect: signed_tx.v, signed_tx.r, signed_tx.s are the ECDSA signature.
    # signed_tx.v is 27 or 28 (recovery_id 0 or 1 + 27 for legacy format).
    # r and s are 256-bit integers encoding the signature point on secp256k1.

    # =========================================================================
    # Step 5: Apply state transition
    # =========================================================================
    print("\n[5] Applying state transition...")

    # The state transition function:
    #   1. Validates signature (recovers sender), nonce, balance, gas
    #   2. Deducts upfront gas cost from sender
    #   3. Increments sender nonce
    #   4. Executes: value transfer (no EVM for simple ETH send)
    #   5. Refunds unused gas to sender
    result = apply_transaction(signed_tx, world_state, BLOCK_GAS_LIMIT)

    if not result.success:
        raise RuntimeError(f"Transaction failed: {result.error}")

    sender_post_balance    = world_state.get_balance(sender_addr)
    recipient_post_balance = world_state.get_balance(recipient_addr)
    sender_nonce_after     = world_state.get_account(sender_addr).nonce

    gas_cost = result.gas_used * GAS_PRICE

    print(f"    Success:       {result.success}")
    print(f"    Gas used:      {result.gas_used}")
    print(f"    Gas cost:      {gas_cost} wei (gas_used * gas_price)")
    print(f"    Sender nonce:  {sender_nonce_after} (incremented from 0)")
    print(f"    Sender balance after:    {sender_post_balance} wei")
    print(f"    Recipient balance after: {recipient_post_balance} wei")

    # BREAKPOINT: updated balances, gas used.
    # Inspect: world_state._accounts[sender_addr] — balance decreased by value + gas cost.
    # Inspect: world_state._accounts[recipient_addr] — balance increased by transfer value.
    # result.gas_used should equal 21,000 (intrinsic gas for simple transfer).
    # result.gas_remaining should equal 0 (gas_limit - intrinsic = 21000 - 21000 = 0).

    # =========================================================================
    # Step 6: Package into block #1
    # =========================================================================
    print("\n[6] Mining block #1...")

    block1_state_root = world_state.state_root_placeholder()
    block1_timestamp  = int(time.time())

    block1 = create_block(
        parent=genesis_block,
        transactions=[signed_tx],
        state_root=block1_state_root,
        timestamp=block1_timestamp,
    )

    block1_hash = block_hash(block1)

    print(f"    Block number:     {block1.header.number}")
    print(f"    Parent hash:      0x{block1.header.parent_hash.hex()[:16]}...")
    print(f"    Block hash:       0x{block1_hash.hex()[:16]}...")
    print(f"    Transactions:     {len(block1.transactions)}")
    print(f"    State root:       0x{block1_state_root.hex()[:16]}...")
    print(f"    Timestamp:        {block1.header.timestamp}")

    # BREAKPOINT: block hash, block number, transactions.
    # Inspect: block1.header — parent_hash, number, timestamp, state_root.
    # Inspect: block1.transactions[0] — the signed transaction.
    # block1.header.parent_hash == genesis_hash (verify chain linkage).
    # block_hash(block1) changes if any header field changes (immutability).

    # =========================================================================
    # Step 7: Verify final balances
    # =========================================================================
    print("\n[7] Verifying final balances...")

    # Gas cost: 21,000 gas * 1 wei/gas = 21,000 wei
    expected_gas_cost          = GAS_LIMIT * GAS_PRICE
    expected_sender_balance    = ONE_ETH - TRANSFER_VALUE - expected_gas_cost
    expected_recipient_balance = TRANSFER_VALUE

    assert sender_post_balance == expected_sender_balance, (
        f"Sender balance mismatch: "
        f"expected {expected_sender_balance}, got {sender_post_balance}"
    )
    assert recipient_post_balance == expected_recipient_balance, (
        f"Recipient balance mismatch: "
        f"expected {expected_recipient_balance}, got {recipient_post_balance}"
    )
    assert sender_post_balance < sender_initial_balance, (
        "Sender balance should have decreased"
    )

    # =========================================================================
    # Summary
    # =========================================================================
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"  Transfer amount:   {TRANSFER_VALUE} wei ({TRANSFER_VALUE / ONE_ETH} ETH)")
    print(f"  Gas cost:          {expected_gas_cost} wei ({GAS_LIMIT} gas x {GAS_PRICE} wei/gas)")
    print(f"  Sender:    {sender_initial_balance} wei -> {sender_post_balance} wei")
    print(f"  Recipient: {recipient_initial_balance} wei -> {recipient_post_balance} wei")
    print(f"  Block:     #{block1.header.number} (0x{block1_hash.hex()[:16]}...)")
    print("\n  All assertions passed.")


if __name__ == "__main__":
    main()
