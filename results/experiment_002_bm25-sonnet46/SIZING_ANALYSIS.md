# Sizing the powered experiment — G/B/T from this experiment's actuals

Post-reveal analysis (2026-08-14), recorded as plan decision **D11**. It sizes the
next experiment — **seq 3, the POWERED tier: G=5, B=8, T=28** — between the debug
scale this directory records (G=3, B=4, T=8) and the full scale (G=5, B=10, T=47),
which is deferred to seq 4. Every number below is labelled with its set and N.

Instrument: `benchmark/scripts/power_sim.py` (Monte Carlo, 8,000 simulated
experiments per design cell, plus closed-form hypergeometric/binomial checks).
Reproduce with `cd benchmark && uv run --with scipy python scripts/power_sim.py`.
The question follows the pre-collection discipline: fix α, power, and the effect
worth acting on, then solve for the design — never the reverse.

## What seq 2 pins down (the calibration facts)

- **Pool difficulty structure** (`held_out/task_generation_matrix.csv`, N=8 × 4
  generations; the 10-trial task_001 study in git history, 6/10; batch reads 0/4,
  0/4, 2/4): ~15% of tasks reliably pass, ~50% essentially never pass, ~35% sit in
  a stochastic 0.25–0.7 band. Baseline pass ≈ 27–37%; the sim's mixture means 32.5%.
- **Realistic per-mutation effect** (`improvement_records/gen_*.yaml`): three accepted
  generations produced one sustained held-out gain (task_051), one likely over-action
  regression (task_036), and clearly moved process metrics
  (`held_out/ANALYSIS_partial_metrics.md`) without moving reward — net ≈ 0/generation.
- **Costs** (episode manifests): local held-out **$0.62 mean / $0.53 median**
  per episode (n=32); platform batch **$0.70 mean / $0.50 median** (n=13). That is
  ~2.3× the plan's pre-run $0.20-median basis — the full experiment is really
  ~$210–230, not $75–90. Episode cost grew ~8% across generations with
  instruction-block size.
- **Discordance** (H0 vs H3, same 8 tasks): 3/8 tasks flipped — within-task
  stochasticity is the dominant noise source, which is what pooling across a fixed
  task set (D2) is designed against.

## The model

A pool of 96 tasks with per-task pass probabilities drawn from the calibrated
mixture. Each generation, with probability *s* the accepted mutation genuinely
fixes a failure mode afflicting a random ~*m* fraction of currently-failing tasks
(p lifted 0.2–0.6, capped 0.95); with some probability it also over-fires,
damaging a small fraction of currently-passing tasks — the seq-2 signature. The
held-out set is a random T of the pool, so witness representation emerges
naturally. Measurement follows D2: one Bernoulli draw per task per generation.

| Scenario | s | per-generation true gain | endpoint at G=5 |
|---|---|---|---|
| null | 0 | 0 | 0 |
| pessimistic (seq-2-like) | 0.40 | ~+0.3 pp | +1.4 pp |
| moderate | 0.60 | ~+2.2 pp | +10.9 pp |
| optimistic (working loop) | 0.75 | ~+5 pp | +25.7 pp |

Tests per simulated experiment: direction (X_G > X_0), the ≥2-task visual bar,
exact one-sided McNemar on the paired endpoint (H0 vs H_G, same tasks), and a
one-sided **trend test** over all G+1 curve points (permutation-variance normal
approximation of S = Σ_t Σ_g c_g X_tg, c_g centered generation index). Null
calibration verified: trend fires 5%/10% at α=.05/.10; McNemar runs conservative
(1–3%) from discreteness.

## Results (selected cells; full sweep reproducible from the script)

| Scenario | Design | P(dir+) | P(≥2 tasks) | McNemar α=.10 | trend α=.05 |
|---|---|---|---|---|---|
| optimistic (+26 pp) | **G=5, T=28** | **0.97** | **0.94** | **0.73** | **0.82** |
| | G=5, T=47 (full) | 0.99 | 0.98 | 0.88 | 0.92 |
| | G=5, T=24 | 0.96 | 0.92 | 0.67 | 0.79 |
| | G=4, T=28 | 0.93 | 0.89 | 0.59 | 0.67 |
| moderate (+11 pp) | G=5, T=28 | 0.79 | 0.69 | 0.30 | 0.38 |
| | G=5, T=47 (full) | 0.85 | 0.79 | 0.43 | 0.49 |
| pessimistic (+1.4 pp) | G=5, T=47 (full) | 0.52 | 0.43 | 0.10 | 0.11 |
| null (0) | G=5, T=28 | 0.42 | 0.28 | 0.04 | 0.05 |

A harder-pool sensitivity run (mixture mean −8 pp, baseline ≈ 26%) moves no
conclusion: moderate G=5/T=28 reads 0.80 / 0.69 / 0.30 / 0.40.

**Three findings:**

1. **G is a stronger lever than T.** G=4→5 at fixed T=28 lifts trend power
   0.67→0.82: an extra generation compounds the true effect *and* adds a curve
   point. At matched cost, G=5/T=24 beats G=4/T=32.
2. **The full experiment buys little over T=28.** Optimistic: ~10 pp of trend power
   for ~$80. Moderate: even T=47 reaches only ~0.49 — no feasible T fixes that
   (T≈150–200 would, and the pool holds 96).
3. **The honest MDE:** any affordable design is powered for a loop gaining
   **~+4–5 pp/generation (endpoint ≈ +20–26 pp)**. A +2 pp/generation loop shows a
   rising curve ~79% of the time but stays directional; a seq-2-like loop is
   indistinguishable from null at ANY size, including full. The powered experiment
   answers "does the loop work well enough to matter" at 63% of the cost of the
   experiment that could not have answered a finer question either.

