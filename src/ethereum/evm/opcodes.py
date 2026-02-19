"""EVM opcode constants and name lookup table.

Defines hex values for every opcode this simplified EVM supports.
Contract-driven selection: only opcodes needed for Counter and SimpleToken.

Reference: Ethereum Yellow Paper, Appendix H.
See also: https://www.evm.codes/

# SIMPLIFIED: ~25 unique opcodes + PUSH/DUP/SWAP families.
# Real Ethereum defines 140+ opcodes including LOG, DELEGATECALL,
# STATICCALL, SELFBALANCE, BLOCKHASH, and many more.
"""

# === Stop and Arithmetic ===
OP_STOP = 0x00       # Halt execution
OP_ADD = 0x01        # Addition (mod 2^256)
OP_MUL = 0x02        # Multiplication (mod 2^256)
OP_SUB = 0x03        # Subtraction (mod 2^256)
OP_DIV = 0x04        # Integer division (0 if divisor is 0)
OP_MOD = 0x06        # Modulo (0 if divisor is 0)
OP_EXP = 0x0A        # Exponentiation (mod 2^256)

# === Comparison ===
OP_LT = 0x10         # Less than
OP_GT = 0x11         # Greater than
OP_EQ = 0x14         # Equality
OP_ISZERO = 0x15     # Is zero

# === Bitwise ===
OP_AND = 0x16        # Bitwise AND
OP_OR = 0x17         # Bitwise OR
OP_NOT = 0x19        # Bitwise NOT

# === Hashing ===
OP_SHA3 = 0x20       # Keccak-256 hash of memory region

# === Environment ===
OP_ADDRESS = 0x30    # Address of currently executing contract
OP_CALLER = 0x33     # Caller address (msg.sender)
OP_CALLVALUE = 0x34  # Value sent with call (msg.value)
OP_CALLDATALOAD = 0x35  # Load 32 bytes of calldata
OP_CALLDATASIZE = 0x36  # Size of calldata
OP_CALLDATACOPY = 0x37  # Copy calldata to memory
OP_CODESIZE = 0x38   # Size of code
OP_CODECOPY = 0x39   # Copy code to memory

# === Stack, Memory, Storage ===
OP_POP = 0x50        # Remove top of stack
OP_MLOAD = 0x51      # Load 32-byte word from memory
OP_MSTORE = 0x52     # Store 32-byte word to memory
OP_MSTORE8 = 0x53    # Store single byte to memory
OP_SLOAD = 0x54      # Load from storage
OP_SSTORE = 0x55     # Store to storage

# === Flow Control ===
OP_JUMP = 0x56       # Unconditional jump
OP_JUMPI = 0x57      # Conditional jump
OP_GAS = 0x5A        # Remaining gas
OP_JUMPDEST = 0x5B   # Valid jump destination marker
OP_MSIZE = 0x59      # Current memory size

# === Push (PUSH1 through PUSH32) ===
OP_PUSH1 = 0x60
OP_PUSH2 = 0x61
OP_PUSH3 = 0x62
OP_PUSH4 = 0x63
OP_PUSH5 = 0x64
OP_PUSH6 = 0x65
OP_PUSH7 = 0x66
OP_PUSH8 = 0x67
OP_PUSH9 = 0x68
OP_PUSH10 = 0x69
OP_PUSH11 = 0x6A
OP_PUSH12 = 0x6B
OP_PUSH13 = 0x6C
OP_PUSH14 = 0x6D
OP_PUSH15 = 0x6E
OP_PUSH16 = 0x6F
OP_PUSH17 = 0x70
OP_PUSH18 = 0x71
OP_PUSH19 = 0x72
OP_PUSH20 = 0x73
OP_PUSH21 = 0x74
OP_PUSH22 = 0x75
OP_PUSH23 = 0x76
OP_PUSH24 = 0x77
OP_PUSH25 = 0x78
OP_PUSH26 = 0x79
OP_PUSH27 = 0x7A
OP_PUSH28 = 0x7B
OP_PUSH29 = 0x7C
OP_PUSH30 = 0x7D
OP_PUSH31 = 0x7E
OP_PUSH32 = 0x7F

