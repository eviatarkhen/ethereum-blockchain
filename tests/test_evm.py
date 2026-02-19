"""Tests for EVM execute loop and all opcodes."""

import pytest
from ethereum.evm.vm import EVM, ExecutionContext, ExecutionResult
from ethereum.evm.opcodes import *
from ethereum.evm.exceptions import OutOfGas, InvalidJumpDestination, StackUnderflow


def _run(bytecode, gas=100000, calldata=b"", storage=None, value=0):
    """Helper: run bytecode and return (ExecutionResult, EVM instance)."""
    ctx = ExecutionContext(
        caller=b"\x01" * 20,
        address=b"\x02" * 20,
        value=value,
        data=calldata,
        gas=gas,
    )
    evm = EVM(code=bytes(bytecode), context=ctx, storage=storage or {})
    result = evm.execute()
    return result, evm


# === Arithmetic ===


def test_add_simple():
    """PUSH1 3 PUSH1 5 ADD -> 8."""
    result, evm = _run([OP_PUSH1, 3, OP_PUSH1, 5, OP_ADD, OP_STOP])
    assert evm.execution_stack == [8]


def test_add_overflow():
    """ADD(2^256 - 1, 1) wraps to 0 (mod 2^256)."""
    bytecode = [OP_PUSH32] + [0xFF] * 32 + [OP_PUSH1, 1, OP_ADD, OP_STOP]
    result, evm = _run(bytecode)
    assert evm.execution_stack == [0]


def test_sub():
    """PUSH1 3 PUSH1 5 SUB -> 2 (top - second: 5 - 3 = 2)."""
    result, evm = _run([OP_PUSH1, 3, OP_PUSH1, 5, OP_SUB, OP_STOP])
    assert evm.execution_stack == [2]


def test_sub_underflow_wraps():
    """SUB(3, 5) wraps to 2^256 - 2 (mod 2^256)."""
    result, evm = _run([OP_PUSH1, 5, OP_PUSH1, 3, OP_SUB, OP_STOP])
    assert evm.execution_stack == [2**256 - 2]


def test_mul():
    """PUSH1 7 PUSH1 6 MUL -> 42."""
    result, evm = _run([OP_PUSH1, 7, OP_PUSH1, 6, OP_MUL, OP_STOP])
    assert evm.execution_stack == [42]


def test_div():
    """PUSH1 3 PUSH1 10 DIV -> 3 (integer division: 10 / 3 = 3)."""
    result, evm = _run([OP_PUSH1, 3, OP_PUSH1, 10, OP_DIV, OP_STOP])
    assert evm.execution_stack == [3]


def test_div_by_zero():
    """DIV by zero returns 0 (EVM spec)."""
    result, evm = _run([OP_PUSH1, 0, OP_PUSH1, 10, OP_DIV, OP_STOP])
    assert evm.execution_stack == [0]


def test_mod():
    """PUSH1 3 PUSH1 10 MOD -> 1 (10 % 3 = 1)."""
    result, evm = _run([OP_PUSH1, 3, OP_PUSH1, 10, OP_MOD, OP_STOP])
    assert evm.execution_stack == [1]


def test_exp():
    """PUSH1 3 PUSH1 2 EXP -> 8 (2^3 = 8)."""
    result, evm = _run([OP_PUSH1, 3, OP_PUSH1, 2, OP_EXP, OP_STOP])
    assert evm.execution_stack == [8]


# === Comparison ===


def test_lt():
    """PUSH1 5 PUSH1 3 LT -> 1 (3 < 5 is true)."""
    result, evm = _run([OP_PUSH1, 5, OP_PUSH1, 3, OP_LT, OP_STOP])
    assert evm.execution_stack == [1]


def test_lt_false():
    """PUSH1 3 PUSH1 5 LT -> 0 (5 < 3 is false)."""
    result, evm = _run([OP_PUSH1, 3, OP_PUSH1, 5, OP_LT, OP_STOP])
    assert evm.execution_stack == [0]


def test_gt():
    """PUSH1 3 PUSH1 5 GT -> 1 (5 > 3 is true)."""
    result, evm = _run([OP_PUSH1, 3, OP_PUSH1, 5, OP_GT, OP_STOP])
    assert evm.execution_stack == [1]


