# Experiment 012_ceiling-emb-luna56 — independent review

Post-reveal review, written 2026-08-19 from the committed artifacts and git history
(`improvement_records/`, `improvement_backlog.md`, `batch_curve.json`, `endpoint_test.json`,
`gates/`, `GUARDRAIL_WALK.md`, the six mutation PRs #36–#41, the g=0 sub-agent probe, the
seq-11 ceiling probe under `results/experiment_011_ceiling-probe/` +
`benchmark/probes/2026-08-18-phase0-ceiling-probe/` — including the committed H-expert
source — and the process artifacts). Every number re-derived at source; the statistics were
recomputed independently (null simulations, power curves, stratum decompositions). Where
this review disagrees with the closure README, the disagreement is stated with its
arithmetic. This is a closure-phase document: it follows the D33 split, and the session
that wrote it never drives in-loop decisions.

---

## § Batch-derived findings — recallable by later in-loop sessions

### 1. Verdict

The frozen instruments are null and the frozen key was applied verbatim: primary
(episode-level within-task permutation, `batch_08` vs pooled `batch_01`+`batch_02`)
34.62% → 34.62%, Σ = −0.000, p = 0.566; the key's `primary_flat × secondary_flat` cell
resolved on headroom (large) and harvest (0.346, low), and the closure said the cell's
words plainly. The craft was the best this project has produced (§4). Three review-level
findings qualify the verdict — the first corrects the closure, the second reframes it, the
third is the thing to act on:

1. **The closure's central number conflates units, and the corrected statement is
   different in kind.** "The identity round's noise and the objective's total headroom are
   the same size (20.5 pp)" compares the A/A round's **gross per-task churn** (16 flipped
   trial cells / 78 = 20.5% *of cells*) with the **net** headroom (+20.5 pp *of rate*).
   The A/A **net** movement was +2 cells = **+2.6 pp**, and simulation puts the observed
   gross churn dead inside the binomial expectation (14 ± 3 cells; P(≥16) = 0.30) — no
   common-mode or day-level drift, ordinary trial noise. The corrected power statement:
   **the primary had ~94% power for the ceiling-sized effect it was built to detect**
   (net SE ≈ 5.1 pp on the pooled comparison), ~0.4–0.5 power for the ~+8 pp the loop
   actually produced, and the pre-known 80%-power shortfall (17.2 pp needed vs 15.2 pp
   measured headroom) that D36 recorded "not smoothed" — and the closure never mentions.
   So the 0.0% gap closure is a **real result about the endpoint harness**, not an
   instrument artifact; what the churn number truly bounds is *per-task* attribution.
2. **The loop found ~+8 pp and gave it back.** The batch peaked at `batch_05` (42.3% vs
   the 34.6% pooled baseline; interim p = 0.111, CMH z = 1.39) — and the other lane
   peaked at the *same generation* on disjoint tasks (aggregate detail in the quarantined
   section; individually near-significant there too). Two instruments, one generation,
   then three generations of decline to an endpoint of exactly zero. The stratum
   decomposition sharpens it: at the endpoint the **headroom stratum is +12.1 pp**
   (z = 1.53, one-sided p ≈ 0.06) — cancelled by **anchors −16.7 pp** and marginals
   −6.9 pp. The null endpoint is therefore substantially a **retention and interference
   failure, not a discovery failure**: the loop discovered real mechanisms, kept
   layering, regressed what already passed, and owns no rule that reverts to the best
   measured harness. Under a revert-to-best endpoint rule, seq 12 ends ≈ +8 pp on both
   lanes instead of 0.0.
3. **The constitution is the binding constraint, and seq 11 + seq 12 together prove it.**
   The H-expert — built *by the meta-agent itself* during Phase 0, in a day, entirely
   inside the mutable surface, iterated by watching itself fail — nets **+15.2 pp**
   (gross +21.0, with −5.7 of self-inflicted regressions) as a ten-rule interacting
   ensemble with point-of-use reinforcement. The loop, run by the same meta-agent under
   the one-coherent-mechanism / no-interaction / cost-falsifier / revert-on-denial
   constitution, netted 0.0 on the same batch. §7 shows the gap mechanism by mechanism:
   the loop *found* one of the ceiling's core components and its own cost discipline
   reverted it; it never *formed* two others despite holding the evidence; and the
   ensemble the ceiling requires is unbuildable one attributable change at a time. "The
   meta-agent is the problem" (seq 5's reading) is now measured to be false in an exact
   sense: the agent is capable, the instrument was adequate for the ceiling, the
   objective has proven headroom — **the loop's rules are what stand between them.**

