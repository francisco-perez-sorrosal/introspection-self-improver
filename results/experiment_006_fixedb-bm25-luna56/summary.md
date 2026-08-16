# Experiment 006_fixedb-bm25-luna56 — held-out reveal

Revealed 2026-08-16. G=6 generations x B=8 improvement tasks; held-out T=28, 3 trials per task — per-task cells are pass RATES, not flips (D18). Noise band: ±5 pp (one standard error of the mean per-task rate at p=0.5, T=28, n=3) — deltas inside it are noise, and pass^k is never used for generations.

## Progression

| generation | passed (expected) | of | % | basis |
|---|---|---|---|---|
| H0 | 4.3 | 28 | 15.5% | measured |
| H1 | 5 | 28 | 17.9% | measured |
| H2 | 5.7 | 28 | 20.2% | measured |
| H3 | 6.7 | 28 | 23.8% | measured |
| H4 | 6.3 | 28 | 22.6% | measured |
| H5 | 5.7 | 28 | 20.2% | measured |
| H6 | 6.3 | 28 | 22.6% | measured |

**Endpoint:** R_T(H6) - R_T(H0) = +2 task(s) (+7.1 pp) — outside the noise band

**Pre-registered primary (D11):** one-sided trend over the measured generations (H0, H1, H2, H3, H4, H5, H6): z = 1.77, p = 0.038 — significant at alpha = 0.05.

## Transitions

| transition | gains | retained | regressions | unresolved | net | note |
|---|---|---|---|---|---|---|
| H0→H1 | 5 | 0 | 5 | 18 | +0 |  |
| H1→H2 | 3 | 4 | 3 | 18 | +0 |  |
| H2→H3 | 4 | 5 | 2 | 17 | +2 |  |
| H3→H4 | 3 | 4 | 4 | 17 | -1 |  |
| H4→H5 | 3 | 3 | 4 | 18 | -1 |  |
| H5→H6 | 3 | 6 | 2 | 17 | +1 |  |

## Retention

| generation | fully solved | partially solved | ever solved |
|---|---|---|---|
| H0 | 2/28 | 5/28 | 7/28 |
| H1 | 2/28 | 6/28 | 10/28 |
| H2 | 3/28 | 4/28 | 11/28 |
| H3 | 3/28 | 7/28 | 11/28 |
| H4 | 3/28 | 7/28 | 11/28 |
| H5 | 3/28 | 5/28 | 11/28 |
| H6 | 2/28 | 8/28 | 13/28 |

## Provenance

- `held_out/results_by_generation.csv`, `held_out/task_generation_matrix.csv`, `held_out/transitions.csv`, `held_out/retention.csv`, `held_out/trend_test.json` — computed at this reveal.
- `held_out/generation_NNN/` — the vault rounds, copied verbatim.
- `improvement_records/` — the evidence chain, `held_out_result` filled at this reveal and at no other time.

Firewall, as enforced: improvement batches ran fully observable on the platform lane; held-out rounds ran on the local lane with outputs out of tree, structurally invisible to the platform and procedurally sealed locally until this reveal (SIA_EVALUATION_PLAN.md D1/D9).
