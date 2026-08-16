# Experiment 006_fixedb-bm25-luna56 — independent review

Written 2026-08-16, post-reveal, at user request. Independent in a specific sense: every number
below was recomputed from raw artifacts (`generation_00N/`, `episode_manifest.jsonl`,
`bridge_calls.jsonl`, `held_out/` CSVs, `batch_curve.json`), every instruction quote re-derived
from git (`git show` against the mutation commits, tags `exp6-g001…g006`), and every process
claim checked against `improvement_records/`, `improvement_backlog.md`, and
`generation_000/seam_probe/` — none taken on the closure README's word. Where this review
disagrees with the closure, the disagreement is stated in § 6.

Companion report: [`BATCH_TASK_DIFFICULTY.md`](BATCH_TASK_DIFFICULTY.md) — how hard the eight
pinned tasks are relative to the 97-task pool.

**Data-integrity check requested with this review:** `held_out/generation_000…006/` are
byte-identical to `~/.sia_vault/experiment_006_fixedb-bm25-luna56` (recursive diff, zero
differing files). The seven top-level files (`results_by_generation.csv`,
`task_generation_matrix.csv`, `transitions.csv`, `retention.csv`, `trend_test.json`,
`process_metrics_*.csv`) exist only on the results side by design — `summary.md` declares them
computed at reveal. The copy is correct.

## 1. Verdict

The experiment's own verdict — primary null, secondary positive, and the two instruments
disagree — survives independent recomputation. This review adds three things the closure does
not carry:

1. **The held-out trend is statistically fragile on its own terms**, independent of the
   triple-exposure confound the closure already names. Leave-one-task-out: dropping any one of
   six tasks (`task_007`, `task_021`, `task_031`, `task_033`, `task_044`, `task_098`) pushes
   p above 0.05. Two of those (`task_044`, `task_098`) are first-ever passes appearing only at
   H6, where the trend contrast weight is maximal (+3); together they supply 3.0 of the
   statistic's 8.0. Zeroing just those two cells gives z = 1.17, p = 0.121. The closure's
   refusal to make a capability claim is therefore over-determined: exposure *and* fragility
   each independently disqualify the number.
2. **The endpoint round was measured here for the first time on the dimension the experiment
   cared most about.** `batch_07` fed no transition and was never diagnosed, so the final
   harness's transfer rate was unrecorded. Joining `bridge_calls.jsonl` to
   `episode_manifest.jsonl` gives H6 = **9/24 transfers** — exactly H0's 9/24. Six mutations
   across three experiments moved the dial 9 → 11 → 10 → 15 → 6 → 12 → 9: a full round trip.
3. **A set of record errata** (§ 6), one of which — the E2 misquote — has propagated into
   `CLAUDE.md` and weakens the stated basis of the experiment's headline lesson (the lesson
   itself survives on other evidence).

The machinery claims all verify: 756 episodes (168 platform batch + 588 local held-out), one
freeze fingerprint across all 14 `run_metadata.json`, zero seam-disconnect/timeout counters
across 168 platform episodes, batch↔held-out task sets fully disjoint, all six records
`outcome: accepted` with held-out stamps matching the vault, twenty §29 guardrails HELD or
N/A-by-design, none waived, and the cadence gate's single firing (H4) correctly self-inflicted.

## 2. What happened, verified

### 2.1 The two instruments

**Primary — paired batch endpoint, B=8 × 3 trials, platform lane.** Recomputed cell-for-cell
from episode manifests; `batch_curve.json` and the README agree with the raw data exactly.

| task | H0 | H1 | H2 | H3 | H4 | H5 | H6 |
|---|---|---|---|---|---|---|---|
| task_014 | 2/3 | 1/3 | 1/3 | 2/3 | 0/3 | 1/3 | 1/3 |
| task_026 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| task_028 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| task_065 | 0 | 0 | 0 | 1/3 | 1/3 | 0 | 0 |
| task_070 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| task_072 | 0 | 0 | 2/3 | 1/3 | 0 | 0 | 0 |
| task_082 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| task_096 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| mean rate | 8.3% | 4.2% | 12.5% | 16.7% | 4.2% | 4.2% | 4.2% |

Endpoint test: the only non-zero per-task delta is `task_014` (−1/3). Σ = −0.333; all 256 sign
assignments give a value ≥ it, so exact one-sided p = 1.0000. **The pre-registered primary was
decided by one episode on one task.** Five of eight tasks contributed zero dynamic range over
168 episodes — the instrument's failure is quantified, not rhetorical (see the companion
difficulty report).

