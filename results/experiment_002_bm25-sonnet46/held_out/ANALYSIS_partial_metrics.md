# Sub-reward evolution of the held-out set — post-reveal analysis (2026-08-14)

Derived after the reveal from `held_out/generation_NNN/graded/updated_results.json`
(the canonical grading record; the per-simulation lines in each round's `console.log`
render from these same files). Same fixed 8 tasks at every generation: 7 DB-basis,
1 ACTION-basis (task_035). All figures label their set and N; T=8 resolves only
≥2-task effects, so everything here is diagnostic and directional, never a claim.
Mechanized since 2026-08-14 by `tau_adapter/process_metrics.py` (written at reveal;
`scripts/reveal.py --derive-only` backfills) into `process_metrics_by_generation.csv`
and `process_metrics_by_task.csv` beside this file — those CSVs are authoritative
where this prose and they disagree. (One correction they caught: the DB-match row
below originally counted the ACTION-basis task's incidental DB flag; fixed.)

## Aggregate evolution (held-out, N=8 tasks per generation)

| metric | H0 | H1 | H2 | H3 | shape |
|---|---|---|---|---|---|
| tasks passed (of 8) | 3 | 3 | 2 | 2 | decline |
| mean reward % | 37.5 | 37.5 | 25.0 | 25.0 | decline |
| DB match (of 7 DB-basis) | 2 (28.6%) | 2 (28.6%) | 1 (14.3%) | 1 (14.3%) | decline |
| gold actions matched % (93 actions) | 75.3 | 67.7 | 69.9 | 76.3 | U, ends +1.0 pp |
| write actions matched % (60 writes) | 73.3 | 63.3 | 65.0 | 71.7 | U, ends −1.6 pp |
| mean per-task partial action reward % | 75.8 | 72.5 | 70.3 | 76.5 | U, ends +0.7 pp |
| KB_search calls (total) | 54 | 47 | 63 | 65 | **up 20%** |
| discoverable-tool operations (total) | 67 | 61 | 70 | 79 | **up 18%** |
| transfers to human (total) | 3 | 2 | 1 | 1 | **down 67%** |
| messages per episode (mean) | 52.5 | 49.9 | 54.1 | 56.9 | up 8% |
| cost per episode USD (mean) | 0.65 | 0.50 | 0.64 | 0.70 | up 8% |

## Per-task action-match matrix (P = passed, db = DB matched)

| task | H0 | H1 | H2 | H3 | story |
|---|---|---|---|---|---|
| task_017 | 75% P db | 75% · | 25% · | 75% · | **regression at H1**: the simulated user fumbled its dispute-tool calls (invented user id `user_ktanaka_0589`, empty args, a mangled tool name) — user-sim stochasticity, not agent policy |
| task_035 (ACTION) | 100% P | 100% P | 100% P | 100% P | stable pass |
| task_036 | 100% P db | 100% P db | 100% · | 100% · | **regression at H2 with identical gold actions**: the agent additionally filed two transaction disputes gold does not expect, mutating DB state beyond the graded set — over-action |
| task_048 | 62% | 54% | 50% | 62% | flat U |
| task_051 | 85% | 95% P db | 100% P db | 95% P db | **the one sustained gain**: fail at H0 → pass in every generation after g1, retained |
| task_067 | 56% | 56% | 56% | 56% | perfectly flat partial |
| task_091 | 88% | 60% | 72% | 84% | deep dip at H1, near-full recovery |
| task_099 | 40% | 40% | 60% | 40% | flat with one blip |

## Reading

1. **There is no hidden monotone improvement.** Reward, pass count, and DB-match all
   decline; the finer action-level metrics dip at H1 and recover to ≈H0 by H3. The
   hypothesis "partial metrics improved while rewards declined" is not supported at
   the aggregate level.
2. **There is one genuine, retained held-out gain** (task_051: fail → pass from g1
   onward, action-match 85→95/100/95) — the kind of per-task flip the
   task×generation matrix exists to surface.
3. **The two reward regressions have identified, distinct mechanisms.** task_017 is
   environment stochasticity (user-simulator tool fumbling at H1+), largely outside
   the agent's control — the per-episode churn D10 warned about. task_036 is real
   agent behavior: extra unrequested disputes broke an otherwise perfect episode —
   plausibly the "thoroughness" mutations over-firing, though at one trial per
   generation attribution stays uncertain.
4. **The mutations' behavioral signatures are clearly visible in held-out process
   metrics** even where reward is flat: retrieval intensity +20%, discoverable-tool
   usage +18%, premature human transfers 3→1, episodes longer and slightly costlier.
   The harness became measurably more thorough and less escalatory; at T=8 that
   process change did not convert into net reward.
5. Implication for the full experiment: track these process metrics alongside the
   curve, and treat over-action (unrequested state changes) as a first-class failure
   mode — it is the one this run's mutations may have amplified.
