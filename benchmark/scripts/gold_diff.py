#!/usr/bin/env python3
"""Gold-vs-actual action diff for one batch round, whitespace-normalized.

tau compares `call_discoverable_*_tool` payloads as JSON STRINGS, so an agent call that is
semantically identical to gold registers as a MISS on formatting alone (seq-8 measured 39
of 85 misses to be formatting-only). Every prevalence figure must be computed against a
NORMALIZED comparison, never the raw miss list -- and the distinction that matters for
diagnosis is three-way, not two:

    MATCH      gold action performed, arguments semantically identical
    ARGS       gold action performed with the same tool, arguments differ semantically
    ABSENT     the gold action was never performed at all

"never called it" and "called it wrong" are different defects with different owning
layers, and they present identically in tau's miss list.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path


def canon(value):
    """Parse embedded JSON strings, then compare structurally."""
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.startswith(("{", "[")):
            try:
                return canon(json.loads(stripped))
            except json.JSONDecodeError:
                return stripped
        return stripped
    if isinstance(value, dict):
        return {k: canon(v) for k, v in value.items()}
    if isinstance(value, list):
        return [canon(v) for v in value]
    return value


def actual_calls(sim):
    """Every tool call in tau's graded trajectory: (name, canonicalized arguments)."""
    out = []
    for message in sim.get("messages") or []:
        for call in message.get("tool_calls") or []:
            out.append((call.get("name"), canon(call.get("arguments") or {})))
    return out


def classify(gold_action, calls):
    name = gold_action["name"]
    compare = gold_action.get("compare_args")
    gold_args = canon(gold_action.get("arguments") or {})
    same_name = [args for n, args in calls if n == name]
    if not same_name:
        return "ABSENT", None
    for args in same_name:
        if compare is None:
            if args == gold_args:
                return "MATCH", None
        else:
            if all(args.get(k) == gold_args.get(k) for k in compare):
                return "MATCH", None
    # same tool, different arguments -- show the closest call on the compared keys
    keys = compare or sorted(gold_args)
    shown = [{k: a.get(k) for k in keys} for a in same_name]
    return "ARGS", {"gold": {k: gold_args.get(k) for k in keys}, "actual": shown}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("round_dir", type=Path)
    ap.add_argument("--tasks", default="")
    ap.add_argument("--quiet", action="store_true", help="tallies only")
    args = ap.parse_args()
    wanted = {t.strip() for t in args.tasks.split(",") if t.strip()}

    graded = args.round_dir / "graded" / "updated_results.json"
    sims = json.loads(graded.read_text())["simulations"]
    tally = Counter()
    per_task = {}
    for sim in sorted(sims, key=lambda s: (s["task_id"], s.get("trial") or 0)):
        task = sim["task_id"]
        if wanted and task not in wanted:
            continue
        calls = actual_calls(sim)
        ri = sim["reward_info"]
        lines = []
        for check in ri.get("action_checks") or []:
            verdict, detail = classify(check["action"], calls)
            if check.get("action_match"):
                verdict = "MATCH"
            tally[verdict] += 1
            per_task.setdefault(task, Counter())[verdict] += 1
            if verdict != "MATCH":
                lines.append((verdict, check["action"]["name"], detail))
        if not args.quiet:
            print(f"\n{task} t{sim.get('trial')}  reward={ri.get('reward')}  "
                  f"calls={len(calls)}  tools={sorted({n for n, _ in calls})}")
            for verdict, name, detail in lines:
                print(f"   {verdict:6s} {name}")
                if detail:
                    print(f"          gold   {json.dumps(detail['gold'], sort_keys=True)}")
                    for a in detail["actual"][:3]:
                        print(f"          actual {json.dumps(a, sort_keys=True)}")
    print("\n=== gold-action verdicts, normalized ===")
    for task, counts in sorted(per_task.items()):
        print(f"  {task}: " + " ".join(f"{k}={v}" for k, v in sorted(counts.items())))
    print("  TOTAL: " + " ".join(f"{k}={v}" for k, v in sorted(tally.items())))


if __name__ == "__main__":
    main()
