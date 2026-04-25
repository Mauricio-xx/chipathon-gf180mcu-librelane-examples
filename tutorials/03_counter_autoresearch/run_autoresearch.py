#!/usr/bin/env python3
"""Tutorial 03 — Counter QoR autoresearch via eda-agents.

Headless twin of 03_counter_autoresearch.ipynb. Uses
`DigitalAutoresearchRunner` to iterate the agent over a discrete knob
space (PL_TARGET_DENSITY x CLOCK_PERIOD x PDN_VWIDTH), running 3
LibreLane evals (capped) and picking the best by FoM.

Default mode is dry-run (free, ~5 seconds). Flip RUN_REAL=True for the
real run: ~10-15 minutes wall time, ~$0.20-0.30 LLM spend with
opencode + Gemini Flash.

Usage:
    python run_autoresearch.py             # pauses between steps
    python run_autoresearch.py --no-pause  # straight through
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
RUN_PIP_INSTALL = False
RUN_DRY         = True
RUN_REAL        = False

BACKEND = "opencode"   # "opencode" (recommended) | "cc_cli" | "adk" | "litellm"
OPENCODE_MODEL = os.environ.get(
    "EDA_AGENTS_MODEL",
    "openrouter/google/gemini-3-flash-preview",
)
OPENCODE_CLI_PATH = "opencode"

# Capped at 3 for this tutorial to keep cost predictable. The eda-agents
# upstream demo uses 5; you can bump back up if you have budget headroom.
BUDGET = 3

# ---------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------
try:
    NB_DIR = Path(__file__).resolve().parent
except NameError:
    NB_DIR = Path.cwd().resolve()

REPO_ROOT = NB_DIR.parents[1]
HOST_WORKSPACE = Path.home() / "eda" / "designs" / "eda_agents_counter_autoresearch"
WORK_DIR = NB_DIR / "digital_autoresearch_results"
EDA_AGENTS_ROOT = Path(
    os.environ.get("EDA_AGENTS_ROOT", Path.home() / "personal_exp" / "eda-agents")
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
    print(f"  Active python   : {sys.executable}")
    print(f"  EDA_AGENTS_ROOT : {EDA_AGENTS_ROOT}")
    if "VIRTUAL_ENV" not in os.environ:
        print("  WARNING: no $VIRTUAL_ENV")
    if not RUN_PIP_INSTALL:
        print("  [rehearse] RUN_PIP_INSTALL=False; skipping.")
        return
    if not EDA_AGENTS_ROOT.is_dir():
        print(f"  ERROR: clone eda-agents into {EDA_AGENTS_ROOT.parent} or set $EDA_AGENTS_ROOT.")
        sys.exit(1)
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "-e", f"{EDA_AGENTS_ROOT}[adk]"],
        check=True,
    )
    pause(args)


def step1_env_check(args) -> None:
    banner(1, "docker + opencode CLI + provider key")
    print(f"  docker on PATH         : {shutil.which('docker') or 'MISSING'}")
    print(f"  opencode CLI on PATH   : {shutil.which(OPENCODE_CLI_PATH) or 'MISSING (npm i -g opencode-ai)'}")
    print(f"  claude CLI on PATH     : {shutil.which('claude') or 'MISSING (alt for cc_cli)'}")
    for key in ("OPENROUTER_API_KEY", "GOOGLE_API_KEY", "ZAI_API_KEY", "ANTHROPIC_API_KEY"):
        print(f"  {key:<22} : {'set' if os.environ.get(key) else 'unset'}")
    print(f"  selected backend       : {BACKEND}")
    if BACKEND == "opencode":
        print(f"  selected opencode model: {OPENCODE_MODEL}")
    print(f"  budget (LibreLane evals): {BUDGET}")
    pause(args)


def step2_stage_workspace(args) -> None:
    banner(2, "stage rtl/ + librelane/ to host workspace")
    HOST_WORKSPACE.mkdir(parents=True, exist_ok=True)
    for sub in ("rtl", "librelane"):
        src = NB_DIR / sub
        dst = HOST_WORKSPACE / sub
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(src, dst)
        print(f"  staged {src.relative_to(REPO_ROOT)} -> {dst}")
    print(f"\n  Workspace : {HOST_WORKSPACE}")
    pause(args)


async def step3_dry(args) -> None:
    banner(3, f"DigitalAutoresearchRunner dry-run (backend={BACKEND})")
    if not RUN_DRY:
        print("  [rehearse] RUN_DRY=False; skipping.")
        return
    try:
        from eda_agents.core.designs.generic import GenericDesign
        from eda_agents.agents.digital_autoresearch import DigitalAutoresearchRunner
    except ImportError as exc:
        print(f"  ERROR: {exc}")
        return

    design = GenericDesign(
        config_path=str(HOST_WORKSPACE / "librelane" / "config.yaml"),
        pdk_root=os.environ.get("PDK_ROOT") or None,
        pdk_config="gf180mcu",
    )
    kwargs = dict(design=design, backend=BACKEND, budget=BUDGET)
    if BACKEND == "opencode":
        kwargs.update(opencode_cli_path=OPENCODE_CLI_PATH, opencode_model=OPENCODE_MODEL)
    runner = DigitalAutoresearchRunner(**kwargs)

    print(f"  design  : {design.project_name()}")
    print(f"  specs   : {design.specs_description()}")
    print(f"  FoM     : {design.fom_description()}")
    print(f"  budget  : {BUDGET} LibreLane evaluations")
    print(f"  knobs   : PL_TARGET_DENSITY x CLOCK_PERIOD x PDN_VWIDTH")
    print(f"  backend : {BACKEND}")
    if BACKEND == "opencode":
        print(f"  model   : {OPENCODE_MODEL}")
    print(f"  WORK_DIR: {WORK_DIR}")
    pause(args)


async def step4_real(args) -> None:
    banner(4, f"real run (~{BUDGET} LibreLane evals; ~$0.20-0.30)")
    if not RUN_REAL:
        print("  [rehearse] RUN_REAL=False; skipping.")
        print("  Flip RUN_REAL=True after dry-run + env check are clean.")
        print(f"  Expected wall time: 10-15 min for budget={BUDGET}.")
        print(f"  Cost: ~$0.20-0.30 with opencode + Gemini Flash.")
        return

    from eda_agents.core.designs.generic import GenericDesign
    from eda_agents.agents.digital_autoresearch import DigitalAutoresearchRunner

    design = GenericDesign(
        config_path=str(HOST_WORKSPACE / "librelane" / "config.yaml"),
        pdk_root=os.environ.get("PDK_ROOT") or None,
        pdk_config="gf180mcu",
    )
    kwargs = dict(design=design, backend=BACKEND, budget=BUDGET)
    if BACKEND == "opencode":
        kwargs.update(opencode_cli_path=OPENCODE_CLI_PATH, opencode_model=OPENCODE_MODEL)
    runner = DigitalAutoresearchRunner(**kwargs)

    result = await runner.run(WORK_DIR)
    safe = {k: v for k, v in result.__dict__.items() if not k.startswith("_")}
    print(json.dumps(safe, indent=2, default=str))


def step5_inspect(args) -> None:
    banner(5, "inspect program.md + results.tsv")
    for fname in ("program.md", "results.tsv"):
        p = WORK_DIR / fname
        if p.exists():
            print(f"--- {p} ---")
            print(p.read_text()[:3000])
            print()
        else:
            print(f"{p} not yet written; run step 4 first.")


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--no-pause", action="store_true")
    args = parser.parse_args()

    step0_pip_install(args)
    step1_env_check(args)
    step2_stage_workspace(args)
    await step3_dry(args)
    await step4_real(args)
    step5_inspect(args)


if __name__ == "__main__":
    asyncio.run(main())
