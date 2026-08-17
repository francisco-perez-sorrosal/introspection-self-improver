# Experiment 008_stratb-bm25-luna56 — closure

**REVEALED 2026-08-17.** Six generations, run fully autonomously. The stratified-batch
experiment (plan D28): the same design as seq 6 with two instrument repairs — a batch spanning
*measured* strata, and a mechanical nine-cell reading key — and the first run on the D24 seam.

> **Nothing here is comparable to seq ≤ 6.** D24 changed the benchmark semantic adapter's
> semantics between experiments (registry-declared Pi-local tool calls are executed by Pi and
> suppressed from τ). Every number below is on the post-D24 seam.

---

## The verdict, against the pre-registered key

Both instruments are **null**. The frozen `reading_key` cell is
**`primary_flat_secondary_flat`**, and its pre-registered language is applied rather than
edited:

> *"Null on both instruments. With strata verified to move under H0 before the freeze, the
> instrument excuse that survived seq 6 is gone: six generations of composite sets, with the
> structural surfaces available for the first time, produced no detectable change anywhere.
> Against the standing reading this says the meta-agent is the problem, and the closure says
> so plainly."*

**Primary — the paired batch endpoint test (H6's `batch_07` vs H0's `batch_01`).**
Σ per-task rate deltas = **+1.333**, exact one-sided p = **0.2500**. Positive sum, not
significant; `flat` by the frozen direction rule, which classes a non-significant sum of
either sign as flat.

**Secondary — the held-out trend (diagnostic transfer probe).** z = **0.60**, p = **0.274**;
endpoint **+1 task (+3.6 pp)**, inside the ±5 pp band. Fragility is moot: the trend is not
significant, so no task's removal can flip it; one first-ever pass appears only at H6
(`task_092`), and zeroing it gives z = 0.38.

**The held-out set is on its FOURTH exposure** (reused verbatim from seq 4/5/6, all revealed;
declared in `benchmark/partition_reuse.yaml` against each source). Under D25 rule 2 that lane
is formally a diagnostic transfer probe and carries **no capability claim** — which costs
nothing here, since it showed nothing to claim.

### Where the key's language overshoots, stated precisely

The cell says "no detectable change anywhere". That is right about the two instruments and
wrong as a description of the data, and the closure owes both halves:

- The **batch curve moved**: 41.7 → 54.2 → 45.8 → 62.5 → **66.7** → 58.3 → 58.3 %. It peaked
  25 pp above baseline and ended 16.7 pp above it.
- The **primary is underpowered by the batch's own endpoint structure**, not merely
  unpersuaded. Only **two** of eight tasks have a non-zero endpoint delta, and the exact
  sign-flip test enumerates signs over non-zero deltas only — so two movers cap p at 1/4.
  **Five movers were required to reach α = 0.05.** This was computed and recorded in the
  backlog at gen-005, *before* the endpoint round ran, so it is a pre-known limit rather than
  a post-hoc excuse.
- Three mechanisms were **confirmed on behavioural counters** (below), which is a detectable
  change in the harness even though it did not become a detectable change in the score.

The honest summary: **the loop demonstrably changed the harness's behaviour and did not
demonstrably improve its capability.**

---

## The batch, task by task

| task | stratum | b01 | b02 | b03 | b04 | b05 | b06 | b07 | endpoint Δ |
|---|---|---|---|---|---|---|---|---|---|
| task_006 | anchor | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | 0 |
| task_032 | anchor | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | 0 |
| task_014 | marginal | 1/3 | 1/3 | 0/3 | 3/3 | 3/3 | 3/3 | 2/3 | **+0.333** |
| task_057 | marginal | 0/3 | 3/3 | 3/3 | 2/3 | 3/3 | 2/3 | 3/3 | **+1.000** |
| task_076 | marginal | 3/3 | 2/3 | 2/3 | 3/3 | 3/3 | 3/3 | 3/3 | 0 |
| task_026 | headroom | 0/3 | 0/3 | 0/3 | 0/3 | 0/3 | 0/3 | 0/3 | 0 |
| task_072 | headroom | 0/3 | 1/3 | 0/3 | 1/3 | 1/3 | 0/3 | 0/3 | 0 |
| task_096 | headroom | 0/3 | 0/3 | 0/3 | 0/3 | 0/3 | 0/3 | 0/3 | 0 |
| **total** | | 10/24 | 13/24 | 11/24 | 15/24 | 16/24 | 14/24 | 14/24 | |

**Held-out (fourth exposure, no capability claim):** 16.7 → 16.7 → 22.6 → 20.2 → 16.7 → 19.0 →
20.2 %.

---

## What this experiment established that outlives its numbers

### 1. The measured noise floor — the single most useful number here

