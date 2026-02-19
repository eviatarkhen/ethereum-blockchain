"""Hardcoded SimpleToken contract bytecode and ABI encoding helpers.

SimpleToken implements two functions:
  - transfer(address,uint256): transfers tokens from msg.sender to recipient
  - balanceOf(address): returns the token balance for an address

# DECISION: Using DIV-based selector extraction (SHR not available in this EVM).
# Same pattern as counter.py — PUSH32(2^224) first, then PUSH1/CALLDATALOAD,
# then DIV. EVM DIV pops 'a' (top = CALLDATALOAD result) then 'b' (second = 2^224):
# selector = calldata_word // 2^224 = upper 4 bytes of calldata.

# SIMPLIFIED: Real Solidity uses keccak256(abi.encode(address, slot)) for mapping keys.
# We use the address itself as the storage key to avoid requiring the SHA3 opcode.
# Balance of address X is stored at storage[int.from_bytes(X, 'big')].
# This works because an ABI-encoded address (32-byte padded) is already a valid storage slot.
"""

from ethereum.contracts.abi import compute_selector, encode_address, encode_uint256, encode_call

INITIAL_SUPPLY = 1_000_000  # Token units pre-minted to the deploying account

# ============================================================
# Bytecode layout (112 bytes total):
#
# --- Dispatcher (offsets 0-62, same pattern as Counter) ---
#  0     | 33   | PUSH32 <2^224>    | right-shift divisor pushed first
# 33     |  2   | PUSH1 0x00        | calldata offset
# 35     |  1   | CALLDATALOAD      | load 32 bytes from calldata[0] (TOP of stack)
# 36     |  1   | DIV               | selector = calldata_word (top) // 2^224 (second)
# 37     |  1   | DUP1              | duplicate for first compare
# 38     |  5   | PUSH4 a9059cbb    | transfer(address,uint256) selector
# 43     |  1   | EQ                |
# 44     |  2   | PUSH1 0x3f        | jump dest: transfer handler (63)
# 46     |  1   | JUMPI             |
# 47     |  1   | DUP1              | duplicate for second compare
# 48     |  5   | PUSH4 70a08231    | balanceOf(address) selector
# 53     |  1   | EQ                |
# 54     |  2   | PUSH1 0x62        | jump dest: balanceOf handler (98)
# 56     |  1   | JUMPI             |
# 57     |  1   | POP               | clean up selector
# 58     |  2   | PUSH1 0x00        | revert size
# 60     |  2   | PUSH1 0x00        | revert offset
# 62     |  1   | REVERT            |
#
# --- transfer(address,uint256) handler at offset 63 = 0x3f ---
#
# Stack evolution (annotated as [top, ...]):
#   After JUMPDEST + POP: stack is empty
#   Load calldata args and sender:
#     PUSH1 0x04, CALLDATALOAD  -> [to_uint]
#     PUSH1 0x24, CALLDATALOAD  -> [amount, to_uint]
#     CALLER                    -> [sender_uint, amount, to_uint]
#     DUP1                      -> [sender_uint, sender_uint, amount, to_uint]
#     SLOAD                     -> [sender_balance, sender_uint, amount, to_uint]
#   Insufficient-balance check (revert if sender_balance < amount):
#     DUP3                      -> [amount, sender_balance, sender_uint, amount, to_uint]
#     DUP2                      -> [sender_balance, amount, sender_balance, sender_uint, amount, to_uint]
#     LT                        -> [sb<amount, sender_balance, sender_uint, amount, to_uint]
#     PUSH1 0x5c, JUMPI         -> jump to revert if sb < amount
#   Deduct from sender:
#     DUP3                      -> [amount, sender_balance, sender_uint, amount, to_uint]
#     SWAP1                     -> [sender_balance, amount, sender_uint, amount, to_uint]
#     SUB                       -> [sb-amount, sender_uint, amount, to_uint]
#     SWAP1                     -> [sender_uint, sb-amount, amount, to_uint]
#     SSTORE                    -> storage[sender_uint]=sb-amount; stack: [amount, to_uint]
#   Add to recipient:
#     DUP2                      -> [to_uint, amount, to_uint]
#     SLOAD                     -> [to_balance, amount, to_uint]
#     ADD                       -> [to_balance+amount, to_uint]
#     DUP2                      -> [to_uint, to_balance+amount, to_uint]
#     SSTORE                    -> storage[to_uint]=to_bal+amount; stack: [to_uint]
#     POP                       -> stack: []
#     STOP
#
# 63     |  1   | JUMPDEST          |
# 64     |  1   | POP               | remove selector dup
# 65     |  2   | PUSH1 0x04        | calldata offset of 'to' arg
# 67     |  1   | CALLDATALOAD      | to_uint = calldata[4:36] as uint256
# 68     |  2   | PUSH1 0x24        | calldata offset of 'amount' arg (4+32=36=0x24)
# 70     |  1   | CALLDATALOAD      | amount = calldata[36:68] as uint256
# 71     |  1   | CALLER            | sender address as uint256
# 72     |  1   | DUP1              | duplicate sender for SLOAD + SSTORE key
# 73     |  1   | SLOAD             | sender_balance = storage[sender_uint]
# 74     |  1   | DUP3              | amount (for LT check)
# 75     |  1   | DUP2              | sender_balance (for LT check)
# 76     |  1   | LT                | 1 if sender_balance < amount (insufficient)
# 77     |  2   | PUSH1 0x5c        | jump dest: revert handler (92)
# 79     |  1   | JUMPI             | revert if insufficient balance
# 80     |  1   | DUP3              | amount (to subtract)
# 81     |  1   | SWAP1             | sender_balance now on top
# 82     |  1   | SUB               | new_sender_balance = sender_balance - amount
# 83     |  1   | SWAP1             | sender_uint now on top
# 84     |  1   | SSTORE            | storage[sender_uint] = new_sender_balance
# 85     |  1   | DUP2              | to_uint (for SLOAD + SSTORE key)
# 86     |  1   | SLOAD             | to_balance = storage[to_uint]
# 87     |  1   | ADD               | new_to_balance = to_balance + amount
# 88     |  1   | DUP2              | to_uint (for SSTORE key)
# 89     |  1   | SSTORE            | storage[to_uint] = new_to_balance
# 90     |  1   | POP               | clean up remaining to_uint
# 91     |  1   | STOP              |
#
# --- revert handler at offset 92 = 0x5c ---
# 92     |  1   | JUMPDEST          |
# 93     |  2   | PUSH1 0x00        | revert size: 0
# 95     |  2   | PUSH1 0x00        | revert offset: 0
# 97     |  1   | REVERT            |
#
# --- balanceOf(address) handler at offset 98 = 0x62 ---
# 98     |  1   | JUMPDEST          |
# 99     |  1   | POP               | remove selector dup
# 100    |  2   | PUSH1 0x04        | calldata offset of 'address' arg
# 102    |  1   | CALLDATALOAD      | addr_uint = calldata[4:36] as uint256 (ABI-padded address)
# 103    |  1   | SLOAD             | balance = storage[addr_uint]
# 104    |  2   | PUSH1 0x00        | memory write offset: 0
# 106    |  1   | MSTORE            | store 32-byte balance at mem[0]
# 107    |  2   | PUSH1 0x20        | return length: 32 bytes
# 109    |  2   | PUSH1 0x00        | return offset: memory[0]
# 111    |  1   | RETURN            |
# ============================================================

