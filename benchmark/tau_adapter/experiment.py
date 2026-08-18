"""Experiment identity: one experiment is one freeze, and the results tree says so.

results/ carries one level above generations — results/experiment_<id>/generation_NNN/ —
so runs produced under different freezes (models, retrieval configs, splits, trial
counts) can never interleave in one directory. The id derives from benchmark_lock.yaml
(`experiment.seq` + `experiment.name`, e.g. 001_bm25-sonnet46): the lock defines the
freeze, so the lock names the experiment, and the runner derives the path rather than
trusting a caller to choose it.

Once the lock stops being PROVISIONAL, the first run into an experiment snapshots the
parsed freeze (lock values plus split manifest) into experiment.yaml, and every later
run must match it. Values are compared, never file bytes, so a comment edit cannot trip
the check while a re-decided frozen value refuses the run — the enforcement form of the
lock's own header: start a new experiment instead.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import yaml

from tau_adapter import manifest as manifestmod
from tau_adapter.lock import BENCHMARK_DIR, REPO_ROOT, Lock

RESULTS_ROOT = REPO_ROOT / "results"
SPLIT_MANIFEST_PATH = BENCHMARK_DIR / "split_manifest.yaml"
SNAPSHOT_NAME = "experiment.yaml"

#: Written only after τ's runner returned, so it doubles as the round's completion sentinel:
#: results.json without it is an interrupted run, which resumes rather than refuses.
COMPLETION_SENTINEL = "run_metadata.json"

#: The held-out wrapper's console log. Created before the runner starts (it is the redirect
#: target), so the round-directory lifecycle must not read its presence as prior results.
CONSOLE_LOG = "console.log"

#: Grading output, derived from results.json. Dropped with the sentinel when a round turns
#: out to be incomplete, because grading computed over non-measurements is not the round's.
GRADED_DIR = "graded"

#: The surface `introspection dev` serves: the Recipe tree plus the Runtime manifest that
#: resolves it. Dirt anywhere else cannot change what an episode runs.
SERVED_RECIPE_PATHS = ("target-agent", ".introspection")


class ExperimentError(RuntimeError):
    pass


def experiment_dirname(lock: Lock) -> str:
    return f"experiment_{lock.experiment_id}"


def experiment_dir_for(out_dir: Path, lock: Lock, results_root: Path = RESULTS_ROOT) -> Path | None:
    """The experiment directory an output path must live under.

    Returns None for paths outside results/ (tests, scratch dirs) — those are not records
    and are none of this module's business. A path inside results/ but outside the lock's
    experiment is refused: the location is derived from the lock, never chosen per run.
    """
    try:
        relative = out_dir.resolve().relative_to(results_root.resolve())
    except ValueError:
        return None
    expected = experiment_dirname(lock)
    if not relative.parts or relative.parts[0] != expected:
        raise ExperimentError(
            f"--out resolves to results/{relative}, but the lock's experiment is "
            f"{lock.experiment_id!r}: every run under results/ lives at "
            f"results/{expected}/<generation>/<run>. The path derives from "
            "benchmark_lock.yaml experiment.seq + experiment.name — a different freeze "
            "means a new experiment (bump seq) there, not a different output path."
        )
    return results_root.resolve() / expected


def freeze_fingerprint(lock: Lock, split_manifest_path: Path = SPLIT_MANIFEST_PATH) -> str:
    """A digest of the parsed freeze: every lock value plus the split manifest.

    Parsed values, not file bytes, so a comment edit never reads as a new freeze while any
    value change — dropping PROVISIONAL included — does. The lock's `operational:` block
    is excluded: those are recorded defaults an operator may change mid-experiment (the
    effective per-run values live in run_metadata.json), and hashing them would turn a
    wall-clock knob into freeze drift.
    """
    frozen_view = {key: value for key, value in lock.raw.items() if key != "operational"}
    split = yaml.safe_load(split_manifest_path.read_text(encoding="utf-8")) or {}
    material = json.dumps(
        {"lock": frozen_view, "split_manifest": split}, sort_keys=True, default=str
    )
    return "sha256:" + hashlib.sha256(material.encode("utf-8")).hexdigest()


def enforce_snapshot(
    lock: Lock,
    out_dir: Path,
    results_root: Path = RESULTS_ROOT,
    split_manifest_path: Path = SPLIT_MANIFEST_PATH,
) -> str | None:
    """Verify the experiment's freeze snapshot, creating it when the freeze is real.

    Always verified when present — a frozen experiment cannot be quietly re-entered, not
    even by flipping the lock back to PROVISIONAL. Created only by a non-PROVISIONAL lock:
    bring-up runs land unenforced, and the runner's PROVISIONAL banner already says so.
    Returns a one-line status for the run banner, or None for paths outside results/.
    """
    exp_dir = experiment_dir_for(out_dir, lock, results_root)
    if exp_dir is None:
        return None
    return _enforce_snapshot_at(exp_dir, lock, split_manifest_path)


def enforce_snapshot_for_experiment(
    lock: Lock,
    results_root: Path = RESULTS_ROOT,
    split_manifest_path: Path = SPLIT_MANIFEST_PATH,
) -> str:
    """Verify/create the freeze snapshot by experiment id, independent of any output path.

    Held-out rounds write outside results/ by design (D9), so their out_dir can never
    resolve to the experiment directory — yet the measurement they produce is the one the
    freeze exists to protect. This anchors them to the same in-tree snapshot every other
    round verifies, so a lock or partition change between generations refuses the round
    instead of silently producing non-comparable measurements.
    """
    exp_dir = results_root.resolve() / experiment_dirname(lock)
    return _enforce_snapshot_at(exp_dir, lock, split_manifest_path)


def _enforce_snapshot_at(exp_dir: Path, lock: Lock, split_manifest_path: Path) -> str:
    snapshot_path = exp_dir / SNAPSHOT_NAME
    fingerprint = freeze_fingerprint(lock, split_manifest_path)
    if snapshot_path.exists():
        recorded = yaml.safe_load(snapshot_path.read_text(encoding="utf-8")) or {}
        if recorded.get("id") != lock.experiment_id or recorded.get("fingerprint") != fingerprint:
            raise ExperimentError(
                f"the freeze no longer matches {snapshot_path.name} in "
                f"results/{exp_dir.name}: a lock or split-manifest value changed after "
                "this experiment started. A freeze is never re-decided under the same "
                "experiment id — bump experiment.seq in benchmark_lock.yaml and rerun."
            )
        return f"freeze snapshot verified ({SNAPSHOT_NAME})"
    if lock.provisional:
        return "PROVISIONAL — no freeze snapshot written or enforced"
    _write_snapshot(snapshot_path, lock, fingerprint, split_manifest_path)
    return f"freeze snapshot created ({SNAPSHOT_NAME})"


def round_measured(out_dir: Path, expected_episodes: int) -> bool:
    """Did this round actually measure every episode it owed?

    Completed-episode rows counted from the manifest — row counts only, so this is safe
    for the sealed held-out vault as well as for observable rounds: nothing graded is
    read. The single definition of "measured" for both lanes; they diverged once, and the
    divergence cost an operator a round.
    """
    rows = manifestmod.read_manifest(out_dir)
    return sum(1 for row in rows if row.get("completed")) >= expected_episodes


def prepare_round_dir(
    out_dir: Path, overwrite: bool, *, expected_episodes: int | None = None
) -> str | None:
    """Decide what an existing round directory means, and make it safe to run into.

    Four cases, told apart by the completion sentinel and the manifest rather than guessed:

      empty / absent      → fresh round; create it.
      sentinel present,   → a completed record. Refused without --overwrite, because a
      round measured        previous round is not scratch.
      sentinel present,   → the runner RETURNED but the round holds non-measurements — τ
      round incomplete      gave up on an episode after its retries and wrote an
                            `infrastructure_error` placeholder. **The sentinel means
                            "runner returned", never "measured."** The sentinel and the
                            grading derived from the incomplete results are dropped, and
                            the interrupted-run path below resumes.
      results, no sentinel → an interrupted run. Kept as-is: τ's own checkpoint resume
                            (keyed (trial, task_id, seed), `auto_resume`) re-runs only what
                            is missing, and replaces infrastructure-error placeholders.

    `expected_episodes` is what makes the third case distinguishable; without it (a run
    whose episode count is not known up front) the sentinel is still taken at face value
    and the round is refused, which is the safe direction.

    Why the third case exists at all: provider weather on the FROZEN user-simulator surface
    can kill one episode past τ's retry budget, and before this the only way forward was
    --overwrite — re-spending, and re-drawing, every healthy episode in the round to
    recover one. The held-out lane already implemented exactly this recovery privately
    (`heldout.run_round`); the batch lane did not, so an operator hit the refusal with a
    35-of-36 baseline round in hand. One rule, one place, both lanes.

    --overwrite keeps its rm -rf semantics for intentional restarts only.
    Returns a one-line status for the run banner, or None for a fresh directory.
    """
    if overwrite and out_dir.exists():
        shutil.rmtree(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        return "previous contents overwritten"
    evidence = out_dir.exists() and any(p.name != CONSOLE_LOG for p in out_dir.iterdir())
    if not evidence:
        out_dir.mkdir(parents=True, exist_ok=True)
        return None
    if (out_dir / COMPLETION_SENTINEL).exists():
        if expected_episodes is not None and not round_measured(out_dir, expected_episodes):
            measured = sum(
                1 for row in manifestmod.read_manifest(out_dir) if row.get("completed")
            )
            (out_dir / COMPLETION_SENTINEL).unlink()
            shutil.rmtree(out_dir / GRADED_DIR, ignore_errors=True)
            return (
                f"resuming an INCOMPLETE round ({measured}/{expected_episodes} episodes "
                "measured) — the sentinel says the runner returned, not that the round was "
                "measured; τ re-runs only the missing (trial, task, seed) pairs and "
                "re-spends nothing already completed"
            )
        raise ExperimentError(
            f"{out_dir} already holds a completed run ({COMPLETION_SENTINEL} present). "
            "Pass --overwrite to replace it, or point --out at a new directory — a "
            "previous round's record is not scratch."
        )
    return "resuming interrupted run — τ re-runs only the missing (trial, task, seed) pairs"


def pushed_main_sha(repo_root: Path = REPO_ROOT) -> str | None:
    """What origin/main points at, freshly fetched — best effort, None when unknowable.

    The platform mints immutable runtime versions from pushed main (`recipe_ref: main`), so
    on the dev lane this is the commit `recipe_git_commit_sha` will name — while the dev
    overlay serves the work-tree's bytes. A HEAD ahead of origin/main therefore runs the
    right code but records the wrong arm — lineage softness, caught here at pre-flight
    instead of after the money is spent.
    """
    try:
        subprocess.run(
            ["git", "fetch", "--quiet", "origin", "main"],  # noqa: S607 - operator's git
            cwd=repo_root,
            capture_output=True,
            timeout=30,
            check=False,
        )
        proc = subprocess.run(
            ["git", "rev-parse", "origin/main"],  # noqa: S607 - operator's git
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    sha = proc.stdout.strip()
    return sha if proc.returncode == 0 and sha else None


def generation_of(out_dir: Path) -> str | None:
    """The generation directory component of a results path, if any."""
    for part in Path(out_dir).parts:
        if part.startswith("generation"):
            return part
    return None


def repo_arm_state(repo_root: Path = REPO_ROOT) -> tuple[str, list[str]]:
    """The arm this run would serve: HEAD's sha, plus any dirt on the served recipe surface.

    `introspection dev` serves the git work-tree while `recipe_git_commit_sha` names the
    base commit, so uncommitted recipe edits make every lineage claim soft. The check is
    scoped to what is actually served — results/ filling up is not dirt.
    """
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"],  # noqa: S607 - operator's git, on the repo being run
        cwd=repo_root,
        capture_output=True,
        text=True,
        timeout=30,
        check=True,
    ).stdout.strip()
    porcelain = subprocess.run(  # noqa: S603
        ["git", "status", "--porcelain", "--", *SERVED_RECIPE_PATHS],  # noqa: S607
        cwd=repo_root,
        capture_output=True,
        text=True,
        timeout=30,
        check=True,
    ).stdout
    dirty = [line.strip() for line in porcelain.splitlines() if line.strip()]
    return head, dirty


def _write_snapshot(path: Path, lock: Lock, fingerprint: str, split_manifest_path: Path) -> None:
    header = (
        "# Written by the runner on this experiment's first non-PROVISIONAL run. It pins\n"
        "# the freeze every result in this directory was produced under; a later run whose\n"
        "# parsed lock or split manifest differs is refused. The summary is for humans —\n"
        "# the fingerprint is what is compared.\n"
    )
    body = yaml.safe_dump(
        {
            "id": lock.experiment_id,
            "created": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "fingerprint": fingerprint,
            "summary": {
                "domain": lock.domain,
                "retrieval_config": lock.retrieval_config,
                "agent_model": lock.agent_model,
                "user_llm": lock.user_llm,
                "num_trials": lock.num_trials,
                "seed": lock.seed,
                "benchmark_commit": lock.commit,
            },
        },
        sort_keys=False,
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(header + body, encoding="utf-8")
    _write_config_copies(path.parent, lock, split_manifest_path)


def _write_config_copies(exp_dir: Path, lock: Lock, split_manifest_path: Path) -> None:
    """Value-faithful copies of the lock and partition beside the snapshot (protocol §27).

    A results directory should describe its own configuration without needing the repo at
    the right commit. Values, not file bytes — consistent with the fingerprint doctrine —
    so comments are dropped and what is written is exactly what was in force.
    """
    copy_header = (
        "# Value snapshot written at freeze time by the runner (comments dropped; the\n"
        "# canonical commented file lives in benchmark/). Values cannot drift from the\n"
        "# experiment: the freeze fingerprint refuses any change.\n"
    )
    (exp_dir / "benchmark_lock.yaml").write_text(
        copy_header + yaml.safe_dump(lock.raw, sort_keys=False), encoding="utf-8"
    )
    split = yaml.safe_load(split_manifest_path.read_text(encoding="utf-8")) or {}
    (exp_dir / "split_manifest.yaml").write_text(
        copy_header + yaml.safe_dump(split, sort_keys=False), encoding="utf-8"
    )
