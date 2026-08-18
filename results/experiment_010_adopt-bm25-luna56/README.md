# Experiment 010_adopt-bm25-luna56 — closure

**The both-curves experiment.** Pre-registered success was the sig-up × sig-up cell: the
batch primary *and* the held-out secondary both rising. **Neither rose significantly. The
verdict is the `primary_flat_secondary_flat` cell of the frozen reading key, and that cell
says plainly: the loop found nothing.**

Frozen 2026-08-17, run and closed 2026-08-18. G=8 (gen-001 a pre-registered identity),
B=12, T=36, `num_trials: 3`, `batch_mode: fixed`, autonomous under the D34 envelope.
324 platform episodes + 864 local held-out episodes + 114 screen episodes, ≈$32.

> **Reading this file after D33.** The two sections below are separated on purpose. A later
> experiment's **in-loop** sessions may read *§ Batch-derived findings* and the
> `improvement_records/` and `improvement_backlog.md` it summarises. They may **not** read
> *§ Held-out reveal analysis*, `summary.md`, `held_out/`, or the trend and fragility
> artifacts — not now and not ever, revealed or not. The quarantine has no expiry.

---

## § Batch-derived findings — recallable by later in-loop sessions

### The pre-registered primary

Exact one-sided paired sign-flip, endpoint `batch_09` vs the pooled H0 baseline
(`batch_01` + `batch_02`, six trials per task): **Σ rate deltas = +1.333, p = 0.1836 — not
significant at α = 0.05.** Movable 10 of 12, five movers needed; the envelope committed at
freeze said this was attainable, and it was not attained.

Batch curve: **55.6, 55.6, 47.2, 72.2, 52.8, 61.1, 63.9, 61.1, 66.7%.**
Reachable harvest 0.556 → 0.667, **no walled tasks**. Harvest below 90% with every
precondition met is the key's "loop found nothing" branch, not its "objective exhausted"
branch.

### What the identity round bought, and it was the experiment's best investment

`batch_02` re-measured a byte-identical harness: **round total unchanged at 20/36 while 14
of 36 trial cells flipped** (6 cells of net task-rate movement, 16.7 pp). Gains and losses
cancelled almost exactly. Three identical-harness draws put `task_008` at 3/2/0 — a full
three-cell range on no change at all.

**The operational rule that followed, and that every later attribution obeyed:** one cell is
noise, two is suggestive, and nothing is attributable without its own mechanism counter
moving in the predicted direction. Getting this *before* the first mutation is why no
generation in this experiment was spent explaining a swing that turned out to be nothing.

### Per-change verdicts, scored on counters

| change | surface | mechanism | verdict |
|---|---|---|---|
| C1 `compare_options` | **extension-tool** | constrained multi-candidate selection | **adoption CONFIRMED** — `pi_local_calls` 0 → 39 |
| C2 exact-string handover | instructions | the handover message carries the exact tool name and argument names | **CONFIRMED and persistent** |
| C3 narrow the tool | instructions | fire only on genuine choices | mechanism **CONFIRMED** (52 → 28 calls), cost claim **DENIED** |
| C4 per-candidate search | instructions | a product's terms are split across documents | counter confirmed **once**, cost falsifier fired — **reverted** |
| C5 `KB_search` index | **extension-hook** | show the agent what it already retrieved | **measured inert** — **reverted** |
| C6 revert C5 | revert | — | **CONFIRMED** |
| C7 revert C4 | revert | — | **CONFIRMED** on all three counters |

### The five findings worth carrying forward

1. **The D24 Pi-local surface works, and this experiment is the proof.** `pi_local_calls`
   went from **zero across all 168 platform episodes of the prior experiment and every
   episode before it** to 39 in a single round, with well-formed multi-candidate arguments,
   on the first change ever landed on that surface. Three closures had named the unusable
   structural surfaces as the live hypothesis for why this loop could not improve. That
   hypothesis is now dead: the surface is reachable, adoption-first works as a landing
   discipline, and the pre-freeze suppression canary is what converted it from assumption
   to measurement.
2. **Adoption is not improvement.** C1 was adopted enthusiastically and moved no reward.
   The surface being usable and the surface being useful are different claims, and this
   experiment separated them for the first time.
3. **The bare-list null replicates.** A prior experiment measured that a bare *list*
   appended to what the model reads moves no counter, while a *missing-state* note moved one
   0/3 → 3/3. C5 appended a bare list — about the agent's own retrieval history, a case
   different enough to be worth a slot — and produced the same null. Replication across a
   different experiment, surface class and subject matter makes this the project's
   best-established craft finding. **Do not spend another slot on a bare list.**
