# Experiment 002_bm25-sonnet46 — held-out reveal

Revealed 2026-08-14. G=3 generations x B=4 improvement tasks; held-out T=8, one trial per task (D2). Noise band: ±18 pp (one binomial standard error at p=0.5, T=8) — deltas inside it are noise, and pass^k is never used for generations.

## Progression

| generation | passed | of | % | basis |
|---|---|---|---|---|
| H0 | 3 | 8 | 37.5% | measured |
| H1 | 3 | 8 | 37.5% | measured |
| H2 | 2 | 8 | 25.0% | measured |
| H3 | 2 | 8 | 25.0% | measured |

**Endpoint:** R_T(H3) - R_T(H0) = -1 task(s) (-12.5 pp) — inside the noise band; directional only

## Transitions

| transition | gains | retained | regressions | unresolved | net | note |
|---|---|---|---|---|---|---|
| H0→H1 | 1 | 2 | 1 | 4 | +0 |  |
| H1→H2 | 0 | 2 | 1 | 5 | -1 |  |
| H2→H3 | 0 | 2 | 0 | 6 | +0 |  |

## Retention

| generation | currently solved | ever solved |
|---|---|---|
| H0 | 3/8 | 3/8 |
| H1 | 3/8 | 4/8 |
| H2 | 2/8 | 4/8 |
| H3 | 2/8 | 4/8 |

## Provenance

- `held_out/results_by_generation.csv`, `held_out/task_generation_matrix.csv`, `held_out/transitions.csv`, `held_out/retention.csv` — computed at this reveal.
- `held_out/generation_NNN/` — the vault rounds, copied verbatim.
- `improvement_records/` — the evidence chain, `held_out_result` filled at this reveal and at no other time.

Firewall, as enforced: improvement batches ran fully observable on the platform lane; held-out rounds ran on the local lane with outputs out of tree, structurally invisible to the platform and procedurally sealed locally until this reveal (SIA_EVALUATION_PLAN.md D1/D9).