## Witness representation (hypergeometric, pool 96)

A mutation fixes one failure mode; the curve moves only if the mode has held-out
witnesses. For a mode afflicting M of 96 tasks, P(≥1)/P(≥2) witnesses in T:

| M | T=8 (debug) | T=28 (powered) | T=47 (full) |
|---|---|---|---|
| 7 | 0.47 / 0.10 | 0.92 / 0.66 | 0.99 / 0.94 |
| 10 | 0.60 / 0.19 | **0.97 / 0.85** | 1.00 / 0.99 |
| 14 | 0.73 / 0.33 | 0.99 / 0.96 | 1.00 / 1.00 |

At T=8, half of seq 2's real fixes were likely invisible by construction — the
D10 witness logic, now extended to pick the tier.

## Noise bands and the eyeball bar

One binomial SE at the observed base rate: **±17 pp at T=8 → ±9 pp at T=28 →
±7 pp at T=47** (`reveal.py` computes this from T; no code change). One scale
shift to restate wherever the new curve renders: at T=8, "+2 tasks" read as
directional; at T=28 the null produces a ≥2-task endpoint gain **29% of the
time** — the visual bar becomes **≥4–5 tasks** (one-sided 95% ≈ 4.4 tasks at the
observed ~25% discordance). The debug-era "+2 reads directional" heuristic does
not carry over.

## Why B=8

B never enters the power arithmetic — it drives **mutation quality (s), the
variable separating the moderate and optimistic scenarios**. Seq 2 diagnosed from
full transcript reads at B=4 with prevalence quoted in quarters, and its
actually-dominant failure mode (required-procedure incompleteness) surfaced at 1/4
per batch, taking all three batches to be recognized as the recurring family. At
B=8: prevalence in eighths, and P(a 25%-prevalence mode shows ≥2 in-batch
witnesses) jumps 26% → 63% — one-episode anecdotes become diagnosable patterns
within a single generation. Money cost is trivial (+$2.80/generation); the real
spend is `operate` reading 8 transcripts, which is exactly where spend should go.
B=10 adds little over 8 and stretches batch rounds at the ~2-sandbox quota.

## Costs (measured seq-2 basis: $0.62 local, $0.70 platform per episode)

| Design | Episodes | Cost | Notes |
|---|---|---|---|
| debug (seq 2, done) | 32 L + 12 P | **$29 recorded** | manifest sums $19.92 + $9.05 |
| **powered (seq 3)** | 168 L + 40 P | **≈ $132**; plan $150–165 with instruction-growth headroom | ~4–6 h compute, ~2–3 days elapsed with review gates |
| full (seq 4, deferred) | 282 L + 50 P | ≈ $210–230 | supersedes the pre-run $75–90 estimate |

## The decision (D11) and its disciplines

**G=5, B=8, T=28**, tier named **powered**, frozen as seq 3
(`003_powered-bm25-sonnet46`); the full T=47 run deferred to seq 4, contingent on
the powered outcome.

- **Fresh pool.** task_034 plus all 20 seq-2 tasks are excluded from the entire
  partition (68 of 76 eligible; header-documented in `split_manifest.yaml`), so
  nothing the g1–g3 mutations were tuned on — and nothing the reveal exposed —
  reappears in held-out *or* batches. Feasible at this size and not at full
  (47+50 > 76).
- **Pre-registration** (declared here, before any seq-3 run; the vault firewall is
  the no-interim-looks guarantee): primary significance = one-sided trend test over
  H0…H5 at α=0.05, computed at reveal (`tau_adapter/reveal.py`; identity
  generations carry their predecessor's draws forward and are excluded from the
  statistic — a carried column is not an independent measurement); the protocol endpoint R_T(H_G) − R_T(H_0)
  reported with its interval and the ±9 pp band; process metrics
  (`process_metrics_by_generation.csv` family) are pre-declared **directional
  secondaries** carrying no significance claims. One primary comparison — no
  multiplicity correction needed. Fixed n; no interim analyses.
- **D2 held.** At fixed episode budget, more distinct tasks dominates repeated
  trials (heterogeneous per-task p, plus task-space coverage). The endpoint
  reliability addendum stays post-reveal and becomes **conditional**: run it only
  if the endpoint lands positive-but-inside-band (~$70–100 at +2 trials × both
  endpoint arms × 28 tasks).
- **H0 restarts at `h0-baseline`** (`make reset_h0`, D6). The seq-2 mutations are
  evidence for `improve`, not inheritance: their held-out net was ≈ 0, and the
  powered experiment tests whether the loop improves H0, not whether it can
  continue seq 2's endpoint.
- **Over-action is a first-class failure mode** for seq-3 diagnosis (this
  directory's partial-metrics analysis, reading 5): the regression channel in the
  power model is exactly what "more thoroughness" mutations did to passing tasks.

## Limitations

- The difficulty mixture rests on small N (8 held-out tasks × 4 draws, 12 batch
  episodes, one 10-trial task); the −8 pp sensitivity run bounds the exposure.
- The mutation model is synthetic (mode sizes 5–20% of pool, lifts 0.2–0.6);
  scenario labels are honest brackets, not predictions.
- The trend test uses a normal approximation to the within-task permutation null
  (verified well-calibrated at these T); McNemar is exact and conservative.
- Cost projections assume the seq-2 episode mix and ~8%/generation growth.
