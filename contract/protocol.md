# Per-generation procedure

Written 2026-08-14 from the debug experiment that actually ran (seq 2,
`002_bm25-sonnet46`: three accepted generations, revealed) — per the repo's
written-from-what-ran doctrine. The design this instantiates is
`self_improving_agent_evaluation_protocol.md`; the permission envelope is
`constraints.md`; frozen values live in `benchmark/benchmark_lock.yaml`. Where this
file and the code disagree, the code wins and this file gets fixed.

## 0. Freeze (once per experiment)

1. **Screen the pool** before any partition exists (no firewall applies yet):
   `benchmark/scripts/screen_user_sim.py` drives τ's own orchestrator over every pool
   task with a scripted LLM-free agent — real user-sim, real user tools, crash
   verdicts only. Where the screen cannot reach a failure class (real-agent-conditioned
   crashes), probe suspects directly with τ's stock agent (`tau2 run … --agent
   llm_agent`), pre-partition. Seq 2 exists because seq 1 died at H0 on exactly such a
   defect (task_034; upstream tau2-bench#470).
2. **Partition**: `make propose_split` (wraps `propose_split.py`; review the printed
   proposal, then freeze with `WRITE=1`); `--verify` must pass. Exclusions are
   documented in the manifest header, evidence committed beside it
   (`benchmark/data/user_sim_screen.json`). Exclusions carry the crashers AND the
   experiment's decision-row pool discipline: seq 4 (plan D11) additionally excludes
   all 20 seq-2 tasks, so nothing a prior loop was tuned on — and nothing a prior
   reveal exposed — reappears anywhere in the new partition. Two composition rules
   (plan D25) bind here:
   - **A fixed batch spans empirical strata**, measured under the incumbent H0 —
     anchors (reliably passing: regression detectors), marginals (the band where
     `num_trials` resolves movement), and headroom (failing tasks whose modes the
     mutable surface can plausibly address) — with the chosen ratio and each task's
     stratum recorded in the manifest header. An all-known-fail batch is by
     construction a floor: one revealed experiment's primary spent 168 episodes with
     five of eight tasks contributing zero dynamic range, and its endpoint test
     reduced to one task's day-to-day variance. **Headroom is screened for
     reachability, not only level** (seq 8): stratifying by pass rate alone admitted
     three headroom tasks whose failure modes five rounds of layer-peeling proved
     domain-walled — a rounding convention, a governing rate, a gold-label semantics
     disagreement — unreachable by any mutation the invariants allow. The screen
     therefore also reads each headroom candidate's H0 trajectories and classifies
     the terminal failing step **harness-reachable** (procedure, retrieval, ordering,
     handover, verification) or **domain-walled** (needs domain knowledge the
     invariants forbid encoding); walled tasks enter, if at all, as declared
     wall-monitors outside the primary. Screen rates and classifications are
     committed with the probe evidence and land in the manifest header's `strata:`
     mapping, which the freeze snapshot restates under `results/experiment_<id>/`.
   - **A capability-claim freeze draws its held-out set from tasks the loop never
     tuned on: zero batch exposure, ever** (the partition-isolation machinery prints
     every reuse at commit). Under the D33 cross-experiment firewall — in-loop
     decisions are grounded in batches only, and held-out artifacts of every
     experiment stay outside in-loop recall forever — **holdout-only reuse, declared
     per source, carries a claim on the stated procedural basis**: the same
     enforcement class as the local-lane vault (D1/D9), named in every writeup.
     Batch-derived reuse (`held_out_from_batch`) still demotes the lane to a
     diagnostic probe — the loop read those transcripts and tuned on them, and no
     reading discipline undoes that. The freeze decision states which basis its
     held-out lane claims; the unqualified zero-exposure claim requires a pool no
     prior experiment touched.
3. **Freeze**: set `experiment.seq`, protocol block (G/B/T, and the full-quadrant
   `reading_key` — all nine primary × secondary cells, validated by the lock parser;
   optional in code for old snapshots, mandatory here for new freezes: a key that does
   not name every cell is a key that gets rewritten after the data exists), flip
   `frozen.status` to FROZEN; `make reset_h0` (byte-identity to `h0-baseline`);
   commit; `make gate_a0a` (blocking) and commit the PASS record — the first run
   writes the freeze snapshot that every later run must match. Four additions, each
   bought with a seq-8 closure finding:
   - **The primary's power envelope is computed at freeze, not discovered at
     closure** (`scripts/power_envelope.py`; verdict committed to
     `gates/power_envelope.json`): given the frozen composition and test, it states
     the movers α = 0.05 requires, the movable-task count (anchors cannot move by
     construction; walled tasks will not), and the attainable-p ceiling — seq 8's
     five-movers-needed-with-three-walled-tasks envelope was computable before its
     first episode and discovered at closure. An envelope that cannot reach α under
     plausible success means fixing the composition or the test before freezing,
     never the narration after.
   - **One behavioural-identity round is pre-registered**
     (`protocol.identity_generations`, lock-validated; `batch_mode: fixed` only):
     the named generation is identity by design — H_k = H_(k−1), its held-out round
     carries forward, its batch round is the A/A noise measurement, and the reveal
     refuses the pre-registration dishonored. Seq 8 got its noise floor (2 cells,
     8.3 pp on an identical harness) only by accident of a change that never
     executed, and the number re-read every attribution the project had ever made.
     Registered at generation 1 the identity round also pools the baseline: the
     primary's H0 side reads batch_01 + batch_02 (2 × `num_trials` per task) against
     the endpoint.
   - **The D24 suppressing path is exercised before anything relies on it**: the
     pre-freeze suppression canary (`scripts/gate_seam_canary.py --suppression
     --expect-tool <name>`) runs ≥1 platform episode against a temporarily-declared
     probe tool on pushed main — expected `pi_local_calls ≥ 1` in the manifest, the
     tool name absent from τ's graded trajectory, seam counters clean — verdict
     committed to `gates/suppression_canary.json`, the declaration reverted before
     `h0-baseline` is tagged so H0's registry stays empty. Seq 8 ran the D24 seam
     pump-path-only (`pi_local_calls` = 0 across 168 platform episodes), so
     platform-lane suppression entered the next freeze as an assumption; this
     converts it to a measurement. The script's `--judge-only` mode re-judges the
     experiment's first real tool generation post-merge at zero extra episodes.
   - **The reading key distinguishes loop failure from headroom exhaustion**: beside
     the nine cells the freeze pre-registers the **reachable-harvest co-metric** —
     the fraction of non-walled batch cells passed at the endpoint vs baseline
     (emitted by `scripts/batch_curve.py` from the manifest's strata) — and the
     flat-primary cells read it: flat with harvest high (≥90%) says the objective's
     harness-reachable range is spent and the next move is a pool or domain
     decision; flat with harvest low says the loop found nothing. Seq 8 was read
     "the meta-agent is the problem" by a key with no language for a batch the loop
     had nearly saturated — 15 of 15 reachable cells at its peak round.

## Per generation g (H_g is current, tagged; g starts at 0)

**The cadence is a guarantee, not a habit** (user-ratified 2026-08-16). An experiment of
G generations is exactly: *measure H0 on the held-out set → [batch → diagnose → improve →
merge+tag → measure H_(g+1) on the held-out set] × G → reveal* — the baseline is measured
before any learning, every harness that learned is measured, and the sequence always ends
with the latest harness's held-out measurement. Three mechanisms enforce it, so the order
cannot be lost to forgetting: **(a)** `run.py` refuses `--batch N` until H_(N-1)'s
held-out round is graded in the vault (existence of the graded artifact by path — nothing
in the vault is opened) and the recipe surface is byte-identical to H_(N-1)'s tag, both
resolved through the identity chain (an identity/rejected transition carries its
predecessor's tag and measurement forward, D5); **(b)** the held-out runner refuses a
recipe that is not byte-identical to the generation it claims to measure — and, for
H_N (N ≥ 1), refuses to measure at all until batch_N is graded and the transition record
exists with outcome accepted, so a generation cannot be measured that no learning round
produced (a skipped batch would otherwise be invisible: merge, tag, measure, cite older
evidence), and an identity generation is refused before the spend rather than at reveal;
**(c)** `make reveal` refuses to close the experiment while any non-identity generation
H0…H_G lacks its measurement — the final harness cannot go unmeasured, because without
its round there is no reveal. A skipped baseline is not merely late: once the next merge
moves the recipe, (b) makes the missed measurement unrunnable — which is why (a) exists.
Together (a) and (b) make each seam bidirectional: a batch cannot run before its
generation's measurement, and a measurement cannot run before its generation's batch.

1. **Hidden measurement of H_g**: `make heldout GEN=generation_00g`. Local lane only,
   sealed vault, completeness-only terminal (counts, seam incidents, failure classes —
   never rewards). If INCOMPLETE, rerun the same target: τ resumes missing pairs and
   replaces `infrastructure_error` placeholders; completed episodes are never re-spent.
   The round refuses a dirty recipe tree and verifies byte-identity to H_g's tag.
2. **Improvement batch**: `make batch B=<g+1> GEN=generation_00g` (platform lane, at the
   `make batch` concurrency default — pinned low to keep sandbox-provisioning contention
   out of the evidence; the Makefile is the authority on the value).
   Check the manifest: every row
   should be `evidence_complete`, `arm_sha_ok`, with only benign `stream_reattaches`,
   and `pi_local_calls` consistent with the recipe (nonzero only when the registry is
   non-empty; D24).
   The graded read is visible by design; state it as n/B. On B1 it doubles as the D8
   viability read: 0/B or B/B → surface to the user before proceeding.
3. **Diagnose (`operate` skill)**: export all B conversations
   (`introspection conversations get --ids-file …`), read them in full, and read the
   graded `action_checks`/`db_check` from `batch_NN/graded/updated_results.json` —
   field-level diffs for near-misses. Try the observation harvest
   (`introspection events list --event-name introspection.observation`) after the
   ~40-min window; when it returns nothing, say so and use the full-population
   transcript read as the fallback — at these batch sizes it is the stronger evidence
   tier anyway. Open-code failure modes;
   prevalence is n/B by enumeration. Never read anything held-out — this
   experiment's (the vault rule) or **any prior experiment's, revealed included**
   (D33): in-loop decision inputs are improvement batches only, current and past, and
   a prior reveal's per-task results in the diagnosis loop are the answer key leaking
   into mutation selection.
4. **Decide with the user** — two questions with different shapes. Proceed / identity /
   halt is exclusive and stays a single choice. The detected improvements are not:
   present every mode with prevalence and conversation ids as a **multi-select**, and
   the user opts into any subset — or all — as approved mutation targets. Approved
   targets land in `results/experiment_<id>/improvement_backlog.md` (mechanism,
   evidence pointers, approval date, status: pending / consumed-by-gen / retired, and
   `surfaces_considered` — which surface classes could carry the mechanism, decided at
   open time, one line each with its blocker or enabler; the surface decision belongs
   upstream of set composition).
   Targets carry forward re-ranked against each new batch's evidence — each re-ranking
   appends its `<!-- transition: gen_NNN_to_MMM -->` marker, which the record validator
   and the next round's gate both require (plan D26) — and an item later contradicted
   is retired with the reason recorded, never silently dropped.

   Then **compose the improvement set** (plan D22, from seq 6; decided ahead of its
   first run by user direction, to be trued up against what actually runs): the next
   generation lands **any number of changes**, drawn from the approved targets, and the
   orchestrator proposes the set it judges most likely to generalize — never a
   pick-one-of-N menu. Present it as a per-change table — mechanism, surface, evidence
   (n/B + conversation ids), its own falsifiable prediction, its risk — and the user
   opts individual changes in or out. Composition rules:
   - Each change is **one coherent mechanism** (the `improve` skill's discipline,
     held per change, not per generation) and would justify landing on its own.
   - No two changes in a set may interact on the same behavior; candidates that
     interact are either genuinely one mechanism, or the weaker-evidenced one waits.
   - The surface is part of the diagnosis, and the structural surfaces are first-class
     under D24 (Pi-local suppression, `constraints.md` divergence 6): extension tools,
     sub-agents, and the no-tool-call extension hooks are live; a *declared* skill is
     measurably inert on this seam, so skill-shaped judgment is delivered by hook
     injection (wiring and measured verdicts: sia's `recipe-growth` reference +
     `improve/capability-set`). Seq 4 + seq 5 measured that *an instruction added to a
     prompt does not inherit the scope its author reasoned about*; seq 6 added the
     sharper form (*the escape clause is what the model optimises against*) — when the
     mechanism is judgment, scope, verification, or arithmetic, prefer a structural
     surface. **The concentration flag is surface-general** (seq 8 measured why: the
     instructions-only flag never fired while six changes landed on one surface and
     the D24 surfaces went unexercised for the whole experiment — each repaired
     gradient re-forms at the cheapest newly-legal surface). **After ≥3 prior
     mutations on any single surface class, a set confined to that class is no longer
     self-certifying: the next set includes at least one change on a surface class
     this experiment has never exercised, or records a `surface_exhausted` finding in
     the backlog naming, per unexercised surface, either a committed step-4b probe or
     a measured batch fact (cited with its evidence path) that blocks it.** A
     paragraph of argument alone does not discharge the flag — the citation is to a
     measurement, not to reasoning (seq 8's one legitimate shape-argument, "the model
     would have to choose to call it", is dissolved by the adoption-first rule below,
     so it no longer discharges anything).
   - **First use of a never-exercised surface is adoption-first** (from the seq-8
     review): the change's falsifiable prediction targets *adoption and correct
     invocation* — `pi_local_calls ≥ k` on the tasks it targets, well-formed
     arguments, latency inside τ's frozen budget — and the reward-level prediction is
     deliberately deferred to the following round and stated as deferred. A denied
     adoption prediction (the model never calls it) is a mechanism denial and a
     first-class revert trigger; a confirmed adoption with unmoved reward is not. A
     first tool change may bundle the tool with its minimal usage instruction as one
     coherent mechanism — capability and adoption path are one diagnosis, and
     splitting them guarantees the "model must choose to call it" objection.
   - A **revert** of a prior change whose prediction the batch refuted is a
     first-class change, enabled by per-change commits (step 5). **The trigger is a
     refuted mechanism, never a refuted prediction alone**: a change whose prediction
     was denied while its mechanism's counter moved on the tasks where it could fire
     stays in (seq 8's clearest win came two rounds after its prediction was denied);
     a change whose mechanism moved nothing anywhere it could fire is the revert
     candidate. Target retirement carries the same bar: a retirement cites witnesses
     from ≥2 rounds or a mechanism-level impossibility — on one round's evidence the
     target is parked, not retired (seq 8 retired a target on one round's episode
     shapes and had to un-retire it two rounds later).
   G bounds generations, not changes; per-change attribution inside a set is
   **mechanistic** — each prediction is scored against the next batch — while the
   statistical read stays at the generation level, and every record says so.

   **Composition policy, from seq 12 (plan D36), each rule bought with a seq-10
   measurement:**
   - **Land 3–5 non-interacting changes per generation, not one.** Seq 10 landed one at a
     time to keep credit clean and got five forward attempts from seven slots. The caution
     protected nothing: the noise floor (14 of 36 cells flipping on a byte-identical
     harness) meant reward-level attribution was never available, and every conclusion the
     experiment actually reached came from per-change behaviour counters — which work
     unchanged when several changes land together. Bundled changes must act on different
     steps or different tasks; the interaction rule above is what enforces it.
   - **A target must reach ≥3 tasks, or be structural** (a verification, ordering or
     state-tracking pattern that applies across the batch by construction). Applied to
     seq 10 this bar would have blocked exactly one forward change — the one later
     reverted — freeing two slots. Single-task targets are diagnosis material, not slot
     material, however precisely they are understood.
   - **Score every change on a pre-registered counter stated as a DELTA against the prior
     round**, never on a level and never on the round total. Seq 10's C3 carried a
     falsifier reading "stays at 0 on task_023"; it was 0 before the change too, so it
     fired on a pre-existing condition and diagnosed nothing.
   - **At most two reverts per experiment.** Reverts are first-class and both of seq 10's
     were correct, but they consumed two of seven slots. Bundling makes a bad change cost a
     fraction of a generation instead of a whole one.
   - **One slot is reserved for a surface class this project has never exercised.** Seq 10
     discharged the D29 ladder on `extension-hook` and left `sub-agent` unexercised and
     unprobed — no episode has ever run one on this seam — because the remaining slots went
     to reverts the evidence demanded. Reserving it means the reservation cannot be eaten by
     the loop's own housekeeping.
   - **Run the diagnosis instrument, do not re-derive it.** `scripts/gold_diff.py` (the
     normalized MATCH / ARGS / ABSENT comparison), `scripts/round_read.py`, and
     `scripts/endpoint_test.py` are committed. τ's own miss list cannot separate "never did
     it" from "did it wrong", and a loop that re-invents that separation each experiment
     will miss it in the one where it matters.

4b. **Probe an untried surface — one episode, evidence committed.** Required at g=0;
   afterwards whenever the concentration flag fires or a target's mechanism names a
   surface this experiment has not exercised. On a throwaway `probe/<slug>` branch,
   wire the minimal artifact and run one **work-tree-faithful** episode: `make smoke
   TRANSPORT=local` (mock) or `make single_task TRANSPORT=local` (locked domain). The
   platform lane cannot serve an unmerged branch — it pins the recipe to pushed main,
   and `--allow-dirty` runs pushed main anyway with `arm_sha_ok=false` (measured:
   `benchmark/probes/2026-08-16-surface-probes/` P3) — so platform-side verification
   of a landed surface happens post-merge. Delete the branch; commit the evidence
   (markers, manifests, verdict) under `results/experiment_<id>/generation_00g/
   <probe>/` — `benchmark/probes/<date>-<slug>/` when no freeze is open — citing run
   ids **in the probe evidence, never as record provenance** (a probe precedes its
   batch, and provenance validates against batch manifests). The verdict updates
   `recipe-growth.md`'s surface table: measured, never inherited. Probe runs reuse the
   current experiment tree only with a non-colliding suffix, and leave nothing behind
   in a closed experiment's record.
5. **Mutate (`improve` skill)**: the approved set on branch `gen-00<g+1>/<slug>`,
   **one commit per change** — each message naming the mechanism and its prediction,
   because the commit is the unit of selective revert — touching mutable surface only
   (`SYSTEM.md` `<instructions>`; recipe skills/tools/sub-agents per
   `references/recipe-growth.md`; the `<policy>` block is frozen benchmark text).
   `make check` must pass, plus `make smoke` when any change is mechanical (tools,
   sub-agents, wiring). **Extension code cites its host facts**: every line that keys
   on a measured host behavior (message roles, block shapes, event timing) carries a
   comment naming the committed probe evidence that establishes the fact — seq 8
   spent a generation on a hook keyed to role `tool` where its own probe's
   `hook_firings.json` had recorded `toolResult`, and the change was measured inert.
   Push; open **one PR carrying the whole set**, citing per-change
   evidence, predictions, and what is deliberately not targeted. Return the work tree
   to `main` (it must keep serving H_g until the merge).

5b. **Preflight — verify a change runs, never that it works.** Optional, bounded:
   up to ~12 local-lane episodes per generation, on batch tasks (only when the lock's
   `allow_within_batch_verification` is true) and/or on **burned non-partition tasks**
   — tasks in neither the batch nor the held-out set (D34) — where the read doubles as
   a candidate-generalization probe: an out-of-batch check before landing that touches
   nothing held-out. The budget covers execution checks and up to three candidate
   forms of one change (the sanctioned within-generation selection pressure —
   candidates are compared on execution and process counters, never anointed by
   preflight reward). Two rules, both bought with a seq-8
   generation: an injected text is verified **present in a fetched conversation**
   before any behavioural number is read (F1's preflight showed 3/3 against a 0/12
   baseline for a change that never executed — chance); and a preflight's
   behavioural read is never evidence — the scheduled rounds are the measurement,
   preflight runs are never record provenance, and the record's `evidence.summary`
   names any preflights run with their episode counts.
6. **Record as it happens**: `scripts/improvement_record.py --scaffold g --write`,
   fill evidence/signals/counterevidence/hypothesis and the per-change `changes` list
   (schema v4: mechanism, surface, evidence, expected_effect, risk, commit per item;
   per-clause falsifiers for `instructions` changes since v3 — see step 5's adversarial
   wording review; `adoption_stage`/`adoption_criteria` for first-use surfaces and
   `host_facts` for extension changes since v4); verify, and update the backlog in the same transition (its
   per-transition marker is validated with the record). Conversation ids come from the
   manifest — never from memory; **quoted instruction text comes from `git show`
   against the landed commit — never from memory** (a verdict attributed to words the
   text does not carry propagated through three seq-6 documents).
7. **Approval gate**: the user reviews and merges (or declines) the PR; the agent
   does not merge on its own authority. On merge: tag the merge commit
   `exp<seq>-g00<g+1>` (annotated, pushed), set the record's `outcome: accepted` +
   `candidate_commit`, re-verify, commit. On decline: `outcome: rejected` (or
   `identity`), H_{g+1} = H_g, the next held-out round is skipped and the result
   carries forward at reveal. **The interactive shape of this step and step 4 assumes
   the lock's `require_human_approval: true`.** A freeze may set it `false` (the
   D23/D28 autonomy envelope, re-registered per experiment): the orchestrator then
   holds decision authority over step 4's choices, this merge, the tag, and the
   reveal — provenance recorded in every record's `human_approval` block — while
   access limits are untouched (frozen surfaces, partition, `<policy>` block,
   held-out firewall), and a freeze re-decision or a suspected seam defect remains a
   halt-and-report in either mode.

## Close (after the final transition)

1. Final hidden measurement: `make heldout GEN=generation_00G` against the final tag.
2. **Diagnose the endpoint batch round** — any design whose final harness runs an
   observable batch round (`batch_mode: fixed` runs batch_G+1 under H_G) gives that
   round the same diagnosis pass step 3 gives every round: counters, behavioral dials,
   the final change's prediction scored — minus any mutation. Findings land in the
   closure README; a measurement-only round is consumed by no transition and gets no
   improvement record. The final harness's behavioral profile is part of the result —
   seq 6 paid 24 episodes for its endpoint and read only the reward bits, leaving its
   own last prediction unscored and its transfer dial unmeasured until the independent
   review.
3. `make reveal` — the one sanctioned read of the vault: copies rounds verbatim,
   computes progression/matrix/transitions/retention and the pre-registered trend
   test (plan D11: one-sided over measured generations, identity generations
   excluded; machine-readable at `held_out/trend_test.json`), stamps
   `held_out_result` into every record, writes `summary.md` with the scale-aware
   noise band, the trend verdict, and the trend-fragility report
   (`held_out/trend_fragility.json`: leave-one-task-out and endpoint-cell
   sensitivity — a significance that rests on one task's cells is reported as such,
   next to the p-value it qualifies). `summary.md` also narrates the churn its
   transitions table carries — per-transition gains and regressions against the
   net, ever-solved vs point-in-time at the endpoint, and the identity-pair deltas
   when a pre-registered identity round exists (batch A/A; held-out carried-pair) —
   seq 8's held-out lane held a second noise measurement (3–5 cells of churn per
   transition against nets of −2…+3) that its closure never surfaced. Refuses a
   missing final tag, a mixed-fingerprint curve, a measurement for an identity
   generation, or a pre-registered identity generation whose record says otherwise.
4. Walk protocol §29 and record it (`GUARDRAIL_WALK.md` beside the summary), including
   the §27 artifact inventory and the loop-mechanics verdict — plus the **D33
   attestation**: no in-loop session of this experiment opened held-out artifacts of
   any experiment, and every recall digest named its sources.
5. **Structure the closure for the quarantine**: the closure README and any
   post-reveal review separate batch-derived findings (recallable by later
   experiments' in-loop sessions) from held-out reveal analysis (quarantined from
   in-loop recall forever, D33) under explicit headings, so future recalls can honor
   the boundary mechanically instead of parsing prose.
6. Numbers are always labelled with their set and N; batch reads are diagnosis
   evidence, not the progression metric; effects inside the band are directional only.

## What seq 2 measured about the procedure itself

The loop ran end to end with zero mid-run mechanics patching: freeze → 4 hidden
measurements → 3 batches → 3 diagnoses → 3 user-gated PRs → 3 tags → reveal, seam
incident-free throughout. Wall-clock ≈ 3.5 h including review latency; spend ≈ $32
(manifest sums: $19.92 local — agent + user-sim — and $9.05 platform conversation
billing, the τ-side user-sim on that lane being manifest-invisible, plus ~$3
screens/probes; an earlier "≈ $11" note here undercounted by omitting the local
lane's manifests). The endpoint at T=8 was
directional-negative (−1 task, inside ±18 pp): the debug scale demonstrates the
loop, not the claim. Sizing and instrument decisions since then live in the plan's
D-ledger (`SIA_EVALUATION_PLAN.md` §2), not here — this section records only what
the first complete run measured about the procedure itself.
