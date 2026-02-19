#!/usr/bin/env python3
"""SimpleToken Contract Scenario — Deploy, Transfer, Check Balances.

This script demonstrates the complete lifecycle of an ERC-20-like token contract:

  1. Create genesis world state with a funded deployer and a recipient account
  2. Deploy the SimpleToken contract (CREATE transaction)
  3. Manually set deployer's initial token balance in contract storage
     (since our simplified CREATE stores runtime code directly, not init code)
  4. Call balanceOf(deployer) — verify deployer has INITIAL_SUPPLY tokens
  5. Call transfer(recipient, 1000) — transfer 1000 tokens
  6. Call balanceOf(deployer) and balanceOf(recipient) — verify updated balances
  7. Print summary with both final balances

Run from project root:
    PYTHONPATH=src python scenarios/03_token.py

Set a breakpoint at any "# BREAKPOINT:" comment to inspect EVM state
(stack, memory, storage, pc, gas) in your debugger.

The SimpleToken contract bytecode lives in src/ethereum/contracts/token.py.
It implements two functions:
  - transfer(address,uint256): deducts from msg.sender, adds to recipient
  - balanceOf(address): reads storage[int(address)] and returns it

Storage layout (SIMPLIFIED):
  Balance of address X is stored at storage[int.from_bytes(X, 'big')].
  Real Solidity uses keccak256(abi.encode(slot, address)) for mapping keys,
  but that requires SHA3 opcode — our simplified storage avoids this.
"""

import time

from ethereum.crypto.keys import generate_key_pair, private_key_to_address
from ethereum.state.world_state import create_genesis_state
from ethereum.transactions.transaction import Transaction, sign_transaction
from ethereum.core.state_transition import apply_transaction
from ethereum.chain.block import create_genesis_block, create_block, block_hash
from ethereum.contracts.token import (
    TOKEN_RUNTIME_BYTECODE,
    INITIAL_SUPPLY,
    encode_transfer,
    encode_balance_of,
)
from ethereum.contracts.address import compute_contract_address


# =============================================================================
# Constants
# =============================================================================

GAS_PRICE         = 1          # 1 wei per gas unit (round number for clarity)
GAS_LIMIT_DEPLOY  = 100_000    # Gas for contract deployment (CREATE)
GAS_LIMIT_CALL    = 100_000    # Gas for contract function calls
BLOCK_GAS_LIMIT   = 1_000_000  # Block gas limit for validation

ONE_ETH = 10 ** 18             # 1 ETH in wei (funding for gas costs)
TRANSFER_AMOUNT = 1_000        # Token units to transfer in the scenario


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
    runtime_offset = 12  # Offset where runtime code starts (after 12-byte header)

    init_code = bytes([
        0x60, runtime_len,     # PUSH1 <runtime_len>    — byte count to copy
        0x60, runtime_offset,  # PUSH1 <runtime_offset> — source offset in code
        0x60, 0x00,            # PUSH1 0x00             — destination in memory
        0x39,                  # CODECOPY               — mem[0..len] = code[offset..offset+len]
        0x60, runtime_len,     # PUSH1 <runtime_len>    — byte count to return
        0x60, 0x00,            # PUSH1 0x00             — memory offset
        0xF3,                  # RETURN                 — return memory[0..len]
    ]) + runtime_bytecode

    return init_code


def decode_uint256(data: bytes) -> int:
    """Decode a 32-byte ABI-encoded uint256 from return data.

    Args:
        data: At least 32 bytes of return data.

    Returns:
        Decoded uint256 as Python int.
    """
    return int.from_bytes(data[:32], "big")


