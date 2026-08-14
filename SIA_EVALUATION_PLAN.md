# SIA_EVALUATION_PLAN — Implementing the Generation-Based Evaluation Protocol

**Status:** living tracker. Supersedes `PLAN.md` (2026-08-13; removed from the tree at
Phase 0.5 — git history keeps it). Where this file and the code disagree, the code wins
and this file gets fixed.\
**Specification:** `self_improving_agent_evaluation_protocol.md` — the evaluation
protocol this plan implements. The v2 MVP guide's M3/M4 milestones and the pass^k /
discovery-validation-test model are superseded wherever they conflict; the machinery
built for M1/M2 (the seam, the evidence spine, the lock, resume, manifests) is the
substrate this plan adapts, not discards. Invariants stay in `CLAUDE.md` (rewritten in
Phase 0); frozen values stay in `benchmark/benchmark_lock.yaml`.\
**Created:** 2026-08-13, grounded in repo state @ `984c598` and in the Introspection
plugin (0.7.0) + CLI (0.26.0) capability surface verified the same day.

**Done means:** Phase 4 closed — one complete debug-scale experiment (D3's G=3, B=3,
T=5; D10 proposes G=3, B=4, T=8 at `max_concurrency` 4 — ratify at the freeze) ran the
real loop end to end: partition → H0 held-out (hidden) → batch → `operate` →
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

## 2. Decisions (D1–D10)

User override always wins. Items marked **ratify** need explicit sign-off at Phase 0;
the rest are recorded here as the working defaults.

