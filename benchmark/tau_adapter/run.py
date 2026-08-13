#!/usr/bin/env python3
"""Run τ²-bench against the target-agent Recipe.

τ² has no entry point for third-party agents — `registry.py` exposes only
`register_agent_factory`, and the `tau2` CLI resolves `--agent` from what is registered at
import time. So this module is the runner: it registers the seam, builds the run config
entirely from benchmark_lock.yaml, and hands off to τ's own `run_domain`.

Reward is never computed here. `run_domain` grades with τ's evaluator, and the number that
gets reported comes from `tau2 evaluate-trajs` over the saved trajectories.

Two modes, and the distinction is load-bearing:

  locked      --domain equals the locked domain. Uses the committed Recipe as-is and asserts
              its <policy> region against the live environment. The only mode whose numbers
              may be reported.
  diagnostic  --domain is anything else. The committed Recipe carries the locked domain's
              policy, so a different domain needs a different system prompt; the Recipe is
              materialised into a throwaway workspace with that policy substituted. Used for
              seam bring-up and, later, for the Phase A.0 fidelity gate on `mock`. Results
              are not comparable to anything and must not be reported as a score.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tau_adapter import lock as lockmod
from tau_adapter.pi_agent import PiRecipeAgent
from tau_adapter.policy_region import extract_policy, replace_policy
from tau_adapter.tool_bridge import ToolBridge
from tau_adapter.transport_local import LAUNCHER_CLI, LAUNCHER_PI, LAUNCHERS, LocalPiTransport

AGENT_KEY = "pi_recipe"

# Gitignored, and inside the work tree on purpose — see _materialise_workspace.
DIAGNOSTIC_WORKSPACE = lockmod.REPO_ROOT / ".diagnostic-workspace"


def _materialise_workspace(policy: str) -> tuple[Path, Path]:
    """Build a throwaway workspace holding the Recipe with a different domain's policy.

    Diagnostic mode only. Never used for the locked domain, where the Recipe that runs must
    be the Recipe that was committed — otherwise runtime↔commit lineage means nothing, and
    the development lane (which serves the git work-tree) could not run at all.

    A *workspace*, not just a Recipe directory, because `introspection local` resolves the
    Recipe through the `.introspection/` Runtime manifest it finds by walking up from
    `--work-dir`. It lands inside the repository rather than under `/tmp` for a subtler
    reason: the CLI validates the Recipe before launching, and one of its rules is that local
    capability config must not ship with a Recipe. `.pi/mcp.local.json` satisfies that rule by
    being gitignored, and gitignore only applies inside a work tree — the same copy under
    `/tmp` fails validation.

    Returns (workspace root, recipe directory).
    """
    workspace = DIAGNOSTIC_WORKSPACE
    if workspace.exists():
        shutil.rmtree(workspace)
    (workspace / ".introspection").mkdir(parents=True)
    shutil.copy2(lockmod.RUNTIME_MANIFEST, workspace / ".introspection")
    recipe = workspace / lockmod.RECIPE_DIR.name
    shutil.copytree(lockmod.RECIPE_DIR, recipe)
    system_md = recipe / "SYSTEM.md"
    system_md.write_text(
        replace_policy(system_md.read_text(encoding="utf-8"), policy), encoding="utf-8"
    )
    return workspace, recipe


def _tool_version(executable: str, *args: str) -> str:
    """Best-effort version string. Unknown is reported, never guessed or silently omitted."""
    try:
        proc = subprocess.run(  # noqa: S603
            [executable, *args], capture_output=True, text=True, timeout=30, check=False
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return f"unavailable ({type(exc).__name__})"
    line = (proc.stdout or proc.stderr).strip().splitlines()
    return line[0].strip() if line else "unknown"


def _launcher_description(launcher: str) -> str:
    """What actually starts the Recipe, with the versions that decide how it behaves."""
    pi_version = _tool_version("pi", "--version")
    if launcher == LAUNCHER_CLI:
        return (
            f"introspection local ({_tool_version('introspection', '--version')}) → pi {pi_version}"
        )
    return f"pi {pi_version} directly (Recipe resolved by path, not by Runtime manifest)"


def _assert_recipe_valid() -> None:
    """Run `introspection check` once per run, before any episode is spent.

    The default `pi` launcher addresses the Recipe by path, so nothing on the hot path would
    otherwise notice a malformed Recipe — Pi would start, behave differently, and produce a
    score. That is the one failure this experiment cannot tolerate quietly: an invalid harness
    still gets graded, and the number looks like every other number.

    Once per run rather than once per episode. The CLI launcher validates on every episode; the
    checked artefact cannot change mid-run, so the extra 5.5s buys nothing there either.
    """
    try:
        # S607: `introspection` is resolved from PATH deliberately — the operator's installed
        # CLI is the one that must validate the Recipe, not a path this file guesses at.
        proc = subprocess.run(
            ["introspection", "check", "-o", "report"],  # noqa: S607
            cwd=lockmod.REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=180,
            check=False,
        )
    except FileNotFoundError as exc:
        raise SystemExit(
            "`introspection` is not on PATH. It is how the Recipe is validated, so a run "
            "cannot proceed without it — see `make bootstrap`."
        ) from exc
    if proc.returncode != 0:
        raise SystemExit(
            "`introspection check` rejected the Recipe, so no episode was run:\n"
            f"{(proc.stdout or '') + (proc.stderr or '')}"
        )


def _build_env_for_pi() -> dict[str, str]:
    env = dict(os.environ)
    # One fewer network round trip per episode; nothing else about Pi's behaviour changes.
    env.setdefault("PI_SKIP_VERSION_CHECK", "1")
    return env


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--domain",
        default=None,
        help="τ domain. Defaults to the locked domain; anything else runs in diagnostic mode.",
    )
    parser.add_argument(
        "--task-ids",
        nargs="+",
        default=None,
        help="τ task ids to run. Omit to run the whole locked task split.",
    )
    parser.add_argument(
        "--out",
        required=True,
        help="directory for τ's results.json and per-simulation logs",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="replace an existing --out directory instead of refusing",
    )
    parser.add_argument(
        "--launcher",
        choices=LAUNCHERS,
        default=LAUNCHER_PI,
        help=(
            "how to start the Recipe. 'pi' (default) spawns Pi directly. 'introspection' goes "
            "through `introspection local`, which resolves the Recipe through the Runtime "
            "manifest and validates it per episode, at about +5.5s each."
        ),
    )
    args = parser.parse_args()

    lock = lockmod.load_lock()
    lockmod.assert_vendor_commit(lock)
    lockmod.assert_recipe_matches_lock(lock)
    _assert_recipe_valid()

    domain = args.domain or lock.domain
    locked_mode = domain == lock.domain

    from tau2.data_model.simulation import TextRunConfig
    from tau2.metrics.agent_metrics import compute_metrics
    from tau2.registry import registry
    from tau2.runner import get_tasks, run_tasks
    from tau2.utils.display import ConsoleDisplay

    retrieval = lock.retrieval_config if locked_mode else None
    env_kwargs = {"retrieval_variant": retrieval} if retrieval else {}
    probe_env = registry.get_env_constructor(domain)(**env_kwargs)
    live_policy = probe_env.get_policy()
    live_tools = [t.name for t in probe_env.get_tools()]

    if locked_mode:
        lockmod.assert_tool_catalog(lock, live_tools)
        workspace_dir = lockmod.REPO_ROOT
        recipe_dir = lockmod.RECIPE_DIR
        recipe_policy = extract_policy(lockmod.RECIPE_SYSTEM_MD.read_text(encoding="utf-8"))
    else:
        workspace_dir, recipe_dir = _materialise_workspace(live_policy)
        recipe_policy = extract_policy((recipe_dir / "SYSTEM.md").read_text(encoding="utf-8"))

    out_dir = Path(args.out).resolve()
    if out_dir.exists() and any(out_dir.iterdir()):
        if not args.overwrite:
            raise SystemExit(
                f"{out_dir} already holds a run. Pass --overwrite to replace it, or point "
                "--out at a new directory — a previous generation's record is not scratch."
            )
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    results_path = out_dir / "results.json"
    session_dir = out_dir / "pi_sessions"
    base_env = _build_env_for_pi()
    launch_argv: list[str] = []

    def create_agent(tools, domain_policy, **kwargs):
        declared = kwargs.get("llm")
        if declared is not None and declared != lock.agent_llm_declared:
            raise lockmod.LockError(
                f"--agent-llm is {declared!r} but the lock declares {lock.agent_llm_declared!r}"
            )
        bridge = ToolBridge(tau_tools=tools)
        transport = LocalPiTransport(
            recipe_dir=recipe_dir,
            session_dir=session_dir,
            launcher=args.launcher,
            workspace_dir=workspace_dir,
        )
        launch_argv[:] = transport.argv()
        return PiRecipeAgent(
            tools=tools,
            domain_policy=domain_policy,
            bridge=bridge,
            transport=transport,
            recipe_policy=recipe_policy,
            domain=domain,
            base_env=base_env,
        )

    registry.register_agent_factory(create_agent, AGENT_KEY)

    config = TextRunConfig(
        domain=domain,
        agent=AGENT_KEY,
        llm_agent=lock.agent_llm_declared,
        llm_args_agent={},
        user="user_simulator",
        llm_user=lock.user_llm,
        llm_args_user=lock.user_llm_args,
        task_set_name=lock.task_set_name if locked_mode else None,
        task_split_name=lock.task_split_name if locked_mode else None,
        task_ids=args.task_ids,
        num_trials=lock.num_trials,
        seed=lock.seed,
        max_steps=lock.max_steps,
        max_errors=lock.max_errors,
        timeout=lock.timeout_seconds,
        max_concurrency=lock.max_concurrency,
        enforce_communication_protocol=lock.enforce_communication_protocol,
        # Left unset deliberately. `run_domain` turns save_to into a run *name* under
        # TAU2_DATA_DIR/simulations/, which would write results into the pinned vendor
        # checkout. Dropping to run_tasks lets the path stay in results/ where a generation's
        # record belongs.
        save_to=None,
        retrieval_config=retrieval,
    )

    banner = "locked" if locked_mode else "DIAGNOSTIC — results are not reportable"
    print(f"\n── tau-adapter: {domain} [{banner}]")
    print(f"   recipe        {recipe_dir}")
    print(f"   launcher      {_launcher_description(args.launcher)}")
    print(f"   agent model   {lock.agent_model} (thinking: {lock.agent_thinking_level})")
    print(f"   user model    {lock.user_llm}")
    print(f"   retrieval     {retrieval or 'default/none'}")
    print(f"   τ tools       {len(live_tools)}")
    config.validate()
    tasks = get_tasks(
        task_set_name=config.task_set_name or domain,
        task_split_name=config.task_split_name,
        task_ids=list(args.task_ids) if args.task_ids else None,
    )

    selection = ", ".join(args.task_ids) if args.task_ids else f"whole split ({len(tasks)} tasks)"
    print(f"   tasks         {selection} in {lock.num_trials} trial(s)")
    if lock.provisional:
        print("   lock status   PROVISIONAL — not an experiment freeze")
    if not args.task_ids:
        # A full sweep is the expensive path and max_concurrency is frozen at 1, so it runs
        # serially. Say what that costs before spending it rather than after.
        episodes = len(tasks) * lock.num_trials
        print(
            f"\n   full sweep: {episodes} episode(s) at max_concurrency="
            f"{lock.max_concurrency}. Raising concurrency needs a lock change; the bridge "
            "binds a port per episode and should support it, but that is untested."
        )
    print()

    started = time.monotonic()
    results = run_tasks(config, tasks, save_path=results_path, save_dir=out_dir)
    elapsed = time.monotonic() - started

    # Beside τ's results, never inside them: τ owns its own schema. Two launchers produce
    # identically-shaped results, so without this a run directory cannot say which one made it
    # — and "label every score with its configuration" has to survive past the terminal.
    (out_dir / "run_metadata.json").write_text(
        json.dumps(
            {
                "mode": "locked" if locked_mode else "diagnostic",
                "domain": domain,
                "launcher": args.launcher,
                "launch_argv": launch_argv,
                "recipe_dir": str(recipe_dir),
                "toolchain": {
                    "introspection": _tool_version("introspection", "--version"),
                    "pi": _tool_version("pi", "--version"),
                },
                "elapsed_seconds": round(elapsed, 1),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    ConsoleDisplay.display_agent_metrics(compute_metrics(results))
    print(f"\n── {len(results.simulations)} simulation(s) in {elapsed:.0f}s → {results_path}")
    for sim in results.simulations:
        reward = getattr(getattr(sim, "reward_info", None), "reward", None)
        print(
            f"   {sim.task_id}: termination={sim.termination_reason} "
            f"messages={len(sim.messages)} reward={reward}"
        )
    print(
        "\n   Reward above is tau's own in-run evaluation. The reported number comes from\n"
        f"   `tau2 evaluate-trajs {results_path}`."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
