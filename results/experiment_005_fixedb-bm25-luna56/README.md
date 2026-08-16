# Experiment 005_fixedb-bm25-luna56 — closure

**Status:** REVEALED 2026-08-16. **The loop did not improve the harness.** Seq 5 asked the
prerequisite question seq 4 could not answer — *can the improvement loop fix what it stares
at?* — and the answer this run supports is **no**, with a specific and legible reason.

Freeze: G=2 (plan D20), B=8, T=28, `batch_mode: fixed`, `num_trials: 3` (D18),
`openai/gpt-5.6-luna` on both halves, `bm25` retrieval, tau2-bench `fc0055dc` (v1.0.1).
Fingerprint `sha256:7ea86d87…f15e9b`. Deliberately an **odd** sequence (D15): it studies the
loop, not the capability claim.

## Result

**Pre-registered primary — the paired batch endpoint test** (H2 vs H0 on the same 8 tasks,
exact one-sided sign-flip, α=0.05):

| round | harness | mean per-task rate | tasks with any pass |
|---|---|---|---|
| `batch_01` | H0 | 4.2% | 1/8 |
| `batch_02` | H1 | 8.3% | 2/8 |
| `batch_03` | **H2** | **0.0%** | **0/8** |

**Σ rate deltas = −0.333, exact one-sided p = 1.0000 — not significant, direction negative.**

**Held-out transfer probe** (T=28 × 3 trials, per-task cells are rates, band ±5 pp):

| generation | passed (expected) | of | % |
|---|---|---|---|
| H0 | 5.3 | 28 | 19.0% |
| H1 | 4.3 | 28 | 15.5% |
| H2 | 5.3 | 28 | 19.0% |

**Endpoint +0.0 pp** (inside the band). Trend over H0…H2: **z = 0.00, p = 0.500**,
not significant — and underpowered by construction at G=2, as recorded at freeze.

**Against the reading key frozen with the lock** — *B↑T↑ = the loop works and generalizes;
B↑T→ = it optimizes but overfits; **B flat = the meta-agent is the problem*** — the batch
curve does not rise. It ends below where it started. The pre-registered reading is the
third line.

## What actually happened, and why it is worth more than the number

Two mutations, both landed and tagged, both measured on the same eight tasks.

### gen-001 — resolve write-call arguments from their defining source

Targeted the mode seq 4's closure named as never having got a slot: the agent grounds the
customer's subject matter well and then fills *tool-argument* values from its priors.
Prevalence 6/8 tasks.

**Two controlled pairs came out of it, and they are the strongest evidence this project has
produced.** `batch_mode: fixed` is what made them possible — the same tasks, twice.

- **`task_014`, within one round:** the trial that retrieved
  `doc_bank_accounts_bank_accounts_(general)_042` supplied the correct reason code and
  scored 1.0; the two that did not supplied the adjacent wrong code and scored 0.0. At H0
  the *passing* trial had **not** retrieved it — it guessed. Passing began to track
  retrieval rather than luck.
- **`task_065`, across rounds:** identical calls, identical account classes. `batch_01` t2
  volunteered `reason="customer requested closure"` against the tool default
  `"Customer requested closure"` — the tool writes it to `account["closure_reason"]` — and
  scored 0.0. `batch_02` t1 passed `account_id` alone and scored **1.0**.

That second pair resolved backlog item **T4, which had been explicitly rejected as a
target** because its only direct lever is matching a default string, i.e. grader-gaming
against a frozen evaluator. A principled rule fixed it as a side effect. This is the one
unambiguously good outcome in the experiment.

Recorded against gen-001, not for it: `task_072`'s enum was fixed while its **amounts
destabilised** (it was one field from passing before, and one different field from passing
after), and its `task_070` prediction was **denied outright** — zero promotion-directed
queries across three trials, in both rounds.

### gen-002 — count requests for a human instead of acting on the first

Targeted `task_082`'s turn-one capitulation: the customer's opening line asks for a human,
and the agent transferred at the first request after a single KB search, 8 messages against
20 gold actions.

**It did exactly what it was designed to do, and that is why it failed.**

- **Target achieved:** turn-one transfer eliminated 3/3; episodes grew from 8 messages to
  60/72/74. The agent stopped bailing and worked the task.
- **Too broadly:** transfers on DB-basis tasks went **9/21 → 8/21 → 0/21**. It did not
  suppress *premature* transfers; it suppressed transfers.