| # | Decision | Value | Rationale / consequence |
|---|---|---|---|
| D1 | Lane ↔ information-regime mapping | **Improvement batches: platform lane. Held-out: local lane only.** Runner refuses the other combination for each round type. | Batches must produce Introspection evidence (the point of the experiment); held-out must produce none (structural firewall — no trace mixing). Local-lane artifacts (vault) remain procedurally protected — stated in every writeup, per the existing `split_manifest.yaml` held-out doctrine. **Ratified 2026-08-13** (user: run held-out locally so traces don't mix). |
| D2 | Trial doctrine | `num_trials: 1` for batches and held-out. Noise band ±7 pp (T=47) stated wherever a curve is shown; no `pass^k` language for generations. Optional post-reveal endpoint study (H0, H_G × 4 trials) as an addendum with its own config snapshot. | Reverses the lock:118–123 / `CLAUDE.md` doctrine — power now comes from 47-task pooling, not repeated trials. **Ratified 2026-08-13.** |
| D3 | Experiment identity | Protocol change ⇒ new freeze: **seq 2 = debug** (G=3, B=3, T=5 → re-sized to **G=3, B=4, T=8** by D10, 2026-08-13), **seq 3 = full** (G=5, B=10, T=47). `experiment_001_bm25-sonnet46` closes as the bring-up freeze (12 ad-hoc episodes, archived as-is). **Numbering RESET 2026-08-13 (user-directed):** with every bring-up artifact cleared to git history, the sequence restarts at **seq 1 = debug** (D10 sizes), **seq 2 = full**; the reused `001_bm25-sonnet46` id is disambiguated by freeze fingerprints and the historical archive's own README in git history. | Forced mechanically anyway: the freeze fingerprint hashes lock + split manifest jointly (`experiment.py:74–83`); any partition change refuses every run under 001. |
| D4 | Gates | **A.0a stays blocking** per experiment (adapter suite + mock smoke — cheap, guards the seam). **A.0b demoted** from blocking gate to diagnostic instrument (`make fidelity` on demand); the Phase 2 platform-health check replaces its blocking role. **A.0c (`anchor_stock`) retired** — stock-agent comparability is explicitly no longer a goal. **Ratified 2026-08-13.** |
| D5 | Generation semantics | `generation_NNN` dir ≡ H_n. A generation is defined by an approved, merged PR commit on `main`, tagged `exp<seq>-g<NNN>`. **Rejected mutation ⇒ identity generation**: H_(g+1) = H_g recorded in the improvement record, held-out eval skipped, R_g carried forward, next batch consumed as normal. | One batch per generation slot regardless of accept/reject (protocol §13's fresh-evidence rule); no paired baseline/candidate arms anymore. |
| D6 | H0 reset mechanism | Tag the current recipe as **`h0-baseline`** (byte-identical `target-agent/` + `.introspection/target-agent.yaml` since the M1 freeze `0976493`). `make reset_h0` = restore from tag as **replace, not merge** (`git checkout <tag> -- …` + `git clean -fdx target-agent`), then `make bootstrap` (regenerates `.pi/mcp.local.json`), then `introspection check`, then instruct to commit — platform rounds refuse a dirty recipe tree. `.introspection/local.json` (machine-local runtime binding, CLI-written) is preserved, never restored. | Every new experiment starts from the same H0. **Ratified 2026-08-13** — tag `h0-baseline` created at `2e8058b`. |
| D7 | Concurrency | `max_concurrency: 1` stays (bridge is run-scoped, single-episode-safe; raising it needs bridge episode-multiplexing + a re-freeze). Revisit only if Phase 5 wall-clock is unacceptable. **Re-decided 2026-08-13 (user): the episode-multiplexing machinery is built BEFORE Phase 4 (Phase 3.5)** so the debug experiment runs the new bridge at its degenerate concurrency 1 under a fresh A.0a PASS — one code path, no seam swap between debug and full. The frozen VALUE stays 1 for seq 2; seq 3 decides the number. Lane analysis: held-out (local lane) is ~85% of episode wall-clock and the simple half — it parallelizes; platform batches stay serial unless the docs pass proves a native affordance. **Machinery landed at Phase 3.5 (2026-08-13):** per-episode URL channels on the run-scoped bridge; local lane concurrent (2.80× at N=3 on the mock round); platform lane pinned at 1 with the native affordance (`dev --as` attachments) documented in `contract/constraints.md § Platform-lane concurrency`, cited not built. Seq-3 sizing facts: local N is bounded by 2N concurrent Anthropic streams on one key (τ/litellm own retries — `num_retries` defaulted on every user-sim call) and, far later, by the bridge's `asyncio.to_thread` pool (≈ min(32, cpu+4) parked handlers). **Re-decided again 2026-08-13 (user): the platform pin is lifted too — Phase 3.5b builds the `dev --as` attachment pool so BOTH lanes execute concurrent episodes; the VALUE stays a freeze decision, useful ceiling B per batch round / T per held-out round.** **Outcome (2026-08-13): the pool is built and live-proven at N=1, but the platform itself accepts ONE live dev attachment per Runtime (`dev_slot_conflict`, observed) — platform rounds stay serial by upstream constraint, refused pre-spend with the citation; the local lane executes the frozen value in full. Paths if platform N>1 is ever needed: upstream cap lift, or N Runtimes (unprobed, lineage implications).** **Superseded same day by Phase 3.5c: a header probe found the tunnel stamps every forwarded MCP request with its sandbox session, so ONE attachment serves N concurrent tasks via session-keyed channels; the pool is retired, `max_concurrency` is unfrozen to an operational knob (default 10, `--max-concurrency 1` = serial), and both lanes execute it.** | Held-out eval ≈ 2.5–4 h serial at T=47; the machinery targets a 3–5× cut for seq 3, bounded by API concurrency, not code. |
| D8 | H0 viability signal | The old §13.1 discovery floor is replaced by the **B1 read**: batch results are visible by design, so if H0 lands 0/B or B/B on B1, halt and reconsider H0 before spending further generations. Not a hard floor at B=10 (2/10 is within noise of 20%). | The firewall makes a held-out floor check impossible until reveal; B1 is the legitimate window. |
| D9 | Vault & reveal | Held-out outputs (episodes, sessions, graded results, console log) live out of tree at `~/.sia_vault/experiment_<id>/generation_NNN/`. `make reveal` — runnable only when the final generation is tagged — copies the vault into `results/experiment_<id>/held_out/`, computes the matrices, and writes `summary.md`. Until then the orchestrator does not read the vault (procedural, stated in every writeup). | Out-of-tree keeps held-out data away from glob/grep sweeps and the dashboard walk; the dashboard renders held-out views only from revealed artifacts. |
| D10 | Debug-experiment sizing | **Decided 2026-08-13 (user-delegated adjudication, criterion: probability of SHOWING a real generation-after-generation improvement): G=3, B=4, T=8** — superseding D3's G=3/B=3/T=5 debug values; executed mechanically at the Phase 4 freeze (re-propose the partition, set the lock's protocol block and concurrency default). The deciding mechanism is held-out REPRESENTATION: a mutation fixes one failure mode, and the curve can only move if the fixed mode has a witness in T — for a mode afflicting ~10 of the 97 pool tasks, P(≥1 witness) ≈ 43% at T=5 vs ≈ 60% at T=8, so at T=5 most single-mechanism fixes are more likely than not INVISIBLE to the curve regardless of being real. Second: headroom — at H0 ≈ 40% pass, T=5 expects 2/5 passed leaving 3 tasks of room and a live floor/ceiling risk; T=8 expects ~3/8 with ~5 of room. Third: churn dilution — a mid-p task flips between identity-harness measurements with near-coin-flip probability (measured: 6/10 vs 4/10 on one frozen config), so per-transition churn is ~1–2 tasks at either size and only task COUNT separates stable per-task flips (signal) from flip-flops (noise); the 8×4 matrix carries that separation, the 5×4 cannot. The anchor fact: the held-out set is ONE fixed list of T tasks, measured identically at every generation H_0..H_G (frozen in `split_manifest.yaml`, inside the freeze fingerprint; `reveal.py` refuses a measurement on any other task set) — that fixedness is the entire comparability of the curve and matrix. The batches are the opposite by design: G disjoint sets, one consumed per generation, never reused (protocol §13 fresh-evidence rule). Why T=8 over T=5: one task = 12.5 pp instead of 20 pp, binomial band ≈ ±17 pp instead of ±22 pp — a 2-task gain reads as directional at T=8 and drowns at T=5 — and the task×generation matrix grows to 8 rows × 4 measurements, showing per-task flips (gains/regressions/retention) even where the aggregate stays inside the band. Why B=4: prevalence quotes in quarters (2/4 beats 1/3), a slightly stronger D8 viability read, one extra evidence episode per generation. Operational concurrency (deliberately NOT part of this decision — the lock default stays 10 and rounds self-cap at their episode count): held-out rounds run 8-wide on the local lane, which has no sandbox constraint; batch rounds take `--max-concurrency 2` from the `make batch` target to match the org's observed ~2-sandbox quota, because queued tasks behind a long episode churn through τ retries and a diagnosis round must not carry that noise. Honest caveat, stated wherever the debug curve renders: even T=8 resolves only ≥2-task effects; the debug experiment demonstrates the loop and a directional curve — the T=47 full run carries the claim. Cost delta ≈ +$3–6 (32 local + 12 platform episodes vs 20+9); (G×B)+T = 20 ≤ 97. | Debug compute at N=4 ≈ 1–2 h (vs 4–6 h serial); the matrix/curve becomes worth looking at, which is the user's stated goal for the debug run. |

------------------------------------------------------------------------

## 3. Protocol → repo mapping

| Protocol concept | Repo realization |
|---|---|
| Experiment config (§26) | `protocol:` block in `benchmark_lock.yaml` (`generations`, `improvement_tasks_per_generation`, `held_out_tasks`, `allow_within_batch_verification: false`, `holdout_visibility` flags, `require_human_approval: true`). Inside the freeze fingerprint automatically via `lock.raw`. `held_out_trials_per_task` ≡ `frozen.num_trials` (one knob). |
| Partition (§3, §16) | `benchmark/split_manifest.yaml` rewritten: `batches: {batch_01: […], …}` + `held_out: […]`, sizes derived from the lock's `protocol:` block. Same stratification machinery (reward_basis 88 DB / 9 ACTION, dominant doc category, doc count; stride scheduler), disjointness verified dynamically across G+1 partitions, (G×B)+T ≤ 97 enforced, ACTION spread re-expressed (held-out gets its proportional share ≥4 at T=47; batches jointly cover the rest). |
| Improvement batch run (§7) | `make batch B=1 GEN=generation_000` — platform lane forced, resume-friendly (no `--overwrite`), round dir `generation_NNN/batch_NN/`, manifest `split: batch_NN`, labels `[exp_00N:…] τ²-bench banking_knowledge task_X trial 0 gen_NNN bNN - …`. Convention enforced by the runner (2026-08-13): batch_NN is *run by* H\_(NN−1), so it lives under `generation_(NN-1)/` — the wrong GEN is refused pre-spend. Graded output persists to `batch_NN/graded/`. |
| Held-out evaluation (§6, §11) | `make heldout GEN=generation_001` → `scripts/run_heldout.py`: local lane forced, all child stdout/stderr redirected into the vault's `console.log`, grading persisted to the vault (never printed), prints **completeness only** (episodes expected/completed, manifest joined, zero reward tokens — asserted by test). |
| Firewall (§12) | D1 + D9. Platform: structural (no evidence exists). Local artifacts: procedural + out-of-tree + muted output. |
| Diagnosis (§8) | `operate` skill over the batch's platform conversations: task rows → conversations → tool calls/spans; prevalence via `metrics query`; observations/patterns after the ~40-min window (fallback: metrics-over-spans + manual clustering, evidence tier stated). |
| Proposal (§9) | `improve` skill: one coherent mechanism inside the mutable table → branch `gen-NNN/<slug>` → PR citing conversation ids + prevalence + predicted effect. |
| Approval → generation (§10) | Human reviews/merges the PR on `main`; merge commit tagged `exp<seq>-g<NNN>`; `improvement_records/gen_<g>_to_<g+1>.yaml` written (schema: `contract/improvement_record.schema.yaml`, §24 fields; `held_out_result` filled at reveal only). |
| Metrics & artifacts (§18–§21, §27) | `make reveal` → `results/experiment_<id>/held_out/{results_by_generation.csv, task_generation_matrix.csv, transitions.csv, retention.csv}` (gains/regressions/retained/unresolved per transition and currently- vs ever-solved are machine-readable, not summary-only), plus `summary.md` with counts + percentages + the D2 noise band. §27's `config.yaml` is satisfied by `experiment.yaml` (lock+manifest fingerprint snapshot) plus value-copies of `benchmark_lock.yaml` and `split_manifest.yaml` written beside it at snapshot creation, so a results directory describes its own configuration. The dashboard renders the progression view from exactly these revealed artifacts (curve with noise-band whiskers + carried markers, retention line, transitions table, binary matrix) and shows a sealed notice pre-reveal. |
| Guardrail 10 (§29) | Unchanged from today: the adapter never repairs the agent (`contract/constraints.md`), integration code stays task-agnostic, `introspection check` in pre-commit/CI/runner. |

------------------------------------------------------------------------

## 4. Repo delta

### Remove (retire; git history keeps everything) — executed at Phase 0.5, ahead of schedule

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

### Phase 0.5 — Spring cleaning (user-directed 2026-08-13, pulls the Remove list forward)

Scope change ratified by the user: purge superseded machinery, concepts, and documents
now rather than phase-by-phase, so Phases 1+ build on a codebase that speaks only the
current design.

- [x] Retired machinery removed: `checkpoint`/`discovery`/`validation` targets and their
      runner paths (`--split`, `--checkpoint`, `RUNNABLE_SPLITS`), ARM/paired-arm naming,
      `anchor_stock` + `run_stock_anchor.py`, `fidelity_gate` + `--gate`/`--verdict-out`
      + `fidelity_task_set`, the manifest/`run_metadata` `checkpoint` field (2026-08-13).
- [x] Fidelity narrowed further than D4 (user-directed): the cross-lane *statistical*
      layer (Wilson intervals, `within_noise`, aggregate-agreement judgment) removed;
      `benchmark/fidelity/` survives as the per-episode adapter-invariant diagnostic
      plus factual counts — the seam guard, not a comparability instrument (2026-08-13).
- [x] Dashboard trimmed: pass^k plumbing removed (pass¹ + interval stay), split grouping
      made data-driven (no hardcoded taxonomy), verified live against the archived
      experiment-001 data (2026-08-13).
- [x] Superseded documents deleted: `PLAN.md`, both MVP guides; every dangling `v1 §`/
      `v2 §`/`PLAN.md` citation in code comments, the lock, `CLAUDE.md`, and
      `contract/constraints.md` rewritten as self-contained statements; constraints'
      corrections section reframed standalone; the protocol spec's pandoc artifacts
      cleaned (16 sites, wording untouched) (2026-08-13).
- [x] Lint debt cleared: 32 pre-existing ruff violations → 0 (misplaced noqas, import
      order, `datetime.UTC`, `contextlib.suppress`, `zip(strict=True)`, script exec
      bits); formatter clean (2026-08-13).
- [x] Contract reviewed at user request: both files necessary — `constraints.md` is the
      enforced permission envelope, `protocol.md` the procedure's durable home (written
      at Phase 4); both now clean of superseded references (2026-08-13).

