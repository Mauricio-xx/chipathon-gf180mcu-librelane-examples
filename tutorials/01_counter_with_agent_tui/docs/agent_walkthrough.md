# Agent walkthrough — what to expect during the chat session

This document is a transcript-shaped reference for what the `gf180-docker-digital` agent does during Tutorial 01. Read it before your first chat session so the agent's questions and tool calls aren't surprising.

## Turn 1 — Skill loading + bind-mount confirmation

Right after you paste the opening prompt, the agent will:

1. Call `mcp__eda-agents__render_skill(name="flow.rtl2gds_gf180_docker")` to load its playbook. You'll see the MCP tool call in your terminal — approve it.
2. Inspect your prompt and confirm the bind-mount path. It will ask something like:

   > *I see you want to harden the design at `/foss/designs/eda_agents_counter_tui/`. The host-side path under your `~/eda/designs/` bind-mount is `~/eda/designs/eda_agents_counter_tui/`. Confirm I should write there?*

3. Reply *yes* (or correct the path). The agent will not touch the filesystem until you confirm.

**Why this matters:** the skill explicitly tells the agent to confirm the mount path *before* any `docker run`. A wrong `-v` writes to the wrong host directory.

## Turn 2 — Container check

The agent will call:

```
docker ps --filter name=gf180 --format '{{.Names}} {{.Status}}'
```

If the container is up, it proceeds. If not, it asks for permission to run the canonical `docker run` from the skill body. **Approve only if you trust the bind-mount path** — the skill always uses `--user $(id -u):$(id -g)` so output files come out owned by you.

## Turn 3 — Read the staged inputs

The agent reads:
- `rtl/counter.v` — confirms the module signature (clk, rst, q[3:0]).
- `librelane/config.yaml` — confirms `DESIGN_NAME: counter`, `CLOCK_PERIOD: 50`, `DIE_AREA: [0,0,300,300]`.
- `tb/Makefile` and `tb/test_counter.py` — confirms the cocotb harness layout.

It will print a short summary back to you. No tool approvals needed for these reads.

## Turn 4 — cocotb sanity

The skill mandates running cocotb before LibreLane. The agent will issue:

```bash
docker exec gf180 bash -lc '
  cd /foss/designs/eda_agents_counter_tui/tb && \
  make clean && make test-counter
'
```

Expected output (truncated):

```
SIM ?= icarus
TOPLEVEL_LANG ?= verilog
... cocotb 1.x.y ...
TESTS=3 PASS=3 FAIL=0 SKIP=0
```

If a test fails, the agent stops and reports. If all 3 pass, it proceeds.

## Turn 5 — LibreLane

The agent will issue (verbatim from the skill):

```bash
docker exec gf180 bash -lc '
  source sak-pdk-script.sh gf180mcuD gf180mcu_fd_sc_mcu7t5v0 && \
  cd /foss/designs/eda_agents_counter_tui && \
  librelane librelane/config.yaml \
      --pdk gf180mcuD \
      --pdk-root /foss/pdks \
      --manual-pdk \
      --run-tag tutorial01
'
```

**Wall time: ~1-2 minutes** for this small counter. The agent will tail the LibreLane log live in the chat. Watch for:

- "Synthesis complete. Cell count: 4."
- "Floorplan, placement, CTS, routing... all OK."
- "SignOff: setup vio 0, hold vio 0, DRC 0, LVS 0."

If LibreLane fails, the agent will compose `flow.drc_checker` or `flow.drc_fixer` (also from the skill registry) to triage. For this tutorial, that should not happen — the config is identical to the validated `examples/01_*`.

## Turn 6 — Signoff report

The agent reads `final/metrics.csv` and prints:

> *Flow complete. Signoff: 4 stdcells, 0 setup vio, 0 hold vio, 0 DRC, 0 LVS. Power 5.2e-5 W. GDS at `/foss/designs/eda_agents_counter_tui/runs/tutorial01/final/gds/counter.gds`.*

At this point you can:

- Type *thank you* and exit the chat (Ctrl-D in Claude Code, `/exit` in opencode).
- Return to the notebook, flip `RUN_METRICS_CHECK=True`, and re-run cell 5 to verify from the host side.

## What the agent will NOT do unprompted

The skill is intentionally narrow. The agent will not:

- Edit `librelane/config.yaml` to optimise QoR. (Tutorial 03 does that via the autoresearch loop.)
- Re-run the flow with a different seed or density. Ask explicitly if you want that.
- Attempt tapeout-quality signoff. The Classic flow with `RUN_MAGIC_STREAMOUT: false` skips Magic-side DRC entirely.
- Push GDS to a foundry. (Obviously — but the skill explicitly stops at the metrics report.)

## What you should NOT do

- Don't let the agent skip cocotb to "save time". The skill mandates it for a reason: a TB failure on the staged RTL means the LibreLane run will produce silicon that does not match the spec.
- Don't paste the agent invocation inside the notebook. It is meant to run in your terminal so the agent has access to your shell. The notebook only **prints** the command.
- Don't run two agent sessions against the same workspace simultaneously. They will fight over `runs/<tag>/`.

## How to recover from a stuck agent

If the agent loops, hangs, or starts hallucinating about non-existent files:

1. Ctrl-C in Claude Code (`/exit` in opencode) to end the session.
2. Inspect the workspace: `ls ~/eda/designs/eda_agents_counter_tui/runs/`. If a partial run exists, you can either resume it manually or `rm -rf` it.
3. Start a fresh session and paste the opening prompt again. The agent has no memory of the previous session unless you load it via `--resume` (Claude Code) or `--session` (opencode).

## Cost reference

- Claude Code with subscription: **$0**. Subscriptions cover unlimited usage subject to fair-use rate limits.
- opencode + OpenRouter + `google/gemini-3-flash-preview`: **~$0.01-0.05** for a single counter run with one round of clarifying questions.
- opencode + `anthropic/claude-haiku-4-5`: **~$0.10-0.20** for the same.
- opencode + `anthropic/claude-opus-4-7`: **~$1-3** — overkill for this tutorial.