**Secondary — held-out probe, T=28 × 3 trials, local lane.** The full chain reproduces: 588
episodes → 196 matrix cells (0 mismatches) → per-generation expectations → trend test
(statistic 8.000, variance 20.444, z = 1.7693, p = 0.03842, agreeing with `trend_test.json` to
the 14th decimal). Curve: 15.5 → 17.9 → 20.2 → 23.8 → 22.6 → 20.2 → 22.6%; endpoint +2 tasks
(+7.14 pp) against a ±5 pp band. Fragility as in § 1. One texture note the closure lacks: at H6
only 2/28 tasks are fully solved (3/3), down from 3/28 at H2–H5, while partial solves rose
5 → 8 — **the held-out gain is breadth of partial success, not consolidation**.

### 2.2 The transfer dial, end to end

Counted from `bridge_calls.jsonl` joined on `episode_manifest.jsonl` (the join is required —
batch_02/03/04 bridge logs carry 1–3 orphaned retry starts that inflate naive counts):

| harness | H0 | H1 | H2 | H3 | H4 | H5 | H6 |
|---|---|---|---|---|---|---|---|
| transfer-carrying episodes /24 | 9 | 11 | 10 | 15 | 6 | 12 | 9 |
| in-prompt cause | — | C2 clause | D2 revert | E2 | F1 revert | G1 | (H1: no claim) |

Every in-record transfer claim reproduces (D2's "< 11/24" → 10; E2 denied 10 → 15; F1
confirmed-beyond at 6). The H6 value is new: the dial ended where it started while `task_014` —
the one task whose gold *is* a transfer — ended at 1/3 vs H0's 2/3. Rate moved seven times;
discrimination never did. On the held-out lane the same dial is visible faintly:
13 → 18 → 16 → 16 → 15 → 17 → 19 transfers per 84 episodes (`process_metrics_by_generation.csv`).

### 2.3 Process metrics (held-out lane, N=84/generation)

Episodes did not lengthen or grow costlier across generations: messages 43.1 → 44.8 → 43.1
(H0→H5→H6), cost/episode $0.0207 → $0.0210 (peak $0.0223 at H1), duration flat within ±4%.
Two signals worth keeping:

- **`partial_action_reward_pct` is the smoothest curve in the dataset**: 37.5 → 38.3 → 40.8 →
  40.9 → 42.0 (H0→H4), then 41.7/41.6 — near-monotone where the binary pass rate is noisy.
  The harness was measurably doing more gold actions per episode even in rounds the pass
  metric read as flat.
- `action_match_pct` rose 33.0 → 34.1 and `write_match_pct` 14.3 → 15.8 H0→H6 — small,
  consistent, same direction.

### 2.4 Spend

Platform batch: **$4.0846** over the 168 episodes (README says $4.06 twice; § 6). Plus
$0.0239 for the 3-episode `seam_canary` → platform total $4.1085. Local held-out: **$12.67**
across 588 episodes (recorded per-task, reported nowhere). Whole experiment: **≈ $16.75**.

## 3. The six generations, compressed