gen-005 removed a change that never executed, so **H5 was behaviourally identical to H4** and
`batch_06` re-measured the same harness. It still moved **two cells (8.3 pp)**: `task_057`
3/3 → 2/3 and `task_072` 1/3 → 0/3.

> **Round-to-round noise on an identical harness: 2 cells, 8.3 pp.**

No prior experiment in this project had a behavioural-identity round to measure it with. It
re-reads everything: a single-cell movement on a marginal or headroom task is noise, and the
attributions that survive are the ones carrying a mechanism *and* a counter — never a cell.

### 2. Framing, not surface, is what moves an injected note

Not designed in advance. Three changes happened to differ in *framing* while sharing a
surface, and a fixed batch measured each:

| injection shape | measured effect |
|---|---|
| a bare **list** of facts (C1) | changed nothing — target counters 0/3 → 0/3 and 2/3 → 2/3; **reverted** |
| a **missing-state** note (D2) | changed behaviour **and suppressed unasked** — transfer-reason queries 0/3 → 3/3, transfer rate 9/24 → 6/24 |
| a **completed-state** note (E1) | safe, and inert outside its own target |
| a **consequence-stating** note (H1) | prediction confirmed at the endpoint; falsifier held |

The corollary that cost a slot to learn: **a missing-state note carries suppression risk that a
completed-state note does not.** D2 states a fact, gives no instruction and contains no escape
clause, and the transfer rate fell anyway where no suppression was requested. This sharpens
the project's standing lesson past wording: it is not only escape clauses — *any* injected
statement about a missing precondition can be read as a bar to acting.

### 3. Transfer discrimination moved for the first time — on one side

Seven mutations across four experiments had moved the transfer *rate* and none the
*discrimination*. D2 moved it: `task_014` (gold action IS a transfer, gold compares `reason`)
went 1/3 → 3/3 with the correct `unconfirmed_external_communication`, and the conditional is
clean at the endpoint — **every trial that issued the transfer-reason query chose the gold
reason; the one that did not, did not.** `task_032` (gold transfer, reason uncompared) held 3/3
for all seven rounds.

**And only on one side.** Over-escalation did not improve: `task_026` and `task_096` still
carry transfers gold does not want. Correct transfers got better; unwanted ones did not get
rarer.

### 4. A revert rule, with a measured counterfactual

> **A denied prediction is not by itself a revert trigger; a denied *mechanism* is.**

C1's prediction was denied *and* its mechanism moved nothing anywhere *and* its evidence base
was misattributed → reverted. D2's prediction was denied while its mechanism moved a counter
0/3 → 3/3 on the one task where it could fire → kept. **Two rounds later D2 produced the
experiment's clearest win.** Had it been reverted on its denied prediction, that win would not
exist.

### 5. The anchors did their job, and the stratification paid for itself

`task_006` and `task_032` are **21/21 each — 42 episodes, seven rounds, no regression** across
eleven landed changes. The regression channel stayed silent, which is what makes every movement
elsewhere attributable rather than ambient.

The stratification also *produced a finding a known-fail batch cannot*: `task_076`'s regression
was diagnosed by reading a **passing** trial against a **failing** trial of the same task under
the same harness, which identified a duplicate `log_verification` write as the entire
difference. Seq 5 and seq 6 had no such pair by construction.

### 6. The remaining headroom is surface-exhausted, and the layers were peeled to prove it

All three 0-cell tasks fail on the *same* mode, reached only after five rounds of peeling:

- **`task_026`** — by `batch_05` it unlocked the gold tool and called it with **three of four
  gold values exact** (6300, 3800, 1020), one off by one (**1499** vs gold **1500**), plus two
  corrections gold does not carry. One computation slightly off both mis-values a correction
  and manufactures spurious ones. *The procedure is now right; the arithmetic convention is
  not.*
- **`task_096`** — calls both remediation tools with wrong APY-derived amounts.
- **`task_072`** — applies the wrong fee rule. Its `credit_type` enum half was retired at
  gen-002 with cause: the unlock response **already enumerates the legal values with their
  semantics**, the agent read and applied them correctly, and gold classifies the same
  correction differently.

