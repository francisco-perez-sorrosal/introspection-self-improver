# SIA_EVALUATION_PLAN — Implementing the Generation-Based Evaluation Protocol

**Status:** living tracker. Supersedes `PLAN.md` (2026-08-13), which is retained as
history and must not be followed. Where this file and the code disagree, the code wins
and this file gets fixed.\
**Specification:** `self_improving_agent_evaluation_protocol.md` — the evaluation
protocol this plan implements. The v2 MVP guide's M3/M4 milestones and the pass^k /
discovery-validation-test model are superseded wherever they conflict; the machinery
built for M1/M2 (the seam, the evidence spine, the lock, resume, manifests) is the
substrate this plan adapts, not discards. Invariants stay in `CLAUDE.md` (rewritten in
Phase 0); frozen values stay in `benchmark/benchmark_lock.yaml`.\
**Created:** 2026-08-13, grounded in repo state @ `984c598` and in the Introspection
plugin (0.7.0) + CLI (0.26.0) capability surface verified the same day.

**Done means:** Phase 4 closed — one complete debug-scale experiment (G=3, B=3, T=5)
ran the real loop end to end: partition → H0 held-out (hidden) → batch → `operate` →
`improve` PR → human approval → new generation → held-out (hidden) → … → reveal →
result artifacts. Phase 5 then runs the full experiment (G=5, B=10, T=47) under an
unchanged mechanism.

------------------------------------------------------------------------

## 1. Protocol validation verdict

The protocol is implementable on this repo and this platform, with one design choice
doing most of the work and two honest caveats.

**The firewall can be structural, not just procedural.** The Introspection platform
has no access-control wall inside a project: `tasks archive` only hides rows, list
`--filter` silently ignores unknown keys, `--query` filtering is client-side, and the
automatic observation/pattern clustering would fold held-out conversations into
aggregates the orchestrator legitimately reads during `improve`. But the local lane
(`TRANSPORT=local`) creates **no platform evidence at all** — no task, no
conversation, no observation; Pi's session file is the only record. Running held-out
episodes exclusively on the local lane means the platform literally holds nothing to
leak. That, plus out-of-tree results and muted grading, is the firewall (D1).

**Caveat 1 — single-trial noise.** This repo measured per-task reward instability
(10 runs of one task: six 1.0, four 0.0), which motivated the old `num_trials: 4`
doctrine. The protocol's single-trial design is still sound, but the statistical power
moves from repeated trials of one task to pooling across 47 held-out tasks: the
generation-to-generation held-out count carries binomial noise of roughly ±3 tasks
(≈ ±7 pp). Per-generation wiggles inside that band are noise; the endpoint claim
R_T(H_G) > R_T(H_0) is clean at ≳15 pp or with a broadly monotone trajectory. This
re-argument is recorded in the lock and summary template (D2), and the optional
endpoint reliability study (protocol §23) is the named upgrade path.

**Caveat 2 — cross-lane evidence, cross-lane measurement.** Diagnosis evidence comes
from platform-lane batches; generalization is measured on local-lane held-out runs.
A fix targeting a platform-only artifact will simply fail to move the held-out number
and be rejected — the design is self-correcting — but the known lane divergences
(`contract/constraints.md §Known adapter divergences`) must stay documented, and the
`make fidelity` instrument stays available as a diagnostic (D4).

Everything else the protocol needs, the platform verifiably provides: conversations
with full tool-call/cost/span/commit evidence (`conversations get`), prevalence via
`metrics query` (spans/conversations/observations/patterns views), observations
landing ~30–40 min after a conversation's last activity (30-min eligibility + 10-min
scan — the harvest cadence must respect this; the metrics-over-spans fallback stays),
`operate` ending in an answer and `improve` ending in a PR behind a human gate, and
`recipe_git_commit_sha` lineage per conversation for generation identity.

------------------------------------------------------------------------

## 2. Decisions (D1–D9)

User override always wins. Items marked **ratify** need explicit sign-off at Phase 0;
the rest are recorded here as the working defaults.

