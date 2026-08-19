# Experiment 012_ceiling-emb-luna56 — held-out reveal

Revealed 2026-08-19. G=7 generations x B=26 improvement tasks; held-out T=36, 3 trials per task — per-task cells are pass RATES, not flips (D18). Noise band: ±5 pp (one standard error of the mean per-task rate at p=0.5, T=36, n=3) — deltas inside it are noise, and pass^k is never used for generations.

## Progression

| generation | passed (expected) | of | % | basis |
|---|---|---|---|---|
| H0 | 5 | 36 | 13.9% | measured |
| H1 | 5 | 36 | 13.9% | carried (identity) |
| H2 | 5 | 36 | 13.9% | carried (identity) |
| H3 | 5 | 36 | 13.9% | carried (identity) |
| H4 | 8 | 36 | 22.2% | measured |
| H5 | 8 | 36 | 22.2% | carried (identity) |
| H6 | 8 | 36 | 22.2% | carried (identity) |
| H7 | 6.7 | 36 | 18.5% | measured |

**Endpoint:** R_T(H7) - R_T(H0) = +1.7 task(s) (+4.6 pp) — inside the noise band; directional only

**Pre-registered primary (D11):** one-sided trend over the measured generations (H0, H4, H7): z = 1.11, p = 0.133 — not significant at alpha = 0.05. Identity generations (H1, H2, H3, H5, H6) carry their predecessor's draws and are excluded from the statistic.

**Fragility (advisory, D25):** the trend is not significant, so no single task's removal can flip it.

## Transitions

| transition | gains | retained | regressions | unresolved | net | note |
|---|---|---|---|---|---|---|
| H0→H1 | 0 | 8 | 0 | 28 | +0 | identity |
| H1→H2 | 0 | 8 | 0 | 28 | +0 | identity |
| H2→H3 | 0 | 8 | 0 | 28 | +0 | identity |
| H3→H4 | 9 | 2 | 4 | 21 | +5 |  |
| H4→H5 | 0 | 12 | 0 | 24 | +0 | identity |
| H5→H6 | 0 | 12 | 0 | 24 | +0 | identity |
| H6→H7 | 3 | 4 | 7 | 22 | -4 |  |

**Churn:** ~3.3 task cells move per transition (gains + regressions) against a mean |net| of 1.3 — per-task movement inside that churn band is noise, not signal. Ever solved 15/36 vs 3/36 fully solved at the endpoint.
Identity generations (H1, H2, H3, H5, H6) carry their predecessor's held-out draws forward — the zero-movement rows above are carried copies, not fresh measurements; the A/A noise number lives on the batch side (batch_curve.json).

## Retention

| generation | fully solved | partially solved | ever solved |
|---|---|---|---|
| H0 | 2/36 | 6/36 | 8/36 |
| H1 | 2/36 | 6/36 | 8/36 |
| H2 | 2/36 | 6/36 | 8/36 |
| H3 | 2/36 | 6/36 | 8/36 |
| H4 | 4/36 | 8/36 | 15/36 |
| H5 | 4/36 | 8/36 | 15/36 |
| H6 | 4/36 | 8/36 | 15/36 |
| H7 | 3/36 | 8/36 | 15/36 |

## Provenance

- `held_out/results_by_generation.csv`, `held_out/task_generation_matrix.csv`, `held_out/transitions.csv`, `held_out/retention.csv`, `held_out/trend_test.json` — computed at this reveal.
- `held_out/generation_NNN/` — the vault rounds, copied verbatim.
- `improvement_records/` — the evidence chain, `held_out_result` filled at this reveal and at no other time.

Firewall, as enforced: improvement batches ran fully observable on the platform lane; held-out rounds ran on the local lane with outputs out of tree, structurally invisible to the platform and procedurally sealed locally until this reveal (SIA_EVALUATION_PLAN.md D1/D9).