Slot use: gen-001 C1+C2+C3 · gen-002 D1+D2 · gen-003 E1+E2 · gen-004 F1 (revert only) ·
gen-005 G1+G2 · gen-006 H1 (revert only). All eleven changes touched exactly one recipe file,
`target-agent/SYSTEM.md` (verified per-commit; the only sibling file in any mutation commit is
the experiment's own backlog). `<instructions>` grew 573 → 2055 chars (peak 2223 at g005),
SYSTEM.md 85 → 109 lines; the two shrinkages are the two reverts, byte-exact by blob hash.
Final harness: five survivors — C3, D1, D2, E1, G1.

| change | one-line mechanism | prediction vs next batch | verdict |
|---|---|---|---|
| C1 | enumerate the bank's option set before choosing | task_070 opens Sky Blue | behaviour confirmed, outcome denied; superseded by D1 |
| C2 | every named item acted on "or explained" | task_096/065 act on both | half confirmed, escape clause measurably harmful; clause reverted by D2 |
| C3 | never volunteer optional write arguments | ≥1 task_065 close bare | confirmed 3/3, above prediction; survives |
| D1 | retrieve the rule in force that decides the choice | in-force query + Sky Blue | behaviour confirmed; outcome confirmed on unpredicted task_072 (first new pass); denied 3rd time on task_070 |
| D2 | tie completion to what the KB prescribes, delete the escape | transfers < 11/24 | confirmed; kept half strengthened to 3/3 |
| E1 | order state changes by the standing they consume | task_065 reorders, ≥ 1/3 | confirmed exactly (second new pass) — later shown unstable |
| E2 | inability to explain is not a reason to transfer | transfers < 9/24 | denied — 10 → 15/24, the wrong direction |
| F1 | revert E2 | transfers ≤ 10/24 | confirmed beyond — 6/24; task_014 collapsed 2/3 → 0/3 |
| G1 | a prescribed handover is a retrievable action | task_014 ≥ 1/3 | confirmed at threshold — the experiment's thinnest keep; transfers doubled 6 → 12/24 |
| G2 | name the charges you sum | task_072 pairs both amounts | denied — 0/18 over six rounds |
| H1 | revert G2 | no movement | not scored (endpoint round undiagnosed) |

## 4. Highs

- **The loop ran fully autonomously for six generations without a single procedural breach.**
  Approval frozen false (D23), not waived; every decision recorded with auditable reasoning;
  the cadence gate fired once, against the operator's own sequencing error, and was resolved
  without reading sealed data. This is the strongest end-to-end demonstration of the machinery
  in the project's history, and it is the second consecutive experiment with zero seam
  incidents at 24-episode batch scale.
- **Pre-registration was real, not decorative.** G2's falsifier, written before the round,
  named the exact condition on which H1 later reverted it ("the enumeration appears in the
  narration while the amounts stay unpaired ⇒ prose is the wrong surface for arithmetic").
  D1 carried an explicit surface-escalation clause. T4's un-hold condition was set at g=1 and
  honored at g=3. Reverts were pre-committed as first-class outcomes and two generations spent
  their whole slot on one, saying so.
- **The meta-agent registered objections against itself in the record** — gen-002: "a loop
  which keeps building on a falling curve is exactly the failure mode the frozen reading key
  calls 'the meta-agent is the problem'. Recorded so the closure can judge it rather than
  discover it"; gen-006: refusing to fill the last slot with a speculative change *because* it
  would optimise the endpoint statistic. This is the behavioral contract functioning under
  autonomy.
- **The fixed batch did the one thing it was designed for.** `task_065` is a clean
  demonstration of layer peeling: class choice wrong for three rounds → fixed (gen-002) and a
  hidden ordering/tenure constraint surfaced → fixed (gen-003, E1) and the task passed →
  regressed at batch_06 with ordering still correct 3/3 and class choice collapsed 3/3. The
  masked-constraint discovery (T8) was only possible because the same tasks were re-measured.
- **The loop measured its own action space before spending slots on it** — the g=0 seam probe
  is the first time in three experiments the "unused growth surfaces" hypothesis was tested
  rather than repeated, and it falsified the project's own documentation (`recipe-growth.md`
  corrected the same day, against committed evidence).
- **First positive held-out trend in project history** (z = 1.77, p = 0.038, +7.1 pp
  endpoint) — recorded with both hands tied behind its back, correctly.
- Two batch tasks earned their first-ever passes (`task_072` at H2 via D1, `task_065` at H3
  via E1) — both from retrieval/ordering mechanisms, both attributable to a specific change by
  a pre-registered prediction.

## 5. Lows

- **The primary instrument had almost no dynamic range and the experiment knew it by round
  two.** Five of eight tasks never passed under any harness (155 consecutive failures across
  five tasks — see companion report); the endpoint test reduced to whether `task_014` scored
  2/3 or 1/3 on a given day. A pre-registered test whose answer is one coin flip cannot return
  anything but noise, in either direction.
- **The batch curve round-tripped.** 8.3 → 16.7% by H3, then 4.2% for three straight rounds —
  ending below baseline. Whatever the held-out curve suggests, the loop did not durably improve
  the eight tasks it stared at for six generations, and the two tasks it fixed, it could not
  keep fixed (`task_072` 2/3 → 0 by H4; `task_065` 1/3 → 0 by H5).
- **The transfer dial consumed the experiment.** Four of eleven changes (C2-clause/D2, E2, F1,
  G1) were spent moving or unmoving a single scalar that ended exactly where it began, while
  `task_014`'s discrimination — the actual objective — ended *worse* (2/3 → 1/3). Six
  mutations over three experiments now form a controlled demonstration that this surface
  cannot express the needed distinction.
- **The endpoint round is a measurement hole.** `batch_07` fed no transition, so H1's own
  prediction ("no movement") was never scored and the final harness's behavioral profile went
  unmeasured until this review. The experiment paid 24 episodes for its endpoint and read only
  the reward bits.
- **The backlog went stale halfway through.** Last written at `record(gen-003)`; F1, G1/G2,
  H1, T6's consumption, and T7's second witness never reached it, and `gen_003_to_004.yaml`
  cites a backlog update that does not exist. The closure's "eight targets: six consumed" is a
  correct end-state the artifact itself never records. The sia write-through discipline held
  for records and failed silently for the backlog.
- **The one legal structural surface was argued away with an argument that only covers half of
  it, then dropped** (§ 7.3). T6's pre-registered deterministic home (a `tool_result` hook —
  measured legal by the probe) was silently replaced at gen-005 by "an extension tool would be
  the correct home... the right surface does not exist here" — a true statement about a
  different surface. G2, the change that resulted, failed 0/18 exactly as its own falsifier
  anticipated.