| # | Decision | Value | Rationale / consequence |
|---|---|---|---|
| D1 | Lane ↔ information-regime mapping | **Improvement batches: platform lane. Held-out: local lane only.** Runner refuses the other combination for each round type. | Batches must produce Introspection evidence (the point of the experiment); held-out must produce none (structural firewall — no trace mixing). Local-lane artifacts (vault) remain procedurally protected — stated in every writeup, per the existing `split_manifest.yaml` held-out doctrine. **Ratified 2026-08-13** (user: run held-out locally so traces don't mix). |
| D2 | Trial doctrine | `num_trials: 1` for batches and held-out. Noise band ±7 pp (T=47) stated wherever a curve is shown; no `pass^k` language for generations. Optional post-reveal endpoint study (H0, H_G × 4 trials) as an addendum with its own config snapshot. | Reverses the lock:118–123 / `CLAUDE.md` doctrine — power now comes from 47-task pooling, not repeated trials. **Ratified 2026-08-13.** |
| D3 | Experiment identity | Protocol change ⇒ new freeze: **seq 2 = debug** (G=3, B=3, T=5), **seq 3 = full** (G=5, B=10, T=47). `experiment_001_bm25-sonnet46` closes as the bring-up freeze (12 ad-hoc episodes, archived as-is). | Forced mechanically anyway: the freeze fingerprint hashes lock + split manifest jointly (`experiment.py:74–83`); any partition change refuses every run under 001. |
| D4 | Gates | **A.0a stays blocking** per experiment (adapter suite + mock smoke — cheap, guards the seam). **A.0b demoted** from blocking gate to diagnostic instrument (`make fidelity` on demand); the Phase 2 platform-health check replaces its blocking role. **A.0c (`anchor_stock`) retired** — stock-agent comparability is explicitly no longer a goal. **Ratified 2026-08-13.** |
| D5 | Generation semantics | `generation_NNN` dir ≡ H_n. A generation is defined by an approved, merged PR commit on `main`, tagged `exp<seq>-g<NNN>`. **Rejected mutation ⇒ identity generation**: H_(g+1) = H_g recorded in the improvement record, held-out eval skipped, R_g carried forward, next batch consumed as normal. | One batch per generation slot regardless of accept/reject (protocol §13's fresh-evidence rule); no paired baseline/candidate arms anymore. |
| D6 | H0 reset mechanism | Tag the current recipe as **`h0-baseline`** (byte-identical `target-agent/` + `.introspection/target-agent.yaml` since the M1 freeze `0976493`). `make reset_h0` = restore from tag as **replace, not merge** (`git checkout <tag> -- …` + `git clean -fdx target-agent`), then `make bootstrap` (regenerates `.pi/mcp.local.json`), then `introspection check`, then instruct to commit — platform rounds refuse a dirty recipe tree. `.introspection/local.json` (machine-local runtime binding, CLI-written) is preserved, never restored. | Every new experiment starts from the same H0. **Ratified 2026-08-13** — tag `h0-baseline` created at `2e8058b`. |
| D7 | Concurrency | `max_concurrency: 1` stays (bridge is run-scoped, single-episode-safe; raising it needs bridge episode-multiplexing + a re-freeze). Revisit only if Phase 5 wall-clock is unacceptable. | Held-out eval ≈ 2.5–4 h serial; acceptable for now. |
| D8 | H0 viability signal | The old §13.1 discovery floor is replaced by the **B1 read**: batch results are visible by design, so if H0 lands 0/B or B/B on B1, halt and reconsider H0 before spending further generations. Not a hard floor at B=10 (2/10 is within noise of 20%). | The firewall makes a held-out floor check impossible until reveal; B1 is the legitimate window. |
| D9 | Vault & reveal | Held-out outputs (episodes, sessions, graded results, console log) live out of tree at `~/.sia_vault/experiment_<id>/generation_NNN/`. `make reveal` — runnable only when the final generation is tagged — copies the vault into `results/experiment_<id>/held_out/`, computes the matrices, and writes `summary.md`. Until then the orchestrator does not read the vault (procedural, stated in every writeup). | Out-of-tree keeps held-out data away from glob/grep sweeps and the dashboard walk; the dashboard renders held-out views only from revealed artifacts. |

------------------------------------------------------------------------

## 3. Protocol → repo mapping

| Protocol concept | Repo realization |
|---|---|
| Experiment config (§26) | `protocol:` block in `benchmark_lock.yaml` (`generations`, `improvement_tasks_per_generation`, `held_out_tasks`, `allow_within_batch_verification: false`, `holdout_visibility` flags, `require_human_approval: true`). Inside the freeze fingerprint automatically via `lock.raw`. `held_out_trials_per_task` ≡ `frozen.num_trials` (one knob). |
| Partition (§3, §16) | `benchmark/split_manifest.yaml` rewritten: `batches: {batch_01: […], …}` + `held_out: […]`, sizes derived from the lock's `protocol:` block. Same stratification machinery (reward_basis 88 DB / 9 ACTION, dominant doc category, doc count; stride scheduler), disjointness verified dynamically across G+1 partitions, (G×B)+T ≤ 97 enforced, ACTION spread re-expressed (held-out gets its proportional share ≥4 at T=47; batches jointly cover the rest). |
| Improvement batch run (§7) | `make batch B=1 GEN=generation_001` — platform lane forced, resume-friendly (no `--overwrite`), round dir `generation_NNN/batch_01/`, manifest `split: batch_01`, labels `[exp_00N:…] τ²-bench banking_knowledge task_X trial 0 gen_001 b01 - …`. |
| Held-out evaluation (§6, §11) | `make heldout GEN=generation_001` → `scripts/run_heldout.py`: local lane forced, all child stdout/stderr redirected into the vault's `console.log`, grading persisted to the vault (never printed), prints **completeness only** (episodes expected/completed, manifest joined, zero reward tokens — asserted by test). |
| Firewall (§12) | D1 + D9. Platform: structural (no evidence exists). Local artifacts: procedural + out-of-tree + muted output. |
| Diagnosis (§8) | `operate` skill over the batch's platform conversations: task rows → conversations → tool calls/spans; prevalence via `metrics query`; observations/patterns after the ~40-min window (fallback: metrics-over-spans + manual clustering, evidence tier stated). |
| Proposal (§9) | `improve` skill: one coherent mechanism inside the mutable table → branch `gen-NNN/<slug>` → PR citing conversation ids + prevalence + predicted effect. |
| Approval → generation (§10) | Human reviews/merges the PR on `main`; merge commit tagged `exp<seq>-g<NNN>`; `improvement_records/gen_<g>_to_<g+1>.yaml` written (schema: `contract/improvement_record.schema.yaml`, §24 fields; `held_out_result` filled at reveal only). |
| Metrics & artifacts (§18–§21, §27) | `make reveal` → `results/experiment_<id>/held_out/{results_by_generation.csv, task_generation_matrix.csv}`, gains/regressions/retained/unresolved per transition, currently-solved vs ever-solved, `summary.md` with counts + percentages + the D2 noise band. §27's `config.yaml` is satisfied by `experiment.yaml` (lock+manifest fingerprint snapshot). |
| Guardrail 10 (§29) | Unchanged from today: the adapter never repairs the agent (`contract/constraints.md`), integration code stays task-agnostic, `introspection check` in pre-commit/CI/runner. |

------------------------------------------------------------------------

## 4. Repo delta

### Remove (retire; git history keeps everything)

- `checkpoint` target + `--checkpoint` path (`Makefile:145–148`, `run.py:326–335,436`) — replaced by `heldout`.
- `discovery` / `validation` targets (`Makefile:132–140`) — replaced by `batch`.
- `anchor_stock` + `scripts/run_stock_anchor.py` (D4: A.0c retired).
- `fidelity_gate` target + `--gate` blocking path (`Makefile:167–177`) — `make fidelity` (single-task cross-lane diff) survives as the diagnostic; `split.fidelity_task_set` (reads the literal `discovery` key) goes with the gate.
- The three-way-split semantics: `SPLIT_SIZES` (`split.py:38`), `RUNNABLE_SPLITS` (`run.py:73–77`), the ARM/paired-arm round naming (`ARM` var, `<split>_<arm>` dirs) — no paired arms exist in the new design.
- pass^k as a reported metric for generations: `num_trials: 4` rationale (lock:118–123), doctrine text in `CLAUDE.md:67–73,150–153`, `constraints.md:145–146`. Dashboard pass^k plumbing degrades gracefully at 1 trial (`app.js:131` already nulls it) — trim the dead columns/series when Phase 5 touches the dashboard, not before.

### Adapt

- `split.py` — dynamic G+1 partition proposal/verify/render, sizes from the lock's `protocol:` block; `propose_split.py` CLI accordingly.
- `lock.py` + `benchmark_lock.yaml` — `protocol:` block accessors; `num_trials: 1`; seq bump per D3.
- `run.py` — `--batch NN` (platform forced) and `--heldout` (local forced, reward lines `run.py:836–846` and metrics table `:835` suppressed in-process as defense-in-depth under the wrapper's redirect); selection banner; sweep-cost arithmetic.
- `Makefile` — `batch`, `heldout`, `reset_h0`, `reveal` targets; retire the removed ones; `gate_a0a` still shells `make smoke`, keep it working.
- `manifest.py` / retitle pass — `split` field carries `batch_NN`/`held_out`; label gains the batch token.
- `grade.py` — quiet mode + always-persist graded output when pointed at the vault (today the graded number exists only in the terminal — `grade.py:95–99` prints and writes nothing).
- `experiment.py` — recognize `held_out/` + `improvement_records/` at reveal; vault paths stay outside `results/` (already the unenforced zone by design, `experiment.py:51–71`).
- Dashboard — cheap path now: write the new round names into `run_metadata.json["split"]` (`serve.py:300–301` already prefers it). Progression view (held-out curve + task×generation heatmap from revealed CSVs) in Phase 5.
- Tests — rewrite `test_split.py` (12) and the two fingerprint tests in `test_experiment.py`; extend `test_round_lifecycle.py` for the new targets.
- Docs — `CLAUDE.md` invariants (test-split → held-out-until-reveal; trial doctrine → D2; frozen list: partition manifest), `README.md` stale blocks (`:235–244`), `constraints.md` single-trial re-argument + dangling `gates/a0b.json` citation, `split_manifest` header semantics (regenerated by `split.py`).

### Add

- `protocol:` config schema + validation ((G×B)+T ≤ N, disjointness) — lock + split machinery.
- `scripts/run_heldout.py` — the muted held-out wrapper + vault layout + completeness-only status output (tested: captured stdout contains no reward figures).
- `scripts/reveal.py` — end-of-experiment computation: per-generation counts, task×generation matrix, gains/regressions/retained/unresolved, ever-solved vs currently-solved, `summary.md` with the noise band; refuses to run before the final generation tag exists.
- `contract/improvement_record.schema.yaml` + a scaffolder for `improvement_records/gen_<g>_to_<g+1>.yaml`.
- `make reset_h0` (D6) + a round-trip test (mutate recipe on a scratch branch → reset → byte-identical to `h0-baseline` → `introspection check` passes).
- Git tags: `h0-baseline` now; `exp<seq>-g<NNN>` per accepted generation (procedural, documented in `contract/protocol.md`).
- `contract/protocol.md` rewritten **from the debug run that actually executed** (Phase 4 close), keeping the repo's written-from-what-ran doctrine.

------------------------------------------------------------------------

## 5. Phases

One phase in flight at a time; check boxes with dates; if a phase's scope grows
mid-flight, stop and re-plan. Phases 0–3 spend no benchmark budget (Phase 2's live
checks ≈ $3).

### Phase 0 — Ratify & align the record (docs + decisions only)

- [x] D1 ratified — held-out on the local lane, no trace mixing (2026-08-13).
- [x] D2, D4, D6 ratified as recommended, no overrides (2026-08-13).
- [x] Commit `self_improving_agent_evaluation_protocol.md` as the spec; stamp
      `PLAN.md` with its superseded banner (2026-08-13, `2e8058b`).
- [x] Tag `h0-baseline` at the current recipe state — annotated tag at `2e8058b`,
      recipe byte-identical to the M1 freeze `0976493` (2026-08-13).
- [x] `CLAUDE.md` truth pass: the 8 stale claims fixed, plus the invariants rewrite
      per D1/D2 (held-out-until-reveal replaces test-split language; single-trial
      doctrine; corrected frozen list inline — the "four items are wrong" hedge
      dropped; spec/tracker pointers replace the v2/PLAN.md forward-guide framing)
      (2026-08-13).
- [x] `README.md` stale blocks rewritten (frozen-for-001 truth, D2 doctrine, label
      prefix, A.0a naming); `contract/protocol.md` re-grounded (evidence join landed;
      phase table points at plan phases); `constraints.md` D2 re-argument + D4
      demotion + git-history pointer for the deleted `gates/a0b.json` (2026-08-13).
- [x] Close experiment 001: `results/experiment_001_bm25-sonnet46/README.md` records
      the closure, contents, and gate verdicts with recovery commands (2026-08-13).

**Validate:** docs read true against the code; `make check` green; full benchmark
suite green — 118 passed, untouched (2026-08-13). ✅

### Phase 1 — Partition & configuration machinery (no live runs)

- [ ] `protocol:` block in the lock + `lock.py` accessors + validation.
- [ ] `split.py` dynamic partitions (propose/verify/render for G batches + held-out);
      ACTION-spread rule re-expressed; `propose_split.py` CLI updated.
- [ ] Tests: partition proposal determinism, disjointness, budget check, ACTION
      spread, manifest round-trip, lock protocol-block validation, fingerprint drift
      on partition change.

**Validate:** unit tests green; against real task data, `propose_split.py --write`
produces a verifiable G=5/B=10/T=47 manifest **and** a G=3/B=3/T=5 manifest
(debug-sized), both passing `--verify`; the old 30/15/20 manifest is refused loudly.

### Phase 2 — Runner, firewall, and round targets

- [ ] `run.py --batch` / `--heldout` with lane forcing (D1) + in-process reward
      muting; `Makefile` `batch` / `heldout` targets; old round targets retired.
- [ ] `scripts/run_heldout.py`: vault layout, full-redirect console log, persisted
      grading, completeness-only status.
- [ ] `grade.py` quiet + persist mode.
- [ ] Manifest/label/`run_metadata.json` extensions (`batch_NN` / `held_out`).
- [ ] Tests: mock-domain runs of both paths; **the held-out muting test** (captured
      stdout has zero reward tokens); lane-forcing refusals; resume still keyed on
      `(trial, task, seed)` for batch rounds.

**Validate (live, ≈ $3):** `make smoke` both lanes; one 2-task batch-style round on
the platform lane completing with **zero timeout/stall incidents** (this is the
platform-health check that replaces A.0b's blocking role — the `7aee297` narration
fix validated in anger); one 2-task held-out round on the local lane whose terminal
output demonstrably contains no rewards and whose vault holds graded results.
Note: CI's `frozen-surfaces.yml` will warn on all of this — expected, acknowledge in
the PR.

### Phase 3 — Generation lifecycle: records, reset, reveal

- [ ] `contract/improvement_record.schema.yaml` + scaffolder; identity-generation
      rule (D5) encoded in the record schema (`outcome: accepted | rejected |
      identity`).
- [ ] `make reset_h0` (D6) + round-trip test.
- [ ] `scripts/reveal.py` + `make reveal`: matrices, transitions, retention, summary;
      refusal before the final generation tag; tests over synthetic vault data
      (fabricated results → known-correct matrix/gains/ever-solved).
- [ ] Generation tagging convention documented (`exp<seq>-g<NNN>`).

**Validate:** unit tests green; a synthetic three-generation dry run (fabricated
vault + records, zero episodes) produces correct CSVs, transition tables, and
`summary.md`; reset round-trip proves byte-identical restore + passing
`introspection check`.

### Phase 4 — Debug experiment (seq 2): the real-scenario test

The capstone: everything runs for real, small (G=3, B=3, T=5; 20 held-out + 9 batch
episodes ≈ $10–15, ~4–6 h compute). Same isolation rules as the full experiment
(protocol §29.17).

- [ ] Freeze: `experiment.seq: 2`, debug `protocol:` values, `num_trials: 1`,
      partition proposed + frozen; `reset_h0`; commit; **A.0a gate PASS** recorded.
- [ ] H0 held-out (hidden, vault) → B1 batch → `operate` diagnosis (harvest 1
      immediately; harvest 2 after the ~40-min observation window, fallback stated)
      → `improve` PR → human review/merge → tag `exp2-g001` → H1 held-out (hidden)
      → B2 → … → H3 held-out → final tag.
- [ ] Improvement record per transition, written as it happens; B1 viability read
      (D8) recorded.
- [ ] `make reveal` → held-out artifacts + `summary.md`; verify every §27 artifact
      exists and every §29 guardrail held (walk the 20-item list, record the walk).
- [ ] `contract/protocol.md` rewritten from this run (the per-generation procedure
      as it actually executed).

**Validate:** the complete evidence → signal → hypothesis → mutation → generation →
hidden-measurement chain exists on disk for ≥1 accepted (or cleanly
rejected/identity) transition; no held-out task id, trajectory, or reward appeared in
any orchestrator-visible output before reveal (audit the session record + vault
`console.log` placement); loop mechanics needed zero manual patching mid-run — else
fix and re-run Phase 4 under seq 3 before scaling up.

### Phase 5 — Full experiment + reporting

- [ ] Freeze seq 3 (or next): G=5, B=10, T=47; `reset_h0`; A.0a PASS; partition
      frozen.
- [ ] Run the six held-out evaluations and five generations (~282 local + 50 platform
      episodes ≈ $75–90 compute, ~20–28 h spread over ~a week of sessions; budget
      go/no-go with the user at each generation boundary).
- [ ] Dashboard progression view over revealed artifacts (held-out curve with noise
      band, task×generation heatmap, transition table); trim dead pass^k plumbing.
- [ ] Reveal; `summary.md`; the final claim written per protocol §25 with the D2
      noise band stated.
- [ ] Optional (budget-gated): endpoint reliability addendum — H0 and H_G × 4 trials
      on held-out, reported as τ-style reliability metrics, separate from the
      progression metric.

**Validate:** protocol §25's success bundle — endpoint comparison, transition tables,
retention diagnostic, complete per-generation records, frozen config, firewall
statement — all present and internally consistent.

------------------------------------------------------------------------

## 6. Budget & wall-clock (estimates until replaced by actuals)

| Item | Episodes | Cost | Wall-clock |
|---|---|---|---|
| Phase 2 live checks | ~6 (mock + 2+2 real) | ≈ $3 | < 1 h |
| Debug experiment (seq 2) | 20 local + 9 platform | ≈ $10–15 | ~4–6 h compute + review time |
| Full experiment | 282 local + 50 platform | ≈ $75–90 | ~20–28 h compute, ~1 week elapsed |
| Endpoint reliability addendum (optional) | 376 local | ≈ $40–75 | ~25 h |

Basis: measured $0.10–0.51/local episode (median ≈ $0.20) and ≈ $0.34/platform
episode ($4.09 across the 12 live episodes); serial at `max_concurrency: 1`.

## 7. Risks

| Risk | Mitigation |
|---|---|
| Single-trial noise read as signal | D2 noise band in every rendering; transition tables distinguish net movement from churn; optional endpoint study. |
| Platform stalls recur in batch rounds, polluting diagnosis | Phase 2 platform-health check gates the debug run; incident counters ride every manifest row; `make fidelity` on demand. |
| Held-out leak via habit (grep/glob/dashboard sweep) | Out-of-tree vault; muted wrapper is the only button; dashboard never walks the vault; leak-check is an explicit Phase 4 validation item. |
| Observation/pattern harvest not eligible in cadence | 30-min eligibility + 10-min scan confirmed from platform docs — schedule harvest 2 accordingly; metrics-over-spans fallback with evidence tier stated. |
| H0 secretly broken (or saturated) under the firewall | D8: the B1 read is visible by design; halt on 0/B or B/B. |
| Batch of 10 too thin for a confident diagnosis | Prevalence stated as n/B; prior batches' evidence remains queryable (protocol §13); a directional hypothesis is a legitimate, recorded outcome. |
| Rejected mutations stall progress | D5 identity generations keep the experiment moving and are first-class results (protocol §25). |

## 8. Conventions

- One phase in flight at a time; scope growth ⇒ stop and re-plan here first.
- Check a box by appending the landing date: `- [x] … (2026-08-15)`.
- Estimates above are replaced by recorded actuals as phases close.
- Every writeup that touches held-out data states the enforcement boundary
  (structural on the platform, procedural on local artifacts) — no exceptions.