def test_eq():
    """PUSH1 5 PUSH1 5 EQ -> 1."""
    result, evm = _run([OP_PUSH1, 5, OP_PUSH1, 5, OP_EQ, OP_STOP])
    assert evm.execution_stack == [1]


def test_eq_false():
    """PUSH1 5 PUSH1 3 EQ -> 0."""
    result, evm = _run([OP_PUSH1, 5, OP_PUSH1, 3, OP_EQ, OP_STOP])
    assert evm.execution_stack == [0]


def test_iszero_true():
    """PUSH1 0 ISZERO -> 1."""
    result, evm = _run([OP_PUSH1, 0, OP_ISZERO, OP_STOP])
    assert evm.execution_stack == [1]


def test_iszero_false():
    """PUSH1 1 ISZERO -> 0."""
    result, evm = _run([OP_PUSH1, 1, OP_ISZERO, OP_STOP])
    assert evm.execution_stack == [0]


# === Bitwise ===


def test_and():
    """AND(0xFF, 0x0F) -> 0x0F."""
    result, evm = _run([OP_PUSH1, 0x0F, OP_PUSH1, 0xFF, OP_AND, OP_STOP])
    assert evm.execution_stack == [0x0F]


def test_or():
    """OR(0xF0, 0x0F) -> 0xFF."""
    result, evm = _run([OP_PUSH1, 0x0F, OP_PUSH1, 0xF0, OP_OR, OP_STOP])
    assert evm.execution_stack == [0xFF]


def test_not():
    """NOT(0) -> MAX_UINT256."""
    result, evm = _run([OP_PUSH1, 0, OP_NOT, OP_STOP])
    assert evm.execution_stack == [2**256 - 1]


# === Stack ===


def test_pop():
    """POP removes top of stack."""
    result, evm = _run([OP_PUSH1, 1, OP_PUSH1, 2, OP_POP, OP_STOP])
    assert evm.execution_stack == [1]


def test_dup1():
    """DUP1 duplicates top of stack."""
    result, evm = _run([OP_PUSH1, 42, OP_DUP1, OP_STOP])
    assert evm.execution_stack == [42, 42]


def test_dup2():
    """DUP2 duplicates second item."""
    result, evm = _run([OP_PUSH1, 1, OP_PUSH1, 2, OP_DUP2, OP_STOP])
    assert evm.execution_stack == [1, 2, 1]


def test_swap1():
    """SWAP1 swaps top two stack items."""
    result, evm = _run([OP_PUSH1, 1, OP_PUSH1, 2, OP_SWAP1, OP_STOP])
    assert evm.execution_stack == [2, 1]


def test_swap2():
    """SWAP2 swaps top with third item."""
    result, evm = _run([
        OP_PUSH1, 1, OP_PUSH1, 2, OP_PUSH1, 3, OP_SWAP2, OP_STOP
    ])
    assert evm.execution_stack == [3, 2, 1]


def test_push2():
    """PUSH2 pushes 2 bytes."""
    result, evm = _run([OP_PUSH2, 0x01, 0x00, OP_STOP])
    assert evm.execution_stack == [256]


def test_push4():
    """PUSH4 pushes 4 bytes."""
    result, evm = _run([OP_PUSH4, 0x00, 0x00, 0x01, 0x00, OP_STOP])
    assert evm.execution_stack == [256]


# === Memory ===


def test_mstore_mload():
    """MSTORE then MLOAD round-trips a value."""
    result, evm = _run([
        OP_PUSH1, 42, OP_PUSH1, 0, OP_MSTORE,
        OP_PUSH1, 0, OP_MLOAD, OP_STOP
    ])
    assert evm.execution_stack == [42]


def test_mstore8():
    """MSTORE8 stores a single byte then MLOAD reads full word."""
    result, evm = _run([
        OP_PUSH1, 0xFF, OP_PUSH1, 31, OP_MSTORE8,  # Store 0xFF at byte 31
        OP_PUSH1, 0, OP_MLOAD, OP_STOP
    ])
    assert evm.execution_stack == [0xFF]  # LSB of the 32-byte word


