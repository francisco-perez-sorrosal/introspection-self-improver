#!/usr/bin/env python3
"""Per-round behavioural counters for seq 12's diagnosed mechanisms.

Committed so no round re-derives them and every falsifier is scored the same way twice.
Every counter is reported per-episode so a record can state it as a DELTA against the
prior round (contract/protocol.md step 4: a falsifier keyed on a level fires on a
pre-existing condition and diagnoses nothing).

Reads a graded round directory only; computes no reward.
"""
from __future__ import annotations
import argparse, json, sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from gold_diff import canon, actual_calls  # noqa: E402

# Optional keys the agent volunteers on discoverable-tool payloads (target T2).
VOLUNTEERED = ("reason", "waive_early_closure_fee")
# Catch-all members of the transfer_to_human_agents enum (target T4). Membership is read
# off the round's own calls, not hardcoded policy: these are the two the agent reaches for.
CATCHALL = {"customer_requests_human_no_specific_reason",
            "kb_search_unsuccessful_customer_requests_transfer"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("round_dir", type=Path)
    ap.add_argument("--tasks", default="")
    args = ap.parse_args()
    wanted = {t.strip() for t in args.tasks.split(",") if t.strip()}
    sims = json.loads((args.round_dir / "graded" / "updated_results.json").read_text())["simulations"]

    n_ep = 0
    kb = Counter()            # KB_search calls per episode
    msgs = Counter()
    volunteered_eps = set()   # (task, trial) whose discoverable payload carries a VOLUNTEERED key
    volunteered_calls = 0
    closure_eps = set()
    closure_calls = 0
    catchall_calls = 0
    specific_calls = 0
    transfer_eps = set()
    name_queries = defaultdict(set)   # (task,trial) -> distinct KB_search query strings
    docs_seen = defaultdict(set)      # (task,trial) -> distinct doc ids the KB returned
    total_calls = Counter()

    import re
    DOC_ID = re.compile(r"ID:\s*(doc_[A-Za-z0-9_()\-]+)")
    for s in sims:
        if s["reward_info"].get("reward_basis") is None:
            continue                      # ungraded episode
        tid, tr = s["task_id"], s.get("trial")
        if wanted and tid not in wanted:
            continue
        n_ep += 1
        calls = actual_calls(s)
        total_calls[(tid, tr)] = len(calls)
        msgs[(tid, tr)] = len(s.get("messages") or [])
        for m in s.get("messages") or []:
            c = m.get("content")
            if isinstance(c, str) and "ID: doc_" in c:
                docs_seen[(tid, tr)].update(DOC_ID.findall(c))
        for name, a in calls:
            if name == "KB_search":
                kb[(tid, tr)] += 1
                q = a.get("query")
                if isinstance(q, str):
                    name_queries[(tid, tr)].add(q.strip().lower())
            if name in ("call_discoverable_agent_tool", "call_discoverable_user_tool"):
                inner = a.get("arguments")
                if isinstance(inner, dict) and any(k in inner for k in VOLUNTEERED):
                    volunteered_eps.add((tid, tr)); volunteered_calls += 1
                    # Precise T2 counter. The general one above also catches tools whose
                    # OWN schema marks `reason` required (task_037's replacement-card and
                    # dispute calls), which the target does not touch; close_bank_account_7392
                    # is the call whose unlock text marks both keys `(optional)` and whose
                    # gold payload carries neither.
                    if a.get("agent_tool_name") == "close_bank_account_7392":
                        closure_eps.add((tid, tr)); closure_calls += 1
            if name == "transfer_to_human_agents":
                transfer_eps.add((tid, tr))
                r = a.get("reason")
                if r in CATCHALL: catchall_calls += 1
                elif r: specific_calls += 1

    def per_ep(c): return sum(c.values()) / n_ep if n_ep else 0.0
    print(f"round               {args.round_dir}")
    print(f"graded episodes     {n_ep}")
    print(f"KB_search/episode   {per_ep(kb):.2f}")
    print(f"distinct queries/ep {sum(len(v) for v in name_queries.values())/n_ep:.2f}")
    ndocs = sum(len(v) for v in docs_seen.values())
    nkb = sum(kb.values())
    print(f"distinct KB docs/ep {ndocs/n_ep:.2f}")
    print(f"new docs per search {ndocs/nkb:.2f}   <- C3's counter: does searching differently surface different documents")
    print(f"tool calls/episode  {per_ep(total_calls):.2f}")
    print(f"messages/episode    {per_ep(msgs):.2f}")
    print()
    print(f"T2 volunteered-optional-arg EPISODES  {len(volunteered_eps)}  calls {volunteered_calls}")
    print(f"   {sorted(volunteered_eps)}")
    print(f"T2 PRECISE — close_bank_account_7392 carrying reason/waive_early_closure_fee: "
          f"{len(closure_eps)} episodes, {closure_calls} calls")
    print(f"   {sorted(closure_eps)}")
    print(f"T4 transfer episodes {len(transfer_eps)} — catch-all reason calls {catchall_calls}, "
          f"specific {specific_calls}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