4. **Retrieval volume is the turn cost, established by elimination.** gen-004 halved the
   tool calls and episode length did not move; gen-005 raised `KB_search` 31% and length rose
   with it; gen-008 removed that instruction and `KB_search` fell 11.6 → 9.3 with messages
   46.5 → 43.3. Three rounds, three consistent readings. Episode length tracks `KB_search`
   and nothing else this experiment touched.
5. **A falsifier keyed on a level rather than a delta is not a falsifier.** C3's clause-1
   falsifier read "stays at 0 on `task_023`" — and it was 0 *before* the change too, so it
   fired on a pre-existing condition and diagnosed nothing. Every falsifier after gen-005
   states a delta.

### Craft that held under load

Reverts were first-class and both were justified on *mechanism*, not on cells. A provisional
harm attribution (C5 → `task_003`) was **retracted** when the next round refused to confirm
it. `task_003`'s failure was diagnosed to a specific document — the customer ties on annual
fee, so the decision falls to cash back, and the 4% travel rate that decides it sits in a
document the agent never retrieved — which also gave the task a clean *reachability* verdict
instead of a guess. The anchors moved exactly one cell in nine rounds, which is what made
everything else attributable.

### Surfaces, and the one never exercised

Exercised: `extension-tool` (C1), `instructions` (C2/C3/C4), `extension-hook` (C5).
**`sub-agent` was never exercised**, and the honest reason is a budget one rather than a
measured impossibility: the D29 ladder was discharged at gen-006 by landing on
`extension-hook`, and the two remaining slots went to reverts that the evidence demanded.
No probe was run against `sub-agent` in this experiment, so **no `surface_exhausted` finding
is claimed for it** — it remains open, unmeasured, and the only class this project has never
run a single episode on.

### Operational

`make batch` at concurrency 3 and the lock's default carried unchanged. Nine batch rounds,
324/324 episodes `evidence_complete` and `arm_sha_ok`. Seam incidents in three rounds; one
round (`batch_02`) was **voided and re-measured** because its contamination biased the pooled
baseline *toward* the hypothesis, and the endpoint round's contamination was **kept** because
it biased *against* it — the asymmetry is the rule, and it is recorded in both places.

---

## § Held-out reveal analysis — QUARANTINED from later in-loop recall (D33)

*Nothing in this section may be read by an in-loop session of any later experiment.*

The secondary instrument: one-sided trend over the eight measured generations (H1 carried),
**z = 0.03, p = 0.486 — not significant.** Endpoint R_T(H8) − R_T(H0) = **+0.0 pp**, inside
the ±5 pp band. Progression: 20.4, [20.4 carried], 26.9, 20.4, 22.2, 25.9, 24.1, 23.1,
20.4%. The trend is not significant, so no single task's removal can flip it and the
fragility report is vacuous by construction.

The held-out lane carried a **capability claim on the D33 procedural basis** — T=36
pure-holdout, zero in-loop batch exposure in every experiment, all five sources declared. The
claim was available and **is not made**: there is nothing to claim.

Two things the held-out side shows that the batch side does not. **Churn is ~9.5 task cells
per transition against a mean |net| of 2.8** — the same cancelling-churn structure the batch
A/A measured, reproduced independently on a set the loop never touched. And **ever-solved
rose 12/36 → 21/36 while fully-solved ended where it began at 3/36**: across nine harnesses
the loop touched nearly twice as many tasks at least once as H0 could, and consolidated none
of it. That gap — breadth without retention — is the sharpest description of this null the
data supports, and it is a held-out-only finding.

---

## Verdict

Against the frozen reading key: **`primary_flat_secondary_flat`**. Harvest low, ≥15 reachable
failing cells at baseline, an attainable power envelope, a measured noise floor, and every
surface class certified reachable — **every precondition a prior null could be blamed on was
removed, and the loop still found nothing.** The closure says so plainly, as the key requires.

What seq 10 nevertheless established, and what no prior experiment could: the structural
surfaces are usable, adoption-first is a working landing discipline, retrieval volume is the
turn cost, the bare-list null replicates, and a designed identity round makes an experiment
able to tell its own signal from its own noise before spending a single slot.

The unconsumed targets and the mechanism each never reached are listed in
`improvement_backlog.md`. `sub-agent` remains unexercised and unmeasured.
