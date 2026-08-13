"""Experiment identity: one experiment is one freeze, and the results tree says so.

results/ carries one level above generations — results/experiment_<id>/generation_NNN/ —
so runs produced under different freezes (models, retrieval configs, splits, trial
counts) can never interleave in one directory. The id comes from benchmark_lock.yaml
(`experiment.id`): the lock defines the freeze, so the lock names the experiment, and
the runner derives the path rather than trusting a caller to choose it.

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
from datetime import datetime, timezone
from pathlib import Path

import yaml

from tau_adapter.lock import BENCHMARK_DIR, REPO_ROOT, Lock

RESULTS_ROOT = REPO_ROOT / "results"
SPLIT_MANIFEST_PATH = BENCHMARK_DIR / "split_manifest.yaml"
SNAPSHOT_NAME = "experiment.yaml"

#: Written only after τ's runner returned, so it doubles as the round's completion sentinel:
#: results.json without it is an interrupted run, which resumes rather than refuses.
COMPLETION_SENTINEL = "run_metadata.json"

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
            "benchmark_lock.yaml experiment.id — a different freeze means a new "
            "experiment id there, not a different output path."
        )
    return results_root.resolve() / expected


def freeze_fingerprint(lock: Lock, split_manifest_path: Path = SPLIT_MANIFEST_PATH) -> str:
    """A digest of the parsed freeze: every lock value plus the split manifest.

    Parsed values, not file bytes, so a comment edit never reads as a new freeze while any
    value change — dropping PROVISIONAL included — does.
    """
    split = yaml.safe_load(split_manifest_path.read_text(encoding="utf-8")) or {}
    material = json.dumps({"lock": lock.raw, "split_manifest": split}, sort_keys=True, default=str)
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
    snapshot_path = exp_dir / SNAPSHOT_NAME
    fingerprint = freeze_fingerprint(lock, split_manifest_path)
    if snapshot_path.exists():
        recorded = yaml.safe_load(snapshot_path.read_text(encoding="utf-8")) or {}
        if recorded.get("id") != lock.experiment_id or recorded.get("fingerprint") != fingerprint:
            raise ExperimentError(
                f"the freeze no longer matches {snapshot_path.name} in "
                f"results/{exp_dir.name}: a lock or split-manifest value changed after "
                "this experiment started. A freeze is never re-decided under the same "
                "experiment id — set a new experiment.id in benchmark_lock.yaml and rerun."
            )
        return f"freeze snapshot verified ({SNAPSHOT_NAME})"
    if lock.provisional:
        return "PROVISIONAL — no freeze snapshot written or enforced"
    _write_snapshot(snapshot_path, lock, fingerprint)
    return f"freeze snapshot created ({SNAPSHOT_NAME})"


def prepare_round_dir(out_dir: Path, overwrite: bool) -> str | None:
    """Decide what an existing round directory means, and make it safe to run into.

    Three cases, told apart by the completion sentinel rather than guessed:

      empty / absent      → fresh round; create it.
      sentinel present    → a completed record. Refused without --overwrite, because a
                            previous round is not scratch.
      results, no sentinel → an interrupted run. Kept as-is: τ's own checkpoint resume
                            (keyed (trial, task_id, seed), `auto_resume`) re-runs only what
                            is missing, and replaces infrastructure-error placeholders.

    --overwrite keeps its rm -rf semantics for intentional restarts only.
    Returns a one-line status for the run banner, or None for a fresh directory.
    """
    if overwrite and out_dir.exists():
        shutil.rmtree(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        return "previous contents overwritten"
    if not out_dir.exists() or not any(out_dir.iterdir()):
        out_dir.mkdir(parents=True, exist_ok=True)
        return None
    if (out_dir / COMPLETION_SENTINEL).exists():
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
    right code but records the wrong arm: the lineage softness v2 §2.5 documents, caught
    here at pre-flight instead of after the money is spent.
    """
    try:
        subprocess.run(  # noqa: S603, S607 - best effort; a failed fetch just means stale info
            ["git", "fetch", "--quiet", "origin", "main"],
            cwd=repo_root,
            capture_output=True,
            timeout=30,
            check=False,
        )
        proc = subprocess.run(  # noqa: S603, S607
            ["git", "rev-parse", "origin/main"],
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
    base commit, so uncommitted recipe edits make every lineage claim soft (v2 §2.5). The
    check is scoped to what is actually served — results/ filling up is not dirt.
    """
    head = subprocess.run(  # noqa: S603, S607 - operator's git, on the repo being run
        ["git", "rev-parse", "HEAD"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        timeout=30,
        check=True,
    ).stdout.strip()
    porcelain = subprocess.run(  # noqa: S603, S607
        ["git", "status", "--porcelain", "--", *SERVED_RECIPE_PATHS],
        cwd=repo_root,
        capture_output=True,
        text=True,
        timeout=30,
        check=True,
    ).stdout
    dirty = [line.strip() for line in porcelain.splitlines() if line.strip()]
    return head, dirty


def _write_snapshot(path: Path, lock: Lock, fingerprint: str) -> None:
    header = (
        "# Written by the runner on this experiment's first non-PROVISIONAL run. It pins\n"
        "# the freeze every result in this directory was produced under; a later run whose\n"
        "# parsed lock or split manifest differs is refused. The summary is for humans —\n"
        "# the fingerprint is what is compared.\n"
    )
    body = yaml.safe_dump(
        {
            "id": lock.experiment_id,
            "created": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
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