Reaching a rounding convention or a governing rate requires encoding domain knowledge, which
the invariants forbid outright. Two plausible mutations were ruled out on *evidence* rather
than argument: a D24 extension-tool calculator would have computed the same wrong number
(`task_072`'s arithmetic is internally consistent), and surfacing the enum would have changed
nothing (it was already surfaced).

---

## Rejected, reverted and failed — first-class results

| change | surface | outcome |
|---|---|---|
| **C1** — list KB-named tools after a search | `extension-hook` | **DENIED**, reverted at gen-002. Counter moved nowhere; half its evidence was misattributed (see errata). |
| **C2** — hand a user tool over by its exact name | `instructions` | **CONFIRMED**, and clause-resolved: clause 1 ("with the tool name alone") fired its falsifier and the task passed anyway; **clause 2 is the mechanism**. First clause-level attribution in this project. |
| **D2** — report the missing transfer-reason lookup | `extension-hook` | Prediction **denied at gen-003, confirmed at gen-004**. The experiment's clearest win, and a suppression side effect. |
| **E1** — report verification on record | `extension-hook` | **CONFIRMED** on its counter; later shown insufficient when `task_057` logged twice across separate turns. |
| **F1** — list unclaimed KB-named tools | `extension-hook` | **MEASURED INERT** — never executed. Reverted at gen-005; its repair deliberately not landed. |
| **H1** — state the consequence, not only the state | `extension-hook` | **CONFIRMED** at the endpoint: zero duplicate writes, falsifier held at 9/24. |

**Two reverts, one inert change, one retirement reversed.** All in the record.

### Errata against this experiment's own records

1. **`gen_000_to_001.yaml`, signal 1 is wrong.** It states `task_096` "unlocked neither"
   remediation tool in 3/3 trials. In 2 of 3 it unlocked **and called** both and failed on
   argument *values*. The "retrieved and never used" population is `task_026` alone — 3/24
   episodes, not 6/24 — and C1 was justified on evidence half of which name salience could not
   address. The record is left as written (the schema refuses unknown fields, and rewriting a
   verified record erases the error rather than recording it); `improvement_backlog.md` is the
   durable home. **Generalized: an aggregated miss list is not a mechanism.**
2. **T3 was retired at gen-003 and un-retired at gen-004.** The retirement rested on one
   round's episode shapes; `batch_04` falsified it.

### Three process failures

1. gen-004 spent a generation on a change that never ran — on a fact recorded in this
   experiment's own probe.
2. F1's preflight showed 3/3 against a 0/12 baseline **for a change that never executed**. A
   preflight verifies that a change *runs*, not that it *works*. Standing rule added: verify
   an injection's text in a fetched conversation before reading any behavioural number.
3. A target was retired on one round of evidence.

---

## Machinery

- **756 episodes**: 168 platform batch + 588 local held-out, plus probes and preflights.
- **One freeze fingerprint** (`sha256:fea4ae1c…`) across all 15 runs; `arm_sha_ok` on 168/168
  platform rows.
- **Seam health**: zero disconnects, zero timeouts, zero stall warnings across 168 platform
  episodes. Two `sandbox_seam_unclassified` and two `sandbox_tool_errors` on a single episode
  (`task_096` t1, `batch_02`), which completed with evidence intact — disclosed rather than
  rounded to "zero incidents".
- **`pi_local_calls` = 0 across all 168 episodes**, correctly: every change landed was a hook,
  and hooks are not registered tools. **So the D24 seam change was exercised in its pump path
  and never in its suppressing path** — a real limit of this experiment, since D24 was the
  groundwork that motivated it. Extension tools and sub-agents remain, after all this,
  *available but unexercised in a graded round*.
- **Spend ≈ \$17**: \$2.61 platform, \$12.03 local, ≈\$2.4 probes and preflights.
- **§29 walk**: seventeen HELD, two N/A by design, one HELD by frozen delegation, **none
  waived** — `GUARDRAIL_WALK.md`.

## Reading this experiment against seq 5 and seq 6 — and why you mostly cannot

Seq 5 and seq 6 both returned a null primary and both left the same escape open: the batch
could barely have said yes. Seq 8 closed that escape — the strata were measured under H0 before
the freeze, anchors were verified, and the batch moved 25 pp at its peak — and **still returned
a null primary**, because six of eight tasks ended where they started.

But the comparison stops there. D24 changed the seam between experiments, so the curves are not
commensurable, and the batch composition changed by design. What transfers is not a number but
the method: **stratify, and you can tell a regression from noise; keep a behavioural-identity
round, and you can measure the noise itself.**

## Artifacts

`summary.md` (progression, trend, fragility) · `batch_curve.json` (the pre-registered primary)
· `GUARDRAIL_WALK.md` · `improvement_records/gen_000_to_001 … gen_005_to_006.yaml` (six, schema
v3) · `improvement_backlog.md` (six transition stamps, the errata, the surface-exhausted
finding) · `generation_000…006/` (168 platform episodes, gates, step-4b probes, preflights) ·
`held_out/` (588 episodes, copied verbatim at reveal) · `benchmark_lock.yaml`,
`split_manifest.yaml`, `experiment.yaml`. Tags `h0-baseline` (`b76f274`), `exp8-g001…g006`.
PRs #17–#22.
