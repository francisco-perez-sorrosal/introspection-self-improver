# Experiment 010_adopt-bm25-luna56 — held-out reveal

Revealed 2026-08-18. G=8 generations x B=12 improvement tasks; held-out T=36, 3 trials per task — per-task cells are pass RATES, not flips (D18). Noise band: ±5 pp (one standard error of the mean per-task rate at p=0.5, T=36, n=3) — deltas inside it are noise, and pass^k is never used for generations.

## Progression

| generation | passed (expected) | of | % | basis |
|---|---|---|---|---|
| H0 | 7.3 | 36 | 20.4% | measured |
| H1 | 7.3 | 36 | 20.4% | carried (identity) |
| H2 | 9.7 | 36 | 26.9% | measured |
| H3 | 7.3 | 36 | 20.4% | measured |
| H4 | 8 | 36 | 22.2% | measured |
| H5 | 9.3 | 36 | 25.9% | measured |
| H6 | 8.7 | 36 | 24.1% | measured |
| H7 | 8.3 | 36 | 23.1% | measured |
| H8 | 7.3 | 36 | 20.4% | measured |

**Endpoint:** R_T(H8) - R_T(H0) = +0 task(s) (+0.0 pp) — inside the noise band; directional only

**Pre-registered primary (D11):** one-sided trend over the measured generations (H0, H2, H3, H4, H5, H6, H7, H8): z = 0.03, p = 0.486 — not significant at alpha = 0.05. Identity generations (H1) carry their predecessor's draws and are excluded from the statistic.

**Fragility (advisory, D25):** the trend is not significant, so no single task's removal can flip it.

## Transitions

| transition | gains | retained | regressions | unresolved | net | note |
|---|---|---|---|---|---|---|
| H0→H1 | 0 | 12 | 0 | 24 | +0 | identity |
| H1→H2 | 8 | 7 | 3 | 18 | +5 |  |
| H2→H3 | 3 | 7 | 8 | 18 | -5 |  |
| H3→H4 | 6 | 4 | 7 | 19 | -1 |  |
| H4→H5 | 7 | 7 | 3 | 19 | +4 |  |
| H5→H6 | 4 | 4 | 8 | 20 | -4 |  |
| H6→H7 | 6 | 3 | 6 | 21 | +0 |  |
| H7→H8 | 2 | 6 | 5 | 23 | -3 |  |

**Churn:** ~9.5 task cells move per transition (gains + regressions) against a mean |net| of 2.8 — per-task movement inside that churn band is noise, not signal. Ever solved 21/36 vs 3/36 fully solved at the endpoint.
Identity generations (H1) carry their predecessor's held-out draws forward — the zero-movement rows above are carried copies, not fresh measurements; the A/A noise number lives on the batch side (batch_curve.json).

## Retention

| generation | fully solved | partially solved | ever solved |
|---|---|---|---|
| H0 | 3/36 | 9/36 | 12/36 |
| H1 | 3/36 | 9/36 | 12/36 |
| H2 | 5/36 | 11/36 | 18/36 |
| H3 | 4/36 | 9/36 | 19/36 |
| H4 | 3/36 | 10/36 | 20/36 |
| H5 | 5/36 | 10/36 | 20/36 |
| H6 | 5/36 | 7/36 | 20/36 |
| H7 | 5/36 | 7/36 | 21/36 |
| H8 | 3/36 | 8/36 | 21/36 |

## Provenance

- `held_out/results_by_generation.csv`, `held_out/task_generation_matrix.csv`, `held_out/transitions.csv`, `held_out/retention.csv`, `held_out/trend_test.json` — computed at this reveal.
- `held_out/generation_NNN/` — the vault rounds, copied verbatim.
- `improvement_records/` — the evidence chain, `held_out_result` filled at this reveal and at no other time.

Firewall, as enforced: improvement batches ran fully observable on the platform lane; held-out rounds ran on the local lane with outputs out of tree, structurally invisible to the platform and procedurally sealed locally until this reveal (SIA_EVALUATION_PLAN.md D1/D9).
