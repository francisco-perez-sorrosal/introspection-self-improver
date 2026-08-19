# Experiment `012_ceiling-emb-luna56` — closure

**REVEALED 2026-08-19. Null on both instruments.** G=7 (identity at gen-001, six mutation
slots), B=26 `fixed`, T=36 pure holdout, `num_trials` 3 on both lanes,
`--retrieval-config openai_embeddings`, `openai/gpt-5.6-luna` on both halves, autonomous
under the frozen D23 envelope.

The first experiment in this project's history that knew how much room it was playing for —
and the answer is that it used none of it.

> **Absolute numbers here do not compare to seq ≤ 10.** `--retrieval-config` moved from
> `bm25` to `openai_embeddings`, which rewrites both the tool set and the graded policy text.
> Gap-closure against the measured ceiling is the comparable statistic, and it is why the
> primary reports that way.

---

## § Batch-derived findings — recallable by later in-loop sessions

### The pre-registered primary

`scripts/endpoint_test.py`, a within-task permutation on episode outcomes, `batch_08` vs the
pooled H0 baseline (`batch_01` + `batch_02`, 156 episodes vs 78):

**34.62% → 34.62%. Σ per-task rate deltas = −0.000. p = 0.566. CMH cross-check z = 0.000.**

Phase 0 measured this batch's harness headroom at **+20.5 pp** (H0 32.1%, H-expert 52.6%).

> **The loop closed 0.0% of the measured reachable headroom.**

Zero to three decimal places is a coincidence of the arithmetic, not a designed result — but
the reading does not depend on the coincidence: no interim round was significant either
(p = 0.30, 0.11, 0.16, 0.66 at `batch_04`…`batch_07`).

**Batch curve (mean per-task rate):** 33.3, 35.9, 37.2, 38.5, 42.3, 41.0, 33.3, **34.6%**.

**Reachable harvest: 0.333 → 0.346, no walled tasks.**

### Reading the frozen key

