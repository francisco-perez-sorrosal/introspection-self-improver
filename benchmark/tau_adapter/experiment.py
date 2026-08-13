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
from datetime import datetime, timezone
from pathlib import Path

import yaml

from tau_adapter.lock import BENCHMARK_DIR, REPO_ROOT, Lock

RESULTS_ROOT = REPO_ROOT / "results"
SPLIT_MANIFEST_PATH = BENCHMARK_DIR / "split_manifest.yaml"
SNAPSHOT_NAME = "experiment.yaml"


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