def main():
    print("=" * 60)
    print("SimpleToken Contract Scenario")
    print("=" * 60)
    print(f"  INITIAL_SUPPLY: {INITIAL_SUPPLY:,} tokens")
    print(f"  Transfer amount: {TRANSFER_AMOUNT:,} tokens")

    # =========================================================================
    # Step 1: Generate key pairs and create genesis state
    # =========================================================================
    print("\n[1] Creating genesis world state...")

    deployer_priv, _ = generate_key_pair()
    deployer_addr = private_key_to_address(deployer_priv)

    recipient_priv, _ = generate_key_pair()
    recipient_addr = private_key_to_address(recipient_priv)

    world_state = create_genesis_state({
        deployer_addr:  ONE_ETH,  # Fund deployer with 1 ETH for gas
        recipient_addr: 0,        # Recipient starts with 0 ETH
    })

    print(f"    Deployer:  0x{deployer_addr.hex()}")
    print(f"    Recipient: 0x{recipient_addr.hex()}")
    print(f"    Deployer ETH balance: {world_state.get_balance(deployer_addr)} wei")

    # Create genesis block (block #0)
    genesis_block = create_genesis_block(
        state_root=world_state.state_root_placeholder(),
        timestamp=0,
    )

    # BREAKPOINT: world_state, deployer_addr, recipient_addr visible.
    # Inspect: world_state._accounts — deployer funded with 1 ETH, recipient has 0.
    # Neither account has any token balance yet (token contract not deployed).

    # =========================================================================
    # Step 2: Deploy the SimpleToken contract
    # =========================================================================
    print("\n[2] Deploying SimpleToken contract...")

    init_code = build_init_code(TOKEN_RUNTIME_BYTECODE)

    print(f"    Runtime bytecode: {len(TOKEN_RUNTIME_BYTECODE)} bytes")
    print(f"    Init code:        {len(init_code)} bytes")

    # CREATE transaction: to=b"" triggers contract creation
    deploy_tx = Transaction(
        nonce=0,               # Deployer's first transaction
        gas_price=GAS_PRICE,
        gas=GAS_LIMIT_DEPLOY,
        to=b"",                # Empty `to` = CREATE new contract
        value=0,               # No ETH value to token contract
        data=init_code,        # Init code wrapping TOKEN_RUNTIME_BYTECODE
    )
    signed_deploy_tx = sign_transaction(deploy_tx, deployer_priv)

    # BREAKPOINT: signed_deploy_tx fields, init_code content visible.
    # Inspect: signed_deploy_tx.to == b"" — this is what triggers the CREATE path.
    # Inspect: signed_deploy_tx.data — the full init code including runtime bytecode.
    # Token runtime code: transfer() and balanceOf() with DIV-based dispatch.

    deploy_result = apply_transaction(signed_deploy_tx, world_state, BLOCK_GAS_LIMIT)

    if not deploy_result.success:
        raise RuntimeError(f"Deployment failed: {deploy_result.error}")

    # Compute contract address: keccak256(RLP([deployer, nonce=0]))[12:]
    contract_addr = compute_contract_address(deployer_addr, nonce=0)
    contract_code = world_state.get_account(contract_addr).code

    print(f"    Contract address: 0x{contract_addr.hex()}")
    print(f"    Gas used:         {deploy_result.gas_used}")
    print(f"    Stored code:      {len(contract_code)} bytes")

    assert contract_code == TOKEN_RUNTIME_BYTECODE, (
        f"Deployed code mismatch: expected {len(TOKEN_RUNTIME_BYTECODE)} bytes, "
        f"got {len(contract_code)} bytes"
    )

    # BREAKPOINT: contract_addr, world_state[contract_addr].code visible.
    # Inspect: world_state._accounts[contract_addr].code == TOKEN_RUNTIME_BYTECODE.
    # Inspect: world_state._accounts[contract_addr].storage — empty at this point.
    # The token contract has NO initial balances yet. We must set them manually.

    # =========================================================================
    # Step 3: Manually set deployer's initial token balance
    # =========================================================================
    print("\n[3] Setting initial token supply in contract storage...")
    print("    (SIMPLIFIED: real contracts set supply in constructor init code)")

    # SIMPLIFIED: Real contracts set initial supply in constructor (init code).
    # We set it manually since our simplified CREATE stores runtime code directly
    # without executing any constructor logic. The deployer's initial balance is
    # stored at storage[int.from_bytes(deployer_addr, 'big')], which matches the
    # simplified storage layout used by the token bytecode's balanceOf/transfer
    # handlers (they use CALLER/CALLDATALOAD uint256 as the storage key directly).
    deployer_storage_key = int.from_bytes(deployer_addr, "big")
    world_state.set_storage(contract_addr, deployer_storage_key, INITIAL_SUPPLY)

    deployer_initial_tokens = world_state.get_storage(contract_addr, deployer_storage_key)
    print(f"    Deployer token balance (storage): {deployer_initial_tokens:,}")

    # =========================================================================
    # Step 4: Call balanceOf(deployer) to verify initial supply
    # =========================================================================
    print("\n[4] Calling balanceOf(deployer)...")

    balance_of_deployer_calldata = encode_balance_of(deployer_addr)
    print(f"    Calldata: 0x{balance_of_deployer_calldata.hex()[:16]}...  (balanceOf selector + address)")

    balance_check_tx = Transaction(
        nonce=1,               # Deployer's second transaction
        gas_price=GAS_PRICE,
        gas=GAS_LIMIT_CALL,
        to=contract_addr,
        value=0,
        data=balance_of_deployer_calldata,
    )
    signed_balance_check_tx = sign_transaction(balance_check_tx, deployer_priv)

    balance_check_result = apply_transaction(signed_balance_check_tx, world_state, BLOCK_GAS_LIMIT)

    if not balance_check_result.success:
        raise RuntimeError(f"balanceOf(deployer) failed: {balance_check_result.error}")

    deployer_balance_initial = decode_uint256(balance_check_result.return_data)
    print(f"    Success:             {balance_check_result.success}")
    print(f"    Gas used:            {balance_check_result.gas_used}")
    print(f"    Deployer balance:    {deployer_balance_initial:,} tokens")

    # BREAKPOINT: balance_check_result.return_data, decoded deployer_balance_initial.
    # Inspect: balance_check_result.return_data — 32-byte big-endian of INITIAL_SUPPLY.
    # The EVM executed: CALLDATALOAD(4) -> deployer_addr_uint, SLOAD -> INITIAL_SUPPLY,
    # MSTORE(0, INITIAL_SUPPLY), RETURN(0, 32).

    assert deployer_balance_initial == INITIAL_SUPPLY, (
        f"Expected deployer balance={INITIAL_SUPPLY}, got {deployer_balance_initial}"
    )

    # =========================================================================
    # Step 5: Call transfer(recipient, TRANSFER_AMOUNT)
    # =========================================================================
    print(f"\n[5] Calling transfer(recipient, {TRANSFER_AMOUNT:,})...")

    transfer_calldata = encode_transfer(recipient_addr, TRANSFER_AMOUNT)
    print(f"    Calldata: 0x{transfer_calldata.hex()[:16]}...  (transfer selector + to + amount)")
    print(f"    To:       0x{recipient_addr.hex()}")
    print(f"    Amount:   {TRANSFER_AMOUNT:,} tokens")

    transfer_tx = Transaction(
        nonce=2,               # Deployer's third transaction
        gas_price=GAS_PRICE,
        gas=GAS_LIMIT_CALL,
        to=contract_addr,
        value=0,
        data=transfer_calldata,
    )
    signed_transfer_tx = sign_transaction(transfer_tx, deployer_priv)

    transfer_result = apply_transaction(signed_transfer_tx, world_state, BLOCK_GAS_LIMIT)

    if not transfer_result.success:
        raise RuntimeError(f"transfer() failed: {transfer_result.error}")

    print(f"    Success:  {transfer_result.success}")
    print(f"    Gas used: {transfer_result.gas_used}")

    # BREAKPOINT: world_state storage after transfer, gas used.
    # Inspect: world_state._accounts[contract_addr].storage after transfer:
    #   storage[int(deployer_addr)] should be INITIAL_SUPPLY - TRANSFER_AMOUNT
    #   storage[int(recipient_addr)] should be TRANSFER_AMOUNT
    # The EVM CALLER opcode returns deployer's address as uint256 (the msg.sender).

    # =========================================================================
    # Step 6: Call balanceOf(deployer) — verify deduction
    # =========================================================================
    print("\n[6] Calling balanceOf(deployer) after transfer...")

    balance_deployer_tx = Transaction(
        nonce=3,
        gas_price=GAS_PRICE,
        gas=GAS_LIMIT_CALL,
        to=contract_addr,
        value=0,
        data=encode_balance_of(deployer_addr),
    )
    balance_deployer_result = apply_transaction(
        sign_transaction(balance_deployer_tx, deployer_priv),
        world_state,
        BLOCK_GAS_LIMIT,
    )

    if not balance_deployer_result.success:
        raise RuntimeError(f"balanceOf(deployer) failed: {balance_deployer_result.error}")

    deployer_balance_final = decode_uint256(balance_deployer_result.return_data)
    print(f"    Deployer balance: {deployer_balance_final:,} tokens")

    # BREAKPOINT: deployer_balance_final decoded from return_data.
    # Expected: INITIAL_SUPPLY - TRANSFER_AMOUNT = 999,000 tokens.

    # =========================================================================
    # Step 7: Call balanceOf(recipient) — verify receipt
    # =========================================================================
    print("\n[7] Calling balanceOf(recipient) after transfer...")

    balance_recipient_tx = Transaction(
        nonce=4,
        gas_price=GAS_PRICE,
        gas=GAS_LIMIT_CALL,
        to=contract_addr,
        value=0,
        data=encode_balance_of(recipient_addr),
    )
    balance_recipient_result = apply_transaction(
        sign_transaction(balance_recipient_tx, deployer_priv),
        world_state,
        BLOCK_GAS_LIMIT,
    )

    if not balance_recipient_result.success:
        raise RuntimeError(f"balanceOf(recipient) failed: {balance_recipient_result.error}")

    recipient_balance_final = decode_uint256(balance_recipient_result.return_data)
    print(f"    Recipient balance: {recipient_balance_final:,} tokens")

    # BREAKPOINT: recipient_balance_final decoded from return_data.
    # Expected: TRANSFER_AMOUNT = 1,000 tokens.

    # =========================================================================
    # Step 8: Package into block #1
    # =========================================================================
    print("\n[8] Mining block #1...")

    block1 = create_block(
        parent=genesis_block,
        transactions=[
            signed_deploy_tx,
            signed_balance_check_tx,
            signed_transfer_tx,
        ],
        state_root=world_state.state_root_placeholder(),
        timestamp=int(time.time()),
    )
    b1_hash = block_hash(block1)

    print(f"    Block number:  {block1.header.number}")
    print(f"    Transactions:  {len(block1.transactions)}")
    print(f"    Block hash:    0x{b1_hash.hex()[:16]}...")

    # =========================================================================
    # Step 9: Verify final balances
    # =========================================================================
    print("\n[9] Verifying final balances...")

    expected_deployer_balance  = INITIAL_SUPPLY - TRANSFER_AMOUNT
    expected_recipient_balance = TRANSFER_AMOUNT

    assert deployer_balance_final == expected_deployer_balance, (
        f"Deployer balance mismatch: "
        f"expected {expected_deployer_balance:,}, got {deployer_balance_final:,}"
    )
    assert recipient_balance_final == expected_recipient_balance, (
        f"Recipient balance mismatch: "
        f"expected {expected_recipient_balance:,}, got {recipient_balance_final:,}"
    )
    assert deployer_balance_final + recipient_balance_final == INITIAL_SUPPLY, (
        "Token conservation violated: total tokens changed"
    )

    # =========================================================================
    # Summary
    # =========================================================================
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"  Contract address: 0x{contract_addr.hex()}")
    print(f"  Initial supply:   {INITIAL_SUPPLY:,} tokens")
    print(f"  Transfer amount:  {TRANSFER_AMOUNT:,} tokens")
    print(f"  Deployer:  {INITIAL_SUPPLY:,} -> {deployer_balance_final:,} tokens")
    print(f"  Recipient: 0 -> {recipient_balance_final:,} tokens")
    print(f"  Total conserved: {deployer_balance_final + recipient_balance_final:,} tokens")
    print(f"  Block:     #{block1.header.number} (0x{b1_hash.hex()[:16]}...)")
    print("\n  All assertions passed.")


if __name__ == "__main__":
    main()
