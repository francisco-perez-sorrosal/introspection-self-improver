# Calibration pilot — luna-H0 on the 28 non-partition tasks (2026-08-14)

Pre-freeze pilot required by D12 consequence (c): the D11 sizing was calibrated on
seq-2 Sonnet-pair actuals, so the model swap re-prices its calibration facts —
baseline pass rate, episode cost, wall-clock. This pilot re-measures them for
**$1.06** before the freeze. Diagnostic, never reportable: it ran under the
PROVISIONAL lock (banner recorded in `run_metadata.json`), on the local lane at
`--max-concurrency 10`, against arm `2ea2475` — the current `h0-baseline`, i.e.
exactly luna-H0.

## Why these 28 tasks and not the held-out 28

Deliberate, and firewall-required. Measuring the *frozen held-out set* pre-freeze —
and reading its per-task results, as this analysis does — would burn it before the
experiment starts (CLAUDE.md invariant: nothing held-out reaches the orchestrator
before reveal). The pilot therefore uses exactly the 28 tasks in **nobody's
partition**: the 8 eligible-but-unused stratification leftovers (task_001, 002, 004,
053, 060, 074, 079, 080) plus the 20 seq-2-burnt tasks (excluded from seq 3
everywhere by the fresh-pool discipline; their seq-2 results are public since the
reveal, and H0 is fixed, so measuring it on them tunes nothing). The sizing consumes
the pool's difficulty *distribution*, not task identities; this set is drawn from
the same stratified pool as the held-out set. Caveat stated: it is not a uniform
random pool sample (20 are seq-2's stratified picks, 8 are leftovers).

## Results (n=28, one trial each, graded by `tau2 evaluate-trajs` via `grade.py`)

| measurement | luna-H0 (this pilot) | Sonnet pair (seq-2 actuals) |
|---|---|---|
| baseline pass | **7/28 = 25.0%** (Wilson 95%: 13–43%) | 3/8 held-out H0; ~27–37% pooled |
| cost / episode (local) | **$0.038 mean / $0.026 median** (max $0.111; total $1.06) | $0.62 mean / $0.53 median |
| duration / episode | 94 s mean / 75 s median | 168 s mean |
| messages / episode | 55 mean | ~52 mean |

Episodes are the *same length* (55 msgs) — the 16× cost drop is pricing, not
brevity. Wall-clock ≈ 1.8× faster per episode.

Per-task: pass = 001, 002, 004, 008, 035, 036, 089; fail = the other 21.

**Overlap with seq-2 outcomes (n=20; Sonnet side mixes H0–H2 harnesses — batch
tasks were graded under the generation that ran them):** luna 4/20 vs Sonnet 5/20,
agreement 17/20. Luna-only pass: task_008. Sonnet-only: task_017 (the known
user-sim-stochasticity flip from the seq-2 analysis) and task_058. The two models
largely fail the same tasks — no sign that luna performs the harness behaviours
natively enough to erase the signal.

## Verdict — the D11 sizing carries unchanged

- **No saturation.** 25% baseline leaves ~75% headroom; the D12 sensitivity worry
  (B/B regime) did not materialize at H0. The harness remains plausibly the binding
  constraint.
- **Power re-checked at the measured baseline** (`power_sim.py` scenarios with the
  mixture shifted −0.075 → sim baseline ≈ 26.5%): G=5/T=28 reads dir 0.97 /
  ≥2-task 0.95 / trend@.05 0.83 under the optimistic scenario (vs 0.82 at the
  Sonnet-calibrated baseline); null stays calibrated at 5%/10%. **G=5, B=8, T=28
  stands.**
- **Budget re-priced.** Powered local side: 168 × ~$0.04 ≈ **$7** (was ≈$104 at
  Sonnet rates). Platform-lane luna pricing is unknown from here and re-prices at
  the first batch episode (conversation billing).
- **One argument honestly retired:** at luna prices, *cost* no longer separates the
  powered tier from full — both are cheap. What still decides T=28 for seq 3 is the
  fresh-pool discipline (T=47 + 50 batch tasks need 97 > 76 fresh tasks, so full
  cannot avoid reusing tuned-on/revealed tasks) and wall-clock. The full run's case
  strengthens for seq 4.

## Provenance

- Run: `generation_000/calibration_pilot/` (manifest, results, pi_sessions,
  run_metadata) — created by `tau_adapter/run.py --task-ids <28> --transport local
  --max-concurrency 10` under the PROVISIONAL seq-3 lock.
- Sonnet comparison values: `experiment_002_bm25-sonnet46` held-out matrix (H0
  column) and batch `graded/updated_results.json` files.
- Power re-check: `benchmark/scripts/power_sim.py` scenario machinery with
  `shift=-0.075` (the committed harder-pool sensitivity mechanism at the measured
  luna baseline), 8,000 sims/cell.
