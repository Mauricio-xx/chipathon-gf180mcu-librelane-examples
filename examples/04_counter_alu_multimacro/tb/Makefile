# cocotb test dispatcher for the counter + ALU multi-macro example.
#
#   make test-counter    # 4 cocotb tests, ~2 s
#   make test-alu        # exhaustive 16x16x8 sweep, ~10 s
#   make test-all        # both
#   make clean           # nuke sim_build / results.xml
#
# Requires:  cocotb, icarus-verilog  (both in the hpretl/iic-osic-tools container)

.PHONY: test-counter test-alu test-all clean

TOPLEVEL_LANG ?= verilog
SIM           ?= icarus
RTL            = ../rtl

test-counter:
	$(MAKE) -f Makefile.cocotb \
	    TOPLEVEL=counter \
	    MODULE=test_counter \
	    VERILOG_SOURCES="$(RTL)/counter.sv"

test-alu:
	$(MAKE) -f Makefile.cocotb \
	    TOPLEVEL=alu \
	    MODULE=test_alu \
	    VERILOG_SOURCES="$(RTL)/alu.sv"

test-all: test-counter test-alu

clean:
	rm -rf sim_build results.xml