The lock's nine-cell key, cell **`primary_flat × secondary_flat`**, resolves on the measured
headroom and the harvest. Headroom **large** (+20.5 pp on this batch) and harvest **low**
(0.346, against the key's 0.90 exhaustion threshold), so the key's own words apply:

> *every precondition a prior null could be blamed on was removed and the loop found nothing
> — say so plainly.*

Saying it plainly: **five prior nulls could each be blamed on something — an unknown ceiling,
a saturated batch, unusable structural surfaces, single-trial noise, a marginal-only task
set. Seq 12 removed all of them and returned the same answer.** The batch had 53 reachable
failing cells at H0, a proven-reachable headroom stratum, a measured maximum, a pre-registered
noise floor, four passing gates, and every surface class exercised. The loop still moved
nothing.

### The measurement that reframes the whole experiment

**The A/A identity round measured 16 cells / 20.5 pp of movement on a byte-identical
harness** (`batch_01` → `batch_02`, 13 of 26 task rates moving, three by two full cells).

**The batch's entire harness headroom is also 20.5 pp.** The instrument's noise and the
objective's total available signal are the same size. That is the single most important
number this experiment produced, and it was available before the first mutation.

A useful corollary for future freezes: the *strata* differ sharply in noise. Across the A/A
pair the **headroom stratum moved zero cells** (3/33 twice) while anchors moved three of nine.
Attribution inside a batch should be stratum-aware, not batch-wide.

### Per-change verdicts, scored on pre-registered counters

| change | surface | mechanism | verdict |
|---|---|---|---|
| C1 required-args-only | instructions | send only a tool's required arguments | **DENIED** — counter 9, 9, 9 across three rounds |
| C2 specific enum member | instructions | name the situation, not the catch-all | **CONFIRMED** — catch-all calls 7 → 3, transfers held |
| C3 search by candidate name | instructions | query formulation, not volume | **DIRECTIONAL** — distinct KB docs/ep +2.96 vs a ≥3.0 threshold |
| C4 required-args as a hook | **extension-hook** | the same rule, delivered at the point of use | **DENIED** — counter 9 → 8 |
| C5 procedure-named tool | instructions | unlock the tool the procedure names | **DENIED** — counter 12 → 14 → 16, wrong direction |
| C6 requirement coverage | instructions | check coverage before committing | **DENIED**; cost falsifier fired |
| C7 revert C6 | revert | — | **CONFIRMED** — messages/ep fell |
| C8 `track_requests` | **extension-tool** | hold the outstanding-request list | **adoption + mechanism CONFIRMED, reward NOT** |
| C9 apply the retrieved rule | instructions | apply the KB's stated selection rule | **DENIED** — counter 5 → 8 |
| C10 revert C5 | revert | — | **CONFIRMED** — the rise stopped |
| C11 `compare_candidates` | **extension-tool** | hold candidates × requirements | **adoption CONFIRMED, mechanism DENIED**, cost fired |
| C12 revert C11 | revert | — | **PARTIALLY confirmed** — round 33.8 → 36.5%, costs fell, but short of `batch_06` |

**Six of twelve changes denied. One confirmed. Three reverts.**

### The five findings worth carrying forward

**1. The surface is not the axis — for demands the model does not want to satisfy.**
The strongest result of the experiment. C1 delivered "send only the required arguments" as
prose; C4 delivered *the same rule* as a `tool_result` hook that named the concrete parameters
at the moment of unlocking, with no escape clause. The hook was **verified firing on the
graded platform lane**, injecting verbatim:

> *Argument set for close_bank_account_7392 — required: account_id. The remaining parameters
> (reason, waive_early_closure_fee) are optional; this call sends the required arguments and
> nothing else.*

The agent read that and sent both optional keys anyway. **The counter across four rounds:
9, 9, 9, 8.** Two rounds with no instruction, one with prose, one with structure.

This **narrows a standing project doctrine.** "When the mechanism is judgment, scope,
verification or arithmetic, prefer a structural surface" survives only for mechanisms needing
**state the model cannot hold**. It does not survive for mechanisms asking the model to
**withhold something it wants to emit** — there, both channels failed identically.

**2. Adoption is not improvement, and neither is a moving mechanism counter.**
Seq 10 established the first half. Seq 12 establishes the second. `track_requests` was called
**578 times** in one round and moved its own mechanism counter (gold-actions-absent episodes
15 → 13 → 10) — and moved no reward. `compare_candidates` was called **1515 times** across
77 of 78 episodes and moved *neither* its counter nor reward, while firing its cost falsifier.
**Three tiers now separate: reachable, used, useful. This project has demonstrated the first
two and not the third.**

**3. Instruction-shaped demands failed five times running, and shape did not predict it.**
Mid-experiment I formed a hypothesis from six measurements: changes succeed when they ask for
a **positive choice among visible alternatives** and fail when they ask the model to withhold,
verify, or rest on a precondition it can decline. It was recorded as post-hoc. **C9 was built
deliberately in the "confirmed" shape and was denied, with its counter moving the wrong way.**
One out-of-sample test, refuted. What survives is only the tally: C1, C4, C5, C6, C9 denied;
C2 confirmed; C3 directional.

The one shape that *did* work twice is narrow and worth naming: **C2 and C3 both told the
agent which of a small, enumerated, already-visible set of strings to emit.**

**4. The futility check is unstable near its threshold — and declaring it is what proves it.**
It fired at gen-004 on a margin of **0.3 pp** (gap 7.5 pp vs 7.2 pp of capacity) and the very
next round refuted it, taking the accumulated delta from +3.9 to +7.7 pp. It fired again at
gen-007 with a margin of **8.9 pp** and was correct. The statistic it depends on — *the largest
gain the experiment has actually produced* — is updated by the very round that would refute it,
so it is unreliable while few gains exist. **A loop that had quietly drifted into knowledge
mode would never have discovered this; declaring it out loud is what made the refutation
visible.** Recommendation for future freezes: require two consecutive firings, or compute
capacity from the ceiling rather than from observed gains.

**5. `sub-agent` is exercised at last, and it is bounded by measurement.**
The g=0 step-4b probe closed the last unexercised surface class in this project's history.
Delegation **works**: the auto-generated `agent` tool is called and fully suppressed from τ
(`pi_local_calls` 2 per episode, 3/3 episodes, zero occurrences in the graded trajectory), and
`from: agent` binds the frozen model pair. But **a child cannot use τ's tools at all** — it
resolves the mangled name, issues `mcp_tau_KB_search_*`, and every call dies at
`MCP daemon: Timeout` after 120 s **without reaching the bridge** (that run's
`bridge_calls.jsonl` holds one row, the parent's). So the question three closures carried —
*does a child's tool call spend the parent's τ step budget?* — is **moot: it spends no τ step
because it never reaches τ.** It spends wall-clock, 120 s per attempt; all three episodes
collapsed to 6 messages and reward 0.0.

Net: usable only for reasoning over parent-supplied text, competing directly with `context`
and `tool_result` hooks that do the same work deterministically at zero latency.
`generation_000/subagent_probe/VERDICT.md`.

### Craft notes

- **A hook must be verified firing on the graded lane, not only in preflight.** C4's verdict
  is only interpretable because the injected text was confirmed present in `batch_04`'s own
  conversation before any number was read.
- **Preflight on a task where the mechanism applies.** C11's first preflight showed zero
  invocations on a task with no candidate choice — ambiguous between "not applicable" and "not
  registered". The second, on a task where the mechanism demonstrably applies, showed 43–46
  invocations per session. Only the second carried information.
- **Compare cost to the task's own baseline, not the round mean.** C11's preflight looked
  expensive against the round; against `task_056`'s own history (66/66/66 then 70/90/76
  messages) it was not.
- **A falsifier keyed on a level is not a falsifier** — re-learned the hard way. C9's second
  clause named `task_056` as "0 of 15 lifetime" when it was 1 of 15, so it fired on a
  pre-existing condition and diagnosed nothing.

### Unconsumed targets, and the mechanism that never reached them

Per the reading key's instruction to name these:

- **EXTRA_ARGS** (`task_060`, `task_061`, `task_065`; 9 episodes every round) — attacked twice,
  through both delivery surfaces, never moved. The mechanism that never reached it: **anything
  that asks the model to withhold an argument it has decided to send.**
- **Gold-action-absent** (10–15 episodes / 7–11 tasks) — `track_requests` moved the counter and
  not the reward. The mechanism that never reached it: **whatever converts a tracked
  outstanding item into a performed action.**
- **Wrong discoverable tool** (`task_046` 0 of 15 lifetime) — attacked once, wrong direction.
  The mechanism that never reached it: **anything that makes the agent look up which tool the
  procedure names before choosing one.**
- **Wrong named class** — attacked four times (C3 partial, C6, C9, C11), the largest sole cause
  in almost every round. The mechanism that never reached it: **anything that converts a gap
  the agent has already articulated in words into a decision not to commit.**

### Operational

Eight batch rounds (platform, concurrency 3) and three held-out rounds (local), ~$12 of
graded episodes plus probes and preflights. Every round's health counters clean apart from the
recorded incidents. The four freeze gates passed before any graded episode. Detail and the two
orchestrator errors: `GUARDRAIL_WALK.md`.

---

## § Held-out reveal analysis — QUARANTINED from later in-loop recall (D33)

*Everything below is off-limits to any future experiment's in-loop session. Later recalls read
the section above, `improvement_records/`, and `improvement_backlog.md` — never this one.*

### The secondary

| generation | passed / 36 | rate | basis |
|---|---|---|---|
| H0 | 5 | 13.9% | measured |
| H4 | 8 | 22.2% | measured |
| H7 | 6.7 | 18.5% | measured |

Omitted generations carry their predecessor's draws, as the freeze specified.

**Endpoint H7 − H0 = +1.7 tasks (+4.6 pp)** — inside the ±4.5 pp band at T=36×3, so
**directional only**. Pre-registered trend over the three measured generations:
**z = 1.11, p = 0.133 — not significant.** Fragility is advisory only, since nothing was
significant to be fragile.

**Secondary verdict: flat.** With the primary flat, the frozen key resolves to
`primary_flat × secondary_flat`.

### What the midpoint says that the endpoint does not

H4 (22.2%) is the experiment's high, and H7 (18.5%) falls back from it — the same shape the
batch curve shows (peak at `batch_05`, decline through `batch_07`). The two instruments agree
on the *trajectory* even though neither is significant, which is worth more than either alone:
**the harness genuinely got better through gen-004 and genuinely got worse after it.** The
batch-side attribution for the decline is C11 plus accumulated instruction growth; the
held-out lane cannot separate those, and neither can the batch lane.

### Transitions and retention

Churn is ~3.3 task cells per transition against a mean |net| of 1.3 — per-task movement inside
that band is noise. Ever-solved rose 8/36 → 15/36 while fully-solved went 2 → 4 → 3. **The
harness learned to touch more tasks and to finish no more of them**, which is the same story
the batch-side ARGS/ABSENT split told from the first round.

### On the capability claim

The held-out set is pure-holdout — 36 tasks with zero in-loop batch exposure in any
experiment — and its claim rests on the stated **procedural** basis (the cross-experiment
firewall, declared per source in `benchmark/partition_reuse.yaml`), not on an unqualified
zero-exposure basis. **No capability claim is made**: the secondary is flat.

---

## Verdict

**Null on both instruments, with every prior excuse removed.** The measured ceiling was real
(+20.5 pp on this batch), the batch was proven reachable, the noise floor was measured before
the first mutation, every surface class was exercised, and the loop closed **0.0%** of the
available headroom.

The two things seq 12 leaves the project are not scores. First: **the identity round's noise
and the objective's total headroom are the same size (20.5 pp)** — this instrument cannot
resolve the effect it was built to detect, and that was knowable before any mutation landed.
Second: **structural delivery is not a general answer to instruction failure** — the same rule
failed identically through prose and through a verified point-of-use injection, and two state
tools were adopted at 578 and 1515 calls without moving reward.

A future experiment that wants a different answer should change the instrument, not the loop:
more trials per cell, or a batch whose per-task rates are not concentrated where the A/A pair
showed them moving most.
