#!/usr/bin/env python3
"""Diagnosis-side reader for one batch round.

Prints, per task and trial: reward, the graded action_checks (gold action, matched or
missed, with a whitespace-normalized argument comparison so JSON-string formatting misses
do not read as semantic misses), db_check, termination, message count, Pi-local call
count, and the Introspection conversation id — everything protocol step 3 asks for before
any conversation is exported.

Usage: round_read.py <round dir> [--tasks task_014,task_057] [--misses]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def norm(value) -> str:
    """Whitespace-normalized JSON for argument comparison (seq-8 reading correction 1)."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def load(round_dir: Path):
    graded = round_dir / "graded" / "updated_results.json"
    if not graded.is_file():
        graded = round_dir / "results.json"
    sims = json.loads(graded.read_text())["simulations"]
    manifest = {}
    mpath = round_dir / "episode_manifest.jsonl"
    if mpath.is_file():
        for line in mpath.read_text().splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            manifest[(row.get("tau_task_id"), row.get("trial"))] = row
    return sims, manifest


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("round_dir", type=Path)
    ap.add_argument("--tasks", default="")
    ap.add_argument(
        "--misses", action="store_true", help="only print missed gold actions"
    )
    args = ap.parse_args()

    wanted = {t.strip() for t in args.tasks.split(",") if t.strip()}
    sims, manifest = load(args.round_dir)
    by_task: dict[str, list] = {}
    for s in sims:
        by_task.setdefault(s["task_id"], []).append(s)

    total_pass = total = 0
    for task in sorted(by_task, key=lambda t: int(t.split("_")[1])):
        if wanted and task not in wanted:
            continue
        trials = sorted(by_task[task], key=lambda s: s.get("trial") or 0)
        passes = sum(1 for s in trials if (s["reward_info"].get("reward") or 0) > 0)
        total_pass += passes
        total += len(trials)
        print(
            f"\n=== {task}  {passes}/{len(trials)}  basis={','.join(trials[0]['reward_info']['reward_basis'])}"
        )
        for s in trials:
            ri = s["reward_info"]
            row = manifest.get((task, s.get("trial")), {})
            db = ri.get("db_check") or {}
            print(
                f"  t{s.get('trial')}  reward={ri.get('reward')}  db_match={db.get('db_match')}"
                f"  msgs={row.get('messages')}  pi_local={row.get('pi_local_calls')}"
                f"  term={str(s.get('termination_reason')).split('.')[-1]}"
                f"  conv={row.get('introspection_task_id')}"
            )
            for check in ri.get("action_checks") or []:
                act = check["action"]
                matched = check.get("action_match")
                if args.misses and matched:
                    continue
                mark = "OK " if matched else "MISS"
                cmp_args = act.get("compare_args")
                shown = act.get("arguments")
                if cmp_args:
                    shown = {
                        k: v
                        for k, v in (act.get("arguments") or {}).items()
                        if k in cmp_args
                    }
                print(f"      {mark} {act['requestor']}:{act['name']} {norm(shown)}")
    print(
        f"\n--- round total: {total_pass}/{total} episodes"
        f" ({100.0 * total_pass / total:.1f}%)"
        if total
        else ""
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
