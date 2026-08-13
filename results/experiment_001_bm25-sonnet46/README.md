# Experiment 001 — bm25-sonnet46 (closed)

The bring-up freeze. Closed 2026-08-13 without a graded round, superseded by the
generation-based evaluation protocol (`self_improving_agent_evaluation_protocol.md`;
plan: `SIA_EVALUATION_PLAN.md`) before any split round ran. Its lock and split manifest
remain frozen as the record of what this experiment was; the next freeze is experiment
002 at debug scale.

## What this directory holds

Twelve ad-hoc platform-lane episodes across three tasks (`task_001`–`task_003` × 4
trials, $4.09 total), run under the M1 freeze — `bm25` retrieval, Sonnet 4.6 agent,
Sonnet 4.5 user simulator, `num_trials: 4` — to prove the M2 evidence spine, not to
produce a number. Every manifest row joins its τ episode to a named platform
conversation with cost, span metrics, and commit lineage (`arm_sha_ok: true`
throughout); one round also captured a real τ infrastructure retry (5 tasks created,
4 referenced, 1 orphan) with its incident counters.

No number here is a result: every row carries `split: null` (no split round ever ran),
and rewards at `num_trials: 4` are draws per episode by the project's own measurement.

## Gate record

- **A.0a (pipe semantics): PASS** — 110-test adapter suite + mock smoke 4/4.
- **A.0b (cross-lane consistency): FAIL** — aggregates agreed within Wilson noise
  (pass¹ 0.083 local vs 0.25 platform, N=12 per lane) but 3/12 platform episodes hit
  the 600 s ceiling on rendezvous stalls. The remedy (narration reassembled with its
  tool call, `7aee297`) landed after the gate run; under the evaluation protocol A.0b
  is an on-demand diagnostic, not a blocking gate (plan D4).

The verdict files were removed from the working tree with the 2026-08-13 fresh start;
recover them from git history:

```bash
git show 984c598^:results/experiment_bm25-sonnet46/generation_000/gates/a0a.json
git show 984c598^:results/experiment_bm25-sonnet46/generation_000/gates/a0b.json
```
