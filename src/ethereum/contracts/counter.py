"""Hardcoded Counter contract bytecode and ABI encoding helpers.

Counter implements two functions:
  - increment(): adds 1 to storage slot 0
  - getCount(): returns the value of storage slot 0

# DECISION: Using DIV-based selector extraction (SHR not available in this EVM).
# The opcodes.py file does not define OP_SHR (0x1c), so we use PUSH32(2^224)/DIV
# to shift the 32-byte CALLDATALOAD result right by 28 bytes (224 bits), leaving
# the 4-byte selector as a uint256.
#
# 2^224 in 32-byte big-endian: 0x00000001 followed by 28 zero bytes.
# Dividing a 32-byte value by 2^224 drops the lower 28 bytes, yielding the upper 4 bytes.
"""

from ethereum.contracts.abi import compute_selector

# ============================================================
# Bytecode layout (88 bytes total):
#
#  Offset | Size | Instruction        | Notes
# --------|------|--------------------|---------------------------
#   0     |  2   | PUSH1 0x00         | calldata offset
#   2     |  1   | CALLDATALOAD       | load 32 bytes of calldata
#   3     | 33   | PUSH32 <2^224>     | divisor = 2^224
#  36     |  1   | DIV                | selector = calldata_word / 2^224
#  37     |  1   | DUP1               | duplicate selector for first compare
#  38     |  5   | PUSH4 d09de08a     | increment() selector
#  43     |  1   | EQ                 |
#  44     |  2   | PUSH1 0x3f         | jump dest: increment handler (63)
#  46     |  1   | JUMPI              |
#  47     |  1   | DUP1               | duplicate selector for second compare
#  48     |  5   | PUSH4 a87d942c     | getCount() selector
#  53     |  1   | EQ                 |
#  54     |  2   | PUSH1 0x4b         | jump dest: getCount handler (75)
#  56     |  1   | JUMPI              |
#  57     |  1   | POP                | clean up selector
#  58     |  2   | PUSH1 0x00         | revert size
#  60     |  2   | PUSH1 0x00         | revert offset
#  62     |  1   | REVERT             | no matching function
#
#  63 = 0x3f: increment handler
#  63     |  1   | JUMPDEST           |
#  64     |  1   | POP                | remove selector dup from stack
#  65     |  2   | PUSH1 0x00         | storage slot 0
#  67     |  1   | SLOAD              | load counter value
#  68     |  2   | PUSH1 0x01         | increment by 1
#  70     |  1   | ADD                | new_count = count + 1
#  71     |  2   | PUSH1 0x00         | storage slot 0
#  73     |  1   | SSTORE             | store new_count
#  74     |  1   | STOP               |
#
#  75 = 0x4b: getCount handler
#  75     |  1   | JUMPDEST           |
#  76     |  1   | POP                | remove selector dup from stack
#  77     |  2   | PUSH1 0x00         | storage slot 0
#  79     |  1   | SLOAD              | load counter value
#  80     |  2   | PUSH1 0x00         | memory offset 0
#  82     |  1   | MSTORE             | store 32-byte value at mem[0]
#  83     |  2   | PUSH1 0x20         | return length: 32 bytes
#  85     |  2   | PUSH1 0x00         | return offset: 0
#  87     |  1   | RETURN             |
# ============================================================

# fmt: off
COUNTER_RUNTIME_BYTECODE = bytes([
    # --- Function dispatcher ---
    0x60, 0x00,              # PUSH1 0x00         — push calldata offset 0
    0x35,                    # CALLDATALOAD       — load 32 bytes from calldata[0]
    # PUSH32: 2^224 in big-endian = 0x00000001 followed by 28 zero bytes.
    # Dividing CALLDATALOAD result by 2^224 right-shifts 224 bits, yielding the 4-byte selector.
    0x7F,                    # PUSH32             — next 32 bytes are the immediate value
    0x00, 0x00, 0x00, 0x01,  # 2^224 high word    — byte[0..3]: 0x00000001
    0x00, 0x00, 0x00, 0x00,  # 2^224 word 2       — byte[4..7]: zero
    0x00, 0x00, 0x00, 0x00,  # 2^224 word 3       — byte[8..11]: zero
    0x00, 0x00, 0x00, 0x00,  # 2^224 word 4       — byte[12..15]: zero
    0x00, 0x00, 0x00, 0x00,  # 2^224 word 5       — byte[16..19]: zero
    0x00, 0x00, 0x00, 0x00,  # 2^224 word 6       — byte[20..23]: zero
    0x00, 0x00, 0x00, 0x00,  # 2^224 word 7       — byte[24..27]: zero
    0x00, 0x00, 0x00, 0x00,  # 2^224 word 8       — byte[28..31]: zero
    0x04,                    # DIV                — selector = calldata_word / 2^224
    0x80,                    # DUP1               — duplicate selector for increment compare
    0x63, 0xd0, 0x9d, 0xe0, 0x8a,  # PUSH4 d09de08a  — increment() selector
    0x14,                    # EQ                 — check selector == increment
    0x60, 0x3f,              # PUSH1 0x3f         — jump dest: increment handler (offset 63)
    0x57,                    # JUMPI              — jump if equal
    0x80,                    # DUP1               — duplicate selector for getCount compare
    0x63, 0xa8, 0x7d, 0x94, 0x2c,  # PUSH4 a87d942c  — getCount() selector
    0x14,                    # EQ                 — check selector == getCount
    0x60, 0x4b,              # PUSH1 0x4b         — jump dest: getCount handler (offset 75)
    0x57,                    # JUMPI              — jump if equal
    0x50,                    # POP                — clean up selector copy
    0x60, 0x00,              # PUSH1 0x00         — revert data size: 0
    0x60, 0x00,              # PUSH1 0x00         — revert data offset: 0
    0xFD,                    # REVERT             — no function matched

    # --- increment() handler at offset 63 = 0x3f ---
    0x5B,                    # JUMPDEST           — valid jump destination marker
    0x50,                    # POP                — remove duplicated selector from stack
    0x60, 0x00,              # PUSH1 0x00         — storage slot 0 (counter)
    0x54,                    # SLOAD              — load counter value from slot 0
    0x60, 0x01,              # PUSH1 0x01         — increment amount: 1
    0x01,                    # ADD                — new_count = count + 1
    0x60, 0x00,              # PUSH1 0x00         — storage slot 0
    0x55,                    # SSTORE             — store new_count to slot 0
    0x00,                    # STOP               — halt execution successfully

    # --- getCount() handler at offset 75 = 0x4b ---
    0x5B,                    # JUMPDEST           — valid jump destination marker
    0x50,                    # POP                — remove duplicated selector from stack
    0x60, 0x00,              # PUSH1 0x00         — storage slot 0 (counter)
    0x54,                    # SLOAD              — load counter value from slot 0
    0x60, 0x00,              # PUSH1 0x00         — memory write offset: 0
    0x52,                    # MSTORE             — store 32-byte value at mem[0]
    0x60, 0x20,              # PUSH1 0x20         — return length: 32 bytes
    0x60, 0x00,              # PUSH1 0x00         — return offset: memory[0]
    0xF3,                    # RETURN             — return 32 bytes from memory[0]
])
# fmt: on


def encode_increment() -> bytes:
    """Return calldata for Counter.increment() — just the 4-byte selector.

    Returns:
        4-byte bytes object: the function selector for increment().
    """
    return compute_selector("increment()")


def encode_get_count() -> bytes:
    """Return calldata for Counter.getCount() — just the 4-byte selector.

    Returns:
        4-byte bytes object: the function selector for getCount().
    """
    return compute_selector("getCount()")
