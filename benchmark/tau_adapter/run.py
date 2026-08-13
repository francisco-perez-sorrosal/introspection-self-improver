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

A round ends with three artifacts, not one: τ's `results.json`, the runner's
`run_metadata.json` (the completion sentinel — written only after τ's runner returned), and
`episode_manifest.jsonl`, one row per (task, trial) joining the episode to its platform
conversation, lineage, cost, completeness and incident counters. The manifest is what
`operate` receives at the top of a generation (v2 §5.1).
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
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tau_adapter import lock as lockmod
from tau_adapter import manifest as manifestmod
from tau_adapter import split as splitmod
from tau_adapter.dev_lane import (
    DevAttachment,
    assert_no_connected_binding,
    resolve_runtime_id,
    warm_runtime,
)
from tau_adapter.experiment import (
    enforce_snapshot,
    generation_of,
    prepare_round_dir,
    repo_arm_state,
)
from tau_adapter.pi_agent import PiRecipeAgent
from tau_adapter.policy_region import extract_policy, replace_policy
from tau_adapter.tool_bridge import ToolBridge
from tau_adapter.transport_local import LAUNCHER_CLI, LAUNCHER_PI, LAUNCHERS, LocalPiTransport
from tau_adapter.transport_platform import PlatformTransport

AGENT_KEY = "pi_recipe"

TRANSPORT_LOCAL = "local"
TRANSPORT_PLATFORM = "platform"
TRANSPORTS = (TRANSPORT_LOCAL, TRANSPORT_PLATFORM)
DEFAULT_RUNTIME = "target-agent"

# The runnable splits. `test` is deliberately absent: the held-out enforcement decision
# (split_manifest.yaml header) makes test-split inspection procedural-only, and the cheapest
# way to keep the procedure honest is for the runner to have no button for it. Test tasks are
# exercised only inside the full-domain checkpoint.
RUNNABLE_SPLITS = ("discovery", "validation")

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


def _cli_json(args: list[str], timeout: float) -> Any:
    proc = subprocess.run(  # noqa: S603
        ["introspection", *args, "-o", "json"],  # noqa: S607
        cwd=lockmod.REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError((proc.stderr or proc.stdout).strip()[:300])
    return json.loads(proc.stdout)


def _account_of(item: dict[str, Any]) -> tuple[str | None, dict[str, Any]]:
    """One conversation export → (id, accounting fields). Tolerant of single/batch shapes."""
    conversation = item.get("conversation") or item
    meta = item.get("meta") or {}
    account = {
        key: conversation.get(key) for key in ("cost", "usage", "metrics", "recipe_git_commit_sha")
    }
    # Recorded rather than assumed. "The episode finished" is otherwise an inference from the
    # reward, and a reward can be produced while the conversation is still open — the export
    # says so itself, and `complete: false` means this record is a snapshot of something that
    # had not settled when it was read.
    account["evidence_complete"] = meta.get("complete")
    account["item_count"] = meta.get("item_count")
    identity = conversation.get("id") or conversation.get("conversation_id")
    return (str(identity) if identity else None), account


def _platform_accounting(task_ids: list[str]) -> dict[str, Any]:
    """Read cost, usage and lineage back out of the platform for each episode.

    The platform lane leaves τ's own cost metric as `nan`, because AG-UI events carry no token
    usage — the numbers live on the conversation record instead. Fetching them here keeps a
    generation's record self-contained rather than only reproducible by hand, and picks up the
    lineage field the local lane has no equivalent for.

    Pulled in batches of 20 — the CLI's own per-call ceiling — because at sweep scale one
    ~5.5s CLI startup per episode would spend eleven minutes on a 120-episode round. Ids the
    batch response does not name fall back to a per-id call rather than silently vanishing.
    """
    accounting: dict[str, Any] = {}
    remaining = list(task_ids)
    for start in range(0, len(remaining), 20):
        chunk = remaining[start : start + 20]
        try:
            payload = _cli_json(["conversations", "get", *chunk], timeout=180)
        except (OSError, subprocess.SubprocessError, json.JSONDecodeError, RuntimeError):
            continue  # the per-id fallback below covers the whole chunk
        items = payload if isinstance(payload, list) else [payload]
        for item in items:
            if not isinstance(item, dict):
                continue
            identity, account = _account_of(item)
            if identity in chunk:
                accounting[identity] = account
    for task_id in task_ids:
        if task_id in accounting:
            continue
        try:
            identity, account = _account_of(
                _cli_json(["conversations", "get", task_id], timeout=120)
            )
            accounting[task_id] = account
        except (OSError, subprocess.SubprocessError, json.JSONDecodeError, RuntimeError) as exc:
            accounting[task_id] = {"error": f"{type(exc).__name__}: {exc}"[:200]}
    return accounting


def _retitle_episodes(
    payload: dict[str, Any],
    domain: str,
    generation: str | None,
    experiment_id: str,
) -> tuple[dict[str, str], int]:
    """Post-run label pass: name every platform task after the τ episode it served.

    The agent factory never learns which simulation it serves, so a sweep's tasks are titled
    with the domain alone at episode end. Ground truth arrives only when τ's runner returns —
    each simulation's raw_data names its task — so the labels are applied here, from the
    record, rather than guessed during the run (the retitle works on archived rows). One CLI
    call per episode; failures are counted, never fatal, and never touch the score.
    """
    gen_short = ""
    if generation and generation.startswith("generation_"):
        gen_short = f" gen{generation.removeprefix('generation_')}"
    labels: dict[str, str] = {}
    failed = 0
    for sim in payload.get("simulations") or []:
        ref = manifestmod.session_ref_of(sim)
        if not ref:
            continue
        label = (
            f"τ²-bench {domain} {sim.get('task_id')} trial{sim.get('trial')}"
            f"{gen_short} [exp:{experiment_id}]"
        )
        try:
            _cli_json(["tasks", "update", ref, "--title", label], timeout=60)
            labels[ref] = label
        except (OSError, subprocess.SubprocessError, json.JSONDecodeError, RuntimeError):
            failed += 1
    return labels, failed


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
        "--split",
        choices=RUNNABLE_SPLITS,
        default=None,
        help=(
            "run a frozen split from benchmark/split_manifest.yaml (verified before any "
            "episode is spent). `test` is deliberately not runnable here — the held-out "
            "boundary is procedural, and the runner refuses to offer a button for it; test "
            "tasks run only inside --checkpoint."
        ),
    )
    parser.add_argument(
        "--checkpoint",
        action="store_true",
        help=(
            "the full-domain checkpoint: every task in the locked split at ONE trial — the "
            "H2 decision trades the ×4 number's strength for a quarter of its cost, and the "
            "result is labeled single-trial wherever it is reported. Its output includes "
            "test-split tasks; per the enforcement decision, do not inspect those episodes."
        ),
    )
    parser.add_argument(
        "--out",
        required=True,
        help="directory for τ's results.json and per-simulation logs",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help=(
            "replace an existing --out directory instead of refusing. Without it, a "
            "directory holding results.json but no run_metadata.json is an interrupted run "
            "and resumes: τ re-runs only the missing (trial, task, seed) pairs."
        ),
    )
    parser.add_argument(
        "--allow-dirty",
        action="store_true",
        help=(
            "run the platform lane despite uncommitted changes on the served recipe surface. "
            "The dirt is recorded prominently and every manifest row's arm_sha_ok is false — "
            "for debugging only, never for a round that will be cited."
        ),
    )
    parser.add_argument(
        "--transport",
        choices=TRANSPORTS,
        default=TRANSPORT_LOCAL,
        help=(
            "where the agent runs. 'local' (default) is a Pi subprocess on this machine and "
            "produces no Introspection evidence. 'platform' runs each episode as a task in the "
            "development environment, which yields conversations, traces and lineage, and starts "
            "`introspection dev` itself to route the τ bridge back here."
        ),
    )
    parser.add_argument(
        "--runtime",
        default=DEFAULT_RUNTIME,
        help="Runtime name to resolve for --transport platform (TAU_RUNTIME_ID overrides the id)",
    )
    parser.add_argument(
        "--environment",
        default="development",
        choices=("development", "staging", "production"),
        help="platform environment. Only development serves the local work-tree via `dev`.",
    )
    parser.add_argument(
        "--bridge-port",
        type=int,
        default=0,
        help=(
            "loopback port for the τ MCP bridge. 0 (default) takes an ephemeral one, which is "
            "fine because the runner starts the bridge before anything needs its URL. Pin it "
            "only to point a hand-started `introspection dev --mcp` at a known address."
        ),
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

    if args.split and args.task_ids:
        raise SystemExit("--split and --task-ids are mutually exclusive")
    if args.checkpoint and (args.split or args.task_ids):
        raise SystemExit("--checkpoint runs the whole locked split; drop --split/--task-ids")

    lock = lockmod.load_lock()
    lockmod.assert_vendor_commit(lock)
    lockmod.assert_recipe_matches_lock(lock)
    _assert_recipe_valid()

    domain = args.domain or lock.domain
    locked_mode = domain == lock.domain
    if (args.split or args.checkpoint) and not locked_mode:
        raise SystemExit("--split/--checkpoint are experiment rounds; they run the locked domain")

    # Resolve what runs and at how many trials. A split round refuses to start on a manifest
    # that fails verification — a broken split silently narrows every claim built on it.
    split_name: str | None = None
    task_ids: list[str] | None = args.task_ids
    num_trials = lock.num_trials
    if args.split:
        split_name = args.split
        manifest_doc = splitmod.load_manifest()
        problems = splitmod.verify(manifest_doc, splitmod.load_task_rows(lock.domain), lock.domain)
        if problems:
            raise SystemExit(
                "split manifest failed verification; no episode was spent:\n  "
                + "\n  ".join(problems)
            )
        task_ids = list(manifest_doc[args.split])
    elif args.checkpoint:
        split_name = "checkpoint"
        task_ids = None
        num_trials = 1  # H2 decision: the recognizable 97-task number at ×1, labeled single-trial

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

    # The arm this run serves. `introspection dev` serves the work-tree while lineage names
    # the base commit, so a dirty served surface makes every arm claim soft (v2 §4 W3.3):
    # the platform lane refuses it outright unless --allow-dirty records it prominently.
    arm_sha, dirty_paths = repo_arm_state() if locked_mode else (None, [])
    if args.transport == TRANSPORT_PLATFORM and dirty_paths and not args.allow_dirty:
        raise SystemExit(
            "the served recipe surface has uncommitted changes, so lineage would name a "
            "commit that is not what runs. Commit them, or pass --allow-dirty for a "
            "debugging run whose rows are marked arm_sha_ok=false:\n  " + "\n  ".join(dirty_paths)
        )

    out_dir = Path(args.out).resolve()
    # Before --overwrite can delete anything: a run aimed at the wrong experiment directory
    # must refuse here rather than clear another freeze's record first. Also verifies — or,
    # for a non-PROVISIONAL lock, creates — the experiment's freeze snapshot.
    experiment_status = enforce_snapshot(lock, out_dir)
    round_status = prepare_round_dir(out_dir, args.overwrite)
    generation = generation_of(out_dir)
    results_path = out_dir / "results.json"
    session_dir = out_dir / "pi_sessions"
    base_env = _build_env_for_pi()
    launch_argv: list[str] = []

    # Run-scoped, not per-episode. The development lane hands one URL to `introspection dev`
    # before the first episode and holds it for the whole run, so the bridge has to outlive an
    # episode. Built from the probe environment's tools because the schemas are what it
    # advertises, and the tool surface is asserted identical to the lock.
    bridge = ToolBridge(tau_tools=probe_env.get_tools(), port=args.bridge_port)
    bridge.start()

    dev: DevAttachment | None = None
    runtime_id: str | None = None
    if args.transport == TRANSPORT_PLATFORM:
        if not locked_mode:
            raise SystemExit(
                "the platform transport serves the Recipe from the git work-tree, so it cannot "
                "run diagnostic mode: that materialises a modified Recipe elsewhere. Use "
                "--transport local for a non-locked domain."
            )
        runtime_id = resolve_runtime_id(args.runtime, lockmod.REPO_ROOT)
        assert_no_connected_binding(runtime_id, args.environment, lockmod.REPO_ROOT)
        dev = DevAttachment(
            mcp_url=bridge.url, repo_root=lockmod.REPO_ROOT, runtime_name=args.runtime
        )
        dev.start()
        # Before the first episode, never during one.
        warm_runtime(
            runtime_id=runtime_id,
            environment=args.environment,
            repo_root=lockmod.REPO_ROOT,
            dev_target=dev.dev_target,
        )

    # What a platform task row reads as while its episode is still running. A sweep cannot
    # name the specific τ task at creation time (the factory does not learn which simulation
    # it serves), so this is the during-run fallback; the post-run retitle pass upgrades every
    # row to `<domain> <task> trial<k> gen<NNN>` from τ's own record once it exists. The
    # experiment suffix keeps platform evidence separable even where two experiments share a
    # recipe commit — e.g. a user-simulator-only change.
    episode_label = (
        f"τ²-bench {domain}"
        + (f" {task_ids[0]}" if task_ids and len(task_ids) == 1 else "")
        + f" [exp:{lock.experiment_id}]"
    )

    # Every transport constructed, one per episode *attempt*. This is the queue-tolerant side
    # of the accounting: τ retries infrastructure errors and keeps only the final attempt, so
    # the platform tasks a run created can exceed the episodes its results file names — the
    # difference is the orphan count, and it must be visible (v2 §4 W3.5). The registry also
    # lets the shutdown path archive whatever is still open, so an interrupted sweep does not
    # leave a sandbox idling toward its timeout (W5.3); close() is idempotent.
    episode_transports: list[Any] = []

    def create_agent(tools, domain_policy, **kwargs):
        declared = kwargs.get("llm")
        if declared is not None and declared != lock.agent_llm_declared:
            raise lockmod.LockError(
                f"--agent-llm is {declared!r} but the lock declares {lock.agent_llm_declared!r}"
            )
        transport: Any
        if args.transport == TRANSPORT_PLATFORM:
            assert runtime_id is not None
            transport = PlatformTransport(
                runtime_id=runtime_id,
                repo_root=lockmod.REPO_ROOT,
                environment=args.environment,
                # Must exceed the gap while τ's user simulator thinks (2-12s healthy, up to its
                # 60s per-attempt ceiling plus retries), or the sandbox is torn down mid-episode.
                idle_timeout_seconds=int(lock.timeout_seconds),
                dev_target=dev.dev_target if dev else None,
                episode_label=episode_label,
            )
            launch_argv[:] = ["introspection", "tasks", "create", "--runtime-id", runtime_id]
        else:
            transport = LocalPiTransport(
                recipe_dir=recipe_dir,
                session_dir=session_dir,
                launcher=args.launcher,
                workspace_dir=workspace_dir,
            )
            launch_argv[:] = transport.argv()
        episode_transports.append(transport)
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
        task_ids=task_ids,
        num_trials=num_trials,
        seed=lock.seed,
        max_steps=lock.max_steps,
        max_errors=lock.max_errors,
        timeout=lock.timeout_seconds,
        max_concurrency=lock.max_concurrency,
        enforce_communication_protocol=lock.enforce_communication_protocol,
        # τ's own checkpointing, adopted rather than reimplemented (v2 §4 W5.1): results.json
        # is written incrementally, and a rerun into the same directory resumes from it,
        # re-running only missing (trial, task, seed) tuples and replacing infrastructure-
        # error placeholders. auto_resume keeps that path non-interactive; prepare_round_dir
        # decides above whether resuming is the right meaning for this directory.
        auto_resume=True,
        # Left unset deliberately. `run_domain` turns save_to into a run *name* under
        # TAU2_DATA_DIR/simulations/, which would write results into the pinned vendor
        # checkout. Dropping to run_tasks lets the path stay in results/ where a generation's
        # record belongs.
        save_to=None,
        retrieval_config=retrieval,
    )

    banner = "locked" if locked_mode else "DIAGNOSTIC — results are not reportable"
    print(f"\n── tau-adapter: {domain} [{banner}]")
    print(
        f"   experiment    {lock.experiment_id}"
        + (f" — {experiment_status}" if experiment_status else "")
    )
    if round_status:
        print(f"   round         {round_status}")
    print(f"   recipe        {recipe_dir}")
    if arm_sha:
        dirt = (
            f" — DIRTY served surface ({len(dirty_paths)} path(s), --allow-dirty)"
            if dirty_paths
            else ""
        )
        print(f"   arm           {arm_sha[:12]}{dirt}")
    print(f"   transport     {args.transport}")
    if args.transport == TRANSPORT_PLATFORM:
        print(f"   runtime       {args.runtime} ({runtime_id}) in {args.environment}")
        print(f"   dev target    {dev.dev_target if dev else '(none)'}")
    else:
        print(f"   launcher      {_launcher_description(args.launcher)}")
    print(f"   τ bridge      {bridge.url.rsplit('/', 1)[0]}/<token>")
    print(f"   agent model   {lock.agent_model} (thinking: {lock.agent_thinking_level})")
    print(f"   user model    {lock.user_llm}")
    print(f"   retrieval     {retrieval or 'default/none'}")
    print(f"   τ tools       {len(live_tools)}")
    config.validate()
    tasks = get_tasks(
        task_set_name=config.task_set_name or domain,
        task_split_name=config.task_split_name,
        task_ids=list(task_ids) if task_ids else None,
    )

    if split_name and split_name != "checkpoint":
        selection = f"{split_name} split ({len(tasks)} tasks)"
    elif args.checkpoint:
        selection = f"full-domain checkpoint ({len(tasks)} tasks, ×1 trial by decision)"
    elif task_ids:
        selection = ", ".join(task_ids)
    else:
        selection = f"whole split ({len(tasks)} tasks)"
    print(f"   tasks         {selection} in {num_trials} trial(s)")
    if lock.provisional:
        print("   lock status   PROVISIONAL — not an experiment freeze")
    if len(tasks) * num_trials > 20:
        # A sweep is the expensive path and max_concurrency is frozen at 1, so it runs
        # serially. Say what that costs before spending it rather than after.
        episodes = len(tasks) * num_trials
        print(
            f"\n   sweep: {episodes} episode(s) at max_concurrency="
            f"{lock.max_concurrency}, serial. An interruption is safe: rerunning the same "
            "--out resumes and re-spends nothing."
        )
    print()

    started = time.monotonic()
    try:
        results = run_tasks(config, tasks, save_path=results_path, save_dir=out_dir)
    finally:
        # Reverse acquisition order, and everything best-effort. Closing the transports first
        # archives any task an interrupted episode left open — otherwise its sandbox idles
        # against the org concurrency limit until the platform's timeout backstop fires.
        for transport in episode_transports:
            try:
                transport.close()
            except Exception:  # noqa: BLE001 - shutdown must not mask the real failure
                pass
        if dev is not None:
            dev.stop()
        bridge.stop()
    elapsed = time.monotonic() - started
    episode_summaries = [manifestmod.episode_summary(sim) for sim in results.simulations]

    # Post-run evidence pass, all from the record τ just wrote: per-episode labels, batched
    # accounting, the manifest, and the arm assertion. Everything below reads results.json
    # rather than in-memory state so that what it derives is exactly what a later reader sees.
    payload = json.loads(results_path.read_text(encoding="utf-8")) if results_path.exists() else {}
    is_platform = args.transport == TRANSPORT_PLATFORM

    labels: dict[str, str] = {}
    retitle_failures = 0
    accounting: dict[str, Any] = {}
    if is_platform:
        labels, retitle_failures = _retitle_episodes(
            payload, domain, generation, lock.experiment_id
        )
        referenced = sorted(
            {
                ref
                for sim in payload.get("simulations") or []
                if (ref := manifestmod.session_ref_of(sim))
            }
        )
        accounting = _platform_accounting(referenced)
    else:
        referenced = []

    incidents_by_ref = {
        t.session_ref: t.incidents.as_dict()
        for t in episode_transports
        if getattr(t, "session_ref", None)
    }
    unattributed_incidents = [
        t.incidents.as_dict()
        for t in episode_transports
        if not getattr(t, "session_ref", None) and t.incidents.any()
    ]
    incident_totals: dict[str, int] = {}
    for counters in (*incidents_by_ref.values(), *unattributed_incidents):
        for key, value in counters.items():
            incident_totals[key] = incident_totals.get(key, 0) + value

    tasks_created = sorted(
        {
            t.session_ref
            for t in episode_transports
            if is_platform and getattr(t, "session_ref", None)
        }
    )
    orphaned_tasks = sorted(set(tasks_created) - set(referenced))

    # The arm assertion (v2 §4 W3.4): the platform's lineage, not the runner's bookkeeping,
    # is what makes "which harness produced this score" a verified claim.
    sha_mismatches = sorted(
        ref
        for ref, account in accounting.items()
        if account.get("recipe_git_commit_sha") not in (None, arm_sha)
    )

    context = manifestmod.RoundContext(
        experiment_id=lock.experiment_id,
        transport=args.transport,
        generation=generation,
        arm_sha=arm_sha,
        arm_dirty=bool(dirty_paths),
        checkpoint=bool(args.checkpoint),
        split=split_name,
        accounting=accounting,
        incidents_by_ref=incidents_by_ref,
        labels_by_ref=labels,
    )
    manifest_rows = manifestmod.build_rows(payload, context)
    manifest_path = manifestmod.write_manifest(out_dir, manifest_rows)

    # Beside τ's results, never inside them: τ owns its own schema. Two launchers produce
    # identically-shaped results, so without this a run directory cannot say which one made it
    # — and "label every score with its configuration" has to survive past the terminal.
    # The file doubles as the run's completion sentinel: it is written only after `run_tasks`
    # returned, so a directory holding results.json without it is an interrupted run.
    (out_dir / "run_metadata.json").write_text(
        json.dumps(
            {
                "mode": "locked" if locked_mode else "diagnostic",
                "experiment": lock.experiment_id,
                "domain": domain,
                "generation": generation,
                "split": split_name,
                "checkpoint": bool(args.checkpoint),
                "num_trials": num_trials,
                "transport": args.transport,
                "launcher": args.launcher if args.transport == TRANSPORT_LOCAL else None,
                "launch_argv": launch_argv,
                "resumed": round_status is not None and "resuming" in (round_status or ""),
                "arm": {
                    "sha": arm_sha,
                    "dirty_paths": dirty_paths,
                    "allow_dirty": bool(args.allow_dirty),
                },
                "episodes": episode_summaries,
                "incidents": {
                    "totals": incident_totals,
                    "unattributed": unattributed_incidents,
                },
                "platform": (
                    {
                        "runtime": args.runtime,
                        "runtime_id": runtime_id,
                        "environment": args.environment,
                        "dev_target": dev.dev_target if dev else None,
                        # Task id doubles as the conversation id: the anchor that links a score
                        # back to the platform evidence that produced it.
                        "task_ids": referenced,
                        "tasks_created": tasks_created,
                        "orphaned_task_ids": orphaned_tasks,
                        "accounting": accounting,
                        "retitles": {"applied": len(labels), "failed": retitle_failures},
                        "arm_sha_mismatches": sha_mismatches,
                    }
                    if is_platform
                    else None
                ),
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

    if not results.simulations:
        # A run that produced no episode must not exit like one that did: the directory would
        # look complete at a glance, and its absence of evidence read as evidence.
        print(f"\n── NO simulations were produced in {elapsed:.0f}s; this run is not a record")
        return 1

    ConsoleDisplay.display_agent_metrics(compute_metrics(results))
    print(f"\n── {len(results.simulations)} simulation(s) in {elapsed:.0f}s → {results_path}")
    for sim, episode in zip(results.simulations, episode_summaries, strict=True):
        verdict = (
            "completed"
            if episode["completed"]
            else "DID NOT COMPLETE — infrastructure or protocol, not a graded outcome"
        )
        print(
            f"   {sim.task_id}: termination={sim.termination_reason} "
            f"messages={len(sim.messages)} reward={episode['reward']}  [{verdict}]"
        )
    print(f"\n   manifest      {manifest_path.name}: {len(manifest_rows)} episode row(s)")
    if incident_totals:
        noted = ", ".join(f"{k}={v}" for k, v in sorted(incident_totals.items()) if v)
        print(f"   incidents     {noted or 'none'}")
    if orphaned_tasks:
        print(
            f"   orphans       {len(orphaned_tasks)} platform task(s) created but absent from "
            "results — τ retried past them; their sandboxes were archived"
        )
    if retitle_failures:
        print(
            f"   labels        {retitle_failures} retitle(s) failed; rows keep their fallback title"
        )
    print(
        "\n   Reward above is tau's own in-run evaluation. The reported number comes from\n"
        f"   `tau2 evaluate-trajs {results_path}`."
    )
    if sha_mismatches:
        print(
            "\n── ARM ASSERTION FAILED: these conversations carry a recipe_git_commit_sha that "
            f"is not this run's arm ({arm_sha[:12] if arm_sha else '?'}):\n   "
            + "\n   ".join(sha_mismatches)
            + "\n   The round's artifacts are on disk but must not be cited as this arm's."
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