Deliberately untouched: lock *values* and the split manifest (frozen for closed
experiment 001 — the freeze fingerprint was asserted byte-identical after comment edits);
`split.py`/`propose_split.py` partition semantics (Phase 1's rewrite surface, marked as
such in the module docstring); runner batch/held-out modes (Phase 2); seam internals
(bridge/transports — proven, no churn).

**Validate:** full suite green post-trim; `make check` green; ruff + format clean;
freeze fingerprint unchanged; dashboard serves archived data with zero pass^k residue;
stale-term grep sweep clean. ✅ (2026-08-13)

### Phase 1 — Partition & configuration machinery (no live runs)

- [x] `protocol:` block in the lock + `lock.py` accessors + validation — unknown keys
      refused, `held_out_trials_per_task` refused by name (the knob is
      `frozen.num_trials`) (2026-08-13).
- [x] `split.py` dynamic partitions (propose/verify/render for G batches + held-out);
      ACTION-spread rule re-expressed as scale-aware proportional floors (⌊n·T/N⌋ for
      held-out, ⌊n·G·B/N⌋ jointly for batches); `propose_split.py` CLI updated with
      `--manifest` + per-size overrides for pre-freeze sizing (2026-08-13).
- [x] Tests: partition proposal determinism, disjointness, budget check, ACTION
      spread, manifest round-trip, lock protocol-block validation, fingerprint drift
      on partition change (2026-08-13).