### 2. What happened, verified

#### 2.1 The primary, and the corrected power statement

`scripts/endpoint_test.py` (new at D36, replacing the sign test, validated on prior data
at freeze): baseline 0.3462 (156 episodes) vs endpoint 0.3462 (78), Σ per-task rate deltas
−0.000, p = 0.56588 at 100k permutations, CMH z = 0.000 (`endpoint_test.json`). Interim
endpoint p's: 0.30, 0.11, 0.16, 0.66 at `batch_04`…`batch_07`. Batch curve (mean per-task
rate): 33.3, 35.9, 37.2, 38.5, **42.3**, 41.0, 33.3, 34.6%. Harvest 0.333 → 0.346,
`walled: []`. The diagnostic all-rounds batch trend — z = 0.110, p = 0.456 — is
unnarrated in the closure.

Independent power simulation at the actual task-rate structure: power 0.94 at the
H-expert's per-task rates (net +17.9 pp on this batch), 0.59 at a uniform +10 pp, 0.25 at
+5 pp; 80%-power detectable effect 14.6 pp at 3 trials/cell, falling to 8.4 pp at 9
trials. The envelope gate (`gates/power_envelope.json`) had computed SE 6.93 pp,
detectable-at-α 11.4 pp, 80%-power 17.2 pp — verdict REACHABLE because 11.4 < 15.2, with
the 80% shortfall recorded in D36 and acted on by no one. **The instrument could see the
ceiling and could not see the loop.**

#### 2.2 The A/A round: churn, not signal-sized noise

`batch_01` → `batch_02` on a byte-identical harness: net +2 cells (+2.6 pp), gross 16
trial cells across 13 of 26 tasks, three tasks by two full cells (`batch_curve.json`
`noise_floor`; the closure's counts verified). Against 20k simulated identical-round
pairs at the pooled per-task rates: expected gross 14.0 ± 3.0, P(≥16) = 0.30 — **the
seam's episodes behave as independent draws; there is no excess noise to blame.** Null SD
of the *net* aggregate delta: 5.9 pp (78 vs 78), 5.1 pp for the primary's pooled
comparison. Per-stratum A/A: anchors gross 3 / **net +3** (4/9 → 7/9 — under the
embeddings backend the "anchors" are marginals wearing the wrong label), marginals gross
9 / net −1, headroom gross 4 / **net 0** (3/33 twice). The backlog's two-regimes rule —
reward-level movement is unattributable without a mechanism counter, headroom-stratum
movement excepted — is exactly right and was derived before the first mutation.

#### 2.3 The peak the endpoint erased

`batch_05` (run by H4, after C7/C8 landed) is the experiment's high: +7.7 pp over the
pooled baseline, interim p = 0.111 — roughly **43% of the in-experiment headroom closed
at generation 4**. The other lane's measured midpoint peaked at the same generation
(quarantined section). The decline through `batch_06`–`batch_08` tracks the C9→C11 phase:
`batch_07` collapsed to 33.8% with every stratum down, C12's removal of C11 recovered
partially (34.6%, "short of batch_06" as the record says). Endpoint stratum decomposition
vs baseline: headroom **+12.1 pp** (p ≈ 0.06), anchors **−16.7 pp**, marginals −6.9 pp —
net zero by cancellation. A batch-wide statistic cannot flag this; a pre-registered
headroom co-primary would have sat at the edge of significance, and a live
anchor-regression brake would have caught the giveback while it was happening.

#### 2.4 The ceiling, and what stands between the loop and it

Phase 0 (seq 11, PROVISIONAL): 35 candidates × 3 trials × {H0, H-expert} × {bm25,
openai_embeddings}, 416 episodes, $12.82. Backend chosen on *harness headroom* (+15.2 pp
embeddings vs +6.7 bm25) against the higher-absolute-H0 backend — the pre-registered rule
working as designed. The H-expert (committed at
`benchmark/probes/2026-08-18-phase0-ceiling-probe/h-expert/`): a ~95-line ten-rule
`<instructions>` rewrite plus one `tool_result` hook re-injecting the selection
discipline after every `KB_search` and a completed-state "walk the customer's stated
requests again" note after every state-changing call. **Fully legal** — no gold values,
no document ids, no per-task procedure; it also *regressed five tasks H0 passes*
(over-work and early-stop — the project's most-replicated lesson, reproduced inside the
instrument that measured the ceiling), which makes +15.2 pp a lower bound built by an
imperfect author. It was aimed by seq-10's batch finding (failures concentrate in
*which value*, not *which tool*) and re-aimed twice by preflight rounds watching it fail.

