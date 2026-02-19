"""Tests for EVM infrastructure: Memory, opcodes, gas, exceptions."""

from ethereum.evm.memory import Memory
from ethereum.evm.opcodes import OP_ADD, OP_PUSH1, OP_STOP, OPCODE_NAMES
from ethereum.evm.gas import GAS_COSTS, INTRINSIC_GAS_TX, calculate_intrinsic_gas
from ethereum.evm.exceptions import (
    OutOfGas,
    StackUnderflow,
    StackOverflow,
    InvalidJumpDestination,
    InvalidOpcode,
)


# === Memory Tests ===


def test_memory_store_and_load():
    """MSTORE then MLOAD at offset 0 round-trips correctly."""
    mem = Memory()
    mem.store(0, 42)
    assert mem.load(0) == 42


def test_memory_expansion():
    """Accessing offset 0 expands memory to 32 bytes."""
    mem = Memory()
    mem.store(0, 0)
    assert mem.size() == 32


def test_memory_high_offset_expansion():
    """Accessing offset 64 expands memory to 96 bytes (3 words)."""
    mem = Memory()
    mem.store(64, 1)
    assert mem.size() == 96


def test_memory_store8():
    """MSTORE8 stores a single byte."""
    mem = Memory()
    mem.store8(0, 0xAB)
    # First byte should be 0xAB, rest zeros
    assert mem.load(0) == 0xAB << (31 * 8)


def test_memory_initial_size():
    """Fresh memory has size 0."""
    mem = Memory()
    assert mem.size() == 0


def test_memory_read_range():
    """read_range returns bytes from memory region."""
    mem = Memory()
    mem.store(0, 0xDEADBEEF)
    data = mem.read_range(28, 4)  # Last 4 bytes of the 32-byte word
    assert data == b"\xde\xad\xbe\xef"


def test_memory_write_range():
    """write_range writes arbitrary bytes."""
    mem = Memory()
    mem.write_range(0, b"\x01\x02\x03")
    assert mem.read_range(0, 3) == b"\x01\x02\x03"


def test_memory_read_empty_range():
    """read_range with size 0 returns empty bytes."""
    mem = Memory()
    assert mem.read_range(0, 0) == b""


# === Opcode Tests ===


def test_opcode_names_exist():
    """Opcode constants have human-readable names."""
    assert OPCODE_NAMES[OP_ADD] == "ADD"
    assert OPCODE_NAMES[OP_PUSH1] == "PUSH1"
    assert OPCODE_NAMES[OP_STOP] == "STOP"


def test_push_names():
    """All 32 PUSH opcodes have names."""
    for i in range(32):
        assert OPCODE_NAMES[0x60 + i] == f"PUSH{i + 1}"


def test_dup_names():
    """All 16 DUP opcodes have names."""
    for i in range(16):
        assert OPCODE_NAMES[0x80 + i] == f"DUP{i + 1}"


def test_swap_names():
    """All 16 SWAP opcodes have names."""
    for i in range(16):
        assert OPCODE_NAMES[0x90 + i] == f"SWAP{i + 1}"


# === Gas Tests ===


def test_gas_costs_defined():
    """Gas costs exist for core opcodes."""
    assert GAS_COSTS[OP_ADD] == 3
    assert GAS_COSTS[OP_STOP] == 0
    assert INTRINSIC_GAS_TX == 21000


def test_intrinsic_gas_empty():
    """Empty calldata costs just the base 21000."""
    assert calculate_intrinsic_gas(b"") == 21000


def test_intrinsic_gas_zero_bytes():
    """Zero bytes cost 4 gas each."""
    assert calculate_intrinsic_gas(b"\x00\x00") == 21000 + 4 * 2


def test_intrinsic_gas_non_zero_bytes():
    """Non-zero bytes cost 16 gas each."""
    assert calculate_intrinsic_gas(b"\x01\x02") == 21000 + 16 * 2


def test_intrinsic_gas_mixed():
    """Mixed zero and non-zero bytes."""
    assert calculate_intrinsic_gas(b"\x00\x01") == 21000 + 4 + 16


# === Exception Tests ===


def test_out_of_gas_exception():
    """OutOfGas stores needed and remaining."""
    e = OutOfGas(needed=100, remaining=50)
    assert e.needed == 100
    assert e.remaining == 50
    assert "100" in str(e) and "50" in str(e)


def test_stack_underflow_exception():
    """StackUnderflow stores needed and actual."""
    e = StackUnderflow(needed=2, actual=1)
    assert e.needed == 2
    assert e.actual == 1
    assert "2" in str(e)


def test_stack_overflow_exception():
    """StackOverflow stores max_depth."""
    e = StackOverflow(max_depth=1024)
    assert e.max_depth == 1024


def test_invalid_jump_destination_exception():
    """InvalidJumpDestination stores destination."""
    e = InvalidJumpDestination(destination=0x42)
    assert e.destination == 0x42
    assert "42" in str(e).lower() or "66" in str(e)


def test_invalid_opcode_exception():
    """InvalidOpcode stores opcode and pc."""
    e = InvalidOpcode(opcode=0xFF, pc=10)
    assert e.opcode == 0xFF
    assert e.pc == 10
    assert "FF" in str(e).upper() or "255" in str(e)
