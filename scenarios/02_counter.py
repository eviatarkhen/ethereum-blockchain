#!/usr/bin/env python3
"""Counter Contract Scenario — Deploy, Increment, Read.

This script demonstrates the complete lifecycle of a smart contract interaction:

  1. Create genesis world state with a funded deployer account
  2. Deploy the Counter contract (CREATE transaction: to=b"", data=init_bytecode)
  3. Compute the contract address: keccak256(RLP([sender, nonce]))[12:]
  4. Call increment() — send transaction to contract with ABI-encoded calldata
  5. Call getCount() — send read transaction, decode 32-byte return value
  6. Verify count == 1 and print summary

Run from project root:
    PYTHONPATH=src python scenarios/02_counter.py

Set a breakpoint at any "# BREAKPOINT:" comment to inspect EVM state
(stack, memory, storage, pc, gas) in your debugger.

The Counter contract bytecode lives in src/ethereum/contracts/counter.py.
It implements two functions:
  - increment(): SLOAD slot 0 -> ADD 1 -> SSTORE slot 0
  - getCount(): SLOAD slot 0 -> MSTORE mem[0] -> RETURN mem[0:32]

Function dispatch uses DIV-based selector extraction (PUSH32(2^224)/DIV)
because SHR (0x1c) is not available in this EVM implementation.
"""

import time

from ethereum.crypto.keys import generate_key_pair, private_key_to_address
from ethereum.state.world_state import create_genesis_state
from ethereum.transactions.transaction import Transaction, sign_transaction
from ethereum.core.state_transition import apply_transaction
from ethereum.chain.block import create_genesis_block, create_block, block_hash
from ethereum.contracts.counter import (
    COUNTER_RUNTIME_BYTECODE,
    encode_increment,
    encode_get_count,
)
from ethereum.contracts.address import compute_contract_address


# =============================================================================
# Constants
# =============================================================================

GAS_PRICE         = 1          # 1 wei per gas unit (round number for clarity)
GAS_LIMIT_DEPLOY  = 100_000    # Gas for contract deployment (CREATE)
GAS_LIMIT_CALL    = 100_000    # Gas for contract function calls
BLOCK_GAS_LIMIT   = 1_000_000  # Block gas limit for validation

ONE_ETH = 10 ** 18             # 1 ETH in wei (funding for deployer)


# =============================================================================
# Inline init code builder
# =============================================================================
# A CREATE transaction's `data` field is "init code" — the bytecode that runs
# once to set up the contract and returns the runtime code to store.
#
# SIMPLIFIED: Our init code is minimal: it pushes the runtime code length and
# offset, then uses CODECOPY to copy runtime code into memory, then RETURN.
# Real Solidity constructors execute logic before returning runtime code.
#
# Init code pattern (standard minimal deployer):
#   PUSH1 <len>     — length of runtime code
#   PUSH1 <offset>  — offset in init code where runtime code starts
#   PUSH1 0x00      — memory destination offset
#   CODECOPY        — copy runtime code to memory[0..<len>]
#   PUSH1 <len>     — length again (for RETURN)
#   PUSH1 0x00      — memory offset
#   RETURN          — return memory[0..<len>] as runtime code

def build_init_code(runtime_bytecode: bytes) -> bytes:
    """Build minimal init code that deploys the given runtime bytecode.

    The init code is the transaction data for a CREATE transaction. When
    executed by the EVM, it copies the runtime code into memory and returns
    it — that returned data becomes the contract's stored bytecode.

    Args:
        runtime_bytecode: The contract's runtime bytecode to deploy.

    Returns:
        Init code bytes. The total length is 12 + len(runtime_bytecode).
    """
    runtime_len = len(runtime_bytecode)
    # Offset where runtime code starts in init code (after the 12-byte header)
    runtime_offset = 12

    init_code = bytes([
        # --- Copy runtime code from init code into memory ---
        0x60, runtime_len,     # PUSH1 <runtime_len>   — byte count to copy
        0x60, runtime_offset,  # PUSH1 <runtime_offset> — source offset in code
        0x60, 0x00,            # PUSH1 0x00            — destination in memory
        0x39,                  # CODECOPY              — mem[0..len] = code[offset..offset+len]
        # --- Return runtime code from memory ---
        0x60, runtime_len,     # PUSH1 <runtime_len>   — byte count to return
        0x60, 0x00,            # PUSH1 0x00            — memory offset
        0xF3,                  # RETURN                — return memory[0..len]
    ]) + runtime_bytecode

    return init_code


