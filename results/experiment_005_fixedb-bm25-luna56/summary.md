# Experiment 005_fixedb-bm25-luna56 — held-out reveal

Revealed 2026-08-16. G=2 generations x B=8 improvement tasks; held-out T=28, 3 trials per task — per-task cells are pass RATES, not flips (D18). Noise band: ±5 pp (one standard error of the mean per-task rate at p=0.5, T=28, n=3) — deltas inside it are noise, and pass^k is never used for generations.

## Progression

| generation | passed (expected) | of | % | basis |
|---|---|---|---|---|
| H0 | 5.3 | 28 | 19.0% | measured |
| H1 | 4.3 | 28 | 15.5% | measured |
| H2 | 5.3 | 28 | 19.0% | measured |

**Endpoint:** R_T(H2) - R_T(H0) = +0 task(s) (+0.0 pp) — inside the noise band; directional only

**Pre-registered primary (D11):** one-sided trend over the measured generations (H0, H1, H2): z = 0.00, p = 0.500 — not significant at alpha = 0.05.

## Transitions

| transition | gains | retained | regressions | unresolved | net | note |
|---|---|---|---|---|---|---|
| H0→H1 | 2 | 2 | 6 | 18 | -4 |  |
| H1→H2 | 6 | 3 | 2 | 17 | +4 |  |

## Retention

| generation | fully solved | partially solved | ever solved |
|---|---|---|---|
| H0 | 1/28 | 9/28 | 10/28 |
| H1 | 2/28 | 5/28 | 10/28 |
| H2 | 2/28 | 8/28 | 13/28 |

## Provenance

- `held_out/results_by_generation.csv`, `held_out/task_generation_matrix.csv`, `held_out/transitions.csv`, `held_out/retention.csv`, `held_out/trend_test.json` — computed at this reveal.
- `held_out/generation_NNN/` — the vault rounds, copied verbatim.
- `improvement_records/` — the evidence chain, `held_out_result` filled at this reveal and at no other time.

Firewall, as enforced: improvement batches ran fully observable on the platform lane; held-out rounds ran on the local lane with outputs out of tree, structurally invisible to the platform and procedurally sealed locally until this reveal (SIA_EVALUATION_PLAN.md D1/D9).