def test_msize():
    """MSIZE returns current memory size."""
    result, evm = _run([
        OP_PUSH1, 0, OP_PUSH1, 0, OP_MSTORE,  # Expand to 32 bytes
        OP_MSIZE, OP_STOP
    ])
    assert evm.execution_stack == [32]


# === Storage ===


def test_sstore_sload():
    """SSTORE then SLOAD round-trips: store 42 at slot 0, load slot 0."""
    result, evm = _run([
        OP_PUSH1, 42, OP_PUSH1, 0, OP_SSTORE,
        OP_PUSH1, 0, OP_SLOAD, OP_STOP
    ])
    assert evm.execution_stack == [42]
    assert evm.storage == {0: 42}


def test_sload_unset_returns_zero():
    """SLOAD of unset slot returns 0."""
    result, evm = _run([OP_PUSH1, 99, OP_SLOAD, OP_STOP])
    assert evm.execution_stack == [0]


def test_sstore_overwrites():
    """SSTORE overwrites existing value."""
    result, evm = _run([
        OP_PUSH1, 1, OP_PUSH1, 0, OP_SSTORE,  # slot 0 = 1
        OP_PUSH1, 2, OP_PUSH1, 0, OP_SSTORE,  # slot 0 = 2
        OP_PUSH1, 0, OP_SLOAD, OP_STOP
    ])
    assert evm.execution_stack == [2]


# === Flow Control ===


def test_jump():
    """JUMP to a JUMPDEST skips intermediate code."""
    result, evm = _run([
        OP_PUSH1, 4, OP_JUMP, OP_INVALID,
        OP_JUMPDEST, OP_PUSH1, 42, OP_STOP
    ])
    assert evm.execution_stack == [42]


def test_jumpi_taken():
    """JUMPI taken when condition is non-zero."""
    result, evm = _run([
        OP_PUSH1, 1, OP_PUSH1, 6, OP_JUMPI, OP_INVALID,
        OP_JUMPDEST, OP_PUSH1, 42, OP_STOP
    ])
    assert evm.execution_stack == [42]


def test_jumpi_not_taken():
    """JUMPI not taken when condition is zero."""
    result, evm = _run([
        OP_PUSH1, 0, OP_PUSH1, 7, OP_JUMPI,
        OP_PUSH1, 99, OP_STOP,
        OP_JUMPDEST
    ])
    assert evm.execution_stack == [99]


def test_jump_invalid_destination():
    """JUMP to non-JUMPDEST raises InvalidJumpDestination."""
    with pytest.raises(InvalidJumpDestination):
        _run([OP_PUSH1, 3, OP_JUMP, OP_PUSH1, 42, OP_STOP])


# === Return and Revert ===


def test_return():
    """RETURN reads from memory and stops execution with success."""
    result, evm = _run([
        OP_PUSH1, 42, OP_PUSH1, 0, OP_MSTORE,
        OP_PUSH1, 32, OP_PUSH1, 0, OP_RETURN
    ])
    assert result.success is True
    assert len(result.return_data) == 32
    assert int.from_bytes(result.return_data, "big") == 42


def test_revert():
    """REVERT stops execution with failure."""
    result, evm = _run([
        OP_PUSH1, 0, OP_PUSH1, 0, OP_REVERT
    ])
    assert result.success is False


# === Calldata ===


def test_calldataload():
    """CALLDATALOAD reads 32 bytes from calldata at offset."""
    calldata = b"\x00" * 28 + b"\xde\xad\xbe\xef"
    result, evm = _run(
        [OP_PUSH1, 0, OP_CALLDATALOAD, OP_STOP], calldata=calldata
    )
    assert evm.execution_stack == [int.from_bytes(calldata[:32], "big")]


def test_calldataload_zero_pads():
    """CALLDATALOAD zero-pads if reading past end of calldata."""
    calldata = b"\xFF"  # Only 1 byte
    result, evm = _run(
        [OP_PUSH1, 0, OP_CALLDATALOAD, OP_STOP], calldata=calldata
    )
    expected = 0xFF << (31 * 8)  # 0xFF followed by 31 zero bytes
    assert evm.execution_stack == [expected]


