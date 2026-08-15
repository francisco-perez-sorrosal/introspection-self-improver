# Experiment 004_powered-bm25-luna56 — held-out reveal

Revealed 2026-08-15. G=5 generations x B=8 improvement tasks; held-out T=28, one trial per task (D2). Noise band: ±9 pp (one binomial standard error at p=0.5, T=28) — deltas inside it are noise, and pass^k is never used for generations.

## Progression

| generation | passed | of | % | basis |
|---|---|---|---|---|
| H0 | 6 | 28 | 21.4% | measured |
| H1 | 8 | 28 | 28.6% | measured |
| H2 | 5 | 28 | 17.9% | measured |
| H3 | 6 | 28 | 21.4% | measured |
| H4 | 7 | 28 | 25.0% | measured |
| H5 | 4 | 28 | 14.3% | measured |

**Endpoint:** R_T(H5) - R_T(H0) = -2 task(s) (-7.1 pp) — inside the noise band; directional only

**Pre-registered primary (D11):** one-sided trend over the measured generations (H0, H1, H2, H3, H4, H5): z = -0.85, p = 0.802 — not significant at alpha = 0.05.

## Transitions

| transition | gains | retained | regressions | unresolved | net | note |
|---|---|---|---|---|---|---|
| H0→H1 | 3 | 5 | 1 | 19 | +2 |  |
| H1→H2 | 2 | 3 | 5 | 18 | -3 |  |
| H2→H3 | 3 | 3 | 2 | 20 | +1 |  |
| H3→H4 | 3 | 4 | 2 | 19 | +1 |  |
| H4→H5 | 2 | 2 | 5 | 19 | -3 |  |

## Retention

| generation | currently solved | ever solved |
|---|---|---|
| H0 | 6/28 | 6/28 |
| H1 | 8/28 | 9/28 |
| H2 | 5/28 | 11/28 |
| H3 | 6/28 | 12/28 |
| H4 | 7/28 | 12/28 |
| H5 | 4/28 | 13/28 |

## Provenance

- `held_out/results_by_generation.csv`, `held_out/task_generation_matrix.csv`, `held_out/transitions.csv`, `held_out/retention.csv`, `held_out/trend_test.json` — computed at this reveal.
- `held_out/generation_NNN/` — the vault rounds, copied verbatim.
- `improvement_records/` — the evidence chain, `held_out_result` filled at this reveal and at no other time.

Firewall, as enforced: improvement batches ran fully observable on the platform lane; held-out rounds ran on the local lane with outputs out of tree, structurally invisible to the platform and procedurally sealed locally until this reveal (SIA_EVALUATION_PLAN.md D1/D9).