# fmt: off
TOKEN_RUNTIME_BYTECODE = bytes([
    # --- Function dispatcher ---
    # PUSH32(2^224) first so it lands BELOW CALLDATALOAD on the stack.
    # EVM DIV: a=pop() (CALLDATALOAD result, top), b=pop() (2^224, second).
    # selector = a // b = calldata_word // 2^224 = upper 4 bytes of calldata.
    0x7F,                    # PUSH32             — next 32 bytes are the immediate value
    0x00, 0x00, 0x00, 0x01,  # 2^224 high word    — byte[0..3]: 0x00000001
    0x00, 0x00, 0x00, 0x00,  # 2^224 word 2       — byte[4..7]: zero
    0x00, 0x00, 0x00, 0x00,  # 2^224 word 3       — byte[8..11]: zero
    0x00, 0x00, 0x00, 0x00,  # 2^224 word 4       — byte[12..15]: zero
    0x00, 0x00, 0x00, 0x00,  # 2^224 word 5       — byte[16..19]: zero
    0x00, 0x00, 0x00, 0x00,  # 2^224 word 6       — byte[20..23]: zero
    0x00, 0x00, 0x00, 0x00,  # 2^224 word 7       — byte[24..27]: zero
    0x00, 0x00, 0x00, 0x00,  # 2^224 word 8       — byte[28..31]: zero
    0x60, 0x00,              # PUSH1 0x00         — calldata offset 0
    0x35,                    # CALLDATALOAD       — load 32 bytes from calldata[0] (now on TOP)
    0x04,                    # DIV                — selector = calldata_word (top) // 2^224 (second)
    0x80,                    # DUP1               — duplicate selector for transfer compare
    0x63, 0xa9, 0x05, 0x9c, 0xbb,  # PUSH4 a9059cbb  — transfer(address,uint256) selector
    0x14,                    # EQ                 — check selector == transfer
    0x60, 0x3f,              # PUSH1 0x3f         — jump dest: transfer handler (offset 63)
    0x57,                    # JUMPI              — jump if equal
    0x80,                    # DUP1               — duplicate selector for balanceOf compare
    0x63, 0x70, 0xa0, 0x82, 0x31,  # PUSH4 70a08231  — balanceOf(address) selector
    0x14,                    # EQ                 — check selector == balanceOf
    0x60, 0x62,              # PUSH1 0x62         — jump dest: balanceOf handler (offset 98)
    0x57,                    # JUMPI              — jump if equal
    0x50,                    # POP                — clean up selector copy
    0x60, 0x00,              # PUSH1 0x00         — revert data size: 0
    0x60, 0x00,              # PUSH1 0x00         — revert data offset: 0
    0xFD,                    # REVERT             — no function matched

    # --- transfer(address,uint256) handler at offset 63 = 0x3f ---
    0x5B,                    # JUMPDEST           — valid jump destination marker
    0x50,                    # POP                — remove duplicated selector from stack
    0x60, 0x04,              # PUSH1 0x04         — calldata offset of 'to' argument
    0x35,                    # CALLDATALOAD       — to_uint = calldata[4:36] as uint256 (ABI address)
    0x60, 0x24,              # PUSH1 0x24         — calldata offset of 'amount' arg (4+32=36=0x24)
    0x35,                    # CALLDATALOAD       — amount = calldata[36:68] as uint256
    0x33,                    # CALLER             — sender address as uint256 (20-byte addr = uint160)
    0x80,                    # DUP1               — duplicate sender_uint (for SSTORE key)
    0x54,                    # SLOAD              — sender_balance = storage[sender_uint]
    0x82,                    # DUP3               — copy amount onto top for LT check
    0x81,                    # DUP2               — copy sender_balance onto top for LT check
    0x10,                    # LT                 — 1 if sender_balance < amount (insufficient funds)
    0x60, 0x5c,              # PUSH1 0x5c         — jump dest: revert handler (offset 92)
    0x57,                    # JUMPI              — revert if sender_balance < amount
    0x82,                    # DUP3               — copy amount to top for subtraction
    0x90,                    # SWAP1              — swap: sender_balance now on top
    0x03,                    # SUB                — new_sender_balance = sender_balance - amount
    0x90,                    # SWAP1              — sender_uint now on top
    0x55,                    # SSTORE             — storage[sender_uint] = new_sender_balance
    0x81,                    # DUP2               — copy to_uint for SLOAD + SSTORE key
    0x54,                    # SLOAD              — to_balance = storage[to_uint]
    0x01,                    # ADD                — new_to_balance = to_balance + amount
    0x81,                    # DUP2               — copy to_uint for SSTORE key
    0x55,                    # SSTORE             — storage[to_uint] = new_to_balance
    0x50,                    # POP                — clean up remaining to_uint on stack
    0x00,                    # STOP               — halt execution successfully

    # --- revert handler at offset 92 = 0x5c ---
    0x5B,                    # JUMPDEST           — valid jump destination marker
    0x60, 0x00,              # PUSH1 0x00         — revert data size: 0
    0x60, 0x00,              # PUSH1 0x00         — revert data offset: 0
    0xFD,                    # REVERT             — insufficient balance

    # --- balanceOf(address) handler at offset 98 = 0x62 ---
    0x5B,                    # JUMPDEST           — valid jump destination marker
    0x50,                    # POP                — remove duplicated selector from stack
    0x60, 0x04,              # PUSH1 0x04         — calldata offset of 'address' argument
    0x35,                    # CALLDATALOAD       — addr_uint = calldata[4:36] as uint256
    0x54,                    # SLOAD              — balance = storage[addr_uint]
    0x60, 0x00,              # PUSH1 0x00         — memory write offset: 0
    0x52,                    # MSTORE             — store 32-byte balance at mem[0]
    0x60, 0x20,              # PUSH1 0x20         — return length: 32 bytes
    0x60, 0x00,              # PUSH1 0x00         — return offset: memory[0]
    0xF3,                    # RETURN             — return 32 bytes from memory[0]
])
# fmt: on


def encode_transfer(to_address: bytes, amount: int) -> bytes:
    """Return calldata for SimpleToken.transfer(address,uint256).

    Args:
        to_address: 20-byte recipient address.
        amount: Token amount to transfer (uint256).

    Returns:
        68-byte calldata: 4-byte selector + 32-byte address + 32-byte uint256.
    """
    selector = compute_selector("transfer(address,uint256)")
    return encode_call(selector, encode_address(to_address), encode_uint256(amount))


def encode_balance_of(address: bytes) -> bytes:
    """Return calldata for SimpleToken.balanceOf(address).

    Args:
        address: 20-byte Ethereum address to query.

    Returns:
        36-byte calldata: 4-byte selector + 32-byte address.
    """
    selector = compute_selector("balanceOf(address)")
    return encode_call(selector, encode_address(address))