def main():
    print("=" * 60)
    print("Counter Contract Scenario")
    print("=" * 60)

    # =========================================================================
    # Step 1: Generate deployer key pair and create genesis state
    # =========================================================================
    print("\n[1] Creating genesis world state...")

    deployer_priv, deployer_pub = generate_key_pair()
    deployer_addr = private_key_to_address(deployer_priv)

    world_state = create_genesis_state({
        deployer_addr: ONE_ETH,  # Fund deployer with 1 ETH for gas
    })

    print(f"    Deployer: 0x{deployer_addr.hex()}")
    print(f"    Balance:  {world_state.get_balance(deployer_addr)} wei")

    # Create genesis block (block #0)
    genesis_block = create_genesis_block(
        state_root=world_state.state_root_placeholder(),
        timestamp=0,
    )

    # BREAKPOINT: world_state, deployer_addr visible.
    # Inspect: world_state._accounts[deployer_addr] — balance = 10^18, nonce = 0.
    # deployer_addr is derived from public key: last 20 bytes of keccak256(pubkey).

    # =========================================================================
    # Step 2: Deploy the Counter contract
    # =========================================================================
    print("\n[2] Deploying Counter contract...")

    # Build init code that wraps COUNTER_RUNTIME_BYTECODE
    init_code = build_init_code(COUNTER_RUNTIME_BYTECODE)

    print(f"    Runtime bytecode: {len(COUNTER_RUNTIME_BYTECODE)} bytes")
    print(f"    Init code:        {len(init_code)} bytes")
    print(f"    Runtime hex:      0x{COUNTER_RUNTIME_BYTECODE[:8].hex()}...")

    # CREATE transaction: to=b"" signals contract creation
    deploy_tx = Transaction(
        nonce=0,               # Deployer's first transaction
        gas_price=GAS_PRICE,
        gas=GAS_LIMIT_DEPLOY,  # 100,000 gas for deployment
        to=b"",                # Empty `to` triggers contract creation
        value=0,               # No ETH sent to new contract
        data=init_code,        # Init code that deploys COUNTER_RUNTIME_BYTECODE
    )
    signed_deploy_tx = sign_transaction(deploy_tx, deployer_priv)

    # BREAKPOINT: signed_deploy_tx fields, init_code content visible.
    # Inspect: signed_deploy_tx.data — this is the init code (not runtime code).
    # Inspect: signed_deploy_tx.to == b"" — empty bytes triggers CREATE path.
    # COUNTER_RUNTIME_BYTECODE contains the DIV-based function dispatcher.

    # Apply state transition — runs init code, stores returned runtime code
    deploy_result = apply_transaction(signed_deploy_tx, world_state, BLOCK_GAS_LIMIT)

    if not deploy_result.success:
        raise RuntimeError(f"Deployment failed: {deploy_result.error}")

    # Compute the contract address (deterministic from deployer + nonce=0)
    # Note: nonce used is the tx nonce (0), not the account nonce after increment.
    contract_addr = compute_contract_address(deployer_addr, nonce=0)

    contract_code = world_state.get_account(contract_addr).code
    print(f"    Contract address: 0x{contract_addr.hex()}")
    print(f"    Gas used:         {deploy_result.gas_used}")
    print(f"    Stored code:      {len(contract_code)} bytes")

    # BREAKPOINT: contract_address, world_state[contract_addr].code visible.
    # Inspect: world_state._accounts[contract_addr].code — should equal COUNTER_RUNTIME_BYTECODE.
    # Inspect: world_state._accounts[contract_addr].storage — empty dict (not incremented yet).
    # contract_addr == keccak256(RLP([deployer_addr, b'']))[12:] (nonce=0 encodes as empty bytes).

    assert contract_code == COUNTER_RUNTIME_BYTECODE, (
        f"Deployed code mismatch: expected {len(COUNTER_RUNTIME_BYTECODE)} bytes, "
        f"got {len(contract_code)} bytes"
    )

    # =========================================================================
    # Step 3: Call increment()
    # =========================================================================
    print("\n[3] Calling increment()...")

    # Calldata for increment(): just the 4-byte selector (no arguments)
    increment_calldata = encode_increment()
    print(f"    Calldata: 0x{increment_calldata.hex()}  (increment() selector)")

    increment_tx = Transaction(
        nonce=1,               # Deployer's second transaction (nonce incremented after deploy)
        gas_price=GAS_PRICE,
        gas=GAS_LIMIT_CALL,
        to=contract_addr,      # Send to the deployed contract
        value=0,               # No ETH with function call
        data=increment_calldata,
    )
    signed_increment_tx = sign_transaction(increment_tx, deployer_priv)

    increment_result = apply_transaction(signed_increment_tx, world_state, BLOCK_GAS_LIMIT)

    if not increment_result.success:
        raise RuntimeError(f"increment() call failed: {increment_result.error}")

    # Inspect storage after increment
    storage_slot_0 = world_state.get_storage(contract_addr, 0)
    print(f"    Success:        {increment_result.success}")
    print(f"    Gas used:       {increment_result.gas_used}")
    print(f"    Storage slot 0: {storage_slot_0}  (counter value)")

    # BREAKPOINT: world_state.get_storage(contract_addr, 0), gas used.
    # Inspect: world_state._accounts[contract_addr].storage — {0: 1}.
    # The EVM executed: SLOAD(slot=0) -> 0, ADD(0, 1) -> 1, SSTORE(slot=0, 1).
    # increment() has no RETURN opcode — it ends with STOP, so return_data = b"".

    # =========================================================================
    # Step 4: Call getCount() and read the result
    # =========================================================================
    print("\n[4] Calling getCount()...")

    # Calldata for getCount(): just the 4-byte selector
    get_count_calldata = encode_get_count()
    print(f"    Calldata: 0x{get_count_calldata.hex()}  (getCount() selector)")

    get_count_tx = Transaction(
        nonce=2,               # Deployer's third transaction
        gas_price=GAS_PRICE,
        gas=GAS_LIMIT_CALL,
        to=contract_addr,
        value=0,
        data=get_count_calldata,
    )
    signed_get_count_tx = sign_transaction(get_count_tx, deployer_priv)

    get_count_result = apply_transaction(signed_get_count_tx, world_state, BLOCK_GAS_LIMIT)

    if not get_count_result.success:
        raise RuntimeError(f"getCount() call failed: {get_count_result.error}")

    # Decode return value: 32-byte big-endian integer from return_data
    count = int.from_bytes(get_count_result.return_data[:32], "big")

    print(f"    Success:     {get_count_result.success}")
    print(f"    Gas used:    {get_count_result.gas_used}")
    print(f"    Return data: 0x{get_count_result.return_data.hex()}")
    print(f"    Count value: {count}")

    # BREAKPOINT: get_count_result.return_data, decoded count value.
    # Inspect: get_count_result.return_data — 32 bytes, big-endian encoding of count.
    # The EVM executed: SLOAD(slot=0) -> 1, MSTORE(offset=0, 1), RETURN(offset=0, size=32).
    # int.from_bytes(return_data[:32], 'big') decodes the 32-byte ABI uint256.

    # =========================================================================
    # Step 5: Package into block #1
    # =========================================================================
    print("\n[5] Mining block #1...")

    block1 = create_block(
        parent=genesis_block,
        transactions=[signed_deploy_tx, signed_increment_tx, signed_get_count_tx],
        state_root=world_state.state_root_placeholder(),
        timestamp=int(time.time()),
    )
    b1_hash = block_hash(block1)

    print(f"    Block number:  {block1.header.number}")
    print(f"    Transactions:  {len(block1.transactions)}")
    print(f"    Block hash:    0x{b1_hash.hex()[:16]}...")

    # =========================================================================
    # Step 6: Verify result
    # =========================================================================
    print("\n[6] Verifying counter value...")

    assert count == 1, f"Expected count=1 after one increment(), got {count}"

    # =========================================================================
    # Summary
    # =========================================================================
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"  Contract address: 0x{contract_addr.hex()}")
    print(f"  Bytecode size:    {len(COUNTER_RUNTIME_BYTECODE)} bytes")
    print(f"  Counter value:    {count}  (after 1 increment() call)")
    print(f"  Block:            #{block1.header.number} (0x{b1_hash.hex()[:16]}...)")
    print("\n  All assertions passed.")


if __name__ == "__main__":
    main()