**Validate:** unit tests green; against real task data, `propose_split.py --write`
produces a verifiable G=5/B=10/T=47 manifest **and** a G=3/B=3/T=5 manifest
(debug-sized), both passing `--verify`; the old 30/15/20 manifest is refused loudly.
✅ (2026-08-13) Suite 114 → 147, all green; `make check` green; ruff + format clean.
Real-data checks: the full-scale proposal lands 1 ACTION task in every batch and 4 in
held-out (its exact ⌊9·47/97⌋ share) with 0 tasks unused; the committed debug manifest
passes `--verify`; the legacy manifest exits 1 naming the retired scheme. Intake
decision (user-ratified): experiment 002 opened PROVISIONAL in this phase — `seq: 2`,
debug `protocol:` values, `num_trials: 1` (D2), version-2 debug manifest committed —
so Phases 2–3 run in a real experiment context; Phase 4 finalizes the values and flips
the lock to FROZEN. The 001 archive, snapshot fingerprint, and git-history record are
untouched.

### Phase 2 — Runner, firewall, and round targets

- [x] `run.py --batch` / `--heldout` with lane forcing (D1, resolved in
      `tau_adapter/rounds.py` before any spend: wrong lane refused, task selection
      from the frozen manifest only, partition re-verified, held-out `--overwrite`
      refused — measured once) + in-process reward muting; `Makefile` `batch` /
      `heldout` targets (old round targets were retired at Phase 0.5) (2026-08-13).
- [x] `scripts/run_heldout.py` + `tau_adapter/heldout.py`: vault layout
      (`~/.sia_vault`, `SIA_VAULT_DIR` override), full-redirect console log, three
      idempotent stages (run → quiet grade → report), completeness-only status with
      reward-free seam-incident totals (2026-08-13).
- [x] `grade.py` quiet + persist mode — fd-level silence (rich resolves stdout late
      but loguru pins stderr at import); `--quiet` requires `--output-dir`
      (2026-08-13).
- [x] Manifest/label/`run_metadata.json` extensions (`batch_NN` / `held_out`; platform
      titles gain the `bNN` token) (2026-08-13).
- [x] Tests: the held-out muting test (fake stages spray graded figures into the
      console log; the wrapper's stdout must carry none — even the word); lane-forcing
      refusals; resume lifecycle (incl. console.log not misread as prior results).
      "Mock-domain runs of both paths" as written cannot exist — protocol rounds
      refuse `--domain` by design — so coverage is: mock smoke for the seam, injected
      fakes for the wrapper, and the live real-domain rounds below for both paths
      end to end (2026-08-13).

**Validate (live, ≈ $3):** `make smoke` both lanes; one 2-task batch-style round on
the platform lane completing with **zero timeout/stall incidents** (this is the
platform-health check that replaces A.0b's blocking role — the `7aee297` narration
fix validated in anger); one 2-task held-out round on the local lane whose terminal
output demonstrably contains no rewards and whose vault holds graded results.
Note: CI's `frozen-surfaces.yml` will warn on all of this — expected, acknowledge in
the PR.
✅ (2026-08-13) Suite 147 → 172; ruff + format clean; `make check` green. "Both
lanes" for smoke corrected: mock+platform is refused by design (locked-domain-only
platform lane), so the platform half of the live gate is the batch round itself.
Evidence: `make smoke` (local, mock) PASS, graded. `make heldout
GEN=generation_smoke` — the full 5-task held-out set, local lane — 5/5 completed,
graded artifact persisted in the vault, terminal output verbatim reward-free (the
muting working in production); one task needed 3 τ attempts (seam counters all zero
across every attempt → attributed to transient provider conditions, not
agent/benchmark/platform). `make batch B=1 GEN=generation_000` — real batch_01, 3
episodes, platform lane — 3/3 `USER_STOP`, `evidence_complete` and `arm_sha_ok` true
on every row, retitles applied, no orphans, and the stall/timeout incident class all
zero (stall_warnings, settle_timeouts, prompt_409, prompt_failures, stream_failures)
→ **platform-health check PASS**; `stream_reattaches=15` recorded as a latency
observation (designed lost-race recovery, no data loss, no grading impact). H0 read
0/3 on batch_01's tasks — visible by design, not a record (PROVISIONAL). Two fixes
landed from validation findings: fresh held-out rounds no longer record
`resumed=true`, and the completeness report now carries reward-free incident totals.
**Phase 4 pre-flight note:** bring-up artifacts cleared 2026-08-13, ahead of the
freeze (user-directed grounding pass) — vault `generation_smoke/`,
`results/experiment_002_*/` (mock_smoke + batch_01), and `.diagnostic-workspace/`
all removed; the tree carries only committed record. Rerun the partition proposal
at Phase 4 if the freeze re-decides it.

