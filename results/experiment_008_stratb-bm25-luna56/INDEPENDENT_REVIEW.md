# Experiment 008_stratb-bm25-luna56 — independent review

Post-reveal review, written 2026-08-17 from the committed artifacts and git history only
(`improvement_records/`, `improvement_backlog.md`, `batch_curve.json`, `held_out/`, `gates/`,
`GUARDRAIL_WALK.md`, the six mutation PRs, the probes, and the process artifacts:
`contract/protocol.md`, `contract/improvement_record.schema.yaml`, `skills/sia/`,
`SIA_EVALUATION_PLAN.md`, `target-agent/` at every tag). Everything cited was re-read at
source; where this review disagrees with the closure README or the driver's summary, the
disagreement is stated with its evidence. Structure follows the seq-6 review; §7 answers the
standing question — why, one groundwork later, the loop still did not use the growth surfaces
— and §8 is what to change.

Three questions organize it: **what happened** (§1–§6), **why only hooks** (§7), **what to
change in the loop** (§8).

---

## 1. Verdict

The frozen instruments are null and were read honestly: primary (paired batch endpoint,
H6 vs H0) Σ = +1.333, exact one-sided p = 0.25; secondary (held-out trend, fourth exposure,
no capability claim available) z = 0.60, p = 0.274. The pre-registered
`primary_flat_secondary_flat` cell was applied verbatim, and its language — "the meta-agent
is the problem" — is in the closure unedited. That discipline is itself a result: seq 8 is
the first experiment here whose reading key covered what was observed, whose §29 walk has
**none waived**, and whose machinery (cadence gates, record validation, backlog stamp gate,
fingerprints) all demonstrably fired.

Three findings of this review qualify the verdict without overturning it:

1. **The batch was nearly saturated, and the null is partly arithmetic.** Of the batch's 24
   cells per round, 15 belong to the anchor and marginal strata. At `batch_01` the harness
   passed 10 of those 15; at `batch_05` it passed **15 of 15** — every cell the invariants
   permit reaching — and the endpoint held 14 of 15, the one give-back inside the measured
   2-cell noise floor. The 9 headroom cells were proven domain-walled (§2.2). A primary that
   needs five moving tasks, applied to a composition with two anchors that cannot move and
   three headroom tasks that turned out to be unreachable, had a power ceiling that was thin
   from the freeze. This is a post-hoc gloss, clearly labeled as such — the frozen cell
   stands — but "the meta-agent is the problem" and "the reachable range was harvested and
   was too small to be significant" are both consistent with this data, and §8 proposes the
   next freeze be designed to tell them apart.
2. **The loop's surface use did move — one rung.** Seq 6 put 17 of 18 slots into one
   `SYSTEM.md` paragraph; seq 8 put one slot into instructions and everything else into
   extension hooks, the structural surface the seq-6 review demanded. What did not move is
   the rung above: extension tools, sub-agents, and skills — the surfaces D24 was built to
   unlock — ended the experiment with `pi_local_calls = 0` across all 168 platform episodes.
   §7 shows this was mostly evidence-based restraint recorded in the open, amplified by a
   process that never forces an untried surface and one stale reference document.
3. **The honest summary survives review**: the loop demonstrably changed the harness's
   behaviour (three mechanisms confirmed on counters) and did not demonstrably improve its
   capability.

## 2. What happened, verified

### 2.1 The two instruments