The gap table — H-expert mechanism vs what the loop did with it — is in §7. The
uncomfortable headline: of the expert's ten rules, the loop confirmed one (exact-strings
/ verbatim handover, seq-10 C2 ≙ expert R5/R6), **found and reverted one on a cost
falsifier** (per-candidate search, seq-10 C4 ≙ expert R4b — a core ceiling component),
attacked one through tools three times where the expert makes the model write the
comparison itself (R4), and **never attempted** the two rules the probe discovered by
iterating on failures (R2 ordering-before-closure; R4a the-figure-that-applies-to-THIS-
customer) — despite the loop's own diagnoses containing the same evidence
(seq-10's `task_003` read names the identical mode).

#### 2.5 The D29–D36 machinery in battle

Condensed; the full table is in the process map this review rests on. Worked as designed:
the identity round (twice, now the project's most important instrument), adoption-first
(three times — and it is what keeps "reachable", "used", "useful" separate), the ladder +
reserved slot (sub-agent, the last unexercised class, closed by the g=0 probe: delegation
works and is cleanly suppressed, but a child's τ-tool calls die at the MCP daemon without
reaching the bridge — 120 s per attempt, reward 0.0 — so the step-budget question is moot
and the surface is `surface_exhausted` for every retrieval-shaped target), the host-facts
lint (zero F1-class failures in two experiments), the harvest co-metric (resolved the
flat×flat cell mechanically), the D33 split headings (seq-12's recall read seq-10's
batch-derived section only; attestation clean), the cadence byte-identity check (caught a
live `make reset_h0` mistake before the endpoint held-out round at zero cost). Misfired
or exposed: the **power envelope** (REACHABLE from theoretical SE while the 80% shortfall
was known and recorded — the gate asked the wrong question), the **futility check**
(fired at a 0.3 pp margin and was refuted the next round; fired at 8.9 pp and was right —
its capacity statistic is updated by the very round that refutes it), the **revert cap**
(≤2, exceeded by a declared, reasoned third revert — the cap conflicts with post-futility
knowledge mode), and the **sparse held-out cadence** (three measured points cannot carry
a trend; quarantined section).

#### 2.6 Ops

624 platform batch episodes (614 graded; 10 lost to user-sim/infra weather, resumed where
resumable under D35), 3 × 108 local held-out, ~24 probe/preflight/canary episodes.
Spend ≈ $12 graded + probes (D36 had budgeted $60–70 for a B=30/10-round shape). All four
freeze gates PASS before the first graded episode; the suppression canary's first FAIL
(unbuilt Runtime image) was separated from a load failure via the local lane — the gate
doing its job. §29: 19 HELD, 1 N/A-by-design, **one declared composition-policy
deviation** (the third revert), two orchestrator errors recorded (§6), D33 attestation
clean, autonomy provenance uniform across all seven records. Tags `exp12-g002…g007`,
PRs #36–#41.

### 3. The six mutation slots, compressed

| slot | change | surface | outcome |
|---|---|---|---|
| — (gen-001) | pre-registered identity | — | A/A measured: net +2.6 pp, gross 16 cells; headroom stratum 0 movement; the two-regimes attribution rule derived |
| 1 | **C1** required-args-only; **C2** name the specific enum member; **C3** search by candidate name | instr ×3 | C1 DENIED (9→9→9); **C2 CONFIRMED** (catch-all 7→3, transfers held, sole-cause 5→2); C3 DIRECTIONAL (+2.96 distinct docs/ep vs ≥3.0, costs clean) |
| 2 | **C4** C1's rule as a `tool_result` hook, no escape clause; **C5** unlock the procedure-named tool; **C6** requirement-coverage check | hook + instr ×2 | C4 **DENIED with the strongest evidence in the project** — verified firing on the graded lane, injecting the exact required/optional split, and the agent sent both optional keys anyway (counter 9,9,9,8 across no-instruction/prose/structure rounds); C5 DENIED wrong-direction (12→14→16); C6 DENIED + cost fired — but its safety falsifier held (completed-state framing did not suppress) |
| 3 | **C7** revert C6; **C8** `track_requests` state tool | revert + tool | C7 CONFIRMED (messages fell — C6 was a cost driver); C8 adoption 0→**578 calls**, 76/78 episodes, zero τ leak; mechanism counter 15→13→10 CONFIRMED at deferral; **reward NOT** |
| 4 | **C9** apply the KB's stated selection rule — built deliberately in the "confirmed shape" as the shape-hypothesis' first out-of-sample test; **C10** revert C5 | instr + revert | C9 DENIED, counter wrong way (5→8) — **the shape hypothesis refuted on its first prospective test**; its second clause was mis-specified (a level, not a delta — orchestrator error #1); C10 CONFIRMED |
| 5 | **C11** `compare_candidates` state tool | tool | adoption **1515 calls / 77 of 78 episodes** CONFIRMED; mechanism DENIED (8→8, wider 26→28); cost fired; the round collapsed 41.0→33.8 with every stratum down; the pre-registered adversarial reading measured true: "the model asks for the gaps, receives them, and chooses anyway" |
| 6 | **C12** remove C11 — third revert, over the ≤2 cap, "a policy violation with its reasoning attached", refuting branch stated in advance | revert | PARTIALLY confirmed: 33.8→34.6, costs fell, short of `batch_06` |

Futility: fired gen-004 (margin 0.3 pp, sensitivity recorded) → **refuted by `batch_05`**;
fired gen-007 (margin 8.9 pp) → correct. Both firings declared out loud, which is what
made the refutation visible.

### 4. Highs

1. **The craft.** This is the best-run experiment in the project's history, and it is not
   close: C4's injected text verified in the graded episode before any number was read;
   C9 built deliberately as an out-of-sample test of the orchestrator's own hypothesis
   (and the hypothesis surrendered when it lost); the third revert declared as a policy
   violation with its refuting branch pre-stated; two preflight designs declared
   uninterpretable and discarded rather than used; the futility check argued with in the
   open; the A/A expectation pre-registered per stratum. Every epistemic norm the last
   four reviews asked for was practiced.
2. **The ceiling exists and is legal** — Phase 0 turned "is there anything to find?" from
   a four-experiment argument into a $13 measurement: +15.2 pp on the mutable surface,
   no domain knowledge, reachability certificates per task. "There was nothing to find"
   is dead as an explanation, permanently.
3. **The loop moved something real at gen-004** — ~43% of the in-experiment gap, with the
   other lane peaking at the same generation (§2.3) — the first time in seven experiments
   the project has cross-lane, same-generation evidence of a genuine harness improvement.
   That it was subsequently destroyed is a process finding (§5.1), not a retraction.
4. **The three-tier separation — reachable / used / useful** — is now measured with
   spectacular numbers: 578 and 1515 adoptions with zero reward movement. Adoption-first
   did exactly what it was designed to do: kept the tiers from being conflated.
5. **"The surface is not the axis" for withholding demands** (C1 vs C4): the same rule,
   denied identically through prose and through a verified point-of-use injection with no
   escape clause. This narrows a three-experiment doctrine to its true scope — structure
   wins for *state the model cannot hold*, not for *restraint the model does not want*.
6. **The last surface class is closed by measurement, not argument** — the sub-agent
   probe's disqualifying finding (children cannot reach τ's tools; the carried
   step-budget question is moot) discharges the reserved slot and ends the
   "unused growth surfaces" hypothesis that has haunted every closure since seq 4.
7. **The safety falsifier as first-class output**: C6's completed-state framing failed
   its target and *held its safety clause* (no suppression) — confirming the seq-8
   framing taxonomy prospectively, on a new backend, from the failure side.
8. **The machinery caught real errors live**: byte-identity caught a mid-experiment
   `reset_h0`; the suppression canary caught an unbuilt image; D35's resume contract
   absorbed the user-sim weather. Zero episodes lost to any of them.

### 5. Lows

1. **No retention mechanism.** The project's first real, cross-lane-corroborated gain
   (+8 pp at gen-004) was layered over and given back, and nothing in the process — not
   the futility check, not the reading key, not the closure procedure — selects the best
   *measured* harness as the endpoint. The loop optimizes its most recent hypothesis, not
   its best result. This is the single most consequential process gap seq 12 exposed.
2. **The envelope gate asked the wrong question.** REACHABLE-at-α passed while the
   recorded 80%-power shortfall (17.2 > 15.2) went unacted-on, and the loop's plausible
   per-generation effect sizes (~5–8 pp) sat at 0.25–0.5 power all along. Marginal-power
   experiments produce exactly what five of them have now produced.
3. **The sparse held-out cadence deleted the secondary's power by construction**
   (quarantined section for the numbers): three measured points cannot carry a trend, and
   the ~$8 saved is small against 624 platform episodes. The protocol's cadence prose was
   never updated for the new lock field either.
4. **The central closure claim conflates gross churn with net noise** (§2.2, §6.1) — and
   the conflation propagated into CLAUDE.md's ledger row and the closure's final advice,
   which recommends "change the instrument, not the loop" on the strength of the wrong
   number. The corrected reading indicts the instrument *less* and the loop's
   constitution *more*.
5. **B shrank from the validated design** (30 → 26 under the certificate rule) at a known
   sensitivity cost (the new primary was validated at freeze showing p = 0.044 at B=30
   for a seq-10-sized movement vs 0.133 at B=12) — unremarked at close; and `num_trials`
   stayed 3 against the prior closure's own recommendation, with the A/A churn landing
   exactly where that recommendation pointed.
6. **Anchors were not re-screened for the new backend** — the 3-task anchor stratum ran
   4/9 → 7/9 across the A/A pair; under embeddings they are marginals, which is part of
   why the endpoint's anchor "regression" reads so large and noisy.
7. **Two orchestrator errors** (both §29-recorded): C9's second clause keyed on a level
   that was already true (fired on a pre-existing condition, diagnosed nothing — the
   level-falsifier ban re-learned); one commit swept round data (path-scoped revert
   recorded).
8. **Instruction-shaped demands failed five times running and the loop kept buying
   them** — C1, C4, C5, C6, C9; the mid-experiment shape hypothesis that would have
   licensed more was honestly refuted (C9), but four of six slots still led with
   instruction-or-equivalent demands into a failure mode the ledger already documented.

### 6. Errata and narration gaps (closure cross-check)

Everything per-change cross-checks clean (README = records = backlog; slot→record map
complete; endpoint arithmetic verified; strata tables consistent). The gaps:

1. **"16 cells / 20.5 pp" vs "+20.5 pp headroom" is a unit conflation** — gross cell
   churn vs net rate; A/A net was +2.6 pp; the churn is binomial-consistent
   (P(≥16) = 0.30). The verdict sentence "this instrument cannot resolve the effect it
   was built to detect" is **false for the ceiling effect** (power 0.94) and true only
   for loop-sized effects. Propagated to CLAUDE.md's seq-12 ledger row — worth
   correcting there.
2. **The 80%-power shortfall (17.2 vs 15.2), recorded at freeze, is absent from the
   closure** — the real, pre-known instrument limitation, displaced by the wrong one.
3. **Two headroom figures circulate unreconciled**: 15.2 pp (probe-wide; what the
   envelope gated on) and +20.5 pp (batch-restricted; what the README headlines) — the
   latter never committed as a machine artifact.
4. **Two batch-curve statistics circulate** (mean per-task rate vs episode fraction),
   differing by up to 1.1 pp per round without a note.
5. **`summary.md` labels H2/H3/H5/H6 "carried (identity)"** — they are carried by the
   sparse `heldout_generations` schedule; only H1 is an identity generation.
6. **Held-out churn "~3.3 cells/transition" averages over five carried zero-rows** — the
   two genuinely measured transitions moved 13 and 10 cells (quarantined section) — the
   same dilution error the A/A round exists to prevent.
7. **The tally "one confirmed" under-counts its own table**: C7 and C10 confirmed their
   predictions, C8's mechanism clause confirmed; one *reward-moving* change is the honest
   phrasing.
8. **The diagnostic batch trend (p = 0.456) and the B=30-vs-26 sensitivity context are
   absent from the closure.**
9. Under-narrated positives: the live `reset_h0` catch, the 403 wait, the first
   `max_steps` termination — all in the walk, none in the README.

### 7. Why the loop cannot assemble what the ceiling requires

The H-expert and the loop were the same meta-agent, the same evidence class, the same
mutable surface, days apart. The difference is constitutional, and the gap decomposes
exactly:

| H-expert mechanism | The loop's encounter with it |
|---|---|
| R5/R6 exact strings, verbatim handover | **Confirmed** (seq-10 C2) — the loop's one persistent win matches the expert |
| R10 escalate-last with the retrieved reason code | Confirmed historically (seq-8 D2), carried |
| R4b per-candidate attribute search | **Found and killed**: seq-10 C4, counter confirmed once, cost falsifier fired, reverted. The expert pays this cost knowingly — its episodes run long — because the value exceeds it. The loop's cost discipline prunes on price without a value term |
| R4 write-out filter-then-rank comparison | Attacked three times as a *tool* (seq-10 C1, seq-12 C9 as instruction, C11) — externalizing to a tool what the expert makes the model write in its own words; the tool was used 1515 times and changed nothing ("asks for the gaps, receives them, and chooses anyway") |
| R4a "the figure that applies to THIS customer" | **Never formed** — despite seq-10's own diagnosis of the identical mode. The probe found it by watching a failure; the loop's per-round diagnosis holds the same transcripts and never converted the observation into this mutation |
| R2 additive-before-closure ordering | **Never formed** — same story: one preflight failure taught the expert; the batch evidence contains the same eligibility-destruction events |
| R1 request-list + ACTING_NOTE walk-the-list after every write | Half-tried as a *tool* (C8: tracked 578 times, reward unmoved). The expert's form — a completed-state note that ends "if anything on that list closes, cancels, removes or transfers away, do it LAST" — was never attempted; the closure's own unconsumed-targets table names the missing piece exactly ("whatever converts a tracked outstanding item into a performed action") |
| The ensemble itself: ten interacting rules + two point-of-use re-injections | **Constitutionally unbuildable**: D22 forbids interacting changes in a set; per-change falsifiers demand each component justify itself alone; cost falsifiers fire on components whose value arrives only in combination (C6-style verification works inside the expert's procedure and failed as a standalone); reverts-on-denial dismantle partial assemblies. The expert nets +15.2 *despite* −5.7 of drafting errors because it is evaluated as a whole; the loop nets 0 *because* it prunes every part that cannot stand alone |

Add the retention gap (§5.1) and the diagnosis is complete: **the loop's constitution
optimizes attribution, and attribution-optimal is assembly-hostile.** Every rule exists
for a measured reason — seq 4's unattributable paragraph, seq 6's interacting-change
ambiguity, seq 10's cost blowouts — and their joint effect is a loop that can only take
steps small enough to prove, toward a target that requires a staircase. Seq 12 is the
experiment that finally makes this measurable rather than arguable, because for the first
time both ends of the comparison exist: what the unconstrained agent builds (+15.2) and
what the constrained loop lands (0.0), on the same tasks, at adequate power.

### 8. What to change

Grouped per the review's charter: instrument, process/constitution, artifacts. Standing
recommendations already recorded (the closure's futility fix, stratum-aware attribution,
the craft notes; D36's deferred control arm) are adopted by reference, not re-derived.
Freeze-level items are user decisions for the D-ledger.

#### The instrument

1. **Gate the envelope on the measured A/A noise and on 80% power, not α-detectability.**
   Seq 12's gate passed an instrument whose known 80%-power shortfall was recorded the
   same day. New rule: the envelope computes power at the *measured headroom* AND at a
   declared plausible per-generation effect (~5–8 pp from two experiments' evidence);
   below 0.8 on the first or 0.5 on the second, the freeze changes trials/B/cadence
   before any episode. The A/A round's realized churn feeds a mid-experiment re-check.
2. **Trials are the lever: 3 → 9 on the compared rounds** (baseline pair and endpoint;
   80%-power detectable falls 14.6 → 8.4 pp), or equivalently raise compared-round
   episode mass ~3×. Interior rounds may stay at 3 — diagnosis doesn't need the power,
   the endpoint claim does.
3. **Full (or near-full) held-out cadence.** The sparse schedule saved ~$8 and reduced
   the secondary to a three-point trend. If cost binds, thin the *interior* batch
   diagnosis instead — never the pre-registered claim channel.
4. **Pre-register the stratum decomposition**: a headroom-stratum co-primary (it was
   +12.1 pp, p ≈ 0.06, invisible to the batch-wide test) and an **anchor-regression
   brake** — a live per-round check that fires when the passing strata fall while
   headroom rises, turning §2.3's cancellation from a post-hoc discovery into an
   in-experiment signal. Re-screen strata whenever the backend or model pair changes
   (seq 12's anchors weren't).
5. **Adopt the closure's futility fix** (two consecutive firings, or capacity from the
   ceiling) and reconcile the revert cap with knowledge mode (the cap binds while the
   primary is alive; after a decisive futility firing, reverts that recover a measured
   peak are exempt — C12 was right to exist).

#### The process — the constitutional re-decision

6. **Retention: the endpoint is the best measured harness, pre-registered.** Add to the
   freeze: after the final mutation slot, the loop executes one sanctioned
   *revert-to-best* transition — restore the tagged harness of the argmax batch round
   (ties → latest) — and the endpoint round runs on that. Every mechanism stays
   attributable (the reverts are first-class changes); the experiment stops paying for
   its last hypothesis with its best result. Under this rule seq 12's endpoint is H4 and
   the primary reads ≈ +8 pp instead of 0.0.
7. **Build-then-ablate: amend D22 to allow procedure-sets.** One slot may land a
   **named procedure** — several interacting rules plus their point-of-use
   reinforcements, composed as one mechanism with ONE set-level falsifiable prediction
   (the expert's shape) — followed by a pre-registered **ablation round** that removes
   components to attribute. Attribution moves from per-change-always to
   procedure-then-ablate; the record schema already carries `changes[]` and needs only a
   `procedure` grouping. This is the direct answer to §7: the current constitution
   cannot build a staircase; this lets it build one and then prove which stairs matter.
8. **Price cost against value, not against the round mean.** A cost falsifier alone
   never reverts a mechanism whose counter confirmed — it triggers a cost-reduction
   iteration (seq-10 C4 is the loop's one confirmed core-ceiling component, killed on
   price). Cost ceilings are set per-task against the task's own baseline (the closure's
   craft note) and traded against the reward at stake.
9. **Iterated drafting inside a slot.** The expert's method — watch it fail, re-aim,
   three times — is currently available only outside the loop. Raise the preflight
   budget for procedure slots (~30 local episodes on batch tasks under
   `allow_within_batch_verification`), with the existing rules (execution-verification,
   never provenance, never reward-anointed) intact.
10. **The next experiment is the constitutional A/B, and it is the "show it improves"
    experiment.** Freeze the re-constituted loop (items 6–9) against the same measured
    ceiling; D36's deferred non-diagnosing control arm is the falsification arm. Success
    is pre-registered as closing ≥50% of measured headroom, retained at the endpoint,
    visible on both lanes. If the re-constituted loop also nets ~0, the self-improvement
    claim fails honestly at adequate power against a proven-reachable target — which is
    a publishable answer either way.
11. **The H-expert stays quarantined from in-loop recall** (like held-out artifacts): it
    is the existence proof and the yardstick. A loop that reads it is distilling a
    human-process artifact, not self-improving; the loop must re-derive its mechanisms
    from batch evidence — §7's table shows the evidence is there. (User decision; the
    alternative — seeding the backlog from the expert — should be taken knowingly as a
    change of claim, not silently.)

#### The artifacts

12. **Narrow the surface doctrine where it is written** (`skills/sia/SKILL.md` mutation
    classes; `contract/protocol.md` step 4): "prefer a structural surface" holds only for
    mechanisms needing **state the model cannot hold**; for withholding demands both
    channels fail identically (C1/C4), and five consecutive instruction-shaped-demand
    denials belong in the ledger's standing lessons next to it.
13. **Promote the closure's craft notes into `contract/protocol.md` / record-craft**:
    graded-lane verification of hooks before any verdict; preflight where the mechanism
    demonstrably applies; cost against the task's own baseline; the level-falsifier ban
    (a falsifier names a delta, never a level).
14. **Fix the drifted prose**: protocol's cadence preamble and Close step 1 for
    `heldout_generations`; `summary.md`'s "carried (identity)" label; CLAUDE.md's
    conflated ledger row (§6.1); commit the batch-restricted headroom derivation as a
    machine artifact; standardize on one batch-curve statistic.
15. **Housekeeping**: reset `target-agent/` to `h0-baseline` post-close (working tree
    still carries H7); cite both seq-11 evidence locations when referencing the probe;
    consider a schema slot for futility declarations (currently prose — acceptable, but
    the check's firings are load-bearing results).

---

## § Held-out reveal analysis — QUARANTINED from later in-loop recall (D33)

*Everything below is off-limits to any future experiment's in-loop session.*

Measured generations {0, 4, 7}: 5, 8, 6.7 of 36 → 13.9%, **22.2%**, 18.5%. Endpoint
+1.7 tasks (+4.6 pp), inside the ±4.5 pp band; trend z = 1.113, p = 0.133 over three
points. The corroboration §2.3 references: **H4 = 22.2% vs H0 = 13.9% is z ≈ 1.6,
one-sided p ≈ 0.054** — the held-out lane's peak, at the same generation as the batch
lane's peak, on disjoint tasks, declining afterward exactly as the batch curve does.
Midpoint selection inflates both p-values somewhat; cross-lane agreement at one
generation is not something the null produces easily. Power context for §5.3: with three
measured points the endpoint-contrast SE is 5.2 pp (80% power needs +13 pp) and the trend
needs ~+5 pp/step monotone — the sparse cadence made the secondary unpowered by
construction. Churn correction for §6.6: the two genuinely measured transitions moved 13
and 10 task-cells of 36 (net +3, −1.3); ever-solved rose 8 → 15/36 while fully-solved
went 2 → 4 → 3 — breadth without retention, the same signature seq 10 recorded, and the
held-out echo of §5.1's retention finding.

---

## 9. Sources

Seq 12: `improvement_records/gen_000_to_001 … gen_006_to_007.yaml`,
`improvement_backlog.md`, `batch_curve.json` (incl. `noise_floor`, `strata`),
`endpoint_test.json`, `summary.md`, `GUARDRAIL_WALK.md`, `gates/` (power envelope, seam +
suppression canaries, A.0a), `generation_000/subagent_probe/VERDICT.md`, preflight
evidence under `generation_00*/`, `split_manifest.yaml`, `benchmark_lock.yaml`,
`experiment.yaml`, `held_out/` (reveal derivatives; quarantined section only), PRs
#36–#41, tags `exp12-g002…g007`. Seq 11: `results/experiment_011_ceiling-probe/`
(README + both headroom JSONs) **and** `benchmark/probes/2026-08-18-phase0-ceiling-probe/`
(h-expert source: `SYSTEM.md`, `expert-discipline.ts`, `ARM_COMMITS.txt`; arm evidence).
Seq 10: closure README (`§ Batch-derived findings`), records, backlog, GUARDRAIL_WALK.
Process: `contract/protocol.md`, `contract/improvement_record.schema.yaml`,
`benchmark/tau_adapter/` (`lock.py`, `reveal.py`, `records.py`, `run.py`),
`benchmark/scripts/` (`endpoint_test.py`, `power_envelope.py`, `gold_diff.py`,
`mech_counters.py`, `headroom.py`), `skills/sia/`, `SIA_EVALUATION_PLAN.md` (D35–D36),
`CLAUDE.md`. Independent computations: null simulations of the A/A pair, primary power
curves, stratum decompositions, cadence power — scratchpad `seq12_stats.py`, inputs cited
inline.
