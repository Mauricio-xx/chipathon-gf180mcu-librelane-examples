# tutorials/ — Experimental: drive the chipathon flow with eda-agents

> **EXPERIMENTAL.** Three optional, AI-driven walkthroughs that take the **same** 4-bit counter you already saw in [`examples/01_rtl2gds_counter.ipynb`](../examples/01_rtl2gds_counter.ipynb) and harden it via the [`eda-agents`](https://github.com/Mauricio-xx/eda-agents) companion project. Useful if you want to learn how an LLM agent can drive LibreLane on your behalf, but **not part of the chipathon tapeout signoff path** — for tapeout work stay with `examples/`.

These tutorials are deliberately separated from `examples/` because:

- They depend on the `eda-agents` Python package + a Claude Code or opencode CLI on your host. The `examples/` tree only needs Docker.
- The autoresearch tutorial (`03_*`) costs **real money** in LLM inference (capped at $0.30 by default).
- They iterate config knobs and agent prompts; results vary across runs. The `examples/` are deterministic given the inputs.

## Reading order

| # | Tutorial | What you learn | Prerequisites | Wall time / cost |
|---|----------|----------------|---------------|------------------|
| 01 | [`01_counter_with_agent_tui/`](01_counter_with_agent_tui/) | Open Claude Code or opencode in your terminal, ask the `gf180-docker-digital` agent to harden the counter, watch the agent walk RTL → cocotb → LibreLane → metrics. Conversational. | `gf180` container + Claude Code subscription **OR** opencode CLI. | 30-45 min, free with Claude subscription |
| 02 | [`02_counter_python_api/`](02_counter_python_api/) | Write ~30 lines of Python: `GenericDesign(config.yaml)` + `ProjectManager(...).run(...)`. The same counter, driven from a script. | `eda-agents` pip-installed + `claude` CLI (cc_cli backend) **OR** API key (adk backend). | 12-15 min; ~$1 of subscription quota (Sonnet 4.6) or ~$0.30 (Haiku 4.5) |
| 03 | [`03_counter_autoresearch/`](03_counter_autoresearch/) | Greedy AI loop pareto-optimises QoR knobs (PL_TARGET_DENSITY, CLOCK_PERIOD, PDN_VWIDTH) over the counter. Shows how to bound LLM cost with a hard $ cap. | `eda-agents` + opencode CLI + `OPENROUTER_API_KEY` (Gemini Flash recommended). | 15-20 min, ~$0.20-0.30 |

Order matters: Tutorial 01 teaches the agent + skill model conceptually, Tutorial 02 lifts it into Python so you can script it, Tutorial 03 closes the loop with QoR exploration.

## One-time setup

All three tutorials share the same setup: `eda-agents` package + either Claude Code or opencode on your host, plus optional API keys for autoresearch.

→ **Read [`docs/eda_agents_setup.md`](docs/eda_agents_setup.md) before opening any tutorial.** It walks the install once.

## What students adapt

Every tutorial assumes:

- `gf180` container is running with `~/eda/designs <-> /foss/designs` bind-mount (same as `examples/`). Run `scripts/bootstrap_container.sh` from the repo root if not.
- `eda-agents` is pip-installed in an active venv.
- For T01: a Claude Code subscription **or** opencode CLI on PATH.
- For T02: same as T01 (cc_cli) **or** an API key (adk).
- For T03: an `OPENROUTER_API_KEY` (or `ZAI_API_KEY`, or `GOOGLE_API_KEY`) in your `.env`.

Copy `.env.example` to `.env` (which is gitignored) and fill in whatever you have:

```bash
cp tutorials/.env.example tutorials/.env
$EDITOR tutorials/.env
```

## Workspace paths (no collision with examples/)

Each tutorial uses its own subdirectory under `~/eda/designs/` so it never touches the workspaces of the curated `examples/` flows:

| Tutorial | Host workspace | Container path |
|----------|----------------|----------------|
| 01 TUI    | `~/eda/designs/eda_agents_counter_tui/`         | `/foss/designs/eda_agents_counter_tui/` |
| 02 Python | `~/eda/designs/eda_agents_counter_pyapi/`       | `/foss/designs/eda_agents_counter_pyapi/` |
| 03 Auto   | `~/eda/designs/eda_agents_counter_autoresearch/`| `/foss/designs/eda_agents_counter_autoresearch/` |

Cleanup is a one-liner:

```bash
rm -rf ~/eda/designs/eda_agents_counter_*
```

## Why are these "experimental"?

- **Reproducibility.** The agent picks paths through the flow that can vary by model, model version, and conversation history. Two runs may land on different floorplan densities. The chipathon `examples/` are deterministic given the same inputs.
- **Cost.** Tutorial 03 burns LLM tokens on every iteration. The cap is $0.30 by default but real spending depends on your provider.
- **Tooling churn.** The `eda-agents` API surface (specifically `ProjectManager`, `DigitalAutoresearchRunner`, agent definitions) is still evolving. We pin the tutorials against the upstream tip and re-validate when things change, but a stale clone may break.

For the chipathon **silicon tapeout submission**, run your design through `examples/03_rtl2gds_chipathon_use.ipynb` (or `examples/04_*` if you have multi-macro). These tutorials are for *learning the agentic flow*.

## Source material

The three tutorials port their structure from the upstream [`eda-agents`](https://github.com/Mauricio-xx/eda-agents) repo:

- T01 invokes the `gf180-docker-digital` agent shipped at `eda-agents/.claude/agents/` and `eda-agents/.opencode/agent/`.
- T02 ports `tutorials/agents-analog-digital/demo/agents_rtl2gds_counter.{ipynb,py}`.
- T03 ports `tutorials/agents-analog-digital/demo/agents_digital_autoresearch.{ipynb,py}`.

See [`../CREDITS.md`](../CREDITS.md) for the full attribution chain.
