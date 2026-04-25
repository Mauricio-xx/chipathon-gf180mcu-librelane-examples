# cocotb testbench for counter.v
#
# Runs with Icarus Verilog (SIM=icarus). Invoke via the Makefile:
#     make test-counter
#
# Three tests on the 4-bit synchronous up-counter:
#   - test_reset_holds_counter_at_zero  rst=1 holds q=0 across multiple cycles
#   - test_increment_runs_freely        rst=0 increments q every clock edge
#   - test_wrap_after_16_cycles         4-bit counter wraps to 0 after 16 cycles
#
# The DUT is intentionally simple (no enable line) so the same TB runs
# unchanged against RTL, post-synth GL, and post-PnR GL netlists.

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer


CLK_PERIOD_NS = 10


async def _start_with_reset(dut):
    """Drive rst=1 and clk=0 BEFORE starting the clock so the first
    rising edge sees a defined rst value (otherwise iverilog samples X
    and the counter increments to garbage)."""
    dut.rst.value = 1
    dut.clk.value = 0
    await Timer(1, unit="ns")
    cocotb.start_soon(Clock(dut.clk, CLK_PERIOD_NS, unit="ns").start())
    # Two edges with rst=1 -> counter is definitely 0.
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)


@cocotb.test()
async def test_reset_holds_counter_at_zero(dut):
    await _start_with_reset(dut)
    await Timer(1, unit="ns")
    assert int(dut.q.value) == 0, (
        f"With rst=1, q should stay at 0; got {int(dut.q.value)}"
    )
    # Hold rst high a few more cycles -- still 0.
    for _ in range(3):
        await RisingEdge(dut.clk)
    await Timer(1, unit="ns")
    assert int(dut.q.value) == 0, (
        f"With rst still 1, q should remain 0; got {int(dut.q.value)}"
    )


@cocotb.test()
async def test_increment_runs_freely(dut):
    await _start_with_reset(dut)
    dut.rst.value = 0
    # Count exactly 5 rising edges with rst=0.
    for _ in range(5):
        await RisingEdge(dut.clk)
    await Timer(1, unit="ns")
    assert int(dut.q.value) == 5, f"Expected q=5, got {int(dut.q.value)}"


@cocotb.test()
async def test_wrap_after_16_cycles(dut):
    await _start_with_reset(dut)
    dut.rst.value = 0
    for _ in range(16):
        await RisingEdge(dut.clk)
    await Timer(1, unit="ns")
    assert int(dut.q.value) == 0, (
        f"4-bit counter should wrap to 0 after 16 cycles, got {int(dut.q.value)}"
    )
