# Experiment 008_stratb-bm25-luna56 — held-out reveal

Revealed 2026-08-17. G=6 generations x B=8 improvement tasks; held-out T=28, 3 trials per task — per-task cells are pass RATES, not flips (D18). Noise band: ±5 pp (one standard error of the mean per-task rate at p=0.5, T=28, n=3) — deltas inside it are noise, and pass^k is never used for generations.

## Progression

| generation | passed (expected) | of | % | basis |
|---|---|---|---|---|
| H0 | 4.7 | 28 | 16.7% | measured |
| H1 | 4.7 | 28 | 16.7% | measured |
| H2 | 6.3 | 28 | 22.6% | measured |
| H3 | 5.7 | 28 | 20.2% | measured |
| H4 | 4.7 | 28 | 16.7% | measured |
| H5 | 5.3 | 28 | 19.0% | measured |
| H6 | 5.7 | 28 | 20.2% | measured |

**Endpoint:** R_T(H6) - R_T(H0) = +1 task(s) (+3.6 pp) — inside the noise band; directional only

**Pre-registered primary (D11):** one-sided trend over the measured generations (H0, H1, H2, H3, H4, H5, H6): z = 0.60, p = 0.274 — not significant at alpha = 0.05.

**Fragility (advisory, D25):** the trend is not significant, so no single task's removal can flip it; 1 first-ever pass(es) appear only in the final measured generation (task_092); zeroing those cells gives z = 0.38, p = 0.352.

## Transitions

| transition | gains | retained | regressions | unresolved | net | note |
|---|---|---|---|---|---|---|
| H0→H1 | 5 | 2 | 5 | 16 | +0 |  |
| H1→H2 | 4 | 7 | 1 | 16 | +3 |  |
| H2→H3 | 3 | 4 | 5 | 16 | -2 |  |
| H3→H4 | 3 | 3 | 5 | 17 | -2 |  |
| H4→H5 | 3 | 2 | 3 | 20 | +0 |  |
| H5→H6 | 4 | 5 | 2 | 17 | +2 |  |

## Retention

| generation | fully solved | partially solved | ever solved |
|---|---|---|---|
| H0 | 2/28 | 5/28 | 7/28 |
| H1 | 1/28 | 9/28 | 12/28 |
| H2 | 2/28 | 9/28 | 13/28 |
| H3 | 1/28 | 10/28 | 14/28 |
| H4 | 3/28 | 4/28 | 14/28 |
| H5 | 3/28 | 4/28 | 14/28 |
| H6 | 2/28 | 9/28 | 15/28 |

## Provenance

- `held_out/results_by_generation.csv`, `held_out/task_generation_matrix.csv`, `held_out/transitions.csv`, `held_out/retention.csv`, `held_out/trend_test.json` — computed at this reveal.
- `held_out/generation_NNN/` — the vault rounds, copied verbatim.
- `improvement_records/` — the evidence chain, `held_out_result` filled at this reveal and at no other time.

Firewall, as enforced: improvement batches ran fully observable on the platform lane; held-out rounds ran on the local lane with outputs out of tree, structurally invisible to the platform and procedurally sealed locally until this reveal (SIA_EVALUATION_PLAN.md D1/D9).
