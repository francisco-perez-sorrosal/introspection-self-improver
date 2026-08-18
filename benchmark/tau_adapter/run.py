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
              seam bring-up and the A.0a pipe-semantics gate on `mock`. Results are not
              comparable to anything and must not be reported as a score.

Orthogonal to those, two protocol round types bind a run to the frozen partition
(tau_adapter/rounds.py): `--batch NN` runs one improvement batch on the platform lane, and
`--heldout` runs the held-out set on the local lane with rewards muted in this process —
completeness only; grading lives in the vault via scripts/run_heldout.py, which is the
entry point that owns the full redirect (`make heldout`). Selection comes from the
manifest, never per invocation, and the wrong lane is refused rather than corrected.

A round ends with three artifacts, not one: τ's `results.json`, the runner's
`run_metadata.json` (the completion sentinel — written only after τ's runner returned), and
`episode_manifest.jsonl`, one row per (task, trial) joining the episode to its platform
conversation, lineage, cost, completeness and incident counters. The manifest is what
`operate` receives at the top of a generation.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tau_adapter import generations as gensmod
from tau_adapter import heldout as heldoutmod
from tau_adapter import lock as lockmod
from tau_adapter import manifest as manifestmod
from tau_adapter import rounds as roundsmod
from tau_adapter import split as splitmod
from tau_adapter.dev_lane import (
    DevAttachment,
    assert_no_connected_binding,
    attachment_name,
    resolve_runtime_id,
    warm_runtime,
)
from tau_adapter.experiment import (
    RESULTS_ROOT,
    enforce_snapshot,
    enforce_snapshot_for_experiment,
    freeze_fingerprint,
    generation_of,
    prepare_round_dir,
    pushed_main_sha,
    repo_arm_state,
)
from tau_adapter.pi_agent import PiRecipeAgent
from tau_adapter.pi_local import pi_local_tool_names
from tau_adapter.policy_region import extract_policy, replace_policy
from tau_adapter.rounds import TRANSPORT_LOCAL, TRANSPORT_PLATFORM, TRANSPORTS
from tau_adapter.tool_bridge import ToolBridge
from tau_adapter.transport_local import LAUNCHER_CLI, LAUNCHER_PI, LAUNCHERS, LocalPiTransport
from tau_adapter.transport_platform import (
    DEFAULT_MAX_CONCURRENT_STARTS,
    PlatformTransport,
    StartGate,
    original_title_of,
)

AGENT_KEY = "pi_recipe"

DEFAULT_RUNTIME = "target-agent"

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
    account.update(_sandbox_tool_failures(item.get("items") or []))
    account.update(_effective_config(item.get("items") or []))
    identity = conversation.get("id") or conversation.get("conversation_id")
    return (str(identity) if identity else None), account


def _effective_config(items: list[dict[str, Any]]) -> dict[str, list[str]]:
    """The configuration the sandbox EFFECTIVELY ran, read off the chat spans.

    The lock asserts the recipe; the sandbox injects defaults on top of it (the effective
    thinking level is one such injection, and a platform-side change to those defaults
    moves scores with zero repo change and no detector). Chat spans carry
    `gen_ai.request.model`, `gen_ai.request.reasoning.level` and `gen_ai.provider.name`,
    so every platform episode can carry its own effective configuration — recorded as
    sorted sets because one episode makes many calls and drift WITHIN an episode is itself
    a finding.
    """
    models: set[str] = set()
    reasoning: set[str] = set()
    providers: set[str] = set()
    for entry in items:
        gen_ai = (entry.get("attributes") or {}).get("gen_ai") or {}
        if ((gen_ai.get("operation") or {}).get("name")) != "chat":
            continue
        request = gen_ai.get("request") or {}
        if request.get("model"):
            models.add(str(request["model"]))
        level = (request.get("reasoning") or {}).get("level")
        if level:
            reasoning.add(str(level))
        provider = (gen_ai.get("provider") or {}).get("name")
        if provider:
            providers.add(str(provider))
    return {
        "effective_models": sorted(models),
        "effective_reasoning": sorted(reasoning),
        "effective_providers": sorted(providers),
    }


#: The sandbox daemon reports a failed tool call in the response BODY, not as a typed error,
#: so these are matched as text. The two classes are counted apart because they mean opposite
#: things about the bridge and are fixed in opposite places:
#:
#:   disconnected — the daemon could not reach the bridge at all. The tunnel considers our
#:                  local MCP endpoint gone. Introduced 2026-08-15 by a hand-built serving
#:                  loop; absent on the commit before it (0/10 vs 3/10 episodes).
#:   upstream timed out — the daemon DID reach the bridge and the bridge did not answer in
#:                  time. Pre-existing, and the reason STALL_WARN_SECONDS exists at all; the
#:                  thread-starvation ceiling is its suspected cause.
_SEAM_DISCONNECT_MARKER = "local MCP"
_SEAM_TIMEOUT_MARKER = "mcp upstream timed out"

#: The daemon's stable prefix on every tool error it reports in a response body. Coarser than
#: the two class markers above, and kept deliberately: those are provider prose that can be
#: reworded upstream at any time, and a rewording must degrade to "unclassified seam error"
#: — loud — rather than to zero, which would make this whole failure class invisible again.
_DAEMON_ERROR_MARKER = "MCP daemon: Error"


def _sandbox_tool_failures(items: list[dict[str, Any]]) -> dict[str, int]:
    """Tool failures visible ONLY in the platform conversation, counted per episode.

    There is a failure class this adapter was blind to. When the sandbox's own MCP daemon
    cannot complete a tool call it answers the call ITSELF, so nothing arrives here: τ records
    no turn, the bridge's refusal counters never fire (nothing was refused — nothing was
    received), `results.json` carries no trace, and the episode ends USER_STOP and grades as
    an ordinary agent failure. The agent was in fact denied its tools. Observed 2026-08-15 on
    3 of 10 platform episodes while the round printed `incidents none`.

    The conversation export is already fetched for cost and lineage, so counting this costs
    nothing and makes the invisible case loud — the seam's whole contract being that a round
    may fail but may never report itself healthy while failing.

    The markers are substring matches over the whole rendered item, which over-counts by
    design: the agent SEES the daemon's error text and tends to quote it in its next visible
    message, so one failure can land in two items. Per-episode presence (>0) is the signal;
    the item count is an upper bound, not a call count. The same breadth means a harness
    mutation that writes a marker string into prompt or tool text would flag its own round —
    if a whole round lights up uniformly, read one conversation before believing it.
    """
    counts = {
        "sandbox_tool_errors": 0,
        "sandbox_seam_disconnects": 0,
        "sandbox_seam_timeouts": 0,
        "sandbox_seam_unclassified": 0,
    }
    for entry in items:
        attributes = entry.get("attributes") or {}
        operation = ((attributes.get("gen_ai") or {}).get("operation") or {}).get("name")
        if operation == "execute_tool" and (attributes.get("error") or {}).get("type"):
            counts["sandbox_tool_errors"] += 1
        rendered = json.dumps(entry)
        disconnect = _SEAM_DISCONNECT_MARKER in rendered
        timeout = _SEAM_TIMEOUT_MARKER in rendered
        if disconnect:
            counts["sandbox_seam_disconnects"] += 1
        if timeout:
            counts["sandbox_seam_timeouts"] += 1
        if _DAEMON_ERROR_MARKER in rendered and not (disconnect or timeout):
            # A daemon-reported tool error whose wording matches neither known class:
            # either a new failure mode or an upstream rewording of an old one. Both are
            # worth a human read, so the bucket exists to keep them from reading as zero.
            counts["sandbox_seam_unclassified"] += 1
    return counts


#: Known infrastructure-failure classes, matched against the failure text τ recorded on the
#: episode. Grounded in observed incidents, not invented: the empty-completion class killed
#: 3 of 6 canary trials on 2026-08-15 (and, deterministically, voided seq 1); the
#: connection class produced 24 retries across 13 tasks in the same day's H0 round. Every
#: class here is provider weather on a FROZEN surface — named so the storm ledger builds
#: itself in run_metadata.json instead of in log greps and commit messages.
_INFRA_CLASS_MARKERS = (
    ("user_sim_empty_completions", "UserMessage must have either content or tool_calls"),
    ("provider_connection_errors", "APIConnectionError"),
    ("provider_connection_errors", "Connection error"),
)


def _infra_failure_classes(rows: list[dict[str, Any]]) -> dict[str, int]:
    """Classify τ's infrastructure-error placeholders by their recorded failure text."""
    counts: dict[str, int] = {}
    for row in rows:
        failure = row.get("failure") or {}
        if not failure:
            continue
        text = f"{failure.get('error_type') or ''}: {failure.get('error') or ''}"
        for name, marker in _INFRA_CLASS_MARKERS:
            if marker in text:
                counts[name] = counts.get(name, 0) + 1
                break
        else:
            counts["infra_other"] = counts.get("infra_other", 0) + 1
    return counts


def _heldout_cadence_problem(lock: lockmod.Lock, generation_name: str) -> str | None:
    """Why measuring this generation would break the cadence, or None when it holds.

    The other half of the measure-then-learn guarantee: H_(g+1) exists only as the
    product of batch_(g+1)'s learnings, so its held-out measurement refuses until that
    batch is graded and the transition record exists with outcome accepted. Without this,
    a skipped batch would be invisible — the mutation could merge, tag and measure while
    citing older evidence, and the curve would carry a point no learning round produced.
    Also refuses identity/rejected generations outright: H_g = H_(g-1) carries forward
    (D5) and re-measuring it both wastes a full round and is refused at reveal anyway —
    better to refuse before the spend. The baseline (generation_000) precedes any batch
    by definition and is exempt.
    """
    from tau_adapter import records as recordsmod

    index = int(generation_name.removeprefix("generation_"))
    if not gensmod.heldout_scheduled(index, lock.protocol.heldout_generations):
        scheduled = ", ".join(str(g) for g in (lock.protocol.heldout_generations or ()))
        return (
            f"{generation_name} is not on this experiment's frozen held-out schedule "
            f"(protocol.heldout_generations: {scheduled}). Its result is CARRIED from the "
            "most recent scheduled measurement, exactly as an identity generation's is — "
            "measuring it would spend a round the freeze did not budget, and the reveal "
            "would refuse the measurement it produced."
        )
    if index == 0:
        return None
    experiment_dir = RESULTS_ROOT / f"experiment_{lock.experiment_id}"
    record_path = experiment_dir / "improvement_records" / recordsmod.record_name(index - 1)
    if not record_path.exists():
        return (
            f"no transition record for H{index - 1} → H{index} ({record_path.name}): the "
            "record is written while the transition happens (protocol step 6), before its "
            "generation is measured — scaffold and fill it first."
        )
    record = recordsmod.load_record(record_path)
    outcome = record.get("outcome")
    if outcome != recordsmod.OUTCOME_ACCEPTED:
        return (
            f"{record_path.name} has outcome {outcome!r}: H{index} = H{index - 1} carries "
            "forward (D5) and is never re-measured — this round would be refused at "
            "reveal after spending every episode. Skip it; the result carries."
        )
    # The backlog write-through gate (plan D26): a v3 record's transition must have
    # stamped the backlog. Refused here — before the spend — for the same reason the
    # record itself is: seq 6's backlog silently froze at gen-003 while the gated
    # records stayed impeccable, and only the gated artifact stayed alive.
    backlog_problems = recordsmod.backlog_problems(record, RESULTS_ROOT)
    if backlog_problems:
        return backlog_problems[0]
    graded = (
        experiment_dir
        / f"generation_{index - 1:03d}"
        / f"batch_{index:02d}"
        / heldoutmod.GRADED_DIR
        / heldoutmod.GRADED_RESULTS
    )
    if not graded.exists():
        return (
            f"batch_{index:02d} is not graded ({graded} missing): H{index} is the product "
            f"of that batch's learnings, so the cadence is batch → learn → merge → "
            f"measure. Run `make batch B={index} GEN=generation_{index - 1:03d}` to "
            "completion first."
        )
    return None


def _batch_cadence_problem(lock: lockmod.Lock, batch_number: int) -> str | None:
    """Why this batch would break the generation cadence, or None when it holds.

    The cadence (protocol, user-ratified 2026-08-16): every harness is MEASURED on the
    held-out set before its batch is spent — H0's baseline before batch_01, H_g's round
    before batch_(g+1) — so learning never runs ahead of measurement, and together with
    reveal's completeness refusal the curve is guaranteed a point for every harness that
    learned, ending on the final one. Two facts are checked, both resolved through the
    identity chain (an identity/rejected transition carries its predecessor's tag and
    measurement forward, D5):

      recipe   the anchored surface is byte-identical to the generation's tag — a batch
               run after an early merge would otherwise attribute H_(g+1) behaviour to
               H_g's round directory with no refusal.
      vault    the generation's held-out round is graded in the vault. EXISTENCE ONLY:
               the gate tests the graded artifact's path and never opens anything in the
               vault — completeness is the operator's signal, rewards stay sealed.
    """
    runner_generation = batch_number - 1
    records_dir = RESULTS_ROOT / f"experiment_{lock.experiment_id}" / "improvement_records"
    effective = gensmod.effective_generation_index(runner_generation, records_dir)
    generation_name = f"generation_{effective:03d}"
    carried = (
        f" (H{runner_generation} carries forward to H{effective} via identity transitions)"
        if effective != runner_generation
        else ""
    )
    tag = gensmod.heldout_generation_tag(lock.experiment_seq, generation_name)
    if not gensmod.tag_exists(tag):
        return (
            f"batch_{batch_number:02d} is run by H{runner_generation}, whose recipe is the "
            f"tag {tag!r}{carried} — and that tag does not exist. The loop order is "
            "merge → tag → held-out → batch."
        )
    problems = gensmod.verify_against_tag(tag)
    if problems:
        return (
            f"the recipe surface is not byte-identical to {tag!r}, so "
            f"batch_{batch_number:02d} would run something other than "
            f"H{runner_generation}{carried}:\n  ✗ " + "\n  ✗ ".join(problems)
        )
    # Every SCHEDULED measurement at or before this generation, not merely the latest: a
    # sparse held-out schedule (plan D36) makes measurement rarer, never optional.
    for due in gensmod.heldout_due_before(effective, lock.protocol.heldout_generations):
        due_name = f"generation_{due:03d}"
        graded = (
            heldoutmod.vault_root()
            / f"experiment_{lock.experiment_id}"
            / due_name
            / heldoutmod.GRADED_DIR
            / heldoutmod.GRADED_RESULTS
        )
        if not graded.exists():
            scope = (
                f"H{runner_generation}"
                if due == effective
                else f"H{due}, which H{runner_generation} depends on,"
            )
            return (
                f"{scope} has no graded held-out measurement in the vault{carried}. The "
                "cadence is measure-then-learn: run "
                f"`make heldout GEN={due_name}` to completion before spending "
                f"batch_{batch_number:02d} — a baseline skipped now becomes unmeasurable "
                "once the next merge moves the recipe."
            )
    return None


def _seam_canary_problem(experiment_id: str) -> str | None:
    """Why a batch round may not start yet, or None when the seam canary is current.

    Current means: a PASS verdict exists for this experiment AND no file under
    benchmark/tau_adapter changed between the verdict's commit and HEAD. Any doubt (missing
    verdict, unreadable verdict, git unable to compare) reads as stale — the canary is the
    cheap side of the asymmetry.
    """
    verdict_path = RESULTS_ROOT / f"experiment_{experiment_id}" / "gates" / "seam_canary.json"
    remedy = "Run `make gate_seam` (one platform canary episode set), then rerun the batch."
    if not verdict_path.exists():
        return f"no platform seam-canary verdict for this experiment ({verdict_path}). {remedy}"
    try:
        verdict = json.loads(verdict_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return f"unreadable seam-canary verdict ({exc}). {remedy}"
    if not verdict.get("passed"):
        return f"the recorded seam canary FAILED ({verdict_path}). {remedy}"
    canary_sha = str(verdict.get("adapter_sha") or "")
    if not canary_sha:
        return f"the seam-canary verdict names no adapter_sha ({verdict_path}). {remedy}"
    try:
        diff = subprocess.run(
            ["git", "diff", "--name-only", f"{canary_sha}..HEAD", "--", "benchmark/tau_adapter"],
            cwd=lockmod.REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=30,
            check=True,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError) as exc:
        return f"cannot compare HEAD against the seam canary's commit ({exc}). {remedy}"
    if diff:
        changed = ", ".join(diff.splitlines()[:5])
        return (
            f"the seam changed since its last platform canary ({canary_sha[:12]}): {changed}. "
            f"{remedy}"
        )
    return None


def _bridge_call_stats(
    call_log: list[dict[str, Any]], episode_transports: list[Any]
) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    """Join the bridge's per-call observations to episodes; return (stats by ref, enriched log).

    The park duration in the log is the only latency the sandbox daemon actually
    experiences while a call is in flight — τ's own timestamps cannot show it — so it is
    the number that explains a `mcp upstream timed out` (observed at 6 and 4 per 24-episode
    round in seq 5's batches, at a concurrency where the old thread ceiling could not
    bind). Joined by channel token and by bound session, both of which the transport knows.
    """
    ref_by_key: dict[str, str] = {}
    for transport in episode_transports:
        ref = getattr(transport, "session_ref", None)
        if not ref:
            continue
        token = getattr(transport, "channel_token", None)
        if token:
            ref_by_key[token] = ref
    stats: dict[str, dict[str, Any]] = {}
    grouped: dict[str, list[float]] = {}
    enriched: list[dict[str, Any]] = []
    for entry in call_log:
        ref = ref_by_key.get(entry.get("token") or "")
        enriched.append({**entry, "episode": ref})
        if ref:
            grouped.setdefault(ref, []).append(float(entry.get("duration_seconds") or 0.0))
    for ref, durations in grouped.items():
        stats[ref] = {
            "bridge_calls": len(durations),
            "bridge_park_max_seconds": round(max(durations), 3),
            "bridge_park_mean_seconds": round(sum(durations) / len(durations), 3),
        }
    return stats, enriched


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


def _experiment_tag(lock: lockmod.Lock) -> str:
    """The title prefix naming the experiment, e.g. `[exp_001:bm25-sonnet46]`."""
    return f"[exp_{lock.experiment_seq:03d}:{lock.experiment_name}]"


def _retitle_episodes(
    payload: dict[str, Any],
    domain: str,
    generation: str | None,
    experiment_tag: str,
    original_titles: dict[str, str],
    round_token: str = "",
) -> tuple[dict[str, str], int]:
    """Post-run label pass: name every platform task after the τ episode it served.

    The agent factory never learns which simulation it serves, so a sweep's tasks are titled
    with the domain alone at episode end. Ground truth arrives only when τ's runner returns —
    each simulation's raw_data names its task — so the labels are applied here, from the
    record, rather than guessed during the run (the retitle works on archived rows).

    The platform's own auto-title (its summary of the conversation) is preserved after
    ` - `: the transports captured it at close() before their interim retitle, so the common
    case costs nothing extra. A row this process did not close — a resumed run's archived
    episode — is read back with one `tasks get` and the original recovered from under the
    label. One `tasks update` per episode; failures are counted, never fatal, and never
    touch the score.
    """
    gen_short = ""
    if generation and generation.startswith("generation_"):
        gen_short = f" gen_{generation.removeprefix('generation_')}"
    labels: dict[str, str] = {}
    failed = 0
    for sim in payload.get("simulations") or []:
        ref = manifestmod.session_ref_of(sim)
        if not ref:
            continue
        original = original_titles.get(ref)
        if original is None:
            try:
                task = _cli_json(["tasks", "get", ref], timeout=60)
                original = original_title_of(str((task or {}).get("title") or ""))
            except (OSError, subprocess.SubprocessError, json.JSONDecodeError, RuntimeError):
                original = ""
        label = (
            f"{experiment_tag} τ²-bench {domain} {sim.get('task_id')} "
            f"trial {sim.get('trial')}{gen_short}{round_token}"
        ) + (f" - {original}" if original else "")
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


class _EpisodeTransportLog:
    """Every transport constructed, one per episode *attempt*.

    τ runs episodes from a worker pool and retries infrastructure errors, so appends arrive
    from concurrent threads and can exceed the episodes the results file names — the
    difference is the orphan count, and it must be visible. Reads happen only after τ's
    runner returned: the shutdown sweep (closing whatever an interrupted sweep left open)
    and the post-run evidence pass both iterate a snapshot.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._items: list[Any] = []

    def add(self, transport: Any) -> None:
        with self._lock:
            self._items.append(transport)

    def snapshot(self) -> list[Any]:
        with self._lock:
            return list(self._items)


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
        help="τ task ids to run. Omit to run the whole locked task split. Ad-hoc runs only.",
    )
    round_group = parser.add_mutually_exclusive_group()
    round_group.add_argument(
        "--batch",
        type=int,
        metavar="N",
        default=None,
        help=(
            "run improvement batch N from the frozen partition. Platform lane forced "
            "(SIA_EVALUATION_PLAN.md D1): batch episodes are the evidence `operate` reads. "
            "Resume-friendly — rerunning re-runs only what is missing."
        ),
    )
    round_group.add_argument(
        "--heldout",
        action="store_true",
        help=(
            "run the held-out set from the frozen partition. Local lane forced (D1), output "
            "must live out of tree, and this process prints completeness only — no rewards. "
            "Prefer `make heldout`, whose wrapper owns the vault and the full redirect."
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
        default=None,
        help=(
            "where the agent runs. 'local' (the ad-hoc default) is a Pi subprocess on this "
            "machine and produces no Introspection evidence. 'platform' runs each episode as a "
            "task in the development environment, which yields conversations, traces and "
            "lineage, and starts `introspection dev` itself to route the τ bridge back here. "
            "Protocol rounds choose their own lane and refuse the other."
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
    parser.add_argument(
        "--max-concurrency",
        type=int,
        default=None,
        help=(
            "episodes in flight at once, each on its own bridge channel. Overrides the "
            "lock's operational default on any round type (1 = serial); the effective "
            "value is recorded in run_metadata.json."
        ),
    )
    parser.add_argument(
        "--max-concurrent-starts",
        type=int,
        default=None,
        help=(
            "platform lane only: episodes allowed between `tasks create` and their first "
            "streamed event at once — sandbox starts, whose provisioning is heavy-tailed "
            f"under bursts. Default {DEFAULT_MAX_CONCURRENT_STARTS}; 0 disables the gate. "
            "Recorded in run_metadata.json; ignored on the local lane."
        ),
    )
    args = parser.parse_args()

    lock = lockmod.load_lock()
    lockmod.assert_vendor_commit(lock)
    lockmod.assert_recipe_matches_lock(lock)
    _assert_recipe_valid()

    # Round-type resolution refuses every lying combination (wrong lane, hand-picked tasks,
    # a drifted partition) before anything below spends time or money.
    needs_partition = args.batch is not None or args.heldout
    try:
        spec = roundsmod.resolve_round(
            batch=args.batch,
            heldout=args.heldout,
            transport=args.transport,
            task_ids=args.task_ids,
            domain=args.domain,
            overwrite=args.overwrite,
            lock=lock,
            manifest=splitmod.load_manifest() if needs_partition else None,
            rows=splitmod.load_task_rows(lock.domain) if needs_partition else None,
        )
    except roundsmod.RoundError as exc:
        raise SystemExit(str(exc)) from exc

    domain = args.domain or lock.domain
    locked_mode = domain == lock.domain
    muted = spec.kind == roundsmod.KIND_HELDOUT

    # Ad-hoc runs keep their free choice of tasks — except the unrevealed held-out set,
    # whose observable evidence must not exist before the reveal. Protocol rounds are
    # partition-driven and skip this; a non-locked domain (mock) shares no task ids.
    if spec.kind == roundsmod.KIND_ADHOC and locked_mode and splitmod.SPLIT_MANIFEST_PATH.exists():
        held_out_ids = set(splitmod.load_manifest().get(splitmod.HELD_OUT) or [])
        revealed = (RESULTS_ROOT / f"experiment_{lock.experiment_id}" / "held_out").is_dir()
        try:
            roundsmod.assert_adhoc_respects_firewall(
                task_ids=spec.task_ids, held_out=held_out_ids, revealed=revealed
            )
        except roundsmod.RoundError as exc:
            raise SystemExit(str(exc)) from exc

    try:
        max_concurrency = roundsmod.resolve_max_concurrency(
            args.max_concurrency, lock_value=lock.max_concurrency
        )
    except roundsmod.RoundError as exc:
        raise SystemExit(str(exc)) from exc

    # The start gate is platform-lane-only and operational, like max_concurrency: it moves
    # wall-clock and start-latency exposure, never what an agent can do inside an episode.
    if args.max_concurrent_starts is not None and args.max_concurrent_starts < 0:
        raise SystemExit("--max-concurrent-starts must be >= 0 (0 disables the gate)")
    max_concurrent_starts: int | None = None
    if spec.transport == TRANSPORT_PLATFORM:
        max_concurrent_starts = (
            DEFAULT_MAX_CONCURRENT_STARTS
            if args.max_concurrent_starts is None
            else args.max_concurrent_starts
        )

    task_ids: list[str] | None = spec.task_ids
    num_trials = lock.num_trials

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

    # The D24 suppression registry, resolved once from the recipe this run serves. Empty
    # for a bare recipe — suppression then never engages and the seam behaves as before.
    pi_local_tools = pi_local_tool_names(recipe_dir)

    # The arm this run serves. `introspection dev` serves the work-tree while lineage names
    # the base commit, so a dirty served surface makes every arm claim soft: the platform
    # lane refuses it outright unless --allow-dirty records it prominently.
    arm_sha, dirty_paths = repo_arm_state() if locked_mode else (None, [])
    if muted and dirty_paths:
        # No --allow-dirty escape here: a held-out round measures exactly one generation,
        # and dirt on the served recipe surface makes the measurement unattributable.
        # Debugging belongs in ad-hoc rounds, never in the measurement.
        raise SystemExit(
            "the recipe surface has uncommitted changes, so this held-out round would not "
            "measure the generation it claims to (guardrail 12). Commit or revert:\n  "
            + "\n  ".join(dirty_paths)
        )
    if spec.transport == TRANSPORT_PLATFORM and dirty_paths and not args.allow_dirty:
        raise SystemExit(
            "the served recipe surface has uncommitted changes, so lineage would name a "
            "commit that is not what runs. Commit them, or pass --allow-dirty for a "
            "debugging run whose rows are marked arm_sha_ok=false:\n  " + "\n  ".join(dirty_paths)
        )
    if spec.transport == TRANSPORT_PLATFORM and locked_mode and not args.allow_dirty:
        # The platform mints runtime versions from pushed main, and `recipe_git_commit_sha`
        # names that pin — while `introspection dev` serves the work-tree's bytes. Running
        # ahead of origin/main therefore runs the right code but records the wrong arm; the
        # A.0b-era probe hit exactly this (every row arm_sha_ok=false after two local-only
        # commits). Caught here, before the money is spent.
        pushed = pushed_main_sha()
        if pushed and arm_sha and pushed != arm_sha:
            raise SystemExit(
                f"HEAD ({arm_sha[:12]}) is ahead of origin/main ({pushed[:12]}), and the "
                "platform pins lineage to pushed main. Push, let the runtime version build, "
                "and rerun — or pass --allow-dirty for a debugging run whose rows are "
                "marked arm_sha_ok=false."
            )

    out_dir = Path(args.out).resolve()
    if muted and out_dir.is_relative_to(lockmod.REPO_ROOT):
        raise SystemExit(
            "held-out outputs live out of tree (SIA_EVALUATION_PLAN.md D9): results/, and "
            "the work tree generally, are exactly where held-out artifacts must not exist. "
            "scripts/run_heldout.py owns the vault layout and the console redirect — prefer "
            "`make heldout`."
        )
    if spec.kind == roundsmod.KIND_BATCH:
        # batch_NN is consumed by the H_(NN-1) → H_NN transition, so it is *run by*
        # H_(NN-1) and its evidence lives under that generation's directory. Enforced so
        # one experiment's tree cannot mix two batch↔generation conventions.
        expected_generation = f"generation_{args.batch - 1:03d}"
        if generation_of(out_dir) != expected_generation:
            raise SystemExit(
                f"batch_{args.batch:02d} is run by H{args.batch - 1} (it feeds the "
                f"H{args.batch - 1}→H{args.batch} transition), so its round directory "
                f"lives under {expected_generation}/ — --out names "
                f"{generation_of(out_dir) or 'no generation directory'}. "
                f"Use GEN={expected_generation}."
            )
        # The generation cadence: measure, then learn. Bypassed only by --allow-dirty,
        # whose rows are already marked non-citable — a debugging escape, never a round.
        if not args.allow_dirty:
            cadence_problem = _batch_cadence_problem(lock, args.batch)
            if cadence_problem:
                raise SystemExit(cadence_problem)
        # A batch round spends real evidence on the platform seam, and the local gate
        # cannot exercise the tunnel — the 2026-08-15 disconnect regression passed 309
        # tests and a mock smoke while denying agents their tools. So a batch refuses to
        # start unless a platform seam canary (make gate_seam) has PASSed for this
        # experiment with no tau_adapter change since. Fail-closed: a missing or stale
        # verdict costs one ~$0.02 canary, a broken seam costs the round.
        canary_problem = _seam_canary_problem(lock.experiment_id)
        if canary_problem:
            raise SystemExit(canary_problem)
    if muted:
        # A held-out measurement must be attributable to exactly one generation: the recipe
        # surface is verified byte-identical to that generation's tag before any spend.
        try:
            gensmod.assert_heldout_measures_a_generation(
                lock.experiment_seq, generation_of(out_dir) or ""
            )
        except (gensmod.GenerationError, ValueError) as exc:
            raise SystemExit(str(exc)) from exc
        # And it must come AFTER the learning that produced the generation: batch graded,
        # record written, outcome accepted (identity generations are never re-measured).
        cadence_problem = _heldout_cadence_problem(lock, generation_of(out_dir) or "")
        if cadence_problem:
            raise SystemExit(cadence_problem)
    # Before --overwrite can delete anything: a run aimed at the wrong experiment directory
    # must refuse here rather than clear another freeze's record first. Also verifies — or,
    # for a non-PROVISIONAL lock, creates — the experiment's freeze snapshot. Held-out
    # rounds write outside results/ by design, so they anchor to the in-tree snapshot by
    # experiment id instead of by path — the freeze is enforced on the measurement that
    # matters most, not just on the observable rounds.
    experiment_status = (
        enforce_snapshot_for_experiment(lock) if muted else enforce_snapshot(lock, out_dir)
    )
    # The episode count this round owes, when it is knowable up front (an explicit task
    # list, which every bound round has). It is what lets prepare_round_dir tell a
    # measured round from one whose runner merely returned — see its docstring.
    expected_episodes = len(task_ids) * lock.num_trials if task_ids else None
    round_status = prepare_round_dir(
        out_dir, args.overwrite, expected_episodes=expected_episodes
    )
    generation = generation_of(out_dir)
    results_path = out_dir / "results.json"
    session_dir = out_dir / "pi_sessions"
    base_env = _build_env_for_pi()

    # Run-scoped: the development lane hands one URL to `introspection dev` before the first
    # episode and holds it for the whole run, so the bridge has to outlive an episode.
    # Episodes rendezvous on per-episode channels within it — both lanes open a fresh channel
    # per episode (the local lane by URL, the platform by sandbox-session routing).
    # Built from the probe environment's tools because the schemas are what it advertises,
    # and the tool surface is asserted identical to the lock.
    bridge = ToolBridge(
        tau_tools=probe_env.get_tools(),
        port=args.bridge_port,
        max_concurrency=max_concurrency,
    )
    bridge.start()

    dev: DevAttachment | None = None
    runtime_id: str | None = None
    if spec.transport == TRANSPORT_PLATFORM:
        if not locked_mode:
            raise SystemExit(
                "the platform transport serves the Recipe from the git work-tree, so it cannot "
                "run diagnostic mode: that materialises a modified Recipe elsewhere. Use "
                "--transport local for a non-locked domain."
            )
        runtime_id = resolve_runtime_id(args.runtime, lockmod.REPO_ROOT)
        assert_no_connected_binding(runtime_id, args.environment, lockmod.REPO_ROOT)
        # ONE attachment serves every concurrent episode: the tunnel stamps each forwarded
        # MCP request with its sandbox session and channels route by it, so attachment
        # multiplicity is unnecessary — and the platform accepts only a single live dev
        # attachment per Runtime anyway (dev_slot_conflict, observed 2026-08-13). The
        # nonce'd name keeps a second run on this machine from claiming this run's dev
        # target.
        dev = DevAttachment(
            mcp_url=bridge.url,
            repo_root=lockmod.REPO_ROOT,
            runtime_name=args.runtime,
            as_name=attachment_name(),
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
    # row to `[exp_NNN:name] τ²-bench <domain> <task> trial <k> gen_NNN - <platform title>`
    # from τ's own record once it exists. The experiment tag keeps platform evidence separable
    # even where two experiments share a recipe commit — e.g. a user-simulator-only change.
    episode_label = f"{_experiment_tag(lock)} τ²-bench {domain}" + (
        spec.label_token or (f" {task_ids[0]}" if task_ids and len(task_ids) == 1 else "")
    )

    transports = _EpisodeTransportLog()

    # One gate per run, shared by every episode transport: it bounds concurrent sandbox
    # *starts* (create → first streamed event), not episodes in flight.
    start_gate = StartGate(max_concurrent_starts) if max_concurrent_starts else None

    # The launch vector is identical for every episode, so it is computed once here rather
    # than inside the factory τ's workers call concurrently. The local probe transport is
    # never started; its only job is to render the argv a run's record names.
    if spec.transport == TRANSPORT_PLATFORM:
        launch_argv = ["introspection", "tasks", "create", "--runtime-id", str(runtime_id)]
    else:
        launch_argv = LocalPiTransport(
            recipe_dir=recipe_dir,
            session_dir=session_dir,
            launcher=args.launcher,
            workspace_dir=workspace_dir,
        ).argv()

    def create_agent(tools, domain_policy, **kwargs):
        declared = kwargs.get("llm")
        if declared is not None and declared != lock.agent_llm_declared:
            raise lockmod.LockError(
                f"--agent-llm is {declared!r} but the lock declares {lock.agent_llm_declared!r}"
            )
        transport: Any
        if spec.transport == TRANSPORT_PLATFORM:
            assert runtime_id is not None and dev is not None
            transport = PlatformTransport(
                runtime_id=runtime_id,
                repo_root=lockmod.REPO_ROOT,
                environment=args.environment,
                # Must exceed the gap while τ's user simulator thinks (2-12s healthy, up to its
                # 60s per-attempt ceiling plus retries), or the sandbox is torn down mid-episode.
                idle_timeout_seconds=int(lock.timeout_seconds),
                dev_target=dev.dev_target,
                episode_label=episode_label,
                start_gate=start_gate,
            )
        else:
            transport = LocalPiTransport(
                recipe_dir=recipe_dir,
                session_dir=session_dir,
                launcher=args.launcher,
                workspace_dir=workspace_dir,
            )
        transports.add(transport)
        return PiRecipeAgent(
            tools=tools,
            domain_policy=domain_policy,
            # Both lanes: a fresh channel per episode. The URL routes it locally; the
            # platform transport binds it to its sandbox session for tunnel routing.
            open_channel=bridge.open_channel,
            transport=transport,
            recipe_policy=recipe_policy,
            domain=domain,
            base_env=base_env,
            pi_local_tools=pi_local_tools,
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
        max_concurrency=max_concurrency,
        enforce_communication_protocol=lock.enforce_communication_protocol,
        # τ's own checkpointing, adopted rather than reimplemented: results.json
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
    if spec.kind == roundsmod.KIND_BATCH:
        print(f"   round type    {spec.split} — improvement batch, fully observable by design")
    elif muted:
        print("   round type    held_out — hidden evaluation; grading stays in the vault")
    print(f"   recipe        {recipe_dir}")
    if pi_local_tools:
        print(f"   pi-local      {', '.join(sorted(pi_local_tools))} — suppressed from τ (D24)")
    if arm_sha:
        dirt = (
            f" — DIRTY served surface ({len(dirty_paths)} path(s), --allow-dirty)"
            if dirty_paths
            else ""
        )
        print(f"   arm           {arm_sha[:12]}{dirt}")
    print(f"   transport     {spec.transport}")
    if spec.transport == TRANSPORT_PLATFORM:
        print(f"   runtime       {args.runtime} ({runtime_id}) in {args.environment}")
        print(f"   attachment    {dev.dev_target if dev else '(none)'}")
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

    if spec.kind == roundsmod.KIND_BATCH:
        selection = f"{spec.split}: {', '.join(task_ids or [])}"
    elif muted:
        selection = f"held_out: {len(tasks)} task(s); outputs sealed in the vault"
    elif task_ids:
        selection = ", ".join(task_ids)
    else:
        selection = f"whole split ({len(tasks)} tasks)"
    print(f"   tasks         {selection} in {num_trials} trial(s)")
    if max_concurrency != 1:
        print(f"   concurrency   {max_concurrency} episode(s) in flight, one bridge channel each")
    if max_concurrent_starts and max_concurrency != 1:
        print(f"   start gate    {max_concurrent_starts} concurrent sandbox start(s)")
    if lock.provisional:
        print("   lock status   PROVISIONAL — not an experiment freeze")
    if len(tasks) * num_trials > 20:
        # A sweep is the expensive path. Say what it costs before spending it rather than
        # after, naming the effective concurrency it will run at.
        episodes = len(tasks) * num_trials
        print(
            f"\n   sweep: {episodes} episode(s) at max_concurrency="
            f"{max_concurrency}{', serial' if max_concurrency == 1 else ''}. An "
            "interruption is safe: rerunning the same --out resumes and re-spends nothing."
        )
    print()

    started = time.monotonic()
    try:
        results = run_tasks(config, tasks, save_path=results_path, save_dir=out_dir)
    finally:
        # Reverse acquisition order, and everything best-effort. Closing the transports first
        # archives any task an interrupted episode left open — otherwise its sandbox idles
        # against the org concurrency limit until the platform's timeout backstop fires.
        for transport in transports.snapshot():
            # Shutdown must not mask the real failure.
            with contextlib.suppress(Exception):
                transport.close()
        if dev is not None:
            dev.stop()
        bridge.stop()
    elapsed = time.monotonic() - started
    episode_transports = transports.snapshot()
    episode_summaries = [manifestmod.episode_summary(sim) for sim in results.simulations]

    # Post-run evidence pass, all from the record τ just wrote: per-episode labels, batched
    # accounting, the manifest, and the arm assertion. Everything below reads results.json
    # rather than in-memory state so that what it derives is exactly what a later reader sees.
    payload = json.loads(results_path.read_text(encoding="utf-8")) if results_path.exists() else {}
    is_platform = spec.transport == TRANSPORT_PLATFORM

    labels: dict[str, str] = {}
    retitle_failures = 0
    accounting: dict[str, Any] = {}
    if is_platform:
        # What the platform's auto-titles were before close() relabeled the tasks, keyed by
        # task id — so the retitle pass can preserve them without a per-episode `tasks get`.
        original_titles = {
            t.session_ref: t.original_title
            for t in episode_transports
            if getattr(t, "session_ref", None) and getattr(t, "original_title", None) is not None
        }
        labels, retitle_failures = _retitle_episodes(
            payload, domain, generation, _experiment_tag(lock), original_titles, spec.label_token
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
    # Bridge-level refusals have no episode to ride on — that is what a refusal means —
    # so they join the totals directly: a round whose seam refused calls must not read
    # as healthy just because no manifest row could carry the count.
    bridge_refusals = {key: value for key, value in bridge.refusal_counters().items() if value}
    for key, value in bridge_refusals.items():
        incident_totals[key] = incident_totals.get(key, 0) + value

    tasks_created = sorted(
        {
            t.session_ref
            for t in episode_transports
            if is_platform and getattr(t, "session_ref", None)
        }
    )
    orphaned_tasks = sorted(set(tasks_created) - set(referenced))

    # The arm assertion: the platform's lineage, not the runner's bookkeeping, is what makes
    # "which harness produced this score" a verified claim.
    sha_mismatches = sorted(
        ref
        for ref, account in accounting.items()
        if account.get("recipe_git_commit_sha") not in (None, arm_sha)
    )

    bridge_stats_by_ref, bridge_call_entries = _bridge_call_stats(
        bridge.call_log(), episode_transports
    )
    # Beside the manifest, one line per handled call: the bridge's own record of arrival,
    # park duration, outcome and result digest. The only vantage that can time the seam
    # from the daemon's side, and the ground truth an integrity audit compares against.
    (out_dir / "bridge_calls.jsonl").write_text(
        "".join(json.dumps(e, ensure_ascii=False) + "\n" for e in bridge_call_entries),
        encoding="utf-8",
    )
    context = manifestmod.RoundContext(
        experiment_id=lock.experiment_id,
        transport=spec.transport,
        generation=generation,
        arm_sha=arm_sha,
        arm_dirty=bool(dirty_paths),
        split=spec.split,
        accounting=accounting,
        incidents_by_ref=incidents_by_ref,
        labels_by_ref=labels,
        bridge_stats_by_ref=bridge_stats_by_ref,
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
                # The freeze this round actually ran under: reveal cross-checks every
                # held-out measurement's fingerprint against the experiment snapshot.
                "freeze_fingerprint": freeze_fingerprint(lock),
                "domain": domain,
                "generation": generation,
                "split": spec.split,
                "num_trials": num_trials,
                "max_concurrency": max_concurrency,
                # The seam's own capacity for this round. Recorded beside max_concurrency
                # because the two together are what decides whether a rendezvous stall was
                # the agent or the bridge running out of threads. The EFFECTIVE pool, never
                # the designed sizing: while the 2026-08-15 revert stands the bridge draws
                # from asyncio's host-sized default executor, and recording the inert design
                # value here would make a diagnostician rule out the true ceiling.
                "bridge_executor_workers": bridge.effective_executor_workers,
                "max_concurrent_starts": max_concurrent_starts,
                "transport": spec.transport,
                "launcher": args.launcher if spec.transport == TRANSPORT_LOCAL else None,
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
                    "bridge": bridge_refusals,
                    # τ's infrastructure placeholders classified by failure text — provider
                    # weather on frozen surfaces, named per class so storms accumulate into
                    # a ledger instead of into log greps (see _INFRA_CLASS_MARKERS).
                    "infra_failure_classes": _infra_failure_classes(manifest_rows),
                },
                "platform": (
                    {
                        "runtime": args.runtime,
                        "runtime_id": runtime_id,
                        "environment": args.environment,
                        # The one named attachment every episode tunneled through; per-
                        # episode routing keys on the sandbox session, not the attachment.
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
                # The D24 suppression registry this run resolved; [] means the seam never
                # suppressed anything (bare recipe) and behaved exactly as pre-D24.
                "pi_local_tools": sorted(pi_local_tools),
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

    # A held-out round's summary states completeness and nothing else: no metrics table,
    # no per-episode reward. Defense-in-depth — the wrapper redirects this whole process
    # into the vault's console.log, but a direct --heldout invocation must not leak either.
    if not muted:
        ConsoleDisplay.display_agent_metrics(compute_metrics(results))
    print(f"\n── {len(results.simulations)} simulation(s) in {elapsed:.0f}s → {results_path}")
    for sim, episode in zip(results.simulations, episode_summaries, strict=True):
        verdict = (
            "completed"
            if episode["completed"]
            else "DID NOT COMPLETE — infrastructure or protocol, not a graded outcome"
        )
        graded_part = "" if muted else f" reward={episode['reward']} "
        print(
            f"   {sim.task_id}: termination={sim.termination_reason} "
            f"messages={len(sim.messages)}{graded_part} [{verdict}]"
        )
    print(f"\n   manifest      {manifest_path.name}: {len(manifest_rows)} episode row(s)")
    if incident_totals:
        noted = ", ".join(f"{k}={v}" for k, v in sorted(incident_totals.items()) if v)
        print(f"   incidents     {noted or 'none'}")
    infra_classes = _infra_failure_classes(manifest_rows)
    if infra_classes:
        noted = ", ".join(f"{k}={v}" for k, v in sorted(infra_classes.items()))
        print(
            f"   infra classes {noted} — provider weather on frozen surfaces (τ excluded "
            f"these from grading); resume the round once it clears"
        )
    if incident_totals.get("zero_bridge_calls"):
        print(
            f"   ⚠ no-tools    {incident_totals['zero_bridge_calls']} episode(s) ended "
            f"without ONE tool call reaching the bridge. Every locked-domain task needs "
            f"tools, so this is a degenerate agent or a dead tunnel — read those "
            f"conversations before trusting this round."
        )
    park_rows = [row for row in manifest_rows if row.get("bridge_park_max_seconds") is not None]
    if park_rows:
        slowest = max(row["bridge_park_max_seconds"] for row in park_rows)
        print(
            f"   bridge park   max {slowest:.1f}s across {len(park_rows)} episode(s) "
            f"(per-call detail in bridge_calls.jsonl) — the latency the sandbox daemon "
            f"actually waits, and the number that explains a seam timeout"
        )
    effective_models = sorted(
        {m for row in manifest_rows for m in (row.get("effective_models") or [])}
    )
    effective_reasoning = sorted(
        {r for row in manifest_rows for r in (row.get("effective_reasoning") or [])}
    )
    if effective_models:
        locked_model = lock.agent_model.rsplit("/", 1)[-1]
        drift = [m for m in effective_models if m != locked_model]
        print(
            f"   agent config  effective model={','.join(effective_models)} "
            f"reasoning={','.join(effective_reasoning) or '?'} (lock: {lock.agent_model}, "
            f"thinking asserted-absent → sandbox default)"
        )
        if drift:
            print(
                f"   ⚠ config      effective model(s) {', '.join(drift)} differ from the "
                f"locked {lock.agent_model} — the sandbox ran something the freeze does not "
                f"describe. Stop and diagnose before citing this round."
            )
    # Printed beside the seam counters and never folded into them: these come from the
    # platform conversation, not from the bridge, and they are the only place a call the
    # sandbox refused can appear at all. Loud on purpose — a round carrying these graded
    # episodes in which the agent was denied its tools, and it must not read as healthy.
    disconnects = sum(row.get("sandbox_seam_disconnects") or 0 for row in manifest_rows)
    timeouts = sum(row.get("sandbox_seam_timeouts") or 0 for row in manifest_rows)
    unclassified = sum(row.get("sandbox_seam_unclassified") or 0 for row in manifest_rows)
    tool_errors = sum(row.get("sandbox_tool_errors") or 0 for row in manifest_rows)
    if disconnects or timeouts or unclassified or tool_errors:
        affected = sum(
            1
            for row in manifest_rows
            if (
                row.get("sandbox_seam_disconnects")
                or row.get("sandbox_seam_timeouts")
                or row.get("sandbox_seam_unclassified")
            )
        )
        print(
            f"   ⚠ sandbox     {tool_errors} tool error(s): {disconnects} unreachable-bridge, "
            f"{timeouts} bridge-too-slow, {unclassified} unclassified, across {affected} "
            f"episode(s) — the sandbox answered these calls itself, so τ never saw them. "
            f"Unreachable-bridge episodes ran with their tools denied: harness failures, not "
            f"agent ones. Bridge-too-slow calls may have recovered on τ's retry — read the "
            f"conversation before excluding the episode."
        )
    if is_platform:
        # The counters above can only see conversations that were actually fetched and
        # complete. An episode whose evidence is missing is UNVERIFIED, not clean — reporting
        # it silently as zero would recreate the exact failure these counters exist to catch
        # (a round reading healthy because the evidence of its sickness never arrived).
        unverified_rows = [row for row in manifest_rows if row.get("evidence_complete") is not True]
        if unverified_rows:
            named = ", ".join(sorted({row["tau_task_id"] for row in unverified_rows})[:6])
            print(
                f"   ⚠ seam-blind  {len(unverified_rows)} episode(s) whose platform "
                f"conversation is missing or incomplete ({named}"
                f"{' …' if len(unverified_rows) > 6 else ''}) — sandbox tool failures there "
                f"are invisible to the counters above. Re-fetch before diagnosing from them."
            )
    if orphaned_tasks:
        print(
            f"   orphans       {len(orphaned_tasks)} platform task(s) created but absent from "
            "results — τ retried past them; their sandboxes were archived"
        )
    if retitle_failures:
        print(
            f"   labels        {retitle_failures} retitle(s) failed; rows keep their fallback title"
        )
    if muted:
        print(
            "\n   Held-out round: nothing graded is printed here. Grading is persisted in\n"
            "   the vault by scripts/run_heldout.py and read at reveal, never before."
        )
    else:
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
        # --allow-dirty already declared this run's lineage soft; the rows say so
        # (arm_sha_ok=false), so the run reports rather than fails.
        return 0 if args.allow_dirty else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