- **The pre-registered falsifier fired:** `task_014` 1/3 → 1/3 → **0/3**, with **zero
  transfers in all three trials** on a task whose gold *is* a transfer.
- **The secondary check fired too:** the record said `task_096`/`task_028`'s
  mid-conversation transfers "should be LEFT ALONE — if those disappear too, the rule is
  broader than intended." They disappeared.

## The finding that outlives the number

**Seq 4 lost three of five generations to transfer guidance that competed with the frozen
policy. Seq 5 lost one more — with that history explicitly in hand, and with two structural
guards built against it.**

The guards were: delegate the *threshold* to the policy so the rule states no condition of
its own, and scope the rule to the case where *the customer asks*. Both were reasoned, both
were written into the record in advance, and **neither held.** `task_014`'s customer does
ask for a human — so the counting rule applied, and suppressed a transfer the policy
required for an entirely different reason (agent inability, not repeated requests).

The lesson is not "transfer guidance is hard." It is that **an instruction added to a prompt
does not inherit the scope its author reasoned about.** The mutation's author had a
two-clause scope in mind; the model received one imperative and generalised it. This is a
property of the mutation *surface*, and four of seven mutations across seq 4 and seq 5 have
now failed on it — all of them in the same `SYSTEM.md` instruction paragraph. The recipe
offers three growth surfaces that were never used in either experiment: a Pi skill, a Pi
extension tool, and a sub-agent. A deterministic tool cannot over-generalise its scope the
way a sentence can.

## What the machinery demonstrated

- 72 platform batch episodes + 252 held-out episodes, **$1.71** platform batch cost.
- Both transitions produced a verified record; both tags verified to carry their mutation.
- All frozen surfaces held mechanically: one freeze fingerprint across every round, the
  `<policy>` region byte-identical (5733 chars) at every commit, zero `arm_sha_mismatches`
  across all 72 batch episodes, `make gate_a0a` PASS before the first episode was spent.
- **Nineteen of twenty §29 guardrails HELD; one was WAIVED and is reported as waived.**

Two things went wrong and were corrected rather than absorbed, both in
`GUARDRAIL_WALK.md`:

1. **`exp5-g002` was first tagged at the wrong commit** — a tag command chained with `;`
   after a merge that branch protection had rejected. Deleted, re-merged after CI, re-tagged,
   and verified by reading `SYSTEM.md` at the tag.
2. **`batch_02`'s seam contamination was undercounted at 3 cells when the user decided to
   keep the round; it is 4.** The fourth (`task_070` t0) surfaced only after the dashboard
   was taught to render the `sandbox_*` counters. No contaminated cell touches `task_014`,
   `task_065` or `task_082`, so no finding above rests on one.

Also worth carrying forward: **halving batch concurrency 4 → 2 did not reduce seam
contamination** (4 affected cells either way). Episode length is the better explanation —
the mutations made episodes up to 9× longer, so per-round tool-call volume rose regardless
of how many episodes run at once. The bridge's known, unfixed thread ceiling is the
suspect, and it is now *more* likely to bite as the harness gets more thorough.

## Caveats that bound every number here

- **`batch_01` is the only round measuring an untuned set** — and even it is not an
  unbiased sample: its 8 tasks were hand-picked from seq-4 known-fails, so its floor
  reading is by construction. From `batch_02` on, the set has been tuned on.
- **The held-out set is reused from seq 4 verbatim** (D19) and the orchestrator has seen
  seq 4's revealed per-task results for it. This is why the batch curve, not the held-out
  lane, was the pre-registered primary.
- **One per-task held-out datum was disclosed in chat during the H0 round.** Recorded, not
  repeated, and used in no diagnosis or mutation.
- **Human approval was waived**, not held. Both PRs passed CI's required checks; branch
  protection was never bypassed.
- No number here is comparable to published τ-Knowledge results — `bm25` is a deliberate
  freeze that rewrites both the tool set and the graded policy text.

## Artifacts

`summary.md` (generated at reveal) · `GUARDRAIL_WALK.md` (§29, nineteen HELD / one WAIVED) ·
`batch_curve.json` (the pre-registered primary) · `held_out/` (three rounds copied verbatim,
progression / matrix / transitions / retention / `trend_test.json`) ·
`improvement_records/gen_00N_to_00M.yaml` (two, both verifying, `held_out_result` stamped at
reveal) · `improvement_backlog.md` (four targets: two consumed, one resolved as a side
effect, one recorded as unreachable) · `generation_000..002/` (three batch rounds + gates) ·
`experiment.yaml` + value-copies of the lock and partition.