**Primary.** Exact one-sided sign-flip on per-task endpoint rate deltas (`batch_07` under H6
vs `batch_01` under H0): Σ = +1.333 from exactly two non-zero deltas (`task_057` +1.000,
`task_014` +0.333, six zeros), p = 2⁻² = 0.25 — verified against `batch_curve.json`. The
test enumerates signs over non-zero deltas only, so two movers cap p at 1/4 and **five were
needed for α = 0.05**. On the pre-knowledge claim the closure slightly overshoots (§6.1):
what was recorded before the endpoint was a three-mover best case of p = 1/8
(`improvement_backlog.md`, batch_05 re-ranking: "the primary cannot reach α = 0.05 without
task_026 and task_096 moving") and the five-mover requirement in `gen_004_to_005.yaml`; the
actual two-mover configuration materialized only when `task_072` fell back at `batch_07`.
The limit was genuinely pre-known; the exact number was not.

**Secondary.** Held-out trend z = 0.6008, p = 0.2740 (`held_out/trend_test.json`); curve
16.7 → 16.7 → 22.6 → 20.2 → 16.7 → 19.0 → 20.2 % (expected-passed 4.7, 4.7, 6.3, 5.7, 4.7,
5.3, 5.7 of 28); endpoint +1 task, inside the ±5 pp band. Fragility
(`held_out/trend_fragility.json`): `load_bearing_tasks: []`; the one endpoint-only first
pass (`task_092`) zeroed gives z = 0.38, p = 0.352. Fourth exposure of this 28-task set
(declared in `benchmark/partition_reuse.yaml`), so under D25 rule 2 the lane carried no
capability claim regardless of outcome — which means **the experiment's only claim channel
was the underpowered primary** (§5.7).

**Batch curve.** 10/24 → 13 → 11 → 15 → 16 → 14 → 14 (41.7 → 54.2 → 45.8 → 62.5 → 66.7 →
58.3 → 58.3 %). Peak +25 pp over baseline, endpoint +16.7 pp — none of it evidentiary under
the endpoint-only primary.

### 2.2 The saturation reading the instruments miss

Per-stratum, from `batch_curve.json`:

| stratum | cells/round | b01 | b05 (peak) | b07 (endpoint) |
|---|---|---|---|---|
| anchors (task_006, task_032) | 6 | 6/6 | 6/6 | 6/6 — 42/42 over the experiment |
| marginals (task_014, task_057, task_076) | 9 | 4/9 | **9/9** | 8/9 |
| headroom (task_026, task_072, task_096) | 9 | 0/9 | 1/9 | 0/9 |

At `batch_05` the harness passed every anchor and marginal cell. The endpoint's give-back
(`task_014` 3/3 → 2/3) is one cell — inside the noise floor of two cells measured one round
later on an identical harness. Meanwhile five rounds of layer-peeling established that all
three headroom tasks fail on domain knowledge the invariants forbid encoding: `task_026`
ends calling the gold tool with three of four values exact and one off by one (1499 vs 1500
— a rounding convention); `task_096` computes wrong APY-derived amounts (a governing rate);
`task_072` applies the wrong fee rule with internally consistent arithmetic. Two plausible
mutations were excluded on *measurement*, not argument: an extension-tool calculator would
compute the same wrong number, and surfacing the `credit_type` enum would surface what the
unlock response already enumerates.

So the descriptive (not pre-registered) summary of the batch: **the loop harvested
everything the invariants left on the table, and the table's reachable part was three
tasks.** The stratification bought exactly this legibility — it is also what capped the
primary (§5.5).

### 2.3 Noise, measured twice

- **Batch lane (the closure's finding).** gen-005 reverted a change that had never executed,
  so H5 ≡ H4 behaviourally and `batch_06` re-measured the same harness: it moved 2 cells,
  8.3 pp (`task_057` 3/3 → 2/3, `task_072` 1/3 → 0/3). First behavioural-identity round in
  the project.
- **Held-out lane (this review's addition — the closure never surfaces it).** The same
  identity pair exists in the held-out data: H4 and H5, behaviourally identical, differ by 2
  passed episodes (14 → 16 of 84) and by 4 transfers (21 → 25,
  `held_out/process_metrics_by_generation.csv`). More broadly,
  `held_out/transitions.csv` shows 3–5 task-cell gains *and* 3–5 regressions per transition
  against net movements of −2…+3, and ever-solved grew 7 → 15/28 while point-in-time stayed
  ~5. The churn corroborates the noise floor on the lane that carries the trend test, and
  `summary.md` does not remark on it (§6.5).

The strata labels themselves show the same physics: `task_057` entered the freeze measured
`marginal` and opened `batch_01` at 0/3; `task_076` entered `marginal` at 3/3. The
pre-freeze screen's per-task rates are not restated in the results tree, so the reader
cannot check screen-vs-run drift (§6.7) — but it is an early sighting of the variance the
identity round later quantified.

### 2.4 Process metrics as prediction channels (D25) — they worked

Batch-lane counters (`batch_process_metrics_by_round.csv`): transfers 9, 9, 6, 10, 9, 10,
11; kb_search_calls 117 → 128 range-bound; writes_matched flat at 27 (26 once);
action_match_pct 42.2 → 48.3 at peak. These carried the experiment's cleanest attributions:
D2's transfer-reason queries 0/3 → 3/3 on the task where the mechanism could fire, H1's
duplicate-write counter at zero in `batch_07` with the falsifier held at 9/24. The
confirmed/denied verdicts in every record rest on these counters, not on pass/fail cells —
exactly what D25 intended.

### 2.5 Machinery and spend

756 episodes: 168 platform batch (7 × 24) + 588 local held-out (7 × 84), plus probes and
preflights. One freeze fingerprint (`sha256:fea4ae1c…`) across all 15 runs; `arm_sha_ok`
168/168. A.0a: 379 adapter tests + mock smoke before the first episode. Seam: zero
disconnects, timeouts, stall warnings on the batch lane; one episode (`task_096` t1,
`batch_02`) carried 2 `sandbox_seam_unclassified` + 2 `sandbox_tool_errors` and completed
with evidence intact; 89 and 65 benign `stream_reattaches` in rounds 1–2. The platform
seam-canary gate PASSed with one disclosed infra `ValueError` in its own trials
(`gates/seam_canary.json` — unnarrated in the closure, §6.3). `pi_local_calls` = 0 on
168/168 platform episodes, noted in every record's round-health block with the same correct
reason: every landed change is a hook, and hooks are not registered tools. Spend: $2.61
platform + $12.03 local + ≈$2.4 probes/preflights ≈ **$17**. Autonomy: `require_human_approval`
frozen `false` (D28); every record's approval block reads "orchestrator — autonomous per D28
(user-delegated; D23's envelope re-registered)". §29: seventeen HELD, two N/A by design, one
HELD by frozen delegation, none waived.

## 3. The six generations, compressed

| gen | change(s) | surface | prediction → outcome | disposition |
|---|---|---|---|---|
| 001 | **C1** list KB-named tools after `KB_search`; **C2** "call `give_discoverable_user_tool` with the tool name alone, and give the user that exact tool name" | `extension-hook` (`tool_result`); `instructions` | C1 DENIED — counters 0/3 → 0/3, 2/3 → 2/3 with the hook verified firing in vivo; C2 CONFIRMED — `task_057` 0/3 → 3/3, and clause-resolved: clause 1's falsifier fired, the task passed anyway, **clause 2 is the mechanism** (first clause-level attribution in the project) | C1 reverted at gen-002; C2 kept |
| 002 | **D1** revert C1; **D2** `context` hook: factual note when a handoff was requested and no transfer-reason lookup has been issued | `revert`; `extension-hook` | D1: `task_057` held 3/3 → attribution settled on C2. D2: prediction DENIED on `task_014` at `batch_03`, mechanism CONFIRMED on `task_032` (queries 0/3 → 3/3); transfer rate fell 9/24 → 6/24 with no suppression requested | both kept; T3 wrongly retired |
| 003 | **E1** `tool_result` hook: "Identity verification is now on record for this conversation" | `extension-hook` | CONFIRMED on both counters (zero duplicate `log_verification`; `task_076` back to 3/3); `task_014` 0/3 → 3/3 → D2 confirmed a round late; T3 un-retired | kept |
| 004 | **F1** `context` hook: list KB-named tools not yet unlocked (D2's missing-state framing aimed at C1's target) | `extension-hook` | **MEASURED INERT** — keyed on message role `tool` where this host spells it `toolResult`; zero injections; H4 ≡ H3. Its preflight (3/3 vs 0/12) was chance | reverted at gen-005 |
| 005 | **G1** revert F1; repair deliberately not landed | `revert` | explicitly predicted **no change**; `batch_06` became the noise measurement: 2 cells, 8.3 pp, on an identical harness | revert stands |
| 006 | **H1** amend E1's note: "…logging it again would write a duplicate verification record" | `extension-hook` | CONFIRMED at the endpoint: zero duplicate writes; falsifier held at 9/24 zero-call episodes | kept |

End state (H6 vs h0-baseline): +3 lines of `SYSTEM.md`, two live hooks
(`transfer-reason-lookup.ts`, `verification-logged.ts`), 175 insertions total.
`agents/agent.yaml`'s `tools: []`, `skills: []`, `subagents: []` — **all three registries
still empty**; the D27 `noop-hook.ts` template still present, still undeclared.

The F1 anatomy deserves one paragraph because §8 builds on it. The harvest branch reads
`if (message?.role === "tool" && …)`; on this host the role is `toolResult` — a fact sitting
in this experiment's own g=1 probe evidence
(`generation_001/context_probe/hook_firings.json`, where every tool-result row says
`"toolResult"`). The same file's other branch reads `block?.input ?? block?.arguments`
correctly; only the role literal was wrong. Nothing in the process consults probe evidence
at mutation time (§5.1), and the preflight could not catch it because a preflight verifies
that a change *runs*, not that it *works* — and this change failing to run produced
`outstanding.length === 0` and a silent no-op, indistinguishable from "nothing to report".

## 4. Highs

1. **The noise floor** — the project's first behavioural-identity round, produced
   deliberately (gen-005 chose the revert knowing `batch_06` would measure noise), plus this
   review's corroborating held-out identity pair (§2.3). Every attribution in every prior
   experiment gets re-read against 2 cells / 8.3 pp.
2. **The framing taxonomy.** Four injection shapes, one shared surface, each measured: bare
   list — nothing; missing-state — behaviour change *plus unrequested suppression*
   (transfers 9/24 → 6/24); completed-state — safe and inert outside its target;
   consequence-stating — confirmed with falsifier held. The sharpened standing lesson: not
   only escape clauses — *any injected statement about a missing precondition can be read as
   a bar to acting*. This is the experiment's most transferable result.
3. **Transfer discrimination moved** — first time in four experiments and seven prior
   attempts, and the conditional is clean: every endpoint trial that issued the prescribed
   lookup chose the gold reason; the one that did not, did not. And the honesty held: only
   one side moved (over-escalation did not improve).
4. **The revert rule with a measured counterfactual.** Denied prediction ≠ revert trigger;
   denied mechanism = revert trigger. C1 (mechanism moved nothing) reverted; D2 (prediction
   denied, mechanism confirmed on its counter) kept — and produced the experiment's clearest
   win two rounds later.
5. **The stratification paid for itself twice**: anchors 42/42 made every movement
   attributable rather than ambient, and the passing-vs-failing trial pair of `task_076`
   under one harness diagnosed the duplicate-write mechanism — a finding a known-fail batch
   cannot produce by construction.
6. **Surface exhaustion proven, not asserted** — five rounds of layer-peeling down to an
   off-by-one on a rounding convention, with the two obvious counter-mutations excluded on
   measurement (§2.2).
7. **The machinery worked under full autonomy.** The D26 backlog-stamp gate refused a record
   once and was satisfied by the re-ranking it demanded (`GUARDRAIL_WALK.md`); the cadence
   gates, record validation, conversation-id cross-checks, and fingerprint checks all held;
   the reading key was applied verbatim with no off-key adjudication (seq 6 needed one);
   none of §29 was waived. The loop ran six generations with zero human interventions and
   the record is checkable end to end.
8. **`surfaces_considered` discipline (D26) was followed at every target open** — the
   surface decision is in the record, per target, verbatim (§7). Whatever §7 concludes, the
   evidence for it exists *because* the groundwork demanded it be written down.
9. **Mid-run epistemic repairs became standing rules**: the injected-text-verification rule
   (from F1's chance preflight) and the H1 preflight applying it ("a `tool_result` patch IS
   persisted to the Pi session… so this change can be verified where F1 could not").

## 5. Lows

1. **A generation spent on a change that never ran** (F1), keyed on a host fact the
   experiment's own probe had recorded — and nothing in the process consults probe evidence
   at mutation time. The slot cost is real: one of six generations, plus the revert slot at
   gen-005 (partially recovered as the noise measurement).
2. **The preflight false positive** — 3/3 against a 0/12 baseline for a never-executing
   change. The standing rule now exists, but it was bought with a generation.
3. **A target retired on one round's evidence** (T3, gen-003) and un-retired one round
   later. The retirement-evidence bar was never stated.
4. **The gen-001 record's signal 1 is wrong** and stays wrong by design (schema refuses
   rewrites; the erratum lives in the backlog): the "retrieved and never used" population
   was `task_026` alone (3/24), not 6/24 — half of C1's justification was misattributed.
   Generalized in the backlog: *an aggregated miss list is not a mechanism.*
5. **The primary's power ceiling was structural and discoverable at freeze.** Endpoint-only
   sign-flip; two anchors excluded from movement by construction (their being at ceiling is
   what makes them anchors); needing 5 of the remaining 6 to move; three of those six
   headroom tasks whose *reachability* was never screened (stratification measured level,
   not reachability). The instrument could essentially only reach significance if the
   domain-wall tasks moved — the very tasks the invariants wall off.
6. **D24's suppressing path was never exercised** — the groundwork seq 8 was built on ran
   its pump path only. Platform-lane suppression under a non-empty registry enters the next
   experiment as an assumption, not a measurement.
7. **The experiment could not have won.** Combine §5.5 with the held-out lane's fourth
   exposure (no capability claim available): before the first episode ran, no outcome of
   seq 8 could have produced a defensible positive capability statement. That is not
   hindsight — both facts were in the freeze. The design bought instrument repairs and
   surface legibility at the price of a claim channel, and nothing in the freeze artifacts
   states that trade explicitly.
8. **Sub-agents were never probed** — not used is defensible (§7.4); never measured, in an
   experiment that ran fourteen probe/preflight episodes, is a gap: the surface's
   availability verdict is still "by construction" three experiments after it was first
   cited.

## 6. Errata and narration gaps (closure cross-check)

Everything numerical cross-checks clean: the batch table = `batch_curve.json`; held-out
curve = CSVs = the records' `held_out_result` stamps; §29 verdicts consistent; PRs #17–#22 =
git; the task_026 message-collapse figures match `gen_002_to_003.yaml`; anchors 21/21 each;
the erratum is consistent between record and backlog. The gaps:

1. **README overshoot on the pre-known power limit** ("only 2 of 8… computed and recorded in
   the backlog at gen-005"): the backlog pre-registered a *three*-mover best case (p = 1/8)
   plus the five-mover requirement; the two-mover configuration (p = 1/4) appeared only at
   `batch_07`. Genuinely pre-known limit, imprecise citation.
2. **`gen_004_to_005.yaml` "1/1 preflights this experiment has run on an injection change"**
   undercounts: D2 and E1 preflights had run on injection changes (defensible only under a
   narrow reading of "unverifiable-in-session context injections").
3. **The seam canary's own infra `ValueError`** (`gates/seam_canary.json`,
   `infra_failures: {ValueError: 1}`, trial-0 incomplete) is disclosed in the JSON and
   narrated nowhere. No claim it contradicts — the "zero incidents" statements scope to the
   168 batch episodes — but the closure's completeness standard would have named it.
4. **The `gen_000_to_001` backlog transition stamp sits at file end**, out of chronological
   position (the other five are in order).
5. **Held-out churn is unremarked in `summary.md`** — 3–5 gains and 3–5 regressions per
   transition against nets of −2…+3; ever-solved 7 → 15/28. It is the held-out half of the
   noise-floor finding and only the batch half made the closure.
6. **The D26 stamp-gate refusal** — machinery working, recorded in `GUARDRAIL_WALK.md`,
   absent from the README's machinery section.
7. **Strata provenance**: the pre-freeze H0 screen rates that assigned `anchor` / `marginal`
   / `headroom` are not restated in the results tree; `task_057` (marginal) opening at 0/3
   and `task_076` (marginal) at 3/3 cannot be checked against their screen values.

## 7. Why the loop stopped at hooks

The question, one experiment on: seq 6's review answered "why were the growth surfaces never
used" with *the seam starved the loop, and every process gradient pointed toward prose* —
and the D24–D27 groundwork repaired both layers. Seq 8 then landed one instructions edit,
four hooks, two reverts, one hook amendment: `pi_local_calls` = 0, all three `agent.yaml`
registries still empty. Why?

### 7.1 First, the ladder did move — one rung

Seq 6: 17 of 18 slots into one `SYSTEM.md` paragraph, zero structural changes. Seq 8: one
instructions change, everything else on the structural surface seq 6's review said was being
argued away (`before_agent_start`/`context`/`tool_result` hooks). The D27 hook template was
used exactly as designed ("the first structural mutation is a one-line reviewable diff");
the concentration flag's target — prose — never accumulated (one instructions mutation all
experiment; the backlog notes the set "nonetheless leads with a structural change" against
the 17-of-18 prior). **The groundwork worked for the surface it scaffolded.** What follows
is about the rung above it.

### 7.2 Skills were never on the menu — correct non-use, now measured

Probe P2 (`benchmark/probes/2026-08-16-surface-probes/`) measured a declared skill reaching
*nothing* on this seam's local lane — prompt byte-identical, zero session trace, with and
without `read`. Skill-shaped judgment therefore ships as hook injection, which is what the
backlog header says in so many words. One of the four "growth surfaces" in the standing
question was never really there. (Seq 6's review had flagged this verdict as inherited,
not measured — seq 8 inherited the *measurement*. Correct non-use, properly grounded.)

### 7.3 Extension tools: considered at every target, rejected in the open — mostly soundly

The D26 `surfaces_considered` discipline produced exactly the evidence this question needs.
Verbatim, from `improvement_backlog.md`:

- **T1** (retrieved-but-unused tool): "`extension-tool` — legal under D24 but wrong shape:
  **the model would have to choose to call it, which is the very step that is failing.**"
- **T3** (transfer discrimination): "`extension-tool` — a checkable 'may I close this out'
  gate, legal under D24, **unexplored**." Named live; hook chosen because the diagnosed
  mechanism was a missing *fact in front of the model*, not a missing capability.
- **T4** (wrong computed values) — the one target that named extension-tool as its
  **primary home** ("the honest home for arithmetic, live under D24 and unexplored; the
  model calls a deterministic calculator instead of computing in prose") — then killed by
  measurement at `batch_02`: the arithmetic is internally consistent and applies the wrong
  fee *rule*; "an extension-tool calculator, the obvious D24 surface, would compute the same
  wrong number"; and reaching the rule means encoding domain knowledge the invariants
  forbid.
- **T6** (duplicate write): "`extension-tool` — the model would have to choose to call it,
  which is the step that fails."

Two things are simultaneously true. (a) **The recorded reasoning is sound per target.**
Every failure the batches diagnosed was of the shape "the model does not notice / act on /
track what it already has" — and a tool the model must volunteer to call is structurally the
wrong fix for a failure of volunteering, while deterministic injection of what the model
reads is the right one. The one genuinely tool-shaped target was refuted by measurement, not
skipped. (b) **The reasoning is also self-reinforcing** (§7.6), and nothing in the process
ever pushes against it.

### 7.4 Sub-agents: never probed, plausibly empty of use-case

Rejected once on the merits ("no stable contract; the job is one deterministic extraction")
and never revisited. At this task scale — single-episode, ~16-turn dialogues, frozen model
pair binding the child — no diagnosed mechanism ever suggested a bounded delegable job. The
inference is reasonable and remains an inference: no sub-agent episode has run in this
project, probe or otherwise (§5.8).

### 7.5 The gradient the groundwork rebuilt one level up

Seq 6's §7.4 catalogued the process gradients that made prose the default. Each was
repaired — and each repair regenerated the same gradient with hooks as the new floor:

| gradient | seq-6 state | post-groundwork state |
|---|---|---|
| template | no scaffold for any structural surface | **D27 shipped a hook template only** — no zero-state for a tool, a sub-agent, or a skill |
| measurement | hooks unprobed | hooks measured on the real domain and lane (P1, g=0/g=1 probes); tools measured on **mock only** (P6); suppression's platform engagement explicitly deferred; sub-agents never probed. Under a 6-slot budget the best-instrumented surface wins every tie |
| forcing function | concentration flag didn't exist | **D26's flag is `instructions`-specific** (`protocol.md`: "After ≥3 prior prompt mutations… at least one non-`instructions` change"). One instructions mutation all experiment → never fired; six hook changes create no obligation. The ladder stops one rung short of where D24 aimed |
| probe trigger | none | step 4b fires "when a target's mechanism names a surface this experiment has not exercised" — but mechanisms are *chosen* first, and chosen mechanisms kept being hook-shaped, so 4b never dispatched a tool probe |
| prediction shape | prose maps 1:1 to a counter | a hook's injected text maps 1:1 to a counter; a tool's effect is conditional on adoption, so its prediction is weaker and its slot riskier — the exact asymmetry that used to favour prose over hooks now favours hooks over tools |
| reference doc | recipe-growth documented dead surfaces as first-class | **`recipe-growth.md` is stale the other way**: never updated after D24. Its surface table still reads "in THIS repo's seam every extension-tool call costs a τ step and an error, so prefer a no-tool-call hook" and sub-agent "the surface is unavailable" — contradicting `SKILL.md`, the protocol, `constraints.md` divergence 6, and `agent.yaml`'s own comments. The driver demonstrably knew better (the backlog corrects it explicitly), so this did not cause ignorance — but the document the sia skill mandates loading *before landing any structural change* argued against the unlocked surfaces at every consultation |

### 7.6 The self-sealing diagnosis shape

The deeper structural reason, and the one §8 most needs to answer: **the evidence pipeline
only produces hook-shaped findings.** Diagnosis is transcript reading; transcripts surface
wording, ordering, and omission failures — always statable as "the model didn't notice X",
always fixable by injecting X. "The harness lacks a capability" is never a first-class
signal from reading a transcript, because a transcript shows what happened, not what a
missing tool would have made possible. The recurring objection — *the model would have to
choose to call it, which is the very step that is failing* — is locally sound every time it
was written, and globally it guarantees the tool surface is never reached, because the only
evidence that could justify a tool (the model *adopting* one) can only exist after one is
landed. A first tool change is an investment whose first-round return is adoption, not
reward — and the record schema prices every slot in next-batch falsifiable predictions,
which under a naive reading makes "landed a tool, reward unchanged" a denied prediction and
a revert candidate. Seq 8 had to invent the denied-prediction-vs-denied-mechanism rule for
D2; the same rule is what a first tool generation would need, stated in advance (§8.10).

### 7.7 Verdict

Non-use of tools and sub-agents in seq 8 was **predominantly evidence-based restraint,
recorded in the open at every target** — the diagnosed mechanisms really were hook-shaped,
and the one tool-shaped target really was refuted by measurement. It was **amplified by an
incentive structure the groundwork rebuilt one level up** — template, measurement status,
forcing function, probe trigger, and prediction economics all favour hooks exactly as they
favoured prose in seq 6 — and **abetted by one genuine artifact defect** (stale
`recipe-growth.md`) and one structural blind spot (transcript-only diagnosis cannot emit
"missing capability" as a signal). The loop will climb exactly one rung per groundwork
unless the process is changed to force exploration of the rung above (§8); after two
experiments this generalizes to a law worth writing down: **each repaired gradient
re-forms at the cheapest newly-legal surface.**

## 8. What to change before the next experiment

Grouped by artifact; each item cites its motivating fact. Items 1–4 are freeze-level (user
decision, D-ledger); the rest are artifact changes landable now. Existing decisions are
built on, not re-litigated (D22 composite sets, D23/D28 autonomy, D24 seam, D25 instrument
rules, D26 schema, D27 zero-state).

### Seam / freeze

1. **Exercise D24's suppressing path before relying on it again.** Add to the freeze gates a
   platform-lane canary with a registered probe tool: one episode, expected
   `pi_local_calls ≥ 1`, tool call absent from τ's trajectory, logged in `raw_data`.
   Converts "suppression engages on the platform lane" from assumption (P6 was mock, local;
   P7 deferred it) to measurement. One episode, ~$0.02.
2. **Take the fresh held-out draw.** D25 rule 2 already mandates it for any capability
   claim; seq 8 knowingly ran without one. The next freeze should either draw fresh (pool
   permitting at T=28) or state in the freeze that the experiment is again
   batch-primary-only — §5.7's trade made explicit at freeze time, not discovered at
   closure.
3. **Screen headroom strata for *reachability*, not just level.** Stratification measured
   pass rates; it never asked whether the failing step is harness-reachable. Add to the
   pre-freeze screen one diagnosis pass over the H0 trajectories of every headroom
   candidate, classifying the terminal failure as harness-reachable vs domain-walled
   (seq 8's wall taxonomy — rounding conventions, governing rates, gold-label semantics —
   is the rubric). Admit walled tasks, if at all, as declared wall-monitors outside the
   primary.
4. **Pre-compute the primary's power envelope at freeze.** With the composition fixed, the
   endpoint test's requirements are arithmetic: state at freeze how many movers α = 0.05
   needs, which strata can supply them, and what the realistic ceiling is. Seq 8's
   five-of-six-with-three-walled envelope was computable before the first episode. If the
   envelope cannot reach α under plausible success, fix the composition or the test before
   freezing, not the narration after.

### The instrument

5. **Repair the primary's shape.** Three options, freeze-decidable: (a) keep the endpoint
   pairing but raise trials on the two compared rounds (power scales with trials, and only
   `batch_01` and the endpoint need it); (b) pre-register a batch trend statistic over all
   rounds (the held-out trend's mirror) as co-primary — seq 8's peak-and-hold shape carried
   real information the endpoint test discards by design; (c) enlarge the marginal stratum
   at the expense of walled headroom (per item 3), since marginals are where movement is
   both possible and resolvable at 3 trials.
6. **Design the behavioural-identity round in.** Seq 8 got its noise floor by accident of
   F1's bug. Pre-register one A/A round per experiment (an identity generation whose batch
   round measures noise on purpose). 24 episodes ≈ $0.40 — the cheapest instrument this
   project has ever bought; it re-read every prior attribution.
7. **Narrate churn at reveal.** `transitions.csv` already computes it; `summary.md` should
   report per-transition gains/regressions, ever-solved vs point-in-time, and the held-out
   identity-pair delta when one exists (§2.3's H4/H5 pair went unmentioned).
8. **Commit the pre-freeze screen rates.** The strata assignments are load-bearing
   (anchors define the regression channel; the primary's power depends on the composition)
   and currently uncheckable (§6.7). One small YAML in the results tree.

### Protocol and record schema

9. **Extend the concentration ladder one rung — make the positive obligation
   surface-general.** Replace "≥3 prior *prompt* mutations → one non-`instructions` change"
   with: after ≥3 mutations on any single surface class, the next set includes one change on
   a *never-exercised* surface, or a committed step-4b probe naming the fact that blocks
   each remaining alternative ("a paragraph alone does not discharge the flag" already
   covers the ritualization risk). Under this rule, seq 8's gen-004 would have owed either a
   tool/sub-agent change or a measured probe of one — either of which beats what the slot
   actually bought.
10. **Adoption-first predictions for first-use surfaces.** For the first change ever landed
    on a surface, the record's falsifiable prediction targets *adoption and correct
    invocation* (`pi_local_calls ≥ k`; well-formed arguments; latency inside τ's budget) —
    reward movement becomes the *next* round's prediction. This is the
    denied-prediction-vs-denied-mechanism rule stated in advance, and it dissolves §7.6's
    trap: "the model would have to choose to call it" stops being a reason never to land the
    tool and becomes the thing the first round measures. Encode in
    `improvement_record.schema.yaml` (an `adoption_stage: true` flag on a change) and in
    protocol step 4.
11. **Consult probe facts mechanically at mutation time.** Minimum: a required record/PR
    field for extension changes — "quote the probe line establishing each host fact this
    code keys on (message roles, block shapes, firing timing)". Better: a repo lint that
    checks role/field literals in `target-agent/extensions/*.ts` against the measured
    vocabulary in the committed probe evidence. F1 died on `"tool"` vs `"toolResult"` with
    the truth sitting in `hook_firings.json`; this is the cheapest class of failure to
    eliminate entirely.
12. **Promote the mid-run rules into `contract/protocol.md`**: (a) a preflight verifies a
    change *runs*, not that it *works* — injected text must be verified in a fetched
    conversation before any behavioural number is read; (b) the
    denied-prediction-vs-denied-mechanism revert rule; (c) give preflights the protocol slot
    they already occupy in practice (four ran in seq 8 under a lock flag the protocol never
    mentions). And reconcile the protocol's human-gate language with frozen
    `require_human_approval: false` — the file promises it gets fixed where it disagrees
    with reality.
13. **Set an evidence bar for retirements**: a target retirement cites witnesses from ≥2
    rounds or a mechanism-level impossibility; otherwise it is `parked`, not `retired`. T3's
    retire/un-retire cost nothing this time only because gen-004's slot was already lost.
14. **Unify the two surface vocabularies** (`owning_layer` prose enum vs
    `changes[].surface` enum) — one drift site, and §7 is the proof that surface naming is
    load-bearing here.

### The sia skill

15. **Update `references/recipe-growth.md` to post-D24 truth.** The mapping table's
    extension-tool row ("every extension-tool call costs a τ step and an error, so prefer a
    no-tool-call hook"), the sub-agent row ("the surface is unavailable"), and trap 4's
    framing ("rules two surfaces out") are all pre-D24 verdicts that survived two post-D24
    edits of the same file. This is the mandated pre-structural-change reference actively
    arguing against the surfaces the seam now supports. Highest-leverage single edit in this
    list, and the clearest lesson for the ecosystem: **when a seam decision re-opens a
    surface, every document that closed it is part of the decision's blast radius.**
16. **Make the recall digest carry the project-scope surface ledger.** One standing line per
    surface: exercised-in-a-graded-round (yes/no), measurement status (real-domain / mock /
    never), current blocker if any. Seq 8's records each correctly noted
    `pi_local_calls = 0` per round; nothing aggregated "tools: still never exercised, three
    experiments running" into the digest where the next generation's surface decision is
    made.
17. **Add adoption-first prediction guidance to `record-craft.md`** (the skill-side half of
    item 10), including the worked shape: first-round falsifier = adoption counters;
    second-round falsifier = the behavioural counter the tool exists to move.

### Target-agent scaffold

18. **Complete the growth zero-state to all-surface parity.** D27 proved the template
    mechanism works — the first hook mutation was, as designed, a small reviewable diff, and
    hooks got used. Ship the same affordance for the remaining surfaces: a
    committed-undeclared no-op extension tool (`registerTool` + TypeBox schema, its
    `agent.yaml tools:` line present-but-commented, header documenting the suppression-path
    interaction) and a minimal sub-agent YAML (`from: agent`, no `ai:`, header documenting
    the delegation contract and frozen-model binding). The rec-1 canary probe tool can be
    exactly this template, exercised. H0's runtime behaviour stays untouched — the zero
    state changes the mutation gradient, which §7.5 shows is what actually governs surface
    choice.

### Meta-agent discipline

19. **Read "the meta-agent is the problem" at the right resolution.** Seq 8's evidence
    localizes it: two concrete meta-agent defects (probe-fact non-consultation → F1;
    single-round retirement → T3), one instrument that could not say yes (§5.5, §5.7), and a
    batch whose reachable range the loop *did* harvest (§2.2). The next freeze's reading key
    should be built to distinguish "the loop cannot find mechanisms" from "the objective's
    harness-reachable headroom is exhausted" — they demand opposite responses (fix the loop
    vs change the pool/objective), and seq 8's data supports the second reading at least as
    strongly as the first.
20. **Consider within-generation candidate selection — as an odd-seq experiment.** The
    improvement batch is fully observable by design; running 2–3 candidate changes as
    preflights against batch tasks before committing the set is firewall-legal and would
    give the loop the selection pressure a one-shot composition lacks. The priced risk is
    batch overfitting, which the reading key already names (B↑T→). A D-ledger decision, not
    a default.
21. **Make the next experiment answer the surface question, whatever else it asks.** The
    closure's own flag is right: extension tools and sub-agents are available and
    unexercised in any graded round. Combining items 1, 9, 10, and 18 makes the first tool
    generation cheap, measurable, and non-ruinous. If a tool generation then confirms on
    adoption and a subsequent round moves its counter, the loop has its first structural
    win; if the next experiment nulls *with the full surface menu exercised*, the honest
    conclusion hardens into something this project can publish: harness mutations at every
    available surface cannot reach this benchmark's remaining failure modes — which is a
    finding about the objective, not a failure of the loop.

## 9. Sources

Raw data: `generation_000…006/` (episode manifests, bridge logs, graded results, probes,
preflights), `batch_curve.json`, `held_out/` (7 rounds + reveal derivatives:
`trend_test.json`, `trend_fragility.json`, `transitions.csv`, `retention.csv`,
process-metric CSVs), `gates/seam_canary.json`, `GUARDRAIL_WALK.md`,
`batch_process_metrics_by_round.csv`. Process record:
`improvement_records/gen_000_to_001…gen_005_to_006.yaml` (schema v3),
`improvement_backlog.md` (six transition stamps, errata, `surfaces_considered` per target),
`summary.md`, `experiment.yaml`, `benchmark_lock.yaml` (protocol block + reading key),
`split_manifest.yaml`. Git: tags `h0-baseline` (`b76f274`), `exp8-g001…g006`; mutation
commits `1bc18de`, `6324712`, `64c1a01`, `c18788c`, `907137b`, `116bd58`, `f13a3ed`,
`3b1bf58`→`3b3a62e`; PRs #17–#22. Probes: `benchmark/probes/2026-08-16-surface-probes/`
(P1–P7), `generation_000/toolresult_probe/`, `generation_001/context_probe/`
(`hook_firings.json`). Design: `contract/protocol.md`,
`contract/improvement_record.schema.yaml`, `contract/constraints.md` (divergence 6),
`skills/sia/SKILL.md` + `references/recipe-growth.md` + `references/record-craft.md`,
`SIA_EVALUATION_PLAN.md` (D22–D28, Phase 6), `benchmark/tau_adapter/`
(`pi_local.py`, `pi_agent.py`, `run.py`, `records.py`), `target-agent/` at `h0-baseline` and
`exp8-g006`. Predecessor: `results/experiment_006_fixedb-bm25-luna56/INDEPENDENT_REVIEW.md`
(§7–§8, the groundwork's source).