### Phase 3 — Generation lifecycle: records, reset, reveal

- [x] `contract/improvement_record.schema.yaml` (single source; `tau_adapter/records.py`
      loads it to validate) + scaffolder/verifier CLI
      (`scripts/improvement_record.py`); D5 encoded: `outcome: accepted | rejected |
      identity`, accepted requires a distinct candidate commit, rejected/identity pin
      H_(g+1)=H_g, every record cites ≥1 conversation id, `held_out_result` refused
      until reveal (2026-08-13).
- [x] `make reset_h0` (D6) + round-trip test — restore strengthened beyond D6's recipe:
      the tree is removed first, so files *committed* after the tag stage as deletions
      (the case checkout+clean both miss); `.introspection/local.json` preserved;
      mechanics proven in a scratch repository (2026-08-13).
- [x] `scripts/reveal.py` + `make reveal`: matrices, transitions, retention, summary
      with a scale-aware noise band; records stamped surgically; refusals for missing
      final tag, populated `held_out/`, broken evidence chain, unmeasured generation,
      measurement-for-identity-generation, wrong task set, multi-trial data; tests over
      synthetic vault data (2026-08-13).
- [x] Generation tagging convention documented (`exp<seq>-g<NNN>`; README §Generations
      and the vault) (2026-08-13).

**Validate:** unit tests green; a synthetic three-generation dry run (fabricated
vault + records, zero episodes) produces correct CSVs, transition tables, and
`summary.md`; reset round-trip proves byte-identical restore + passing
`introspection check`.
✅ (2026-08-13) Suite 172 → 208, ruff + format clean, `make check` green. The synthetic
dry run is the committed test battery: a fabricated G=3/T=5 experiment with H2 an
identity generation reproduces the hand-computed progression (2/5→2/5→2/5→4/5), matrix,
transitions (H0→H1: +1/−1 net 0; H2→H3: +2/−0 net +2), retention curve (ever-solved
4/5 vs currently 4/5), and an endpoint of +40 pp stated against its ±22 pp band; records
are stamped byte-preservingly. Live: the reset round-trip ran on a scratch branch of the
real repo — mutated `SYSTEM.md` + an added file, `make reset_h0`, byte-identity to
`h0-baseline` confirmed before and after committing the staged restore, `introspection
check` green, `local.json` untouched; `make reveal` on main refuses with guardrail 19,
deriving `exp2-g003` from the lock's protocol block. Zero benchmark spend.

### Phase 3.5 — Episode concurrency machinery (pre-Phase-4; no frozen-value change)

User-directed 2026-08-13 (D7 re-decision): build task/conversation concurrency —
one episode per worker — **before the debug experiment**, so seq 2 runs the new
bridge at its degenerate setting (one code path, re-proven by A.0a) and seq 3 can
freeze a real number. Engraved ethos: pragmatic (smallest mechanism that provably
prevents cross-episode result crossing), performant (measure serial vs concurrent,
report the numbers), efficient (minimal spend, minimal seam churn). Runs in its own
session; the frozen `max_concurrency` VALUE is untouched throughout.

- [x] Intake design note: per-episode URL channels chosen (mechanism A) over
      MCP-session-keyed channels, on grounds probed live against the installed MCP
      SDK 2.0.0 (parameterized route + per-request token resolution proven; B's
      episode↔session binding undeterminable at N without a handshake); platform
      docs pass found the native affordance (`dev --as` named attachments,
      fail-closed `INTROSPECTION_DEV_TARGET` routing) and it is cited, not built —
      untestable inside this phase's rules. User confirmed mechanism + ≤$3 mock
      spend. Note: `.ai-work/episode-concurrency/{DESIGN_NOTE,RESEARCH_FINDINGS}.md`
      (2026-08-13).
- [x] Bridge episode channels (common substrate) — `EpisodeChannel` at
      `/mcp/<token>` on the one run-scoped server; result-crossing minitest landed
      first (mailbox-level + live two-client HTTP); stale-result isolation for both
      the replaced run channel and closed fresh channels; per-channel stall
      attribution; identity-guarded release (late close cannot evict a successor);
      unknown/closed tokens refused loudly instead of a 300s park. Suite 208 → 216
      (2026-08-13).
- [x] `run.py` thread-safety under τ's worker pool: transports land in a
      lock-guarded log (concurrent `create_agent` appends, post-run snapshot
      reads); `launch_argv` computed once instead of mutated per factory call;
      `original_titles`, incident aggregation and the manifest pass audited as
      post-run single-threaded (reads happen only after `run_tasks` returns).
      Worker-pool contention test: 8 threads × 25 episodes on one (tool, args)
      key, zero crossings. Suite 216 → 217 (2026-08-13).
