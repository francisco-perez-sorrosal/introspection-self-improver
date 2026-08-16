# How hard are the eight pinned batch tasks? — the batch vs the 97-task pool

Written 2026-08-16, post-reveal. Companion to [`INDEPENDENT_REVIEW.md`](INDEPENDENT_REVIEW.md).
Question: relative to the rest of tau2-bench `banking_knowledge`, how difficult are the eight
tasks frozen as this experiment's fixed batch (`task_014, task_026, task_028, task_065,
task_070, task_072, task_082, task_096`)?

## Answer first

1. **tau2-bench does not catalog difficulty for this domain.** There is no difficulty field,
   tier, or label anywhere in the banking_knowledge data or the task schema. Any "how are they
   catalogued" answer is necessarily a proxy this project constructs.
2. **Structurally, the eight are ordinary — except on retrieval breadth.** On gold-action
   count, write count, tool-discovery depth, and instruction length they sit near the pool
   median. The one enriched dimension is `required_documents` (KB lookups needed): batch mean
   13.4 vs 9.5 for the rest of the pool, with two tasks (`task_065`, `task_096`) at the 94th
   percentile. That is exactly the axis a frozen-`bm25` harness is weakest on — consistent
   with, and probably explanatory of, their empirical hardness.
3. **Empirically, they are very hard — by construction.** They were hand-picked in seq 5 as
   known-fails under seq-4 harnesses. Across every graded attempt this project has ever made
   (31 per task over seq 4/5/6), **five of the eight have never passed once** — 155
   consecutive failures — and the batch's lifetime mean pass rate is 6.5%, versus 19.9% for
   the 28-task held-out set and a pool-wide mean of ~27–28% on noisier measurement. But the
   pool itself is brutal for this harness: 53 of 97 tasks have a 0% recorded rate, so the
   batch is **a hard subset of an already-hard pool, not an outlier class**. A Mann–Whitney
   test against the held-out 28 gives z = −1.27 — directionally harder, not significant at
   n=8.
4. **Consequence for the instrument** (the review's § 5 makes this quantitative): eight
   known-fails give a fixed-batch experiment saturation headroom in theory and almost no
   dynamic range in practice — the whole seq-6 batch curve lived on three tasks, and the
   endpoint test on one.

## 1. What tau2-bench provides (and doesn't)

Verified against the vendored benchmark (`benchmark/vendor/tau2-bench`, commit `fc0055dc`):

- **97 tasks** in `data/tau2/domains/banking_knowledge/tasks.json` (IDs `task_001`–`task_100`
  with gaps at 009, 011, 013, 030, 042), mirrored one-file-per-task under `tasks/`.
- The pydantic `Task` model (`src/tau2/data_model/tasks.py`) has **no difficulty, tier, or
  complexity field**. Every banking task carries `"annotations": null` — a dead key the model
  does not parse.
- `description.purpose` is the auto-generated `"Task: task_NNN"` for 97/97;
  `relevant_policies` is null for 97/97. The only human signal is free-text
  `description.notes` (present 76/97) — scenario-design narratives, not labels.
- Difficulty metadata that exists elsewhere in tau2 does **not** cover banking:
  `audio_difficulty.json` ships for airline/retail/telecom only (and is voice-specific);
  telecom's `tasks_small/full/split` tiering has no banking equivalent. No difficulty language
  in the repo docs.
- Grading in this domain is stark: `reward_basis: ["DB"]` for 88 tasks, `["ACTION"]` for 9
  (including batch member `task_014`). Zero `nl_assertions`, zero `env_assertions`, zero
  populated `communicate_info` — pass/fail is database-state match or exact action match, so
  partial competence is invisible to reward.

## 2. Structural comparison

Per-task features of the eight (from the task JSONs):

| task | basis | gold actions | writes | distinct discoverable tools | required docs | instr chars | transfer in gold | design-note gist |
|---|---|---|---|---|---|---|---|---|
| task_014 | ACTION | 1 | 0 | 0 | 5 | 2313 | **yes** (`unconfirmed_external_communication`) | referral offer that must be escalated, not resolved |
| task_026 | DB | 11 | 8 | 2 | 8 | 2104 | no | cash-back disputes via user-side discoverable tool |
| task_028 | DB | 15 | 12 | 2 | 11 | 2139 | no | 6 transaction corrections + user-tool handover |
| task_065 | DB | 6 | 3 | 2 | **23** | 4158 | no | APY-optimization trap with explicit order dependency (open savings while checking still open, then close) |
| task_070 | DB | 5 | 2 | 2 | 16 | 2950 | no | date-dependent expired-vs-active promotion conflict in the KB |
| task_072 | DB | 9 | 5 | 3 | 9 | 2371 | no | 8 net-credit fee errors across two accounts; overcharge + missing-fee arithmetic |
| task_082 | DB | 20 | 12 | **7** | 12 | 4528 | no | 4 disputes × 2 debit cards, Regulation E liability timing |
| task_096 | DB | 12 | 7 | 4 | **23** | 2341 | no | dual-savings APY investigation; card boosts do NOT stack, different card optimal per account |

Distributions (median, with mean and range):

| feature | batch-8 | held-out-28 | all-97 |
|---|---|---|---|
| gold actions | 10.0 (9.9, 1–20) | 8.5 (9.5, 1–22) | 8.0 (9.8, 1–37) |
| write actions | 6.0 (6.1, 0–12) | 4.0 (5.6, 0–13) | 4.0 (5.6, 0–22) |
| distinct discoverable tools | 2.0 (2.8, 0–7) | 2.0 (2.8, 0–7) | 2.0 (3.0, 0–11) |
| required documents | **11.5 (13.4, 5–23)** | 10.0 (9.9, 1–25) | 9.0 (9.8, 1–30) |
| instruction chars | 2356 (2863, 2104–4528) | 2691 (3071, 1453–6981) | 3246 (3470, 1163–7368) |

Percentile placement within all 97 (gold actions / writes / required docs): task_014
0/0/20 · task_026 63/70/41 · task_028 73/87/60 · task_065 36/36/**94** · task_070
31/25/84 · task_072 52/56/46 · task_082 87/87/65 · task_096 65/65/**94**.

Two structural observations:

- **`task_014` is at the pool floor on every structural axis** (1 gold action, 0 writes,
  shortest doc list) — and it is the batch's only reliably-passable task. Its difficulty is
  purely a discrimination problem (when to transfer), not a complexity problem.
- The pool's own hard-scenario markers are *absent* from the batch: keyword scan of the design
  notes finds `adversarial` 0/8 (4 in pool), `speedbump` 0/8 (3), `lying` 0/8 (12),
  `retention` 0/8 (7), `extreme` 0/8 (7). **The batch is not a selection of tau2's nastiest
  scripted user behaviors.** Its hardness comes from KB-resolution load (rules in force,
  non-stacking rates, date-dependent promotions, enum values) — the retrieval-usage territory
  this project designated as its mutable surface, which is presumably why these modes recurred
  in seq-4 diagnosis and got the tasks picked.

## 3. Empirical difficulty

Every graded attempt on the eight across the project's history (seq 4: 1 trial each in its
batches; seq 5: 3 rounds × 3 trials; seq 6: 7 rounds × 3 trials — 31 attempts per task):

| task | seq 4 | seq 5 (b01/b02/b03) | seq 6 (b01…b07) | lifetime |
|---|---|---|---|---|
| task_014 | 0/1 | 1/3, 1/3, 0/3 | 2,1,1,2,0,1,1 /3 | **10/31 = 32.3%** |
| task_026 | 0/1 | 0, 0, 0 | 0 ×7 | **0/31** |
| task_028 | 0/1 | 0, 0, 0 | 0 ×7 | **0/31** |
| task_065 | 0/1 | 0, 1/3, 0 | 0,0,0,1,1,0,0 /3 | **3/31 = 9.7%** |
| task_070 | 0/1 | 0, 0, 0 | 0 ×7 | **0/31** |
| task_072 | 0/1 | 0, 0, 0 | 0,0,2,1,0,0,0 /3 | **3/31 = 9.7%** |
| task_082 | 0/1 | 0, 0, 0 | 0 ×7 | **0/31** |
| task_096 | 0/1 | 0, 0, 0 | 0 ×7 | **0/31** |

Placement among the 36 well-measured tasks (batch n=31 each; held-out n=36 each across
seq 2/4/5/6):

- Batch-8: mean per-task rate **6.5%**, median **0%**, 5/8 at zero.
- Held-out-28: mean **19.9%**, median 2.8%, 11/28 at zero — but it holds genuinely easy
  anchors the batch entirely lacks: `task_031` (0.889 lifetime, 3/3 in six of seq-6's seven
  generations), `task_007` and `task_012` (0.750), `task_052` (0.722). Those four account for
  most of the mean gap.
- Rank of each batch task among the 36 (1 = easiest): `task_014` **8th** — comfortably in the
  solvable tier; `task_065` 15th, `task_072` 16th — the marginal band; the other five tied in
  the bottom block of 16 tasks that have never passed.
- Mann–Whitney batch vs held-out: U = 78.5, **z = −1.27** — harder on average, not
  significant at n=8.
- Full-pool context (noisier: includes seq-4 single-trial tasks): 53/97 tasks at 0% recorded,
  pool median 0%, non-batch mean ~28%. The domain, under this frozen harness
  (`bm25` + gpt-5.6-luna + DB/ACTION-exact grading), is mostly unsolved; the batch sits in its
  large hard mass, deeper than average but not categorically apart.

## 4. Why these eight — the selection record

The composition was decided in seq 5 and inherited unchanged. The freeze commit's manifest
header (`git show b761e31:benchmark/split_manifest.yaml`):

> seq 5 loop-reliability (plan D17/D19). FIXED BATCH, hand-chosen: 8 tasks that FAILED under
> recent harnesses in seq-4 batches, covering the recurring modes — value resolution
> (task_065, task_072, task_096), discoverable-tool handover (task_026, task_028), transfer
> discipline in both directions (task_014 refused a required transfer; task_082 transferred on
> first request), wholesale abandonment/unbounded search (task_070). Known-fail composition is
> deliberate: saturation headroom is the point, and batch knowledge is fully observable so
> using seq-4 diagnosis to choose is sanctioned.

Each of the eight has exactly one seq-4 batch trial on disk, all reward 0.0 — the premise
checks out. Note what the selection optimized: *mode coverage among failures*, not difficulty
spread. Every recurring failure mode got a representative; no passing task got one.

## 5. Implication for the next fixed batch

The seq-6 result makes the cost of that composition concrete: five zero-range tasks
contributed nothing to the curve in 105 combined episodes, the endpoint test reduced to
`task_014`'s day-to-day variance, and regressions on anything the harness already did well
were invisible by construction. Empirically grounded strata now exist for a better instrument:

- **Anchors (regression detectors), lifetime ≥ 0.7:** `task_031`, `task_007`, `task_012`,
  `task_052` — currently all in the held-out set; a next experiment's re-partition can move
  some to the batch (they are exposed anyway).
- **Marginal band (where 3 trials resolve movement):** `task_014` (0.32), `task_065` (0.10),
  `task_072` (0.10), plus held-out members like `task_021`, `task_033`, `task_059`,
  `task_093` (flippers in seq-6's matrix).
- **Headroom (known-fail):** two or three of the never-passed block — with the seq-6 caveat
  that `task_070`'s failure is likely bounded by the frozen `bm25` backend (T1 retired with
  that reason) and `task_026`/`task_028` sit behind the discoverable-tool + arithmetic modes
  prose could not reach. Picking headroom tasks whose failure mode the mutable surface can
  actually address is part of instrument design.

## 6. Caveats

- The batch-vs-held-out gap is a **selection artifact by construction** (the eight were chosen
  *because* they failed); the comparison quantifies the consequence, it does not discover it.
- Seq-4 per-task numbers are single-trial; the full-pool distribution built on them is noisy
  (14 tasks show 1.000 on n=1). The 36 well-measured tasks are the honest comparison set.
- The structural features in § 2 are proxies invented here (action counts, doc counts,
  instruction length) — tau2 endorses none of them, and they demonstrably under-predict the
  empirical hardness (§ 2 says "ordinary", § 3 says "5/8 never pass"). The one proxy that
  tracks the outcome is `required_documents`. Treat § 2 as weak evidence, § 3 as strong.
- "Pass" = `reward == 1.0` (rewards in this domain are binary in practice); where both
  `results.json` and `graded/updated_results.json` exist, the graded file was used.

## Sources

`benchmark/vendor/tau2-bench/data/tau2/domains/banking_knowledge/` (tasks.json + per-task
files, 97 tasks), `src/tau2/data_model/tasks.py` (schema), `docs/evaluation.md`;
`benchmark/split_manifest.yaml` + this experiment's value snapshot; seq-5 freeze commit
`b761e31`; `SIA_EVALUATION_PLAN.md` D17; graded results under
`results/experiment_002_bm25-sonnet46/`, `results/experiment_004_powered-bm25-luna56/`,
`results/experiment_005_fixedb-bm25-luna56/`, `results/experiment_006_fixedb-bm25-luna56/`
(1437 graded simulations, 55 de-duplicated results files);
`results/experiment_006_fixedb-bm25-luna56/held_out/task_generation_matrix.csv`.
