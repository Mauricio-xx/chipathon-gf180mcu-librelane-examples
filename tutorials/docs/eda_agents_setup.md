# One-time setup: eda-agents + Claude Code / opencode

Every tutorial under `tutorials/` shares this setup. Do it once, then open the notebooks.

## What you are installing

| Component | Why | Where |
|-----------|-----|-------|
| `eda-agents` Python package | Provides `GenericDesign`, `ProjectManager`, `DigitalAutoresearchRunner`, the registered agents and skills, and the MCP server. | pip-installable, see below |
| Claude Code CLI **or** opencode CLI | The TUI / CLI that hosts the `gf180-docker-digital` agent and talks to the MCP server. | npm / standalone install |
| MCP server registration | Lets the agent call `mcp__eda-agents__render_skill(...)` to pull guide skills from the package. | one-time per project |
| `gf180` Docker container | Runs LibreLane / cocotb / Magic / KLayout. Same as `examples/`. | `scripts/bootstrap_container.sh` from repo root |
| (Optional) Provider API key | Only T03 strictly needs one. T01 and T02 work fine on a Claude subscription. | `tutorials/.env` |

## Step 1 — Make sure the chipathon container exists

If you have already worked through `examples/`, you can skip this.

```bash
cd /path/to/chipathon-gf180mcu-librelane-examples
scripts/bootstrap_container.sh        # idempotent
docker ps --filter name=gf180         # should show one container, status Up
```

## Step 2 — Install eda-agents

```bash
# Pick a directory next to this repo.
cd ~/personal_exp                     # or anywhere you keep clones
git clone https://github.com/Mauricio-xx/eda-agents.git
cd eda-agents

# Create a venv and install in editable mode.
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[adk]"               # for ADK backend; see other extras below
```

Available extras:

| Extra | Adds | Needed for |
|-------|------|------------|
| `[dev]` | pytest, ruff | Running the test suite |
| `[adk]` | google-adk, litellm | T02 with `backend="adk"`, T03 with `backend="adk"` or `"litellm"` |
| `[agents]` | openai | OpenAI-direct harness paths |
| `[coordination]` | context-teleport | Optional MCP coordination |

For these chipathon tutorials, `[adk]` covers everything you need. Skip the extra entirely if you only plan to use `cc_cli` (Claude Code subprocess) or `opencode`.

## Step 3 — Install Claude Code or opencode

You need **at least one** of these to drive the TUI agent (T01) or the cc_cli backend (T02). Both work; pick whichever fits your wallet.

### Claude Code (Anthropic subscription)

```bash
npm install -g @anthropic-ai/claude-code
claude --version                      # confirm install
```

You also need a Claude.ai subscription (Pro / Max / API). The CLI authenticates against `~/.claude/` on first use.

### opencode (multi-provider, pay-as-you-go)

```bash
npm install -g opencode-ai
opencode --version
```

Bring your own provider key — OpenRouter, Z.ai, Google AI Studio, Anthropic API, OpenAI, etc. The cheapest path for these tutorials is OpenRouter + `google/gemini-3-flash-preview`.

## Step 4 — Register the eda-agents MCP server

Each tutorial uses the `gf180-docker-digital` agent, which needs to call `mcp__eda-agents__render_skill(...)` to load the `flow.rtl2gds_gf180_docker` skill body. That requires a one-time project-local MCP server registration.

The `eda-agents` package ships an `eda-init` script that does this for you:

```bash
cd /path/to/chipathon-gf180mcu-librelane-examples
eda-init                              # writes .mcp.json + opencode.json + .claude/agents/ + .opencode/agent/
```

This creates the following at the repo root (all gitignored):

- `.mcp.json` — Claude Code MCP server registration
- `opencode.json` — opencode MCP server registration (note: no leading dot)
- `.claude/agents/gf180-docker-digital.md` — the agent definition Claude Code will load
- `.opencode/agent/gf180-docker-digital.md` — same agent for opencode

Verify the MCP server is reachable:

```bash
# From inside Claude Code, type:
/mcp
# You should see: eda-agents (connected)
```

For opencode, the equivalent command is:

```bash
opencode --mcp-list
```

## Step 5 — Set up your .env (optional, only for T03)

```bash
cp tutorials/.env.example tutorials/.env
$EDITOR tutorials/.env
```

Fill in whichever API key you have. T03 defaults to OpenRouter; if you only have a Google AI Studio key, override the model to `gemini/gemini-2.5-flash-preview-04-17` and set `GOOGLE_API_KEY`.

## Step 6 — Sanity check

```bash
# 1. Container running?
docker ps --filter name=gf180 --format '{{.Names}}'   # → gf180

# 2. eda-agents importable?
python -c "from eda_agents.core.designs.generic import GenericDesign; print('ok')"

# 3. Claude Code or opencode on PATH?
claude --version || opencode --version

# 4. MCP server registered?
ls .mcp.json opencode.json
```

If all four checks pass, open [`tutorials/01_counter_with_agent_tui/`](../01_counter_with_agent_tui/) and start.

## Troubleshooting

**`ModuleNotFoundError: eda_agents`** — your venv is not activated. `source ~/personal_exp/eda-agents/.venv/bin/activate` (or wherever you put it) and retry. Each notebook also has an opt-in `RUN_PIP_INSTALL` flag in step 0.

**`claude: command not found`** in T01 / T02 — install Claude Code (`npm install -g @anthropic-ai/claude-code`) **or** switch the tutorial to opencode by following the `opencode --agent ...` path documented in each tutorial's README.

**`opencode: command not found`** in T03 — install opencode (`npm install -g opencode-ai`). All four backends are pluggable in T03; if you have only `claude`, set `BACKEND="cc_cli"` and proceed.

**`eda-init: command not found`** — install eda-agents first (step 2). The console script comes with the package install.

**MCP server "disconnected" in Claude Code** — usually means the venv that has `eda-agents` installed is not on the path Claude Code uses to launch the server. Check `.mcp.json`:

```json
{
  "mcpServers": {
    "eda-agents": {
      "command": "/path/to/your/venv/bin/eda-mcp",
      "args": []
    }
  }
}
```

If `command` points at a venv that no longer exists, edit it or re-run `eda-init` from inside the active venv.

**Container not running** — `scripts/bootstrap_container.sh` from the repo root. Idempotent: if it is already running, the script no-ops.