- [x] Local lane end-to-end: each episode's Pi subprocess receives its channel URL
      via `TAU_MCP_URL` (the recipe's env expansion, zero recipe changes);
      `--max-concurrency` landed diagnostic-mode-only — locked runs read the lock,
      refusal tested. Live minitest, mock domain, 10 tasks ×2 rounds: serial
      10/10 in 104.2s; N=3 10/10 in 37.2s — **2.80× speedup**; fidelity
      per-episode invariants clean on all 20 episodes (checked against the mock
      catalog — the committed instrument's tool-name check presumes the locked
      domain by design); zero seam incidents in both rounds; 10 distinct
      `pi_session_ref`s per round; per-task rewards incidentally identical
      across rounds (8/10, same two failures). Effective concurrency recorded in
      `run_metadata.json` (2026-08-13).
- [x] Platform lane, investigation-first: native affordance FOUND and documented
      (`dev --as` named attachments, N per Runtime, fail-closed
      `INTROSPECTION_DEV_TARGET` routing; per-task MCP config does not exist) —
      cited, not built, because it cannot be live-proven while the frozen value
      is 1 (diagnostic override is local-lane-only). Runner refuses platform
      N>1 pre-spend (`assert_transport_supports_concurrency`, tested); decision
      + evidence durable in `contract/constraints.md § Platform-lane
      concurrency` (2026-08-13).
- [x] Truth-pass: lock comment block rewritten (value untouched, fingerprint
      value-hashed — suite green), README §How the seam works gains the channel
      mechanism, `transport_local.py`/`run.py` comments stop naming the retired
      `reset_for_episode`, D7 row carries the landing note; `CLAUDE.md`'s
      "single episode's reward is a draw" and fidelity's docstring kept — they
      speak of reward variance, not the seam (2026-08-13).

**Validate:** full suite green (baseline 208); ruff + format clean; `make check`
green; `make gate_a0a` PASS recorded (the seam changed — the blocking gate re-proves
it); the concurrency mock round clean with the speedup stated; a serial mock round
regression-free; any locked-domain live spend gated on explicit user go/no-go
(target ≤ $2).
✅ (2026-08-13) Suite 208 → 222 (result-crossing live HTTP test, worker-pool
contention, channel lifecycle, concurrency resolution + platform-pin refusals);
ruff + format clean; `make check` green; **A.0a PASS** re-proven on the channel
bridge (`generation_000/gates/a0a.json`, 222-test suite + graded mock smoke).
Live evidence: serial mock round 10/10 in 104.2s (regression-free, zero
incidents); N=3 round 10/10 in 37.2s — **2.80× wall-clock**, fidelity per-episode
invariants clean on all 20 episodes, 10 distinct pi sessions per round. No
locked-domain spend occurred; measured mock spend ≈ $0.31 (22 episodes including
the smoke run twice, summed from the manifests) — well inside the ≤$3 approval.
Bring-up artifacts (`mock_conc_serial`,
`mock_conc_n3`, `mock_smoke`) left untracked for the Phase 4 pre-flight clear,
their numbers recorded here.

### Phase 3.5b — Platform-lane episode concurrency: the attachment pool (no frozen-value change)

User-directed 2026-08-13, superseding Phase 3.5's pin: both lanes must execute
concurrent episodes. The platform's own affordance (verified in the 3.5 docs pass:
`dev --as <name>` names an attachment, N attachments serve one Runtime,
`INTROSPECTION_DEV_TARGET` routes a task to its attachment fail-closed) gets its
consumer: N attachments, each carrying its own pinned bridge-channel URL, leased to
episodes one at a time. Same ethos as 3.5: smallest mechanism, one code path (N=1 is
a pool of one slot whose token IS today's run token — byte-identical degenerate
case), value stays freeze-decided, VALUE stays 1 in the lock except for one
temporary PROVISIONAL bump during the live proof (restored immediately after).

- [x] Bridge pinned-slot substrate: `mint_pinned_token` + `open_pinned_channel`
      (generalizing the single run channel; slot 0 = `bridge.token`); cross-slot
      result-crossing test landed FIRST; per-slot stale isolation on the run token
      AND a minted slot; unregistered pinned token refused. Suite 222 → 224
      (2026-08-13).
- [x] Attachment pool (`dev_lane.py`): `dev --as` in the launch vector with the
      parsed-dev-target assertion (mismatch refused at startup — routing is
      fail-closed on the exact name); `AttachmentSlot`/`AttachmentPool`; all five
      premortem tests landed — double-release cannot re-queue, exhaustion blocks
      then fails loudly, dead attachment refused and retired at lease,
      nonce-suffixed names, idempotent stop — plus slot-0-rides-the-run-token and
      distinct-URL-per-slot on a started pool. Suite 224 → 232 (2026-08-13).
- [x] Runner wiring: pool of size `max_concurrency`; lease in `create_agent`;
      release on `PlatformTransport.close()` exactly once, proven also under CLI
      failure (a leaked lease starves the pool); per-slot concurrent warm-up; the
      3.5 pin refusal removed and `contract/constraints.md § Platform-lane
      concurrency` rewritten to the built mechanism in the same commit;
      attachments in banner + `run_metadata.json`; teardown transports → pool →
      bridge. Suite 232 → 233 (2026-08-13).