# === Dup (DUP1 through DUP16) ===
OP_DUP1 = 0x80
OP_DUP2 = 0x81
OP_DUP3 = 0x82
OP_DUP4 = 0x83
OP_DUP5 = 0x84
OP_DUP6 = 0x85
OP_DUP7 = 0x86
OP_DUP8 = 0x87
OP_DUP9 = 0x88
OP_DUP10 = 0x89
OP_DUP11 = 0x8A
OP_DUP12 = 0x8B
OP_DUP13 = 0x8C
OP_DUP14 = 0x8D
OP_DUP15 = 0x8E
OP_DUP16 = 0x8F

# === Swap (SWAP1 through SWAP16) ===
OP_SWAP1 = 0x90
OP_SWAP2 = 0x91
OP_SWAP3 = 0x92
OP_SWAP4 = 0x93
OP_SWAP5 = 0x94
OP_SWAP6 = 0x95
OP_SWAP7 = 0x96
OP_SWAP8 = 0x97
OP_SWAP9 = 0x98
OP_SWAP10 = 0x99
OP_SWAP11 = 0x9A
OP_SWAP12 = 0x9B
OP_SWAP13 = 0x9C
OP_SWAP14 = 0x9D
OP_SWAP15 = 0x9E
OP_SWAP16 = 0x9F

# === Contract ===
OP_CREATE = 0xF0     # Deploy a new contract
OP_CALL = 0xF1       # Call another contract
OP_RETURN = 0xF3     # Return data and halt
OP_REVERT = 0xFD     # Revert state and halt
OP_INVALID = 0xFE    # Invalid instruction (consumes all gas)


# === Name Lookup Table ===
# Maps opcode byte -> human-readable name for debugger display.

OPCODE_NAMES: dict[int, str] = {
    OP_STOP: "STOP",
    OP_ADD: "ADD",
    OP_MUL: "MUL",
    OP_SUB: "SUB",
    OP_DIV: "DIV",
    OP_MOD: "MOD",
    OP_EXP: "EXP",
    OP_LT: "LT",
    OP_GT: "GT",
    OP_EQ: "EQ",
    OP_ISZERO: "ISZERO",
    OP_AND: "AND",
    OP_OR: "OR",
    OP_NOT: "NOT",
    OP_SHA3: "SHA3",
    OP_ADDRESS: "ADDRESS",
    OP_CALLER: "CALLER",
    OP_CALLVALUE: "CALLVALUE",
    OP_CALLDATALOAD: "CALLDATALOAD",
    OP_CALLDATASIZE: "CALLDATASIZE",
    OP_CALLDATACOPY: "CALLDATACOPY",
    OP_CODESIZE: "CODESIZE",
    OP_CODECOPY: "CODECOPY",
    OP_POP: "POP",
    OP_MLOAD: "MLOAD",
    OP_MSTORE: "MSTORE",
    OP_MSTORE8: "MSTORE8",
    OP_SLOAD: "SLOAD",
    OP_SSTORE: "SSTORE",
    OP_JUMP: "JUMP",
    OP_JUMPI: "JUMPI",
    OP_MSIZE: "MSIZE",
    OP_GAS: "GAS",
    OP_JUMPDEST: "JUMPDEST",
    OP_CREATE: "CREATE",
    OP_CALL: "CALL",
    OP_RETURN: "RETURN",
    OP_REVERT: "REVERT",
    OP_INVALID: "INVALID",
}

# Add PUSH names
for i in range(32):
    OPCODE_NAMES[OP_PUSH1 + i] = f"PUSH{i + 1}"

# Add DUP names
for i in range(16):
    OPCODE_NAMES[OP_DUP1 + i] = f"DUP{i + 1}"

# Add SWAP names
for i in range(16):
    OPCODE_NAMES[OP_SWAP1 + i] = f"SWAP{i + 1}"