def test_calldatasize():
    """CALLDATASIZE pushes calldata length."""
    calldata = b"\x01\x02\x03\x04"
    result, evm = _run([OP_CALLDATASIZE, OP_STOP], calldata=calldata)
    assert evm.execution_stack == [4]


def test_calldatacopy():
    """CALLDATACOPY copies calldata to memory."""
    calldata = b"\xAA\xBB\xCC\xDD"
    result, evm = _run([
        OP_PUSH1, 4,  # size
        OP_PUSH1, 0,  # offset in calldata
        OP_PUSH1, 0,  # dest offset in memory
        OP_CALLDATACOPY,
        OP_STOP
    ], calldata=calldata)
    assert evm.memory.read_range(0, 4) == b"\xAA\xBB\xCC\xDD"


# === Context ===


def test_caller():
    """CALLER pushes the caller address."""
    result, evm = _run([OP_CALLER, OP_STOP])
    expected = int.from_bytes(b"\x01" * 20, "big")
    assert evm.execution_stack == [expected]


def test_callvalue():
    """CALLVALUE pushes the value sent with the call."""
    result, evm = _run([OP_CALLVALUE, OP_STOP], value=1000)
    assert evm.execution_stack == [1000]


def test_address():
    """ADDRESS pushes the executing contract's address."""
    result, evm = _run([OP_ADDRESS, OP_STOP])
    expected = int.from_bytes(b"\x02" * 20, "big")
    assert evm.execution_stack == [expected]


def test_codesize():
    """CODESIZE pushes the size of the executing code."""
    code = [OP_CODESIZE, OP_STOP]
    result, evm = _run(code)
    assert evm.execution_stack == [2]


# === SHA3 ===


def test_sha3():
    """SHA3 computes keccak256 of memory region."""
    from ethereum.crypto.hashing import keccak256
    result, evm = _run([
        OP_PUSH1, 0xFF, OP_PUSH1, 0, OP_MSTORE8,
        OP_PUSH1, 1, OP_PUSH1, 0, OP_SHA3, OP_STOP
    ])
    expected = int.from_bytes(keccak256(bytes([0xFF])), "big")
    assert evm.execution_stack == [expected]


# === Gas ===


def test_out_of_gas():
    """Execution that exceeds gas limit raises OutOfGas."""
    with pytest.raises(OutOfGas):
        _run([OP_PUSH1, 1, OP_PUSH1, 2, OP_ADD, OP_STOP], gas=1)


def test_gas_tracking():
    """Gas remaining decreases with each opcode."""
    result, evm = _run([OP_PUSH1, 1, OP_STOP], gas=100)
    assert result.gas_used > 0
    assert result.gas_remaining == 100 - result.gas_used


def test_gas_opcode():
    """GAS opcode pushes remaining gas."""
    result, evm = _run([OP_GAS, OP_STOP], gas=1000)
    assert len(evm.execution_stack) == 1
    assert evm.execution_stack[0] < 1000


def test_stack_underflow():
    """ADD with empty stack raises StackUnderflow."""
    with pytest.raises(StackUnderflow):
        _run([OP_ADD, OP_STOP])


def test_execution_result_success():
    """Successful execution returns success=True."""
    result, _ = _run([OP_STOP])
    assert result.success is True


def test_execution_result_gas_accounting():
    """Gas used + gas remaining = initial gas."""
    initial_gas = 50000
    result, _ = _run([OP_PUSH1, 1, OP_PUSH1, 2, OP_ADD, OP_STOP], gas=initial_gas)
    assert result.gas_used + result.gas_remaining == initial_gas


def test_codecopy():
    """CODECOPY copies bytecode to memory."""
    code = [
        OP_PUSH1, 5,   # size: copy 5 bytes
        OP_PUSH1, 0,   # source offset: from start of code
        OP_PUSH1, 0,   # dest offset: to memory start
        OP_CODECOPY,
        OP_STOP
    ]
    result, evm = _run(code)
    # First 5 bytes of code should be in memory
    assert evm.memory.read_range(0, 5) == bytes(code[:5])