- [x] Live proof (locked domain, --allow-dirty, temp PROVISIONAL value 2) — ran
      2026-08-13 and **failed with a first-class finding, spending ~$0**: the
      platform accepts ONE live dev attachment per Runtime. The second `dev --as`
      attachment was refused server-side (`dev_slot_conflict: this Runtime is
      already connected by 'tau-w00-021d'`, ~70s of retries, then timeout); the
      pool's fail-closed startup stopped every attachment before any task
      existed. No plugin doc states this cardinality — the `--as` help describes
      named routing, not attachment multiplicity. Recorded verbatim in
      `contract/constraints.md § Platform-lane concurrency`; the pre-spend
      refusal returned, now citing the observation; lock value restored to 1 the
      same day. The pool machinery stays — it serves N with no code change if
      the upstream cap lifts (or a future decision runs N Runtimes — unprobed,
      real lineage implications). Replacement validation: a pool-of-1 locked
      platform episode through the full refactored path (lease → slot dev-target
      routing → pinned channel → release-on-close), result below: 1 locked
      episode completed and graded through the pool (USER_STOP, 32 messages,
      142s, `evidence_complete=true`), attachment `tau-w00-eae7` with matching
      dev target (the `--as` assertion held live), zero seam-health incidents
      (`stream_reattaches=1` is the designed lost-race recovery), no orphans,
      retitle applied, `arm_sha_ok=false` as declared (--allow-dirty, unpushed
      HEAD). Total 3.5b live spend ≈ $0.4 (2026-08-13).
- [x] Truth-pass: `contract/constraints.md § Platform-lane concurrency` rewritten
      twice — pin → pool at the wiring commit, then pool + the observed
      one-dev-slot-per-Runtime cap with the verbatim conflict after the proof;
      lock comment block tells the observed truth; README seam paragraph;
      D7 row carries both re-decisions and the finding (2026-08-13).
- [x] Close: suite 234 green, ruff + format clean, `make check` green,
      `make gate_a0a` PASS re-recorded on the pool bridge
      (`generation_000/gates/a0a.json`, 234-test suite + graded mock smoke).
      Net for the experiment: the local lane — ~85% of wall-clock — executes
      the frozen `max_concurrency` in full (2.80× measured at N=3); platform
      rounds stay serial by the observed upstream cap, with the pool ready the
      day it lifts (2026-08-13).

### Phase 3.5c — Session-keyed platform concurrency; the knob unfrozen

User-directed 2026-08-13, superseding 3.5b's pin: concurrency must work on both
lanes unconditionally, serial execution becomes the operator's explicit
`--max-concurrency 1`, and the `dev_slot_conflict` cap must be solved, proven by a
platform round with ≥2 tasks genuinely in parallel.

- [x] `max_concurrency` unfrozen (user re-decision): parallelism moves wall-clock,
      never what the agent can do inside an episode, so it leaves the frozen-budget
      doctrine — lock default 10, any round type may override in either direction,
      effective value recorded in `run_metadata.json`; `CLAUDE.md`'s frozen list
      updated (2026-08-13).
- [x] Header probe (1 locked platform episode, ~$0.35 + one earlier run lost to a
      loguru lesson): the dev tunnel stamps every forwarded MCP request with
      `x-introspection-session-id`, and `tasks get` exposes the same value as
      `metadata.agent_session_id` — per-episode identity exists on the platform
      lane without any attachment multiplicity. Instrument kept:
      `TAU_BRIDGE_TRACE_HEADERS=1`, raw stderr because τ's per-task log context
      swallows loguru mid-simulation (2026-08-13).
- [x] Session-keyed channels (tests first): both lanes open a fresh channel per
      episode; the platform transport binds it to its task's session id (create
      response, else a `tasks get` poll beside the stream) and the bridge routes
      tunneled calls by session header with path-token fallback; unbound sessions
      wait a 30s grace instead of losing the race; conflicting binds fail the
      episode loudly; never-bound sessions are refused after the grace. The
      attachment pool and pinned-token machinery retired with their premise (one
      nonce-named attachment serves every task); the 3.5b platform pin removed.
      Suite 231 green (2026-08-13).
- [x] Experiment artifacts cleared from the working tree (user-directed):
      experiment_001 archive, experiment_002 bring-up runs, and the vault — all in
      git history; citation sites annotated (2026-08-13).
- [x] Platform parallel minitest (2026-08-13): 3 locked tasks through ONE
      attachment (`tau-a524`) at lock-default concurrency — **genuinely parallel**
      (overlapping windows: task_023∥task_091, task_091∥task_059), fidelity
      per-episode invariants clean on all 3 (every call answered, no orphan
      results, mapped names, graded), 3 distinct tasks/conversations, evidence
      complete on every row. 479s wall-clock, $3.04 platform-reported (task_091
      ran 112 messages — episode length, not concurrency, drives cost). One
      attempt failed mid-stream and τ retried it (1 orphan task, its sandbox
      archived): the stall + stream-failure counters attribute **entirely to the
      dead attempt** — surviving episodes carry only benign `stream_reattaches`
      (2/1/16, scaling with turns) — so the containment the channels promise held
      under real concurrency. Rows `arm_sha_ok=false` as declared. Watch the
      attempt-failure rate at Phase 4 batches; it is τ-absorbed and visible, not
      silent.
- [x] Close: constraints/README/lock/D7 truth landed alongside the mechanism;
      suite 231 green, ruff + format clean, `make check` green, `make gate_a0a`
      PASS re-recorded on the session-keyed bridge (2026-08-13).
