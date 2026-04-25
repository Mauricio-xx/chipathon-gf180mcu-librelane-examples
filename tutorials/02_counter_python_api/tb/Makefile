# cocotb test dispatcher for the counter tutorial.
#
# RTL sim (pre-synthesis):
#   make test-counter        # 3 cocotb tests on counter.v
#   make clean
#
# Requires:  cocotb, icarus-verilog  (both in hpretl/iic-osic-tools)

.PHONY: test-counter clean

TOPLEVEL_LANG ?= verilog
SIM           ?= icarus
RTL            = ../rtl

test-counter:
	$(MAKE) -f Makefile.cocotb \
	    TOPLEVEL=counter \
	    MODULE=test_counter \
	    VERILOG_SOURCES="$(RTL)/counter.v" \
	    SIM_BUILD=sim_build_counter

clean:
	rm -rf sim_build sim_build_counter results.xml
