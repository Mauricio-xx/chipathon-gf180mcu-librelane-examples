#!/usr/bin/env python3
"""Tutorial 02 — Drive the counter via eda-agents Python API.

Headless twin of 02_counter_python_api.ipynb. Wraps a minimal LibreLane
config with `GenericDesign`, hands it to `ProjectManager` (multi-agent
hierarchy: SynthesisEngineer + PhysicalDesigner + VerificationEngineer
+ SignoffChecker), and runs the full RTL-to-GDS flow with the agent
choosing config knobs.

Default mode is **dry-run**: constructs the agent graph, prints the
prompt length and sub-agent topology, no LLM call. Flip `RUN_REAL=True`
for the real run (~10-15 minutes).

Backends:
    cc_cli (default) — Claude Code CLI subprocess. Free with a Claude.ai
        subscription. Needs `claude` on PATH and ~/.claude/ authenticated.
    adk             — Google ADK with LiteLLM provider. Needs an
        OPENROUTER_API_KEY (or GOOGLE_API_KEY).

Usage:
    python run_counter.py             # pauses between steps
    python run_counter.py --no-pause  # straight through
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


# ---------------------------------------------------------------------
# Toggles
# ---------------------------------------------------------------------
RUN_PIP_INSTALL = False   # pip install eda-agents into the active venv
RUN_DRY_PM      = True    # construct ProjectManager + dry-run (safe, free, ~5s)
RUN_REAL        = False   # full LibreLane flow via the agent (~10-15 min)

# When BACKEND="cc_cli" the agent is launched as `claude --print`. Each
# tool call (docker exec, file read, etc.) hits Claude Code's permission
# layer. In non-interactive subprocess mode there is no human to approve,
# so the agent will refuse / hang unless we pass --dangerously-skip-permissions.
# Double-gated for safety: must set BOTH `allow_dangerous=True` in the
# constructor AND export EDA_AGENTS_ALLOW_DANGEROUS=1 before running.
RUN_DANGEROUSLY = False   # only flip if you understand what cc_cli will be allowed to do

BACKEND   = "cc_cli"      # "cc_cli" (Claude subscription) | "adk" (API key)

# Backend-aware default model. cc_cli routes to `claude --print`, which
# only accepts Anthropic model IDs (claude-sonnet-4-6 etc.) -- passing a
# Google or OpenRouter ID returns API 404. adk and other backends route
# through LiteLLM and accept provider-prefixed IDs like
# "google/gemini-3-flash-preview".
_DEFAULT_MODEL = "claude-sonnet-4-6" if BACKEND == "cc_cli" else "google/gemini-3-flash-preview"
LLM_MODEL = os.environ.get("EDA_AGENTS_MODEL", _DEFAULT_MODEL)
MAX_BUDGET_USD = 1.00     # only meaningful for cc_cli (subscription is unlimited
                          # at fair-use; this caps individual sessions)

# ---------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------
try:
    NB_DIR = Path(__file__).resolve().parent
except NameError:
    NB_DIR = Path.cwd().resolve()

REPO_ROOT = NB_DIR.parents[1]                                  # chipathon repo root
HOST_WORKSPACE = Path.home() / "eda" / "designs" / "eda_agents_counter_pyapi"
WORK_DIR = NB_DIR / "rtl2gds_counter_pyapi_results"            # local agent log output
PROJ_DIR = HOST_WORKSPACE                                      # where staged files land

# eda-agents repo root: try common locations, fall back to env var.
EDA_AGENTS_ROOT = Path(
    os.environ.get(
        "EDA_AGENTS_ROOT",
        Path.home() / "personal_exp" / "eda-agents",
    )
).resolve()


def banner(step: int, title: str) -> None:
    line = "=" * 72
    print(f"\n{line}\nStep {step} | {title}\n{line}")


def pause(args) -> None:
    if args.no_pause:
        return
    try:
        input("  [enter] to continue, ctrl-c to stop ")
    except (EOFError, KeyboardInterrupt):
        sys.exit(0)


def step0_pip_install(args) -> None:
    banner(0, "venv + editable install of eda-agents")
    print(f"  Active python : {sys.executable}")
    print(f"  EDA_AGENTS_ROOT : {EDA_AGENTS_ROOT}")
    if "VIRTUAL_ENV" not in os.environ:
        print("  WARNING: no $VIRTUAL_ENV -- you should be in a venv.")
    if not EDA_AGENTS_ROOT.is_dir():
        print(f"  ERROR: EDA_AGENTS_ROOT does not exist; "
              f"clone https://github.com/Mauricio-xx/eda-agents into "
              f"{EDA_AGENTS_ROOT.parent} or set $EDA_AGENTS_ROOT.")
        sys.exit(1)
    cmd = [sys.executable, "-m", "pip", "install", "-e", f"{EDA_AGENTS_ROOT}[adk]"]
    print(f"  Command : {' '.join(cmd)}")
    if not RUN_PIP_INSTALL:
        print("  [rehearse] RUN_PIP_INSTALL=False; skipping.")
        return
    subprocess.run(cmd, check=True)
    pause(args)


def step1_preflight(args) -> None:
    banner(1, "pre-flight: docker, container, claude / opencode CLI, env keys")

    docker = shutil.which("docker")
    print(f"  docker on PATH         : {docker or 'MISSING'}")

    if docker:
        out = subprocess.run(
            ["docker", "ps", "--filter", "name=gf180", "--format", "{{.Names}}"],
            capture_output=True, text=True, timeout=10,
        )
        running = "gf180" in out.stdout.split()
        print(f"  gf180 container running: {running}")

    print(f"  claude CLI on PATH     : {shutil.which('claude') or 'MISSING (needed for cc_cli)'}")
    print(f"  opencode CLI on PATH   : {shutil.which('opencode') or 'MISSING (alt for cc_cli)'}")

    for key in ("OPENROUTER_API_KEY", "GOOGLE_API_KEY", "ZAI_API_KEY"):
        print(f"  {key:<22} : {'set' if os.environ.get(key) else 'unset'}")

    pause(args)


def step2_stage_workspace(args) -> None:
    banner(2, "stage rtl/ tb/ librelane/ to the host workspace")
    HOST_WORKSPACE.mkdir(parents=True, exist_ok=True)
    for sub in ("rtl", "tb", "librelane"):
        src = NB_DIR / sub
        dst = HOST_WORKSPACE / sub
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(src, dst)
        print(f"  staged {src.relative_to(REPO_ROOT)} -> {dst}")
    print(f"\n  Workspace : {HOST_WORKSPACE}")
    print(f"  Container : /foss/designs/eda_agents_counter_pyapi/")
    pause(args)


async def step3_construct_dry(args) -> None:
    banner(3, "construct ProjectManager + dry-run (no LLM call)")
    if not RUN_DRY_PM:
        print("  [rehearse] RUN_DRY_PM=False; skipping.")
        return
    try:
        from eda_agents.core.designs.generic import GenericDesign
        from eda_agents.agents.digital_adk_agents import ProjectManager
    except ImportError as exc:
        print(f"  ERROR: {exc}")
        print("  -> step 0 (pip install eda-agents) and retry.")
        return

    pdk_root = os.environ.get("PDK_ROOT") or None
    design = GenericDesign(
        config_path=str(HOST_WORKSPACE / "librelane" / "config.yaml"),
        pdk_root=pdk_root,
        pdk_config="gf180mcu",
    )
    pm = ProjectManager(
        design=design,
        model=LLM_MODEL,
        backend=BACKEND,
        max_budget_usd=MAX_BUDGET_USD,
        allow_dangerous=RUN_DANGEROUSLY,
    )
    result = await pm.run(WORK_DIR, dry_run=True)
    print(f"  design       : {design.project_name()}")
    print(f"  specs        : {design.specs_description()}")
    print(f"  FoM          : {design.fom_description()}")
    print(f"  backend      : {BACKEND}")
    print(f"  model        : {LLM_MODEL}")
    if BACKEND == "cc_cli":
        print(f"  prompt length: {result.get('prompt_length', 0)} chars")
    else:
        subs = result.get("sub_agent_names") or result.get("sub_agents") or []
        print(f"  master       : {result.get('master_agent', 'N/A')}")
        print(f"  sub-agents   : {', '.join(str(s) for s in subs)}")
    pause(args)


async def step4_real_run(args) -> None:
    banner(4, f"full RTL-to-GDS flow via {BACKEND} backend")
    if not RUN_REAL:
        print("  [rehearse] RUN_REAL=False; skipping.")
        print("  Flip RUN_REAL=True after the dry-run completes cleanly.")
        print(f"  Expected wall time: ~10-15 min for this counter.")
        print(f"  Artifacts will land under {WORK_DIR}")
        return

    if BACKEND == "cc_cli" and not (
        RUN_DANGEROUSLY and os.environ.get("EDA_AGENTS_ALLOW_DANGEROUS") == "1"
    ):
        print("  ERROR: cc_cli backend in non-interactive subprocess mode needs")
        print("  --dangerously-skip-permissions to call docker / file tools.")
        print("  Flip RUN_DANGEROUSLY=True at the top of this file AND export")
        print("  EDA_AGENTS_ALLOW_DANGEROUS=1 in your shell before re-running.")
        return

    from eda_agents.core.designs.generic import GenericDesign
    from eda_agents.agents.digital_adk_agents import ProjectManager

    pdk_root = os.environ.get("PDK_ROOT") or None
    design = GenericDesign(
        config_path=str(HOST_WORKSPACE / "librelane" / "config.yaml"),
        pdk_root=pdk_root,
        pdk_config="gf180mcu",
    )
    pm = ProjectManager(
        design=design,
        model=LLM_MODEL,
        backend=BACKEND,
        max_budget_usd=MAX_BUDGET_USD,
        allow_dangerous=RUN_DANGEROUSLY,
    )
    result = await pm.run(WORK_DIR)
    safe = {k: v for k, v in result.items() if k not in ("agent_output", "prompt")}
    print(json.dumps(safe, indent=2, default=str))


def step5_show_artifacts(args) -> None:
    banner(5, "inspect results")
    results = WORK_DIR / "rtl2gds_results.json"
    if results.exists():
        print(results.read_text()[:4000])
    else:
        print(f"{results} not yet written; run step 4 first.")


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--no-pause", action="store_true",
                        help="run straight through without enter-to-continue")
    args = parser.parse_args()

    step0_pip_install(args)
    step1_preflight(args)
    step2_stage_workspace(args)
    await step3_construct_dry(args)
    await step4_real_run(args)
    step5_show_artifacts(args)


if __name__ == "__main__":
    asyncio.run(main())