- [x] Second pass (user-directed) — the minitest's one failed attempt diagnosed
      from its platform record: task created 01:52:55, sandbox `started_at`
      01:55:44 — **2m49s in the org's sandbox queue** (a third concurrent sandbox;
      effective plan cap ≈ 2 observed) — our stream read the silent queued run as
      dead, burned its reattach, τ retried; the orphaned attempt still ran after
      starting and burned $0.69 τ discarded. Two fixes landed (`f586941`, suite
      231 → 235, A.0a PASS re-recorded): (1) a silent stream over a task with no
      `started_at` now re-attaches within a 240s queue budget (inside τ's 300s
      turn ceiling), counted as the new `sandbox_queue_waits` incident — queueing
      is latency, not failure, and real stream deaths after start fail exactly as
      before; (2) a `bind()` racing the episode's teardown can no longer
      re-register a closed channel in the routing table (closed flag under the
      bridge lock, late binds ignored). Also recorded: `stream_reattaches` scales
      with turns under concurrency (16 on a 112-message episode) — the designed
      lost-race recovery, ~5.5s each, latency only (2026-08-13).

### Phase 4 — Debug experiment (seq 1 after the numbering reset): the real-scenario test

The capstone: everything runs for real, small. Sizing per D10 (decided and executed while
PROVISIONAL: protocol block 3/4/8, partition re-proposed and verified): 32 held-out + 12 batch episodes ≈ $11–18, compute ≈ 1–1.5 h
(held-out rounds run 8-wide on the local lane, ≈ 4–8 min each; batch rounds run at
`--max-concurrency 2` — the observed sandbox quota — ≈ 6–16 min each). The held-out set
is one fixed list of T tasks measured identically at every generation — the entire
comparability of the curve — while each generation consumes its own disjoint batch.
Same isolation rules as the full experiment (protocol §29.17). Runs on the Phase
3.5/3.5c session-keyed bridge.

- [x] Pre-flight grounding pass (user-directed 2026-08-13, its own session): three parallel
      audits (code staleness, doc truth, protocol §26/§27/§29 alignment) then the fixes.
      Docs: every stale claim corrected (serial/frozen-at-1 comments, ±7 pp hardcoded at
      T=47 → scale-aware, D1–D10, pre-reset narration in `constraints.md`, `protocol.md`
      phase table, dashboard README). Code: dead `ToolBridge.path` / `calls_served` /
      `locked_mode` param removed, stale operator-facing strings in `run.py` rewritten.
      Alignment (all tested; suite 235 → 250, A.0a-relevant surfaces re-proven by the
      suite): `max_concurrency` moved to a lock `operational:` block **excluded from the
      freeze fingerprint** (the file now matches ratified D7); held-out rounds enforce the
      in-tree freeze snapshot by experiment id, refuse a dirty recipe surface outright,
      and verify the recipe byte-identical to the measured generation's tag (h0-baseline
      for H0, `exp<seq>-gNNN` after — guardrails 12/13); every round records its
      `freeze_fingerprint` in `run_metadata.json` and `make reveal` refuses a curve that
      mixes fingerprints; improvement-record validation rejects scaffold TODO
      placeholders; batch↔generation binding enforced; batch grading persisted;
      `transitions.csv` + `retention.csv` added to the reveal; snapshot writes lock +
      manifest value-copies. Dashboard: held-out progression view landed (pulled forward
      from Phase 5) and verified against a synthetic revealed experiment. (2026-08-13)
- [ ] Freeze: `experiment.seq: 1` (numbering reset) with D10 `protocol:` values (G=3, B=4, T=8) and
      the re-proposed partition already in place; flip PROVISIONAL → FROZEN;
      `reset_h0`; commit; **A.0a gate PASS** recorded.
- [ ] H0 held-out (hidden, vault) → B1 batch → `operate` diagnosis (harvest 1
      immediately; harvest 2 after the ~40-min observation window, fallback stated)
      → `improve` PR → human review/merge → tag `exp1-g001` → H1 held-out (hidden)
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
fix and re-run Phase 4 under the next seq before scaling up.

### Phase 5 — Full experiment + reporting

- [ ] Freeze seq 2 (or next): G=5, B=10, T=47; `reset_h0`; A.0a PASS; partition
      frozen.
- [ ] Run the six held-out evaluations and five generations (~282 local + 50 platform
      episodes ≈ $75–90 compute, ~20–28 h spread over ~a week of sessions; budget
      go/no-go with the user at each generation boundary).
- [x] Dashboard progression view over revealed artifacts (held-out curve with noise
      band, task×generation heatmap, transition table) — landed early at the Phase 4
      pre-flight grounding pass, verified against a synthetic revealed experiment; the
      retired arm/learning-record plumbing was trimmed with it (2026-08-13).
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

| Item | Episodes | Cost | Wall-clock (serial) | Wall-clock (concurrent) |
|---|---|---|---|---|
| Phase 2 live checks | ~6 (mock + 2+2 real) | ≈ $3 | < 1 h | — (ran serial) |
| Debug experiment (seq 1, D10 sizes) | 32 local + 12 platform | ≈ $11–18 | ~5–8 h | **≈ 1–1.5 h** compute + review time |
| Full experiment | 282 local + 50 platform | ≈ $75–90 | ~20–28 h, ~1 week elapsed | **≈ 5–7 h** compute (held-out 6×~42 min + batches 5×~20 min), ~2–3 days elapsed |
| Endpoint reliability addendum (optional) | 376 local | ≈ $40–75 | ~25 h | ≈ 6–8 h |

Basis: measured $0.10–0.51/local episode (median ≈ $0.20) and ≈ $0.34–1.0/platform
episode (long episodes dominate cost — a 112-message episode billed ~$1). Concurrent columns
assume the lock default of 10 with rounds self-capped at their episode count: local
held-out rounds run T-wide (2.80× already measured at N=3 on the mock round);
platform batch rounds run at `--max-concurrency 2` (the `make batch` default) to
match the org's observed ~2-sandbox quota, with queueing tolerated by the runner
rather than converted into retries. Concurrency changes wall-clock only — cost is
per-episode and unchanged.

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