- **T4 was consumed in violation of its own pre-registered condition** — the backlog demanded
  "a mechanism that is procedural and counted... a no-tool-call extension hook rather than a
  sentence"; E2 was a sentence, and it over-generalised precisely as the condition predicted.
  G1, attempt six, was also a sentence.
- G1 survives in the final harness on the experiment's own "weakest confirmation" — a
  one-trial recovery riding a dial that simultaneously doubled — with a falsifier the record
  itself calls too loose in hindsight. C3's conditional falsifier (the `agent_name` malformed
  call at batch_02) was set to be re-checked at batch_03 and never mentioned again.

## 6. Errata and internal inconsistencies

Listed so they can be corrected; none overturns the verdict.

1. **The E2 quote is wrong in three documents.** `README.md` ("E2 said 'apply what the
   knowledge base provides first'"), `gen_003_to_004.yaml`, and `CLAUDE.md` (seq-6 bullet) all
   attribute to E2 a clause the landed text does not contain (verified against commit
   `3b1bf58` and the g003 tree). E2 is two sentences about transfers; the "apply what the KB
   gives you" language is D2's, co-resident in the same prompt. The escape-clause lesson keeps
   its first witness (C2's "or explained" — misquote-free) and the E2 *behaviour* (27 writes,
   then transfer anyway) is real, but the claim "E2's precondition taught the model to satisfy
   it" rests on words E2 did not carry; the honest attribution for the E2 failure is "an
   instruction targeting a motive moved the rate the wrong way", with the precondition
   mechanism possibly D2's. CLAUDE.md should be corrected.
2. **"Ten changes landed" vs eleven table rows** (`README.md`, `GUARDRAIL_WALK.md` §16). The
   count excludes H1 but includes F1 — both are pure reverts. Pick one convention.
3. **Platform spend is $4.08, not $4.06** (twice in README, once in GUARDRAIL_WALK). Actual:
   $4.0846 over the 168; the $4.06 figure reproduces exactly as total minus the seam-canary
   cost — subtracted with the wrong sign (the canary was *additional* spend). Local-lane spend
   ($12.67) and experiment total (≈$16.75) appear nowhere.
4. **"Zero seam incidents across all 168 platform episodes" is under-qualified in the README**
   — one `sandbox_tool_errors: 1` counter exists (batch_02, task_072 t1). GUARDRAIL_WALK
   discloses it precisely; the README sentence alone overstates.
5. **The seam probe is cited beyond its coverage.** One tool, mock domain, local lane, three
   trials. The sub-agent verdict is same-mechanism inference (probe README says so); the
   `tool_call`-blocking verdict is inferred and deliberately not run; the Pi-skill row is not a
   probe finding at all but a restatement of pre-existing trap #1. Downstream citations
   (records, recipe-growth.md) present all four rows as settled.
6. **Backlog stale from gen-003** (§ 5), including one dangling cross-reference from
   `gen_003_to_004.yaml`.
7. `summary.md` labels the trend test "(D11)"; the reading-key/primary designation for this
   experiment is D23's. Cosmetic.

## 7. Why the growth surfaces were never used

The question as posed — "the meta-agent had sia functionality for adding skills, sub-agents,
and tools, and never called it" — dissolves into four different answers for four different
surfaces. The premise that all three growth surfaces were available is the first casualty:
**seq 6 established that most of the menu never existed in this seam.**

### 7.1 Two surfaces are measurably unavailable (correct non-use)

The g=0 probe (`generation_000/seam_probe/`) measured that `transport_local._assistant_turn`
forwards every Pi `toolCall` block, so an extension-tool call reaches τ as an invalid call
(`Error: Tool 'probe_note' not found`) costing a τ step and one of ten `max_errors`. Sub-agents
delegate through the same auto-generated `agent` tool. Blocking a τ call from a hook is worse:
τ executes the write anyway while the agent believes it stopped. All six improvement records
cite this paragraph as the reason their sets are prompt-only. **For tools and sub-agents,
non-use was evidence-based restraint, not timidity** — with the caveat (§ 6.5) that the
sub-agent half is inference, not measurement.

### 7.2 One surface was ruled inert by inheritance and never tested

A Pi skill's body loads on demand via the `read` tool, which this recipe deliberately withholds
(`tools: []` — granting `read`/`bash` would put τ's vendored task definitions and gold state in
the agent's reach; `target-agent/README.md`). Only the name + description (≤1024 chars) reach
the system prompt — i.e., **the surviving skill channel is a strictly weaker `SYSTEM.md` edit
with worse placement control**. That is why the records never even discuss it: `grep` finds
zero mentions of "skill" in any improvement record. But the verdict is inherited from
documentation, not measured: `recipe-growth.md` trap #1 explicitly prescribes a one-episode
dev-lane verification of what a declared `skills:` entry does for a read-less agent, with the
conversation id recorded — **never run in seq 4, 5, or 6.**

### 7.3 The one legal structural surface was half-argued, then dropped

The probe certified three no-tool-call extension hooks legal: `before_agent_start`,
`tool_result`, `context` — "this is the structural surface seq 6 actually has" (probe README).
The records engage it exactly once on the merits (gen-001: the mechanisms are "decisions taken
BEFORE a call, where a result-transforming hook has nothing to work on"), restate that formula
twice, and stop mentioning it entirely from gen-004 on. Two problems:

- The rebuttal is valid for `tool_result` and vacuous for `before_agent_start`, which runs
  before any call and can inject deterministic content into the effective prompt. It was never
  separately dispatched.
- T6 (arithmetic drift) had a pre-registered deterministic home in a `tool_result` hook —
  named twice (gen-001 record; backlog) *after* the probe had certified that hook legal. When
  T6 was finally consumed at gen-005, the record says "an extension tool would be the correct
  home... the right surface does not exist here" — true of extension tools, silent about the
  hook it had twice promised. G2 (prose arithmetic) landed instead and failed 0/18. **This is
  the experiment's strongest internal inconsistency, and the closest thing to a genuine missed
  structural mutation.**

### 7.4 The process frictions that made prose the default

Even where structure was legal, the artifact design tilts the choice:

- **Asymmetric gating.** A prompt edit requires zero extra reads. A growth surface requires
  `recipe-growth.md` (196 lines), the upstream `improve/capability-set` skill, a 7-item
  pre-PR checklist, and a dev-lane verification episode that has no slot in
  `contract/protocol.md`'s per-generation steps. The prose says "first-class"; the procedure
  says "gated".
- **Prediction asymmetry.** The record schema demands a per-change falsifiable prediction as
  the only attribution channel. A SYSTEM.md paragraph maps 1:1 onto a behavior counter; a
  skill-description or hook change has no obviously distinct prediction from the prose that
  would say the same thing.
- **The schema cannot name the legal surface.** `improvement_record.schema.yaml`'s
  `changes[].surface` enumerates `instructions | pi-skill | extension-tool | sub-agent |
  retrieval-usage | revert | other` — the two dead surfaces have enum values; the one legal
  structural surface (extension hook) can only be logged as `other`.
- **The concentration flag exits through a paragraph.** Protocol: a prompt-only set after ≥3
  prompt mutations "must say why no structural surface fits." Seq 6 discharged this six times
  with a well-argued paragraph. The mechanism worked as written and changed nothing — a
  correct reason is an accepted exit.
- **No scaffold.** `target-agent/` has no `skills/`, no `extensions/`, and `agent.yaml`'s
  `skills: []` carries no comment (while `tools: []` above it has a three-line load-bearing
  one). The only skill exemplar in the repo lives in a Pi ambient path the orchestrator is
  told never to mutate. The first structural mutation would have been a novel diff with no
  template; every prose mutation had 16 predecessors.

### 7.5 Verdict

The meta-agent did not ignore the growth surfaces — it probed them on day zero, corrected the
project's false documentation about them, and then cited the result in every record, exactly
as the protocol's justification clause demands. Within the frozen seam, prompt-only was the
majority-correct choice. The genuine failures are narrower and more actionable: an untested
inherited assumption (the skill channel), a legal surface argued away with a half-fitting
rebuttal and never revisited (`before_agent_start`), one silently-dropped pre-registered
structural commitment (T6's `tool_result` hook), and a process whose every gradient — reads,
schema, predictions, scaffolding, exit clauses — points toward prose. The seam starves the
loop of the surfaces its own diagnoses kept calling for; the artifacts then make the remaining
surface the path of least resistance. Both layers need changing, and they are § 8.

## 8. What to change before the next experiment

Grouped by artifact. Each item cites the observed fact that motivates it.

### Seam / freeze level (decided at freeze, not mutated mid-experiment)

1. **Resolve the seam question explicitly, either way.** Option A: make Pi-local tool calls
   invisible to τ (the closure's own recommendation) — unlocks extension tools and sub-agents;
   the recorded counter-argument (adapter helpfulness makes the harness unmeasurable,
   `seam_probe/README.md`) must be answered, e.g. by logging suppressed calls to the evidence
   stream so nothing is hidden from diagnosis, only from grading. Option B: re-freeze the
   two-surface menu (`SYSTEM.md` + no-tool-call hooks) as a declared design fact and stop
   citing "unused growth surfaces" as the live hypothesis. The current halfway state — surfaces
   documented as first-class, measured as absent — spent three closures on a hypothesis the
   seam had already decided.
2. **Buy the two missing measurements; they cost one episode each.** (a) Dev-lane-verify what
   a declared `skills:` entry does for this read-less agent (prescribed by recipe-growth trap
   #1, never run). (b) Run a `before_agent_start` no-op hook through the dev lane to certify
   the one legal structural surface on the banking domain, not just mock. Record both
   conversation ids. After this, every surface verdict in `recipe-growth.md` is measured.

### The instrument (batch composition and measurement)

3. **Stratify the fixed batch.** Five of eight tasks at zero across 168 episodes left the
   primary with one task of dynamic range. Compose the next fixed batch as roughly 2–3
   known-pass anchors (regression detectors) + 3–4 marginal tasks (the 1/3–2/3 band, where
   3 trials actually resolve movement) + 2 known-fails (headroom). The companion difficulty
   report identifies candidates in each band.
4. **Diagnose the endpoint round.** batch_07 cost 24 episodes and only its reward bits were
   read; H1's prediction was never scored and the final transfer rate went unmeasured until
   this review. Add to the protocol: the endpoint round receives the same diagnosis pass as
   every other round, minus the mutation step.
5. **Retire the 28-task held-out set for any experiment that wants a capability claim.** It is
   on its third experiment and both predecessors are revealed. A fresh draw from the ~61 never-
   used tasks is available.
6. **Pre-register a reading key that names all four quadrants.** B↓T↑ was observed and the
   frozen key had no language for it; the closure had to adjudicate off-key. Next key: name
   all of {B↑,B→,B↓} × {T↑,T→,T↓} or state explicitly which cells are "impossible, and their
   observation voids the run".
7. **Report trend fragility at reveal.** Leave-one-task-out and endpoint-cell sensitivity are
   cheap (this review's versions took minutes) and would have pre-empted any over-reading of
   p = 0.038. Candidate: add to `reveal.py` next to the trend test.
8. **Promote the process metrics to pre-registered secondary channels.**
   `partial_action_reward_pct` moved near-monotonically (+4.6 pp H0→H4) while the binary pass
   rate thrashed; transfer counts explained four generations of behavior. Attribution is
   already mechanistic in this project — give predictions these counters as first-class
   targets, not just pass/fail.

### Protocol and record schema

9. **Add `extension-hook` (and `pi-skill-description`) to `changes[].surface`** in
   `contract/improvement_record.schema.yaml`. A surface the schema cannot name will not be
   chosen; today the only legal structural surface maps to `other`.
10. **Turn the concentration flag from a justification duty into a positive obligation.**
    After the flag fires, the next set must either include one non-`instructions` change or
    record a `surface_exhausted` finding backed by a *committed probe* naming the seam fact
    that blocks each alternative. Seq 6 proved the probe pattern is cheap (one throwaway
    branch, one `make smoke`); requiring it converts "a paragraph explains why not" into "an
    experiment shows why not".
11. **Give the surface probe a protocol slot** (a step 4b with a fixed budget: one dev-lane or
    smoke episode, evidence committed under `generation_00g/<probe>/`). The g=0 seam probe was
    an act of initiative; make it the required first-generation default.
12. **Enforce backlog write-through mechanically.** The cadence gate already refuses a round
    without an accepted record; extend it (or `records.py` validation) to refuse a record
    whose backlog file was not touched in the same transition. The seq-6 backlog silently
    froze at gen-003 while the records stayed impeccable — the gated artifact stayed alive,
    the ungated one died.
13. **Quote discipline for scored verdicts.** Any record or closure sentence that attributes a
    behavioral mechanism to landed text must quote that text from git, not paraphrase from
    memory. The E2 misquote crossed three documents into CLAUDE.md — in an experiment whose
    central lesson is that *exact wording* is what the model optimises against, paraphrase in
    the record is the same defect one level up.

### The sia skill

14. **Rebalance "Mutation classes".** Move the seq-4/5 failure narrative out of the
    `SYSTEM.md` bullet (where it reads as context for the default) into the section preamble;
    give every surface an activation-path line stating what must be true for it to reach a
    graded episode (for the Pi skill here: "description string only; body needs `read`,
    withheld"); list the no-tool-call hooks as a peer surface, not a buried reference row.
15. **Make recall forward-looking about surfaces.** The digest spec reports surface
    concentration (what happened); add one line for what could happen: "surfaces untried this
    experiment, each with its current blocker". gen-005 — where T6's hook-shaped target came
    up prompt-shaped — is exactly where that line pays.
16. **Add `surfaces_considered` to backlog targets at open time.** T6 and T4 both carried
    surface commitments in prose that later slipped; a required per-target field ("which of
    {instructions, extension-hook, skill-description, none} could carry this mechanism, one
    line each") written when the target is opened moves the surface decision upstream of set
    composition, where the record shows it was actually being made too late.

### Target-agent scaffold

17. **Ship the growth zero-state.** Comment `agent.yaml`'s `skills: []` with the activation
    path and its blocker (parity with the load-bearing `tools: []` comment above it); add an
    `extensions/` directory with a committed no-op `before_agent_start` hook (measured legal)
    behind a disabled flag, so the first structural mutation is a small, reviewable diff with
    a template rather than a novel artifact class. H0 stays exactly as simple in behavior —
    the zero-state changes nothing at runtime and everything about the mutation gradient.

### Meta-agent discipline (instruction authoring)

18. **Adversarial wording review per landed clause.** The experiment's sharpest transferable
    lesson: the escape clause is what the model optimises against. Operationalize it — every
    landed instruction's record must enumerate the instruction's disjunctions, preconditions,
    and licensed alternatives, and attach a falsifier *per clause*, not per instruction. C2's
    record falsified over-reach and left "or explained" unwatched; the harm arrived through
    the unwatched clause one round later.
19. **Correct the propagated record** (§ 6): the E2 quote in `README.md` and `CLAUDE.md`, the
    ten/eleven count, and the $4.06 figure. Small, but this project's value is that its record
    can be trusted verbatim.

## 9. Sources

Raw data: `generation_000…006/` (episode manifests, bridge logs, tau results, graded),
`batch_curve.json`, `held_out/` (7 vault rounds + reveal derivatives), `gates/`,
`GUARDRAIL_WALK.md`. Process record: `improvement_records/gen_000_to_001 … gen_005_to_006.yaml`,
`improvement_backlog.md`, `generation_000/seam_probe/`. Git: tags `h0-baseline`,
`exp6-g001…g006`; mutation commits `5bce8ac`, `bd243c5`, `29a4878`, `440beb8`, `3a64da7`,
`d8b9bb1`, `3b1bf58`, `46b980e`, `c16d3e1`, `bf339c4`, `2291703`; correction commit `34c5012`
(recipe-growth.md). Design: `contract/protocol.md`, `contract/improvement_record.schema.yaml`,
`skills/sia/` (SKILL.md + references), `SIA_EVALUATION_PLAN.md` (D17–D23), `target-agent/`.
Difficulty companion: `BATCH_TASK_DIFFICULTY.md`.
