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

**Done means:** a revealed experiment whose pre-registered analysis can carry the
protocol's endpoint claim. The debug-scale experiment delivered the first half — the
loop demonstrated end to end, no claim made (Phase 4, closed 2026-08-14). Phase 5 (the
powered experiment, seq 4: G=5, B=8, T=28 per D11) is sized to carry the claim; Phase 6
(full, T=47, seq 6) stays deferred unless the powered outcome argues for it.

**Where the path stands (2026-08-16):**

| Phase | Scope | Status |
|---|---|---|
| 0–0.5 | Ratify decisions; clear the bring-up record | ✅ closed |
| 1 | Partition & configuration machinery | ✅ closed |
| 2 | Runner, firewall, round targets | ✅ closed |
| 3 | Generation lifecycle: records, reset, reveal | ✅ closed |
| 3.5–3.5c | Episode concurrency, both lanes | ✅ closed |
| 4 | Debug experiment (seq 1 voided at H0 → seq 2 ran and REVEALED) | ✅ closed 2026-08-14 — loop demonstrated; endpoint −1 task, inside ±18 pp; no claim |
| 5 | Powered experiment (seq 4, D11: G=5/B=8/T=28; renumbered from seq 3 by D15) | ✅ closed 2026-08-15 — REVEALED: endpoint −2 tasks inside ±9 pp, trend p=0.802; no improvement demonstrated; machinery held (208 episodes, zero seam incidents, all twenty §29 guardrails) |
| 5.5 | Loop-reliability experiment (seq 5, D17/D18/D19: fixed batch × 3 trials, G=2 per D20) | ✅ closed 2026-08-16 — REVEALED: paired batch endpoint p=1.0000 (batch curve 4.2→8.3→0.0%), held-out endpoint +0.0 pp; against the frozen key: the meta-agent is the problem; one §29 guardrail waived (human approval, by user instruction) |
| 5.6 | **Fixed batch at depth (seq 6, D23: G=6, composite sets D22, fully autonomous)** | ✅ closed 2026-08-16 — REVEALED: primary null (p=1.0000, curve ends below baseline), secondary held-out trend z=1.77 p=0.038 on a triple-exposed set — no capability claim; machinery held (756 episodes, twenty §29 guardrails HELD or N/A, none waived); independent review + § 8 groundwork follow |
| 5.7 | **§ 8 groundwork (D24–D27): seam suppression, contract v3, instrument rules, sia + scaffold)** | ✅ closed 2026-08-16 — all 19 review-§8 items landed task-agnostically; suppression demo PASS; suite 379 green; seq-6 records validate untouched; next freeze consumes the new rules |
| 5.8 | **Stratified-batch experiment (seq 8, D28: G=6/B=8/T=28, stratified batch, mechanical reading key, autonomous, first run on the D24 seam)** | ✅ closed 2026-08-17 — REVEALED: NULL on both instruments (primary Σ=+1.333, p=0.250; held-out trend z=0.60, p=0.274). Batch curve 41.7→66.7 peak→58.3; noise floor MEASURED at 2 cells on an identical harness |
| 6 | Full experiment (T=47 scale, post-seq-10) | deferred — seq 10 runs per D34 (Phase 5.10); this phase's checklist stands for the next full-scale run |

Fast orientation: every decision with its rationale is a §2 row (the D-ledger); what each
protocol concept became in code is the §3 table; per-phase history with landing dates
is §5; the measured budget basis is §6; distilled learnings are §9.

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

## 2. Decisions (D1–D36)

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
| D10 | Debug-experiment sizing | **Decided 2026-08-13 (user-delegated adjudication, criterion: probability of SHOWING a real generation-after-generation improvement): G=3, B=4, T=8** — superseding D3's G=3/B=3/T=5 debug values; executed mechanically at the Phase 4 freeze (re-propose the partition, set the lock's protocol block and concurrency default). The deciding mechanism is held-out REPRESENTATION: a mutation fixes one failure mode, and the curve can only move if the fixed mode has a witness in T — for a mode afflicting ~10 of the 97 pool tasks, P(≥1 witness) ≈ 43% at T=5 vs ≈ 60% at T=8, so at T=5 most single-mechanism fixes are more likely than not INVISIBLE to the curve regardless of being real. Second: headroom — at H0 ≈ 40% pass, T=5 expects 2/5 passed leaving 3 tasks of room and a live floor/ceiling risk; T=8 expects ~3/8 with ~5 of room. Third: churn dilution — a mid-p task flips between identity-harness measurements with near-coin-flip probability (measured: 6/10 vs 4/10 on one frozen config), so per-transition churn is ~1–2 tasks at either size and only task COUNT separates stable per-task flips (signal) from flip-flops (noise); the 8×4 matrix carries that separation, the 5×4 cannot. The anchor fact: the held-out set is ONE fixed list of T tasks, measured identically at every generation H_0..H_G (frozen in `split_manifest.yaml`, inside the freeze fingerprint; `reveal.py` refuses a measurement on any other task set) — that fixedness is the entire comparability of the curve and matrix. The batches are the opposite by design: G disjoint sets, one consumed per generation, never reused (protocol §13 fresh-evidence rule). Why T=8 over T=5: one task = 12.5 pp instead of 20 pp, binomial band ≈ ±17 pp instead of ±22 pp — a 2-task gain reads as directional at T=8 and drowns at T=5 — and the task×generation matrix grows to 8 rows × 4 measurements, showing per-task flips (gains/regressions/retention) even where the aggregate stays inside the band. Why B=4: prevalence quotes in quarters (2/4 beats 1/3), a slightly stronger D8 viability read, one extra evidence episode per generation. Operational concurrency (deliberately NOT part of this decision — the lock default stays 10 and rounds self-cap at their episode count): held-out rounds run 8-wide on the local lane, which has no sandbox constraint; batch rounds take `--max-concurrency 2` from the `make batch` target to match the org's observed ~2-sandbox quota *(corrected 2026-08-14: no such quota exists — the pin stays, re-rationalized as bounding concurrent-start provisioning contention; see `contract/constraints.md` § Platform-lane concurrency)*, because queued tasks behind a long episode churn through τ retries and a diagnosis round must not carry that noise. Honest caveat, stated wherever the debug curve renders: even T=8 resolves only ≥2-task effects; the debug experiment demonstrates the loop and a directional curve — the T=47 full run carries the claim. Cost delta ≈ +$3–6 (32 local + 12 platform episodes vs 20+9); (G×B)+T = 20 ≤ 97. | Debug compute at N=4 ≈ 1–2 h (vs 4–6 h serial); the matrix/curve becomes worth looking at, which is the user's stated goal for the debug run. |
| D11 | Powered-experiment sizing (seq 3) | **G=5, B=8, T=28 — the POWERED tier between debug and full. Decided 2026-08-14 (user-ratified) from a Monte Carlo power analysis calibrated on seq-2 actuals: `results/experiment_002_bm25-sonnet46/SIZING_ANALYSIS.md` (analysis of record), `benchmark/scripts/power_sim.py` (instrument).** Seq 3 = powered (`003_powered-bm25-sonnet46`, lock cut PROVISIONAL 2026-08-14); the full G=5/B=10/T=47 run defers to seq 4, contingent on the powered outcome. Pre-registered before any seq-3 run: primary significance = one-sided trend test over H0…H5 at α=0.05 computed at reveal; the protocol endpoint reported with its interval and the ±9 pp band (T=28); process metrics are directional secondaries with no significance claims; fixed n, no interim looks (the vault firewall is the mechanism). Partition discipline: fresh pool — task_034 + all 20 seq-2 tasks excluded everywhere (68 of 76 eligible; `make propose_split`, header-documented), so nothing g1–g3 was tuned on and nothing the reveal exposed reappears. H0 restarts at `h0-baseline` (D6): seq-2 mutations are evidence, not inheritance. D2 single-trial held — at fixed budget, more distinct tasks beats repeated trials; the reliability addendum becomes conditional (post-reveal, only if the endpoint lands positive-but-inside-band). | Powered for a working loop (~+4–5 pp/gen, endpoint ≈ +20–26 pp): 97% direction, 94% ≥2-task visual, 82% trend-significance at α=.05. A moderate loop (+2 pp/gen) reads directional ~79%; a seq-2-like loop (≈0) is indistinguishable from null at ANY affordable T — including T=47, which adds only ~10 pp trend power for ~$80 (measured $0.62/$0.70 per local/platform episode ⇒ full ≈ $210–230, not the planned $75–90). T=28 gives a ~10-task failure mode 97%/85% odds of ≥1/≥2 held-out witnesses (vs 60%/19% at T=8) and tightens the band ±17 → ±9 pp; the eyeball bar scales to ≥4–5 tasks (null yields ≥2 tasks 29% of the time at T=28 — the debug-era "+2 reads directional" does not carry). G is the strongest lever (G=4→5 lifts trend power 0.67→0.82 at T=28; compounds mutations AND adds a curve point). B=8 is the cheapest lever on mutation quality: prevalence in eighths, and a 25%-mode shows ≥2 in-batch witnesses 63% vs 26% of the time. |
| D12 | Model pair (seq 3 re-cut) | **Both halves → `openai/gpt-5.6-luna` at medium effort: agent via the recipe (`thinking_level: medium`), user simulator via τ (`user_llm_args.reasoning_effort: medium`). Decided 2026-08-14 (user, with a colleague; motivation: inference cost). Seq 3 re-cut in place as `003_powered-bm25-luna56`** — sanctioned only because the lock is PROVISIONAL with zero episodes and no freeze snapshot; from the first snapshot on, any change bumps seq. Verified before landing: OpenAI key live (`/v1/models` HTTP 200 — the seq-1/2 "429 billing_not_active" note was stale), `gpt-5.6-luna` served by the account, `reasoning_effort: medium` accepted, `temperature: 0.0` rejected (HTTP 400, the same class as Sonnet 5's rejection) ⇒ frozen `user_llm_args` = `{reasoning_effort: medium, timeout: 60}` with temperature deliberately absent; `introspection check` green on the openai model; **mock smoke ran the full seam clean with luna on both halves** (write action 1/1, DB match, normal stop, zero judge errors). H0 anchor re-cut: `h0-baseline` re-tagged at the substitution commit, the seq-2 referent preserved as `h0-baseline-sonnet46` so historical byte-identity statements stay nameable. The live key does NOT reopen `retrieval_config: bm25` — that freeze stands on its own decision. | Consequences accepted knowingly: (a) the Sonnet-4.6 experimental-sensitivity rationale is traded for cost — if luna performs the harness behaviours natively, mutations move the score less; if H0 saturates the batches, headroom dies; the B1 read (D8) guards both directions (0/B = strengthen H0, B/B = this model choice re-opens). (b) The user-sim determinism knob is surrendered — the simulator samples at provider default; D2's task-pooling absorbs the added stochasticity, and the seq-2 user-sim screen is model-conditioned evidence, so the screen re-runs at the start gate (task_034 exclusion kept regardless). (c) D11's G/B/T carries over as a prior — its calibration facts (baseline ≈32%, $0.62/$0.70 per episode, the difficulty mixture) are Sonnet-pair measurements and re-price at H0/B1; the platform lane's managed runtime serving luna is verified at the first batch episode. |
| D13 | Interim model pair (seq 3 re-cut again) | **Both halves → `anthropic/claude-haiku-4-5`, agent `thinking_level: medium` explicit, user-sim `user_llm_args: {temperature: 0.0, timeout: 60}`. Decided 2026-08-14 (user) while the platform sandbox's OpenAI serializer defect blocks every `openai/*` model unconditionally** (it emits the retired `reasoning.level` parameter, explicit thinking level or not — evidence chain in `.ai-state/UPSTREAM_ISSUES.md`, incl. the clean Anthropic control episode). Seq 3 re-cut in place as `003_powered-bm25-haiku45` (PROVISIONAL, zero enforced episodes — same sanction as D12); the luna directory stays as the archived D12 preparation. **D12's luna pair remains the intended configuration and returns via its own re-cut + pilot when the platform fix ships.** The switch restores what luna surrendered: `claude-haiku-4-5` accepts `temperature: 0.0` (verified), so the user-sim determinism knob is back per τ's own doctrine — and since Anthropic rejects temp 0.0 with extended thinking enabled (verified), the simulator carries no thinking argument: determinism for the environment, medium thinking for the agent under test. `reasoning_effort` (OpenAI-shaped) leaves the lock with luna. | Haiku pilot (n=28 non-partition tasks, $6.22 — `results/experiment_003_powered-bm25-haiku45/CALIBRATION_PILOT.md`): baseline **3/28 = 10.7%** (Wilson 4–27%) — a weak-H0 regime: no saturation risk, but P(0/8 batch read) ≈ 0.40, so D8 fires routinely and diagnoses lean on near-miss profiles (seq 2's fallback becomes the norm); "H0 must show basic competence" is the live caveat, guarded by the B1 read. Power re-checked at the measured regime: lower baseline shrinks binomial variance, so **G=5/B=8/T=28 is confirmed and slightly better-powered** (optimistic: 0.97 direction / 0.86 trend@.05); partition unchanged. Costs: $0.283/local episode ⇒ powered ≈ $55–65 (between luna ~$15 and Sonnet ~$150). Local smoke green (reward 1.0, zero judge errors); platform control graded clean at $0.218/episode. |
| D14 | Model pair (luna restored) | **Both halves back to `openai/gpt-5.6-luna` per D13's return clause, decided 2026-08-15 after the platform shipped the sandbox serializer fix** (verified against a freshly built runtime image — the first episode's span shows `reasoning.effort`, not the retired `reasoning.level`; evidence in `.ai-state/UPSTREAM_ISSUES.md`). Re-cut in place as `003_powered-bm25-luna56` under the same PROVISIONAL sanction. The recipe adopts the modern `ai:` spelling (cloud validator 0.3.0; local toolchain since CLI 0.27.1) and deliberately omits `thinking_level` — the lock asserts the absence, the sandbox's injected default (medium) is the effective level. User sim: `reasoning_effort: medium`, no temperature (luna rejects 0.0; D2's pooling absorbs the stochasticity). | Verified end to end 2026-08-15: local smoke and pilot green (baseline 7/28 = 25%, $0.038/local episode — `CALIBRATION_PILOT.md`, the calibration of record), platform episode graded reward 1.0 at $0.0157/episode, zero seam incidents. The D13 haiku detour is archived at `results/experiment_003_powered-bm25-haiku45/` with its own pilot and the 20M-prompt-bytes/hour org-cap caveat. |
| D15 | Experiment-id parity convention (powered → seq 4) | **Decided 2026-08-15 (user): EVEN seqs are stable, reportable experiments; ODD seqs are experimentation — bring-up, detours, voided freezes. The powered experiment renumbers seq 3 → seq 4 (`004_powered-bm25-luna56`); the full T=47 run defers to seq 6.** Sanctioned by the PROVISIONAL re-cut rule (no freeze snapshot, zero enforced episodes under the new id). The history already fits: 1 = voided debug freeze, 2 = debug run (revealed), 3 = powered bring-up (D12–D14 detours, calibration pilots, mock smoke, the 4-wide concurrency validation), whose directories stay in place as the archive — evidence paths are never rewritten. Parity layers on the freeze discipline and never replaces it: a re-decide still bumps seq, to the next number of the right parity, so a voided even experiment bumps to the next even with its diagnosis landing in the odd between (exactly the 1→2 pattern). | Consequence accepted: deliberate gaps in the id sequence. Benefit: the id itself says whether a results/ directory carries a reportable number, mechanizing "no result here is a result yet" for readers and agents. |
| D16 | H0 anchor correction (seq-2 contamination caught before the start gate) | **User-caught 2026-08-15, executed same day: the `h0-baseline` tag had drifted through the D12/D14 re-tags onto main-tip commits (`2ea2475`, then `e4a8677`) whose SYSTEM.md carried all three seq-2 mutations (`3f5f91a` gen-001, `7fb5353` gen-002, `b6b99eb` gen-003 — +30 lines of KB-verification, entity-selection and procedure-completion instructions), so `make reset_h0` would have faithfully restored seq-2 inheritance as the powered H0 — precisely what D6 forbids (seq-2 mutations are evidence, not inheritance).** Corrected: SYSTEM.md reverted byte-identical to `h0-baseline-sonnet46`'s (empty diff, frozen policy region still matches the lock); `agents/agent.yaml` (`ai:` luna block) and the runtime manifest stay current — the sanctioned per-experiment surface; `h0-baseline` re-tagged (annotated) at the restore commit; `make reset_h0` then verifies "staged nothing — the recipe already was H0". Principle now explicit: **a new experiment's H0 is the ORIGINAL harness plus only the sanctioned model/config block; the tag moves only to commits satisfying that identity.** | Casualty handled: the D12 luna pilot ran on the contaminated harness (its own doc names arm `2ea2475` as "exactly luna-H0" — it was H0+g1–g3), so its baseline 7/28 = 25% mislabels H0; the pilot re-ran on corrected H0 with results recorded at `results/experiment_004_powered-bm25-luna56/CALIBRATION_PILOT.md`, which supersedes the 003 pilot as calibration of record (the 003 doc stays sealed, relabelled by this row, not rewritten). |
| D17 | Fixed batch mode — the loop-reliability experiment (seq 5) | **User-directed 2026-08-15, after the seq-4 reveal left two explanations standing ("the mutations did nothing" vs "the measurement could not see it"): seq 5 runs `protocol.batch_mode: fixed` — ONE hand-chosen batch task set measured under every generation, H5 included (batch_06 is H5's measurement-only endpoint round, consumed by no transition), so the batch curve becomes a PAIRED saturation curve asking the prerequisite question directly: can the improvement loop fix what it stares at?** This is deliberate intervention verification — `allow_within_batch_verification` flips true, and the lock refuses the contradictory combination. The fixed 8 are known-fail tasks from seq-4 batches covering the recurring modes (task_014, 026, 028, 065, 070, 072, 082, 096 — manifest header carries the per-task rationale). Pre-registered primary: `scripts/batch_curve.py`'s one-sided EXACT paired sign-flip permutation test on per-task rate deltas, H5 vs H0, α=0.05 (2^8 enumeration, no approximation); interim invocations are descriptive only. Pre-registered reading key: B↑T↑ = loop works and generalizes; B↑T→ = loop optimizes but overfits (mutations task-shaped); B→ = the meta-agent is the problem. Seq 5 is deliberately ODD per D15 — it studies the loop, not the capability claim. Mechanism is config-driven (`fixed`\|`fresh`), fresh preserving the original design byte-for-byte. | Consequences accepted knowingly: (a) batch reads stop being generalization evidence entirely — they are the training curve, and every diagnosis note must say so; (b) §29 guardrail 2 (batches pairwise disjoint) is modified by design for this experiment and the guardrail walk must mark it; (c) prevalence quotes from B2 on measure a tuned-on set. |
| D18 | `num_trials: 3` on every round (revises D2's value, keeps its structure) | **One knob (frozen.num_trials) governs trials on batches and held-out alike — D2's "one knob, never two" survives; only the value changes, 1 → 3.** D2 chose single-trial because trials were unaffordable at Sonnet prices; seq 4 then paid D2's stated cost in full — every cell a coin flip, the whole curve consistent with single-trial sampling noise. At luna's measured ~$0.022/local episode the objection is gone (~$19 for all six held-out rounds at T=28×3). Per-task cells become pass RATES: the noise band tightens ±9 → ±5 pp at T=28; a batch task at 1/3 hands diagnosis a passing AND a failing transcript of the same harness on the same task; cross-generation flips become attributable. The aggregate stays the mean per-task rate — the same quantity seq 4 estimated. pass^k stays banned for generations (guardrail 15); within-generation pass@3/pass^3 are legitimate per-task reliability texture. Reveal machinery is rate-native with EXACT reduction to the binary artifacts at one trial (all 24 pre-existing reveal tests pass unchanged). | Bonus identity: seq-5's H0 held-out round (28 tasks × 3 trials of the same corrected-H0 commit) IS the reliability study's H0 arm — comparing it against seq-4's single-trial 6/28 quantifies the coin-flip noise directly, at no extra cost. |
| D19 | Seq-5 partition: pool exhausted, T reused, firewall caveat recorded | **The pool holds zero virgin tasks (97 − 1 crasher − 20 seq-2 − 68 seq-4 − 8 pilot), so seq 5 CANNOT have a fresh partition; the held-out set reuses seq-4's T=28 EXACTLY.** Chosen over a re-draw because every alternative is equally exposed and identity buys direct comparability (the D18 bonus). Recorded caveat, stated rather than hidden: the orchestrator has SEEN seq-4's revealed per-task results for these 28 tasks, so seq-5's firewall is weaker than seq-4's — seq-5's own results stay sealed until reveal, but prior exposure exists. Acceptable precisely because seq 5 is an odd-seq loop-mechanics experiment whose PRIMARY is the batch curve; the held-out lane is the transfer probe, and any T-based claim must carry this caveat. The user-sim screen is NOT re-run: the model pair is unchanged from seq 4 and the 2026-08-15 luna screen (97/97) is current — screening evidence is model-conditioned (D12/D13) and the condition holds. | The batch side reuses seq-4 batch tasks too (known-fail selection) — harmless by construction: batch evidence is fully observable, and choosing tasks the loop already diagnosed is the point of a saturation test. |
| D20 | Seq-5 scale reduction: G = 5 → 2 | **User-authorized 2026-08-15, before any seq-5 episode: `protocol.generations` 5 → 2, re-cut in place under the PROVISIONAL sanction (zero episodes, no freeze snapshot). B=8 and T=28 are UNCHANGED — only the number of mutation slots moves.** Two transitions (H0→H1→H2) plus the measurement-only endpoint round, which becomes `batch_03` run by H2 and consumed by no transition (was `batch_06`/H5). Rounds: 3 held-out (H0, H1, H2) × 28 × 3 trials = 252 local episodes; 3 batch rounds × 8 × 3 = 72 platform episodes — ~40% of the G=5 episode cost. Dependent consequence, executed with the row: the frozen partition manifest drops `batch_04`–`batch_06` (byte-identical copies of `batch_01` under `batch_mode: fixed`, so NO task set changed and no episode existed); `splitmod.verify` derives the expected batch names from `protocol.generations` and refuses every round — batch and held-out alike — while manifest and lock disagree, so the trim is mandatory, not cosmetic. `--verify` re-passes. | Cost accepted knowingly and stated wherever the seq-5 curve renders: **G is the strongest power lever (D11)**, so the held-out trend test runs over 3 measured points instead of 6 and is underpowered by construction — the held-out lane was already only the transfer probe here (D19), and it now carries two caveats, not one (prior exposure + 3-point trend). The pre-registered PRIMARY is untouched: `batch_curve.py`'s one-sided exact paired sign-flip test on the endpoint pair, now **H2 vs H0**, α=0.05, 2^8 enumeration — its power depends on B and `num_trials`, neither of which moved. Two slots still exercise every loop mechanic end to end (recall → diagnose → mutate → PR → tag → re-measure the same batch), which is what a loop-reliability experiment is for; what two slots CANNOT show is compounding across many generations, and the seq-4 finding that motivated seq 5 (four of five slots spent on one instruction paragraph) is correspondingly harder to reproduce or refute at G=2. |
| D21 | Experiment isolation made mechanical | **Decided 2026-08-15 (user): anything preventing experiment isolation is a defect to fix, not a discipline to maintain. Two enforcement gaps closed.** (1) `benchmark/scripts/check_partition_isolation.py`, wired into `make check` (pre-commit + CI): compares the frozen partition against every prior experiment's committed `results/experiment_*/split_manifest.yaml` and exits non-zero on UNDECLARED reuse. Four kinds, ranked by what the orchestrator could have learned — `held_out_from_held_out` (worst: if the prior revealed, its per-task results are known), `held_out_from_batch`, `batch_from_held_out`, and `batch_from_batch` (reported, never blocking — observable in both, and under `batch_mode: fixed` it is the design). Severity turns on two facts read off the results tree rather than assumed: whether the prior REVEALED (`held_out/` exists) and whether it was ever SPENT (a `generation_*/batch_*/` round ran). Seq 1 froze a partition and died at H0, so its tasks were named but never looked at; demanding a declaration for those would train the operator to wave the check through. Declarations live in `benchmark/partition_reuse.yaml`, deliberately OUTSIDE the freeze fingerprint (it describes history, not configuration, and a fingerprinted key added mid-experiment would invalidate a running freeze); an entry without a `reason` is ignored, so silencing costs the same keystrokes as explaining. Seq 5's D19 reuse is now declared rather than commented. (2) `records.py` cross-checks every cited `conversation_id` against this experiment's own `episode_manifest.jsonl` files — a record citing a prior experiment's conversation previously passed validation, and the failure is silent because a borrowed id looks exactly like a real one. Amended 2026-08-16: no-manifests-yet is a hard FAIL, not a skip — by validation time the ids are real-looking (the scaffold's TODO fails earlier), and before any round there is nowhere legitimate they can have come from; "cannot verify" must never pass as "verified". | What is now enforced vs merely procedural: partition reuse and record evidence provenance are MECHANICAL; the remaining isolation rules — never reading another experiment's vault, keeping prior experiments to labelled prose context — stay procedural, because they govern reading rather than artifacts and no artifact records them. Measured on the live repo: seq 5 reuses **28/28** of seq 4's held-out set and **8/8** of its batch tasks, both deliberate, now both declared. The checker cannot create virgin tasks — a 97-task pool exhausted by four experiments is a structural limit, and the honest response is a declared caveat, not a green check. |
| D22 | Composite improvement sets: the generation is the unit of measurement, the change is the unit of diagnosis | **User-directed 2026-08-16, from seq 6: a generation's mutation is an improvement SET — any number of changes across the full mutable recipe surface (`SYSTEM.md` instructions, Pi skills, extension tools, sub-agents, retrieval usage), composed by the orchestrator from the diagnosed batch and landed as one branch / one commit per change / one PR / one tag.** Replaces the one-mutation-per-generation rule (whose seq-2-era rationale was per-change statistical attribution) on the evidence of seq 4 + seq 5: seven slots produced six `SYSTEM.md`-text mutations, four of which failed the same way (an instruction does not inherit the scope its author reasoned about), while the recipe's growth surfaces went unused — the serialization starved the loop of expressiveness before attribution ever mattered, and both closures name that as the live hypothesis. The CLI `improve` skill's discipline is retained PER CHANGE (one coherent mechanism each, own evidence, own owning layer, own falsifiable prediction, own risk) and its own text sanctions the shape ("one coherent change … unless the approved plan explicitly separates independent fixes"). Composition rules live in `contract/protocol.md` step 4: each change independently justified; no two changes interacting on one behavior; growth surfaces first-class with a stated reason required when a set stays prompt-only after ≥3 prior prompt mutations; reverts of refuted changes are first-class changes. Records: schema v2 adds a per-change `changes` list (`records.py` requires it for landed/declined v2 records; seq ≤5 records validate untouched under the old rules). | Attribution is the accepted trade, stated wherever a curve renders: a generation's delta measures the SET, and no statistical claim about an individual change is available — per-change attribution is mechanistic only (each change's pre-registered prediction scored against the next batch's per-task evidence; `batch_mode: fixed` makes those reads strongest). The goal moves accordingly: the loop is judged on whether the next generation GENERALIZES (held-out, and batch under fresh mode), not on naming which change carried it. Risks accepted knowingly: a bad change can hide inside a good set (recourse: per-change commits + revert-as-change next generation); set size is bounded by evidence and non-interaction, never by a number; the human gate is unchanged — one PR, per-change opt-in/out at step 4, user merges. Decided ahead of its first run (protocol.md notes this against the written-from-what-ran doctrine); seq 6's first transition trues it up. |
| D23 | Seq 6: the loop-reliability design at depth, with composite sets and a fully autonomous loop | **User-directed 2026-08-16, frozen the same day as `006_fixedb-bm25-luna56` (EVEN seq — a reportable experiment run to completion): G=6, B=8, T=28, `batch_mode: fixed`, `num_trials: 3`, `openai/gpt-5.6-luna` on both halves, `bm25`, seed 300, every budget carried from seq 5 UNCHANGED. Exactly three things move — `protocol.generations` 2 → 6, `protocol.require_human_approval` true → **false**, and the operational concurrency defaults (lock 8 → 3, `make batch` 4 → 3, both outside the freeze fingerprint).** The design question is seq 5's own recorded limitation: "what two slots CANNOT show is compounding across many generations." Six slots, each landing a composite improvement SET (D22) with the recipe's growth surfaces first-class, is the direct test — and the mutation shape is the live hypothesis both closures name, so the instrument is deliberately held constant (same partition, same models, same budgets) to make seq 6's curve read against seq 5's. No pilot precedes the freeze: seq 5's calibration is current and no measured surface changed. **Autonomy, and its limits.** The user delegated ALL in-loop decisions to the orchestrator for this experiment: diagnose, compose each set, accept or take an identity generation, open the PR, **merge it**, tag, proceed, through the reveal — superseding, for seq 6 only, root `CLAUDE.md`'s "the agent does not merge its own work", protocol step 4's decide-with-the-user, and step 7's human gate. The deviation is *pre-registered in the freeze* (`require_human_approval: false`) rather than waived at the §29 walk after the fact — seq 5 recorded approval as "waived, not held", and a frozen false is the same fact stated in advance. Records carry `approved_by: "orchestrator — autonomous per D23 (user-delegated)"`. The delegation does NOT extend to: the frozen surfaces (a mid-run edit refuses every round), the partition, the `<policy>` block, or the held-out firewall — **autonomy is decision authority, never access** — nor to a freeze re-decision, which remains a halt-and-report. Branch protection and CI stay on; a merge the required checks reject is blocked, not overridden. **Partition:** seq 5's, verbatim in both halves, declared in `partition_reuse.yaml` against BOTH prior sources (005 and, transitively, 004 — the set has not moved since the powered experiment). Both have revealed, so the held-out lane carries a **triple-exposure** caveat every T-based number must state. **Pre-registration:** primary is `scripts/batch_curve.py`'s exact one-sided paired sign-flip endpoint test, H6's `batch_07` vs H0's `batch_01`, α=0.05, 2^8 enumeration; the reading key is seq 5's, frozen unchanged — B↑T↑ = the loop works and generalizes, B↑T→ = it optimizes but overfits, B flat/↓ = the meta-agent is the problem. Held-out H0…H6 is the transfer probe, reported with the ±5 pp band (T=28 × 3 trials) and the triple-exposure caveat; batch reads from `batch_02` on measure a tuned-on set and every diagnosis says so. | **The parity note, recorded and not relitigated:** D11 and D15 pencilled seq 6 for the full T=47 run. The user overrode that on 2026-08-16 — loop mechanics at depth outrank curve power while the loop has not been shown to improve anything at all — and the T=47 experiment defers past seq 6. Consequences accepted: (a) the held-out set is on its third experiment, so transfer evidence is the weakest instrument here and is labelled as such rather than upgraded by G; (b) six autonomous merges land on `main` without a human read of the diff, mitigated only by CI, branch protection, the frozen-surface refusals, and the per-change commit granularity that makes any of them revertible as a first-class next-generation change; (c) scale is ~756 episodes (7 × 84 local held-out + 7 × 24 platform batch), roughly $30–50 and a long unattended wall-clock at 3-wide, accepted rather than optimized — concurrency is not raised to save time. |
| D24 | Seam re-decision: Pi-local tool calls suppressed from τ | **User-directed 2026-08-16 (post-seq-6 groundwork, decided between experiments — the CLAUDE.md adapter-semantics invariant was amended to name exactly this sanctioned path): a tool call whose name is in the recipe's Pi-local registry — `agents/agent.yaml` `tools:` entries plus `agent` when `subagents:` is non-empty (`tau_adapter/pi_local.py`) — is executed by Pi and never forwarded to τ; no τ step, none of the ten `max_errors`. A name neither τ nor Pi owns still forwards as the graded invalid call it is.** Motivated by the seq-6 seam probe (an extension-tool call reached τ as an invalid call, ruling out two of three growth surfaces) and three closures naming the unused growth surfaces as the live hypothesis. Implementation: a turn-level pump in `pi_agent.generate_next_message` (never a message filter — the platform lane emits one AssistantTurn per tool call, and filtering would recreate the A.0b empty-message deadlock); narration from fully-suppressed turns rides with the next forwardable turn; a 32-turn runaway cap resumes unfiltered forwarding so a pathological harness pays its own graded cost. Evidence: `raw_data.pi_tool_names` + `raw_data.pi_suppressed_tool_names` per assistant message, manifest-derived `pi_local_calls`, registry in `run_metadata.json`; fidelity gains the `pi_local_leaks` invariant; 13 dedicated tests. Measured end-to-end post-landing (probe P6): three mock episodes called a registered `probe_note`, τ saw only its own tools, rewards 1.0, evidence intact. | The measurability objection (`constraints.md`: adapter helpfulness makes a harness unmeasurable) is answered by construction, not waived: the unmeasurable case is SILENT correction; this is declared, deterministic, registry-driven, gated, and fully logged — nothing hidden from diagnosis, only from grading, because τ budgets meter benchmark-environment interactions and Pi-local execution is harness-internal cognition. Consequence stated with the decision: results under D24 are NOT comparable to seq 4–6. H0 re-anchored at the D27 scaffold commit accordingly. |
| D25 | Instrument rules: stratified batches, fresh holdout for claims, full-quadrant reading key, fragility at reveal, process counters as prediction channels | **Decided 2026-08-16 from the seq-6 independent review (§ 8.3, 8.5–8.8), all task-agnostic.** (1) A fixed batch spans empirical strata measured under the incumbent H0 — anchors / marginals / headroom, ratio and per-task stratum in the manifest header; an all-known-fail batch is a floor by construction (seq 6: five of eight tasks at zero across 168 episodes; the endpoint test reduced to one task's variance). (2) A capability-claim freeze draws a zero-prior-exposure held-out set; declared reuse demotes the lane to a diagnostic probe. (3) The reading key becomes mechanical: `protocol.reading_key` names all nine primary × secondary cells (lock-validated, `READING_KEY_CELLS`; a cell may be declared run-voiding, never absent) — seq 6 observed B↓T↑, a cell its prose key never named. (4) Reveal emits `trend_fragility.json` (leave-one-task-out + endpoint-cell sensitivity) beside the trend test, rendered as an advisory summary sentence; backfilled into seq 6 (six load-bearing tasks; zeroing the two endpoint-only first-passes gives p = 0.121). (5) The behavioral process counters become first-class `expected_effect` targets — batch rounds now emit the same counters (`batch_process_metrics_*.csv`, both batch modes), and the domain tool names live in the lock (`operational.process_metric_tools`), not in code. | Rationale for (5), measured: seq-6's `partial_action_reward_pct` climbed near-monotonically (+4.6 pp H0→H4) while the binary pass curve round-tripped — the counters move smoothly where the rate flips coins, and mechanistic per-change attribution (D22) needs exactly that resolution. Fragility is advisory by design — it qualifies the pre-registered p-value, never replaces the test. |
| D26 | Record schema v3 + protocol steps: per-clause falsifiers, backlog write-through, surface probes, positive-obligation concentration flag, endpoint diagnosis, quote discipline | **Decided 2026-08-16 from the seq-6 independent review (§ 8.4, 8.9–8.13, 8.18). Schema v3 (additive, version-keyed; all six seq-6 v2 records validate untouched, asserted by test):** every `surface: instructions` change carries `clauses[]` — {verbatim clause from `git show`, adversarial reading, own falsifier} per disjunction/precondition/licensed alternative (the seq-6 lesson: the escape clause is what the model optimises against; C2's unwatched "or explained" carried its harm one round past the record) — and the transition must stamp `<!-- transition: gen_NNN_to_MMM -->` into the backlog, enforced at `make check` AND pre-spend in the held-out cadence gate (seq-6's backlog silently froze at gen-003 while the gated records stayed impeccable; only gated artifacts stay alive). **Protocol:** step 4b — a required-at-g0 surface probe slot (one work-tree-faithful LOCAL episode on a throwaway branch; the platform lane pins the recipe to pushed main and `--allow-dirty` runs pushed main with `arm_sha_ok=false`, measured in probe P3); the ≥3-prompt-mutations concentration flag becomes a positive obligation (next set includes a non-`instructions` change or records a probe-backed `surface_exhausted` finding — a paragraph no longer discharges it); the Close sequence diagnoses the endpoint batch round (seq 6 paid 24 episodes and read only reward bits, leaving its last prediction unscored); quoted instruction text comes from `git show`, never memory (the E2 misquote crossed three documents); the surface enum gains `extension-hook`; backlog targets carry `surfaces_considered` from open time. | The pre-freeze probe-evidence home is `benchmark/probes/<date>-<slug>/` (new convention, first campaign committed 2026-08-16: hook functional on the real domain; a DECLARED skill measurably reaches nothing on this seam's local lane with or without `read` — overturning both prior beliefs about it — so skill-shaped judgment ships via `before_agent_start` hook injection; platform lineage pinning measured). `recipe-growth.md` re-corrected against measurements and upstream (CLI 0.28.0 / Pi 0.84.1 / recipes 0.19.3): extensions declared once, `tools: []` does not gate hooks, load-failure fatal vs handler-errors swallowed, extension edits need a new dev-lane chat. |
| D27 | Growth zero-state + H0 re-anchor | **Decided 2026-08-16 (§ 8.17): `target-agent/extensions/noop-hook.ts` is committed but NOT declared in `pi.extensions` — genuinely inert (extensions have no convention discovery; agent YAML cannot gate them), so H0's runtime behavior is unchanged while the first structural mutation becomes a one-line reviewable diff against a template whose header carries the design-against semantics. `agent.yaml`'s `tools: []` comment now names its third load-bearing role (the D24 suppression registry); `skills: []` carries the measured-inert verdict and the hook-injection delivery path.** `h0-baseline` re-tagged at the scaffold commit `b76f274` (was `40687fc`, the D16 anchor — recorded here for provenance; precedent: the D16 re-tag), `make reset_h0` verified byte-identity, and a plain `make smoke` on the re-anchored H0 ran clean with an empty registry (suppression never engaged). | The zero-state changes nothing at runtime and everything about the mutation gradient: every prose mutation had sixteen predecessors, the structural surface now has a template. The next freeze's H0 is the post-scaffold recipe. |
| D28 | Seq 8: the stratified-batch experiment, autonomous, on the D24 seam | **User-directed 2026-08-16, frozen the same day as `008_stratb-bm25-luna56` (EVEN seq per D15 — a reportable experiment run to completion): G=6, B=8, T=28, `batch_mode: fixed`, `num_trials: 3`, `openai/gpt-5.6-luna` on both halves, `bm25`, seed 300, max_steps 200, max_errors 10, timeout_seconds 600, `allow_within_batch_verification: true`, all four `holdout_visibility` flags false, `require_human_approval: false`, and BOTH concurrency defaults (lock `operational.max_concurrency` 3; `make batch`'s pinned 3) carried from seq 6 UNCHANGED.** Every value in `frozen:` is seq 6's — what moves is the INSTRUMENT, plus the seam D24 changed between experiments. (1) **The batch is stratified** (D25 rule 1): 2 anchors (`task_006` 3/3, `task_032` 4/4 — the latter transfer-gold, so the batch now holds transfer-gold tasks on BOTH sides of the dial and *discrimination* is measurable rather than only rate) + 3 marginals in the 1/3–2/3 band (`task_014` 2/3, `task_057` 2/3, `task_076` 2/3) + 3 headroom whose modes a now-available structural surface can plausibly reach (`task_026` procedure/handover, `task_072` fee arithmetic and proven reachable at 2/3 under seq-6's H2, `task_096` value resolution under a 94th-percentile document load). Strata measured under the incumbent H0 by a pre-partition probe — `benchmark/probes/2026-08-16-anchor-calibration/`, 69 local episodes, $0.97 — **not** inherited from lifetime rates: seven tasks whose only prior graded attempt passed re-measured at three trials as 3/3, 3/3, 2/3, 2/3, 1/3, 0/3, 0/3, so single-trial history would have mis-picked an anchor about a third of the time. Expected H0 baseline ≈ 50% against seq 6's 8.3%; twelve cells can fall and twelve can rise. (2) **The reading key is mechanical** (D25 rule 3): `protocol.reading_key` names all nine primary × secondary cells, lock-validated — seq 6 observed a cell its prose key never named. Primary stays `scripts/batch_curve.py`'s exact paired sign-flip endpoint test (H6's `batch_07` vs H0's `batch_01`, α=0.05, 2^8 enumeration, no interim looks); secondary is the held-out trend read beside its fragility report. **Held-out: FOURTH exposure**, reused verbatim from seq 4/5/6, all three revealed, declared in `partition_reuse.yaml` against each source — under D25 rule 2 the lane is FORMALLY a diagnostic transfer probe carrying no capability claim, however clean its trend. No pilot, and the user-sim screen is not re-run (D19 precedent: the model pair is unchanged and the 2026-08-15 luna screen, 97/97, is current; `task_034` stays excluded). | **The composition deviates from the directing prompt's literal candidate list, by measurement — which is what requiring a probe is for.** `task_065` and `task_072` were named as marginals on lifetime rate (≈0.10), but both scored 0/3 under the incumbent H0, below the 1/3–2/3 band the marginal tier is *defined* by: `task_065` was dropped (its modes are carried by `task_072`/`task_096`) and `task_072` re-tiered as proven-reachable headroom, with `task_057`/`task_076` promoted into the marginal band on measured 2/3s. Also dropped: `task_028` (0/31 lifetime, a near-duplicate of `task_026`'s mode — two zero-range tasks for one mode is the seq-5/6 mistake at smaller scale), `task_070` (retired in seq 6 as bounded by the frozen `bm25` backend), `task_082` (0/31, no structural mechanism nameable, which D25 requires). Every drop and its reason is in `benchmark/split_manifest.yaml`'s header; `task_037` (3/3) is recorded there as the verified anchor reserve. **Non-comparability is stated with the decision**: D24 changed the adapter's semantics between experiments, so nothing seq 8 produces is comparable to seq ≤ 6, and every curve it renders says so. Autonomy is D23's envelope re-registered — decision authority over diagnosis, set composition, the per-clause adversarial wording review, PR merges, tags and the reveal; never access to the frozen surfaces, the partition, the `<policy>` block, or the held-out firewall, and a freeze re-decision or suspected seam defect remains a halt-and-report. |
| D29 | Loop rules: surface-general concentration ladder, adoption-first first-use, host-fact discipline, preflight slot, revert/retirement bars | **User-delegated 2026-08-17 (post-seq-8-review adjudication; criterion: the loop must be able to reach every legal surface, not only the best-instrumented one), executed from the seq-8 `INDEPENDENT_REVIEW.md` §8 items 9–14.** (1) The concentration flag is **surface-general**: after ≥3 mutations on any single surface class, the next set includes a change on a surface class this experiment has never exercised, or records a `surface_exhausted` finding citing a probe or measured fact per unexercised alternative — argument alone never discharges it (seq 8: the instructions-only flag never fired while six changes landed on hooks and the D24 surfaces went unexercised; each repaired gradient re-forms at the cheapest newly-legal surface). (2) **Adoption-first first-use** (schema v4 `adoption_stage` + `adoption_criteria`, validated by `records.py`): the first change ever landed on a surface class predicts adoption and correct invocation (`pi_local_calls ≥ k`, well-formed arguments, latency inside τ's budget), reward deferred to the following round; a denied adoption is a mechanism denial and revert trigger, confirmed adoption with unmoved reward is not; a first tool change may bundle its minimal usage instruction as one coherent mechanism — dissolving the "the model would have to choose to call it" objection that rejected extension tools at every seq-8 target. (3) **Host-fact discipline**: v4 `extension-hook`/`extension-tool` changes carry `host_facts` ({fact, probe_evidence} pairs); the measured vocabulary lives in `benchmark/probes/host_facts.yaml` and `check_extension_facts.py` lints extension role literals against it in `make check` (seq 8's gen-004 keyed a hook on role `tool` where its own probe had recorded `toolResult`; the change was measured inert and consumed a generation plus its revert slot). (4) **Preflight slot** (protocol step 5b): ≤ ~12 local episodes per generation, batch tasks only under `allow_within_batch_verification`, covering execution checks and up to three candidate forms of one change — the sanctioned within-generation selection pressure, formalizing seq-8 practice with a budget; injected text is verified present in a fetched conversation before any behavioural number is read (a preflight verifies a change *runs*, never that it *works* — seq 8's F1 preflight showed 3/3 vs 0/12 for a change that never executed); preflights are never record provenance. (5) **Revert and retirement bars**: revert triggers on a denied *mechanism*, never a denied prediction alone (seq 8's counterfactual: D2, kept under this rule, produced the clearest win two rounds after its prediction was denied); retirement cites witnesses from ≥2 rounds or a mechanism-level impossibility — one round's evidence parks, never retires (T3's retire/un-retire churn). Protocol step 7 text reconciled with frozen `require_human_approval: false` (the D23/D28 envelope, previously stated only here and in the lock). | Every rule is bought with a named seq-8 measurement, and the two that bind hardest (ladder, adoption-first) are the pair that makes the D24 surfaces reachable: the ladder forces the attempt, adoption-first makes the attempt a one-round bet instead of a two-round gamble. Schema v4 is additive and version-gated — all seq ≤ 8 records validate untouched, asserted by test. |
| D30 | Instrument: power envelope at freeze, pre-registered identity round, reachability-screened strata, batch trend + reachable-harvest, churn at reveal, suppression canary | **User-delegated 2026-08-17, from the seq-8 review §8 items 1, 3–8.** (1) **Power envelope at freeze** (`scripts/power_envelope.py` → `gates/power_envelope.json`): the frozen composition's movers-needed, movable-task count and attainable-p ceiling are computed before the first episode — seq 8's five-movers-needed-with-three-walled-tasks envelope was computable at freeze and discovered at closure; an envelope that cannot reach α under plausible success fixes the composition or the test, never the narration. (2) **Pre-registered identity round** (`protocol.identity_generations`, lock-validated, `batch_mode: fixed` only): one generation per experiment is identity by design — its batch round is the A/A noise measurement, its held-out carries forward, the reveal refuses the pre-registration dishonored, and `batch_curve.py` emits the `noise_floor` block; registered at generation 1 it also pools the primary's baseline (batch_01 + batch_02, six trials per task). Seq 8's noise floor (2 cells / 8.3 pp — the number that re-read every prior attribution) existed only by accident of an inert change. (3) **Reachability-screened strata**: the pre-freeze screen classifies each headroom candidate's terminal failing step harness-reachable vs domain-walled from H0 trajectories (seq 8's wall taxonomy: rounding convention, governing rate, gold-label semantics); walled tasks enter only as declared wall-monitors outside the primary; strata + `walled:` land in the manifest's `strata:` mapping, restated under `results/experiment_<id>/` by the freeze snapshot (review §6.7). (4) **Batch trend + reachable-harvest**: `batch_curve.py` emits a diagnostic all-rounds trend and the **reachable-harvest co-metric** (fraction of non-walled cells passed, endpoint vs baseline); the reading key's flat-primary cells read it — flat with high harvest says the objective's reachable range is spent (a pool/domain decision follows), flat with low harvest says the loop found nothing. Seq 8 was read "the meta-agent is the problem" by a key with no language for a batch the loop had nearly saturated (15/15 reachable cells at peak). (5) **Churn at reveal**: `summary.md` narrates per-transition gains/regressions vs net, ever-solved vs point-in-time, and identity-pair deltas (seq 8's held-out lane carried a second noise measurement — 3–5 cells churn per transition against nets of −2…+3 — that its closure never surfaced). (6) **Suppression canary** (`gate_seam_canary.py --suppression --expect-tool`, `make gate_suppression` → `gates/suppression_canary.json`): ≥1 platform episode against a temporarily-declared probe tool on pushed main, expecting `pi_local_calls ≥ 1` and the tool absent from τ's trajectory; declaration reverted before `h0-baseline` tags. Seq 8 ran the D24 seam pump-path-only (0 × 168), so platform-lane suppression is an assumption until this runs; `--judge-only` re-judges the first real tool generation post-merge at zero extra episodes. | The instrument changes are the other half of D29's pair: the ladder forces surface exploration, and these make the experiment able to *see* what exploration does — noise floor by design, power stated in advance, saturation distinguishable from failure. All code is backward-compatible: absent `identity_generations` and absent `strata:` reproduce seq-8 behavior byte-for-byte. |
| D31 | Growth zero-state parity + H0 re-anchor | **User-delegated 2026-08-17, review §8 item 18.** D27 scaffolded a template for exactly one of the four growth surfaces, and seq 8 measured the gradient it created: hooks (templated) received six changes, tools and sub-agents (untemplated) received zero. Parity restores the gradient to neutral: `target-agent/extensions/noop-tool.ts` (committed, UNdeclared, doubly inert — absent from `pi.extensions` and from the `tools:` registry; registers `probe_note`, the P6-measured tool name, so the suppression canary exercises the same artifact) and `target-agent/agents/noop-subagent.yaml` (committed, UNreferenced; `from: agent` with no `ai:` — the frozen-pair binding — and empty capability lists), each header carrying the enable path, the D24 registry semantics, adoption-first, and the security bounds; `agent.yaml` comments point at both. `target-agent/` was first restored to `h0-baseline` (seq-8's H6 remains at tag `exp8-g006`), then `h0-baseline` re-tagged at the scaffold commit `047f9bf` (was `b76f274`; D16/D27 re-tag precedent), `make reset_h0` verifying "staged nothing — the recipe already was H0". | Runtime behavior of H0 is byte-unchanged — templates load never, run never. What changes is the mutation gradient: the first change on every legal surface is now a small reviewable diff against a template. The next freeze's H0 is the parity scaffold. |
| D32 | Seq 10: the surface-exercise experiment — `010_adopt-bm25-luna56` | *(Superseded same day, kept as design history: the held-out half by D33; sizes, composition, and primary pairing by D34.)* **User-delegated 2026-08-17 (directive: "design the ground, environment and variables that define the best experiment 10"; EVEN seq per D15). Central question: with every gradient repaired (D29–D31), does a loop that exercises the full surface menu move capability — and if it stays flat, the harvest co-metric says which of "loop failed" / "objective exhausted" it was.** Sizes: **G=7 with `identity_generations: [1]`** — gen-001 is the designed A/A (noise floor measured before the first mutation; baseline pooled to six trials/task), leaving six mutation slots, seq 8's count. **B=10**: 2 anchors (`task_006`, `task_032`; reserve `task_037`) + 5 marginals + 3 reachable-headroom, drawn from burned batch stock only (batch ∩ held-out = ∅), composed by a pre-freeze screen of ~16 candidates × 3 trials under the incumbent H0 (~$1, anchor-calibration precedent) including the D30 reachability classification; the proven-walled are excluded up front (`task_026`, `task_072`, `task_096`, `task_028`, `task_070`, `task_082`); candidate marginals from seq-8/seq-4 stock (`task_014`, `task_057`, `task_076`, `task_065`, `task_040`, plus unmeasured seq-4 batch tasks) — the screen decides, the D28 precedent (composition deviates from the candidate list by measurement) binding. **Held-out T=48** = the legacy 28 (FIFTH exposure) + seq-2's 20 (the least-exposed stock the pool has: last measured 2026-08-14 under the sonnet-4.6 pair, untouched by the luna lineage beyond the 97/97 crash screen), all reuse declared per source; the lane is FORMALLY a diagnostic transfer probe carrying **no capability claim, stated at freeze** — the seq-8 "structurally could not have won" trade made explicit rather than discovered (review §5.7) — with the trend over T=48 (band ≈ ±4 pp at ×3 trials) and a pre-registered advisory exposure-stratified sub-read on the 20 beside the fragility report. **Pool fact recorded**: zero virgin tasks remain (97 − 1 crasher − 20 seq-2 − 68 seq-4 − 8 pilot), so a fresh draw is impossible in `banking_knowledge` and a capability-claim-bearing experiment requires a domain decision — user-owned, pencilled seq 12, not taken here. **Unchanged**: `num_trials: 3`, `batch_mode: fixed`, `allow_within_batch_verification: true`, luna on both halves, `bm25`, seed, budgets, `require_human_approval: false` as the working default under the D23/D28 envelope (ratified at freeze). **Primary**: exact one-sided paired sign-flip, endpoint `batch_08` vs pooled baseline (`batch_01`+`batch_02`), α = 0.05; envelope committed at freeze (movable = 8 of 10; 5 movers needed — attainable, unlike seq 8's). **Reading key**: nine cells + the reachable-harvest co-metric per D30. **Surface-exercise obligation, experiment-level**: by close, ≥1 generation lands a registered Pi-local surface change (extension tool or sub-agent) in a graded round under an adoption-first prediction, or the record carries probe/measured-fact evidence per open target why none fits — backed per-generation by D29's ladder, certified reachable by D30's canary. Freeze checklist: user-sim screen currency check, suppression canary PASS, power envelope PASS, strata screen committed, partition declared, A.0a, `reset_h0` byte-identity. | Cost ≈ **$28–30** at seq-8 actuals: 8 batch rounds × 30 platform episodes ≈ $3.7; 7 measured held-out rounds × 144 local ≈ $20.6 (H1 carried); screen + canary + preflights ≈ $3.5 — the identity generation refunds one held-out round, which pays for the screen and canary twice over. What seq 10 gives up, knowingly: no capability claim on any lane (the pool is spent); what it buys: the first graded exercise of the D24 surfaces, a designed noise floor, a primary whose power ceiling is attainable and stated in advance, and a reading key that can finally separate "fix the loop" from "change the objective" — the decision the project has been unable to make mechanically for three experiments. |
| D33 | Cross-experiment held-out firewall: in-loop decisions are batch-grounded, forever | **User-directed 2026-08-17: the meta-agent's in-loop decision inputs are improvement batches only — current and past. It never reads held-out traces, per-task held-out results, or reveal analyses: of the open experiment (the standing vault rule) or of ANY prior experiment, revealed included (new). The firewall does not expire at reveal.** Mechanics: (1) in-loop recall scope excludes, for every experiment: `held_out/`, `summary.md`, trend/fragility artifacts, task×generation matrices, and any closure/review section carrying per-task held-out content; prior-experiment recall reads `improvement_records/` and `improvement_backlog.md` — the batch-derived memory (sia recall step 3 rescoped accordingly). (2) Reveal analysis is a closure-phase activity; from seq 10 on, closure READMEs and reviews separate batch-derived findings (recallable) from held-out reveal analysis (quarantined) under explicit headings, and the §29 walk carries a D33 attestation (no in-loop session opened held-out artifacts of any experiment; recall digests named their sources). (3) Freeze-time design with the user may use prior AGGREGATE reveal outcomes — they size instruments, cannot steer task-targeted mutations, and live unavoidably in CLAUDE.md's always-loaded record; per-task and trace-level held-out information is quarantined absolutely. **Consequences, superseding parts of D19/D25-rule-2/D32:** task exposure is re-graded by its channel — **batch-used tasks (in-loop tuned) stay burnt for held-out use forever** (the loop read those transcripts; no reading discipline undoes it), while **holdout-only tasks are reusable for a claim-bearing held-out set under the procedural firewall** — the same enforcement class as the D1/D9 local-lane vault, stated in every writeup, declared per source in `partition_reuse.yaml` (`held_out_from_held_out` = claim-eligible with declaration; `held_out_from_batch` = demotion stands). **D32's held-out half is redesigned: T=36 pure-holdout — the legacy 28 plus seq-2's 8 never-batched tasks (the freeze partition verifies eligibility mechanically) — carrying a capability claim on the stated procedural basis**; seq-2's 12 batch tasks return to batch stock; the advisory exposure sub-read reshapes to the 8; local cost drops ≈ $5 (7 × 108 vs 7 × 144 episodes). The unqualified zero-exposure claim (no procedural qualifier) still requires a pool no prior experiment touched — the seq-12 domain decision stands as that path. | Honesty boundary stated with the decision: the strong-form guarantee ("no operator ever saw the key") is not restorable for ever-revealed tasks — the matrices are committed and this session's own review read seq-8's. What the rule buys is the guarantee class the project has already trusted pre-reveal for eight experiments: a stated, auditable reading discipline, now with no expiry. A session that performed a reveal or post-reveal review never carries a later experiment's in-loop decisions; each seq-10 in-loop session starts fresh under the scoped recall. This row is also why the pool arithmetic changed: "zero virgin tasks" made a *zero-exposure* draw impossible, and D33 makes zero-exposure the wrong bar for reuse of holdout-only tasks — the bar is zero *in-loop* exposure plus the quarantine, which T=36 satisfies. |
| D34 | Seq 10 final configuration — the both-curves experiment | **User-delegated 2026-08-17 ("design the best experiment 10; see improvement while we train AND on held-out, generation after generation; be bold; don't misuse resources"), superseding D32's sizes and composition; D29–D31/D33 machinery assumed. The design principle: every prior null is explained by a violated precondition — (a) reachable room in the batch, (b) an instrument that can say yes, (c) known noise, (d) surfaces beyond prose usable, (e) craft lessons persisting — seq 4 violated (d), seq 5/6 violated (a)+(d) (all-known-fail floor), seq 8 violated (a)+(b) (~5 reachable failing cells, saturated by round 5, endpoint test needing 5 movers from 6 non-anchor tasks of which 3 were walled). Seq 10 is the first design where all five hold simultaneously.** **Goal, pre-registered**: success = the sig-up × sig-up cell (batch primary AND held-out secondary); every other cell reads per the mechanical key with the reachable-harvest disambiguator. **Sizes**: G=8 with `identity_generations: [1]` — seven mutation slots, the designed A/A noise floor measured BEFORE the first mutation, and the primary's baseline pooled to six trials/task (G is the strongest trend lever, D11; +1 slot and +1 curve point over D32 for ≈ $2). **B=12**: 2 anchors (`task_006`, `task_032`; reserve `task_037`) + 10 screened tasks **targeting ≥15 reachable failing cells at H0** — the load-bearing repair; composition rule: marginal band (1/3–2/3) preferred, reachability-classified 0/3 tasks fill, proven-walled excluded up front (`task_026`, `task_028`, `task_070`, `task_072`, `task_082`, `task_096`); screen ~24 candidates × 3 trials (~72 episodes, ~$1.5) from burned batch stock (the ~23 recently-unmeasured seq-4 batch tasks, seq-2's 12 batch tasks, the 8 pilot tasks, and seq-8's `task_014`/`task_057`/`task_076` plus `task_040`/`task_065`); if fewer than 10 qualify, B shrinks (floor 10) rather than admitting walls, recorded. **T=36** per D33 (legacy 28 + seq-2's 8; claim on the procedural basis), `num_trials: 3` on both lanes (D18 one-knob), `batch_mode: fixed`, `allow_within_batch_verification: true`, `require_human_approval: false` (D23 envelope re-registered, ratified at freeze), luna pair / `bm25` / seed / budgets unchanged. **Instruments**: primary = exact one-sided paired sign-flip, endpoint `batch_09` vs pooled `batch_01`+`batch_02`, α = 0.05 — movable 10, 5 movers needed, envelope committed at freeze and the gate refuses UNREACHABLE; secondary = held-out trend over the 8 measured points (H0, H2…H8) with fragility, claim-bearing per D33; named diagnostics = batch all-rounds trend, reachable-harvest, identity-round noise floor, process counters as per-change prediction channels. **Preflight scope extended** (protocol step 5b): the ≤ ~12-episode budget may draw burned non-partition tasks (in neither batch nor held-out) as candidate-generalization probes — an out-of-batch check before landing that touches nothing held-out. Surface-exercise obligation, ladder, and adoption-first per D29/D32. Freeze runbook: Phase 5.10. | Cost ≈ **$29** at seq-8 actuals: 9 batch rounds × 36 platform episodes ≈ $5.0; 8 measured held-out rounds × 108 local ≈ $17.7; screen + suppression canary + preflights ≈ $6. Wall-clock ≈ 2–3 days autonomous, accepted rather than optimized. What the shape buys per precondition: (a) ≥15 reachable failing cells vs seq 8's ~5; (b) 5-of-10 movers attainable and 8 trend points on each curve; (c) noise measured in round 2, not discovered by accident in round 6; (d) D24 surfaces certified by canary, forced by the ladder, cheap under adoption-first with zero-state templates; (e) sia recall + records carry the standing lessons under the D33 scope. |

------------------------------------------------------------------------
| D35 | Round-resume contract: a sentinel means "runner returned", never "measured" | **User-directed 2026-08-17, mid-experiment, during seq 10's `batch_01`.** The round lost one episode (`task_003` trial 1) to the luna user-simulator empty-completion signature past τ's four retries — weather on a FROZEN surface, all four seam counters zero — and `make batch` then REFUSED to re-enter the round: `prepare_round_dir` saw `run_metadata.json` and reported "already holds a completed run … pass --overwrite". The only sanctioned path forward was `--overwrite`, i.e. re-spending AND re-drawing 35 healthy episodes to recover one. **The held-out lane already had the right behaviour** (`heldout.run_round`: "the sentinel means 'runner returned', never 'measured': drop it … completed episodes are not re-spent") — implemented privately, so the two lanes had diverged and only one operator-facing lane carried the fix. The repair puts one rule in one place: `experiment.round_measured(out_dir, expected_episodes)` is now the single definition of "measured" (completed manifest rows, row counts only — safe for the sealed vault), `prepare_round_dir` gained an `expected_episodes` keyword and a fourth case (sentinel present + round incomplete → drop the sentinel and the grading derived from non-measurements, resume), `run.py` passes the count for every run whose task list is known up front, and `heldout.py` now calls the shared helper instead of its private copy. Without `expected_episodes` the sentinel is still taken at face value and the round refused — the safe direction. Four tests added (`tests/test_round_lifecycle.py`), suite 430 → 434. | **This touches `benchmark/tau_adapter/` mid-experiment, which is why it is a decision row rather than a quiet commit.** It is not a semantic-adapter change: nothing about trajectory construction, tool forwarding, D24 suppression, step accounting or grading moves, and no value the evaluator sees is touched — only when a rerun into an existing round directory is permitted. It is also not silent: the change is gated by its own staleness rule (`run.py` refuses a batch when the seam-canary verdict predates the last `benchmark/tau_adapter` commit), so `make gate_seam` and `make gate_a0a` were both re-run and re-committed before the next round. `batch_01` itself was recovered by hand under the held-out lane's semantics BEFORE this code existed, so no round in seq 10 was produced by untested code. |
| D36 | Seq 12 design: measure the ceiling first, test on episodes, bundle the changes | **User-decided 2026-08-18, from the seq-10 closure.** Seq 10 removed every excuse a prior null could hide behind and still came out null on both instruments — which finally makes the *unmeasured* quantity visible: nobody has ever measured how much better ANY harness could be on this objective. Seq 12 measures it first. **Phase 0, the ceiling probe (before a single generation):** three harnesses over a wide candidate set — H0-minimal, H0-current, and **H-expert**, a harness hand-built with full access to the batch tasks and unlimited effort, never shipped and never part of the loop, existing only to bound the range. It buys three things at once: **headroom** (H-expert − H0, the number the project has never had), a **normalized primary** (fraction of the reachable gap closed, which is meaningful even when absolute movement is small), and an **empirical reachability oracle** — a task H-expert passes is *provably* harness-reachable, which is far better evidence than trajectory reading and is what makes a larger batch safe to compose. If H-expert ≈ H0 the objective is unwinnable by harness change and the loop is not run: a real finding for ~$15. **Instrument:** **G=7** with `identity_generations: [1]` — six mutation slots, which at 3–5 bundled changes each is 18–30 attempts against seq 10's five; `num_trials` stays **3** (τ²'s published metric is pass^4; three trials is informative and the noise is absorbed by the other changes); the primary becomes `scripts/endpoint_test.py`, a **within-task permutation on EPISODE outcomes** with a CMH cross-check, replacing the sign test that collapsed 36 episodes into 12 verdicts and demanded ~5 to align; **B = 30** — validated against seq 10's own data, where the observed +11.1 pp movement reads p = 0.184 under the sign test, 0.133 under the new test at B=12, and would read p = 0.044 at B=30 (SE of the endpoint difference 10.2 → 7.2 → 6.5 pp at B = 12/24/30); the **held-out set is measured at three points** — `heldout_generations: [0, 4, 7]`, a lock field added with this row whose omitted generations are CARRIED exactly as identity generations already are, so reveal needed no new concept; the batch gate walks every *scheduled* measurement at or before its generation, so sparse never means optional (7 tests); the **pre-registered identity round is kept** (seq 10's best design decision — it fixed the attribution bar before the first mutation). **Loop policy** per `contract/protocol.md`: bundle 3–5 non-interacting changes per generation, a ≥3-task-or-structural bar on targets, counters stated as deltas, at most two reverts, one slot reserved for a never-exercised surface class (`sub-agent`), and the committed diagnosis instrument run rather than re-derived. **The retrieval backend is NOT decided here**: Phase 0 runs under both `bm25` and `openai_embeddings`, and a rule registered before the probe picks the winner — freeze whichever yields the larger harness headroom; tie goes to embeddings (what τ² publishes, restoring comparability, and the key is already required at grading time). Consequence accepted either way: `--retrieval-config` rewrites the tool set AND the graded policy text, so seq 12's absolute numbers do not compare to seq ≤ 10 — which gap-closure normalizes, and which is a further reason to prefer it as the primary. **Futility check (added 2026-08-18 on review of the seq-10 tail):** from the midpoint generation onward each transition computes the endpoint delta significance would require, the delta accumulated, and the slots remaining; when the gap exceeds the largest single-generation gain observed times the slots left, the record **declares the primary dead on that round**. Seq 10's became unreachable after `batch_07` — +8.3 pp accumulated against a ~+17 pp requirement, with both remaining slots then spent on reverts, which cannot raise an endpoint. The consequence is deliberately NOT stopping: seq 10's last two slots produced two of its best findings (a prior null replicated on a new surface; an inert change proven inert by its removal). What changes is what a slot optimises for — expected score while the primary lives, knowledge once it is dead, spent on the never-exercised surface or an ambiguous mechanism. A revert landed in the final slots is itself a futility signal and is recorded as one. **Deferred deliberately:** the control arm (a non-diagnosing loop run against the same batch, whose comparison is the sharpest available test of the "self-improving" claim) is a different claim and gets its own freeze; and the weak-H0/strong-H0 pair stays an open option rather than a silent addition. | The design principle inverts the project's habit. Through seq 10 every experiment asked "did the score go up" against an unknown maximum, so a null was uninterpretable — "the loop failed" and "there was nothing to find" stayed equally alive four times running. Measuring the ceiling first makes every outcome informative: no headroom stops the experiment for \$15; headroom plus a flat curve indicts the loop and nothing else; headroom plus a rising curve is the demonstration. Cost ≈ \$60–70 (Phase 0 ≈ \$30 across both backends; 10 batch rounds × 90 episodes ≈ \$25; 3 held-out points ≈ \$12), against seq 10's \$32. |

## 3. Protocol → repo mapping

| Protocol concept | Repo realization |
|---|---|
| Experiment config (§26) | `protocol:` block in `benchmark_lock.yaml` (`generations`, `improvement_tasks_per_generation`, `held_out_tasks`, `allow_within_batch_verification: false`, `holdout_visibility` flags, `require_human_approval` — a per-experiment value: `true` through seq 5, frozen `false` for seq 6 per D23). Inside the freeze fingerprint automatically via `lock.raw`. `held_out_trials_per_task` ≡ `frozen.num_trials` (one knob). |
| Partition (§3, §16) | `benchmark/split_manifest.yaml` rewritten: `batches: {batch_01: […], …}` + `held_out: […]`, sizes derived from the lock's `protocol:` block. Same stratification machinery (reward_basis 88 DB / 9 ACTION, dominant doc category, doc count; stride scheduler), disjointness verified dynamically across G+1 partitions, (G×B)+T ≤ 97 enforced, ACTION spread re-expressed (held-out gets its proportional share ≥4 at T=47; batches jointly cover the rest). |
| Improvement batch run (§7) | `make batch B=1 GEN=generation_000` — platform lane forced, resume-friendly (no `--overwrite`), round dir `generation_NNN/batch_NN/`, manifest `split: batch_NN`, labels `[exp_00N:…] τ²-bench banking_knowledge task_X trial 0 gen_NNN bNN - …`. Convention enforced by the runner (2026-08-13): batch_NN is *run by* H\_(NN−1), so it lives under `generation_(NN-1)/` — the wrong GEN is refused pre-spend. Graded output persists to `batch_NN/graded/`. |
| Held-out evaluation (§6, §11) | `make heldout GEN=generation_001` → `scripts/run_heldout.py`: local lane forced, all child stdout/stderr redirected into the vault's `console.log`, grading persisted to the vault (never printed), prints **completeness only** (episodes expected/completed, manifest joined, zero reward tokens — asserted by test). |
| Firewall (§12) | D1 + D9. Platform: structural (no evidence exists). Local artifacts: procedural + out-of-tree + muted output. |
| Diagnosis (§8) | `operate` skill over the batch's platform conversations: task rows → conversations → tool calls/spans; prevalence via `metrics query`; observations/patterns after the ~40-min window (fallback: metrics-over-spans + manual clustering, evidence tier stated). |
| Proposal (§9) | `improve` skill: one improvement **set** per generation (D22) — any number of changes, each one coherent mechanism inside the mutable table with its own falsifiable prediction — branch `gen-NNN/<slug>`, one commit per change, one PR citing conversation ids + prevalence + per-change predictions. |
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
      effective plan cap ≈ 2 observed) *[corrected 2026-08-14: provisioning latency,
      not an org queue — no plan cap exists, three concurrent sandboxes are proven in
      the task history, and this was the burst's second-created task; see
      `contract/constraints.md` § Platform-lane concurrency]* — our stream read the silent queued run as
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
`--max-concurrency 2` — then believed a sandbox quota; corrected 2026-08-14 to a
provisioning-contention bound — ≈ 6–16 min each). The held-out set
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
- [x] Seam-risk remediation (user-directed, follow-on session to the grounding pass):
      the audit's three RISK items landed with tests. R1 — refused tool calls are now
      counted at the bridge by cause (`tool_refusals_unbound_session` /
      `tool_refusals_stale_endpoint`) and folded into the round's incident totals as
      run-level counters (a refusal has no episode to ride on — that is what it means),
      so an episode starving on refused calls can no longer leave a healthy-looking
      seam. R2 — the platform stream's stderr is drained continuously with a bounded
      tail (undrained, the child blocks once the ~64 KB pipe fills, presenting as a
      silent stream death with a misleading cause); the failure report now carries the
      drained tail, and `stderr_tail` is real on this lane. R3 — stream install is
      atomic and closed-aware: `_spawn_stream` decides under the session lock whether
      its caller's world still stands, so a reattach that loses its race with
      `_stop_stream`/`close()` spawns nothing instead of leaking a subprocess no
      teardown would reap. Suite 250 → 254; ruff + format clean; **A.0a PASS**
      re-proven on the changed seam (254-test suite + graded mock smoke,
      `generation_000/gates/a0a.json`; the untracked gate/smoke artifacts were cleared
      from `results/` the same day, user-directed, so the debug experiment starts into
      an empty tree — this entry is the durable record of the PASS, per the Phase 3.5
      precedent) (2026-08-13).
- [x] Freeze: `experiment.seq: 1` (numbering reset) with D10 `protocol:` values (G=3, B=4, T=8) and
      the re-proposed partition already in place; flip PROVISIONAL → FROZEN;
      `reset_h0`; commit; **A.0a gate PASS** recorded. Executed 2026-08-13: partition
      re-verified, `reset_h0` staged nothing (recipe already byte-identical to
      `h0-baseline`), lock flipped at `af0c4a8`, A.0a PASS (254-test suite + graded mock
      smoke, reward 1.0) recorded at
      `results/experiment_001_bm25-sonnet46/generation_000/gates/a0a.json`; the first
      non-PROVISIONAL run wrote the freeze snapshot (`experiment.yaml` + lock/manifest
      value-copies) beside it. (2026-08-13)
- [x] **Seq 1 VOID** (2026-08-13, user-ratified): the H0 held-out round could not
      complete — `task_034` deterministically crashes τ's user simulator on the opening
      turn (empty Sonnet 4.5 completion at the frozen `temperature: 0.0`;
      `UserMessage.validate()` → `infrastructure_error`; 12/12 across three invocations,
      seam counters zero, failure precedes the agent). A frozen surface owns the crash
      (τ commit + user-sim config; upstream #440 fixed this class for voice only), so
      the freeze is re-decided as **seq 2 = debug attempt 2** (seq 3 takes the full
      run). Two loop-mechanics fixes landed mid-run and are keepers (`ce10da7` held-out
      resume of a measured-but-incomplete round; `9787585` root-cause capture onto
      manifest rows) — per this phase's validate criterion, the debug experiment
      re-runs under the next seq. Closure + firewall accounting:
      `results/experiment_001_bm25-sonnet46/README.md`. Remedy for seq 2: pre-partition
      screening; exclusions documented in the manifest; upstream issue drafted for user
      review before filing.
- [x] **Seq 2 freeze** (2026-08-13): screening refined by falsification — first-turn
      screen 97/97 clean, orchestrated scripted-agent screen
      (`scripts/screen_user_sim.py`, ~$3) 97/97 clean, so the crash needs a real
      agent's replies; stock-agent probes reproduced it on `task_034` (4/4; 16/16
      cumulative) and cleared the other four combo-instruction tasks. Partition
      re-proposed over 96 tasks (`--exclude task_034`, header-documented), lock bumped
      to seq 2 (values otherwise unchanged) at `c1f6ecc`, recipe byte-identical to
      `h0-baseline`, **A.0a PASS** (259-test suite + graded mock smoke) recorded at
      `results/experiment_002_bm25-sonnet46/generation_000/gates/a0a.json` beside the
      freeze snapshot. Residual risk (real-agent-conditioned crash on an unprobed
      task) accepted; fallback is the documented void-and-reseq procedure.
- [x] H0 held-out (hidden, vault) → B1 batch → `operate` diagnosis (harvest 1
      immediately; harvest 2 after the ~40-min observation window, fallback stated)
      → `improve` PR → human review/merge → tag `exp2-g001` → H1 held-out (hidden)
      → B2 → … → H3 held-out → final tag. Ran 2026-08-13/14, zero mid-run mechanics
      patching: 4 sealed held-out rounds (8/8 each, incidents none), 3 batches
      (reads 0/4, 0/4, 2/4 — visible by design), 3 user-gated PRs merged
      (`exp2-g001` KB-answer verification, `exp2-g002` source-grounded selection,
      `exp2-g003` procedure completion). Observation harvest returned zero rows in
      window every time; the stated fallback (full-population transcript reads at
      B=4) carried each diagnosis. (2026-08-14)
- [x] Improvement record per transition, written as it happens; B1 viability read
      (D8) recorded (2026-08-14). **B1 read (2026-08-13, seq 2): 0/4** — all four episodes clean
      (user_stop, evidence_complete, arm_sha_ok true, benign reattaches only), rewards
      0.0/0.0/0.0/0.0 → D8's halt-and-reconsider-H0 condition fires; `operate`
      diagnosis proceeds to inform the reconsideration before any `improve` PR.
- [x] `make reveal` → held-out artifacts + `summary.md`; verify every §27 artifact
      exists and every §29 guardrail held (walk the 20-item list, record the walk).
      Revealed 2026-08-14: **H0 3/8 → H1 3/8 → H2 2/8 → H3 2/8; endpoint −1 task
      (−12.5 pp), inside the ±18 pp band — directional only**, per the D10 caveat
      the debug scale demonstrates the loop, not the claim. All 20 guardrails HELD;
      walk + §27 inventory at
      `results/experiment_002_bm25-sonnet46/GUARDRAIL_WALK.md`. (2026-08-14)
- [x] `contract/protocol.md` rewritten from this run (the per-generation procedure
      as it actually executed) (2026-08-14).

**Validate:** the complete evidence → signal → hypothesis → mutation → generation →
hidden-measurement chain exists on disk for ≥1 accepted (or cleanly
rejected/identity) transition; no held-out task id, trajectory, or reward appeared in
any orchestrator-visible output before reveal (audit the session record + vault
`console.log` placement); loop mechanics needed zero manual patching mid-run — else
fix and re-run Phase 4 under the next seq before scaling up.

### Phase 5 — Powered experiment (seq 4, D11 sizes; prepared as seq 3, renumbered by D15)

The tier between debug and full: G=5, B=8, T=28 — sized from seq-2 actuals so a
working loop has a real chance to SHOW on the curve, at ~63% of full-experiment cost.
Analysis of record: `results/experiment_002_bm25-sonnet46/SIZING_ANALYSIS.md`;
instrument: `benchmark/scripts/power_sim.py`.

- [x] Sizing analysis from seq-2 actuals; G=5/B=8/T=28 ratified as D11; the honest MDE
      stated (powered for ~+4–5 pp/gen; +2 pp/gen reads directional-only; a seq-2-like
      loop is indistinguishable from null at any affordable T) (2026-08-14).
- [x] Lock re-cut PROVISIONAL at seq 3: protocol block
      5/8/28, frozen values carried from seq 2; partition proposed
      and frozen over the 76-task fresh pool (`make propose_split WRITE=1` — task_034 +
      all 20 seq-2 tasks excluded, header-documented), `--verify` green (2026-08-14).
- [x] Model pair re-decided and re-cut in place as `003_powered-bm25-luna56` (D12):
      both halves `openai/gpt-5.6-luna` at medium effort; key/model/args probed live,
      `introspection check` green, mock smoke clean on both halves; `h0-baseline`
      re-anchored with the seq-2 referent archived as `h0-baseline-sonnet46`
      (2026-08-14).
- [x] Calibration pilot (D12 consequence c): luna-H0 on the 28 non-partition tasks
      (8 unused + 20 seq-2-burnt; firewall-clean — the frozen held-out set untouched)
      for $1.06 — **7/28 = 25%** (no saturation), **$0.038/episode** (16× under the
      Sonnet basis), episodes same length; power re-checked at the measured baseline,
      **D11's G=5/B=8/T=28 stands**; record at
      `results/experiment_003_powered-bm25-luna56/CALIBRATION_PILOT.md` (2026-08-14).
- [x] D13 interim re-cut to `003_powered-bm25-haiku45` while the platform's OpenAI
      serializer defect blocks luna: lock re-cut (haiku both halves; `temperature: 0.0`
      restored to the user-sim — verified accepted), assertion/checker/partition green,
      `h0-baseline` re-anchored; **haiku recalibration pilot 3/28 = 10.7% at
      $0.283/episode, G=5/B=8/T=28 re-confirmed** (power slightly better at the lower
      baseline; watch-item: ~40% 0/8 batch reads, D8 is the guard); local smoke green;
      platform path verified by the clean haiku control episode ($0.218, zero
      incidents) — the post-freeze platform re-check hit a transient org Anthropic
      rate limit (the pilot's 10-wide burst) and re-runs after cool-down; record at
      `results/experiment_003_powered-bm25-haiku45/CALIBRATION_PILOT.md` (2026-08-14).
- [x] Reveal computes the pre-registered primary (D11): one-sided trend test over
      H0…H5 at α=0.05 (`tau_adapter/reveal.py` — permutation-variance normal
      approximation; identity generations carry their predecessor's draws and are
      excluded from the statistic), rendered in `summary.md` beside the endpoint +
      band and written machine-readable to `held_out/trend_test.json`; 9 unit tests
      against hand-computed values, suite green at 271 (2026-08-14).
- [x] Start gate CLOSED 2026-08-15 (`bc31f80`), every item citable: `make reset_h0`
      staged nothing — the recipe already was H0, byte-identical to the corrected tag;
      partition `--verify` green; **user-sim screen re-run under the luna pair — 97/97
      survive, zero crashers** (`benchmark/data/user_sim_screen.json`, overwriting the
      Sonnet-conditioned seq-2 report that git history keeps); **A.0a PASS** — 283
      adapter tests + clean mock smoke, recorded at `generation_000/gates/a0a.json`;
      lock flipped PROVISIONAL → FROZEN and the freeze snapshot written
      (`experiment.yaml`, `sha256:1c3a301e…`) — the re-cut-in-place licence is now
      spent. Live finding kept rather than filed away: **task_034's crash class does
      not reproduce under luna** (it voided seq 1 under Sonnet at `temperature: 0.0`);
      the exclusion stands because the manifest is frozen and its header attributes
      that exclusion to seq-2 screening, not to a claim about the current pair.
      The anchor this reset verifies against is D16's CORRECTED `h0-baseline` (the tag
      had drifted onto seq-2-mutated recipes), and the calibration of record is the
      corrected-H0 pilot under `experiment_004_.../CALIBRATION_PILOT.md`. The
      platform-lane luna check closed earlier the same day: graded episode, reward 1.0,
      evidence_complete, arm_sha_ok, $0.0157/episode, zero incidents — the sandbox
      OpenAI defect is fixed platform-side and the `ai:`-spelled template validates on
      both toolchains (CLI 0.27.1). If the pair ever reverts to haiku (D13), respect the
      measured 20M prompt-bytes/HOUR org cap on claude-haiku-4-5; the OpenAI serializer
      defect (`.ai-state/UPSTREAM_ISSUES.md`) now gates only the RETURN to D12's luna
      pair — a fresh re-cut + pilot, never a mid-experiment swap.
      Operational fact learned at the first batch, worth stating once: the platform lane
      pins lineage to **pushed** `main`, so a freeze or infrastructure commit must be
      pushed and its runtime version built before `make batch` will run. The escape
      hatch (`--allow-dirty`) stamps every row `arm_sha_ok=false` and is a debugging
      tool, never a way to start a round.
- [ ] Run: 6 held-out rounds × 28 (local, sealed) interleaved with 5 batches × 8
      (platform) ≈ $132 at measured rates, $150–165 with instruction-growth headroom;
      budget go/no-go with the user at each generation boundary.
- [ ] Reveal; `summary.md` with the trend verdict + endpoint per protocol §25; per-task
      matrix; process-metrics secondaries reported as directional only.
- [ ] Conditional (decide post-reveal, D11): endpoint reliability addendum on H0/H5
      only if the endpoint lands positive-but-inside-band (~$70–100 at +2 trials ×
      2 arms × 28 tasks).

**Validate:** the §25 success bundle plus the pre-registered trend verdict, every
number labelled with its set and N; no held-out exposure before reveal; the
eyeball bar stated as ≥4–5 tasks wherever the curve renders (the debug-era
"+2 tasks reads directional" does not carry to T=28).

### Phase 5.5 — Loop-reliability experiment (seq 5: fixed batch × 3 trials)

The prerequisite question seq 4's null could not answer, attacked directly: instead of 8
fresh tasks per generation, ONE fixed batch of 8 known-fail tasks is measured under every
generation (D17), at 3 trials per task on every round (D18), with seq-4's T=28 reused as
the transfer probe (D19). ~120 platform + ~504 local episodes ≈ $20–25 at measured rates.

- [x] Machinery landed 2026-08-15, all config-driven: `protocol.batch_mode: fixed|fresh`
      (lock validation refuses fixed without within-batch verification; manifest and lock
      must agree; fixed batches verified pairwise IDENTICAL, batch↔held-out disjointness
      enforced in both modes); rate-native reveal (exact binary reduction at one trial —
      all 24 prior tests pass unchanged); `scripts/batch_curve.py` + `make batch_curve`
      (paired sign-flip endpoint test, exact at 2^8); dashboard trials-aware in both lanes
      (rate cells, partial dots, mode-aware notes). Suite 313 green.
- [x] Lock cut PROVISIONAL as `005_fixedb-bm25-luna56`: same pair/budgets/seed as seq 4,
      only batch_mode, allow_within_batch_verification and num_trials changed. Partition
      frozen with explicit lists and `--verify` green: fixed 8 = task_014/026/028/065/
      070/072/082/096 (known-fail, mode-covering, per-task rationale in the manifest
      header); held_out = seq-4's 28 verbatim.
- [ ] Start gate: `make reset_h0` (byte-identity to the D16-corrected tag); lock
      PROVISIONAL → FROZEN; A.0a PASS recorded; partition `--verify` re-run. The user-sim
      screen carries over (pair unchanged; 2026-08-15 luna screen 97/97 — D19).
- [ ] Run: 6 held-out rounds × 28 × 3 (local, sealed) interleaved with 6 batch rounds
      × 8 × 3 (platform; batch_06 is H5's endpoint measurement, consumed by no
      transition). Diagnosis notes must state that batch prevalence from B2 on measures a
      tuned-on set (D17 consequence).
- [ ] Close: `make batch_curve` (primary — paired endpoint verdict), `make reveal`
      (transfer probe, rate-native), guardrail walk with #2 marked modified-by-design,
      closure README interpreting through the pre-registered reading key.

**Validate:** the pre-registered paired endpoint verdict plus the reading-key
interpretation; every number labelled with set, N and trials; the D19 firewall caveat
stated wherever a T number renders.

### Phase 5.6 — Fixed batch at depth (seq 6) — run and REVEALED

Carried entirely by D23 (the design) and the closure record
(`results/experiment_006_fixedb-bm25-luna56/README.md` + Errata + the independent review):
primary null, secondary significant-but-fragile-and-exposed, machinery held across 756
episodes with all twenty §29 guardrails and no waivers. No phase body was written before
the run; this stub exists so the phase list matches the status table.

- [x] Freeze, six autonomous transitions, reveal, closure + guardrail walk (2026-08-16)
- [x] Independent post-reveal review + batch-task difficulty study committed into the
      experiment directory; errata appended to the closure (2026-08-16)

### Phase 5.7 — § 8 groundwork: the common ground for the next experiment

Applies the independent review's § 8 across the seam, contract, instrument, sia skill,
and scaffold — recorded as D24–D27, all task-agnostic. The next freeze consumes these
rules; nothing here cuts it.

- [x] Recipe reset to `h0-baseline` byte-identity (2026-08-16)
- [x] Record hygiene: seq-6 errata appended, CLAUDE.md corrected, tracker de-staled
      (2026-08-16)
- [x] Surface truth: `recipe-growth.md` re-corrected against upstream (CLI 0.28.0 /
      Pi 0.84.1 / recipes 0.19.3) and against measured probes — hook functional on the
      real domain; a DECLARED skill reaches nothing on this seam's local lane; platform
      lane pins the recipe to pushed main (`benchmark/probes/2026-08-16-surface-probes/`)
      (2026-08-16)
- [x] Seam D24: Pi-local suppression landed, tested (13 tests), fidelity leak invariant,
      live demo PASS (probe P6) (2026-08-16)
- [x] Contract D26: schema v3 (per-clause falsifiers, backlog write-through with the
      cadence-gate hook), protocol step 4b, positive-obligation flag, endpoint
      diagnosis, quote discipline (2026-08-16)
- [x] Instrument D25: trend fragility at reveal (backfilled into seq 6), mechanical
      reading key, stratified-batch + fresh-holdout rules, batch process metrics,
      lock-sourced tool names (2026-08-16)
- [x] sia skill: activation-path mutation classes, forward-looking recall,
      `surfaces_considered`, counter-native predictions (2026-08-16)
- [x] Scaffold D27: committed-undeclared hook template, registry-aware comments,
      `h0-baseline` re-anchored at `b76f274`, `reset_h0` + smoke verified (2026-08-16)

**Validate:** full suite green (379); all six seq-6 v2 records validate untouched; the
fragility fixture reproduces the review's numbers; the suppression demo shows a
registered Pi-local call executed, logged, and invisible to τ; agnosticism grep over
`contract/` + `skills/sia/` + schema finds no task-shaped normative text.

**Next freeze checklist (consumes this phase; a freeze decision, not part of it):** bump
`experiment.seq` per parity (D15); stratified batch per D25 with strata in the manifest
header; held-out draw per D25 (fresh for a claim, or declared-demoted); full-quadrant
`protocol.reading_key`; `process_metric_tools` reviewed for the frozen domain; probes
per protocol step 4b at g=0; note D24 non-comparability with seq ≤ 6 wherever a curve
renders.

### Phase 5.8 — Stratified batch on the D24 seam (seq 8) — in flight

Carried by D28 (the design). The first experiment to run with the structural surfaces
actually available and with a batch whose strata were measured before the freeze rather
than assumed after it. Consumes every rule Phase 5.7 landed.

- [x] Anchor calibration probe, pre-partition: 69 local episodes, $0.97, three
      anchor-grade tasks found outside the held-out set, two named marginal candidates
      measured below the marginal band (`benchmark/probes/2026-08-16-anchor-calibration/`)
      (2026-08-16)
- [x] Freeze: seq 8 stratified partition (strata + every drop and its reason in the
      manifest header), full-quadrant `reading_key`, fourth-exposure reuse declared
      against all three prior sources, `process_metric_tools` reviewed and deliberately
      unchanged, `reset_h0` byte-identity, `make check` green (2026-08-16)
- [x] A.0a gate PASS (379 tests + mock smoke) and platform seam canary PASS, both recorded
      before the first episode (2026-08-16)
- [x] Step-4b surface probes: `tool_result` at g=0 and `context` at g=1, both measured
      functional on the real domain — every hook this repo can use is now measured rather
      than inherited (2026-08-16/17)
- [x] Six autonomous transitions (PRs #17–#22, tags exp8-g001…g006), seven held-out rounds,
      seven batch rounds, reveal, §29 walk, closure (2026-08-17)

**Outcome:** NULL on both instruments — the frozen `primary_flat_secondary_flat` cell. Primary
Σ per-task rate deltas +1.333, exact p = 0.250 (only two of eight tasks had a non-zero endpoint
delta; five movers were needed for α = 0.05, computed and recorded BEFORE the endpoint round).
Secondary z = 0.60, p = 0.274, endpoint +1 task inside the ±5 pp band, on a fourth-exposure
set carrying no capability claim. What outlives the number: a MEASURED noise floor (2 cells,
8.3 pp, from a behavioural-identity round — a first for this project); the framing finding
(list → nothing; missing-state → behaviour change plus unasked suppression; completed-state →
safe and inert; consequence-stating → confirmed); transfer discrimination moved for the first
time in four experiments, on one side only; the revert rule *a denied prediction is not a
revert trigger, a denied mechanism is*, with a measured counterfactual; anchors 42/42 across
seven rounds proving the stratification's regression channel; and a surface-exhausted finding
for the remaining headroom, reached by five rounds of layer-peeling. Three process failures are
recorded (an inert change consumed a generation; a preflight manufactured a confirmation out of
noise; a target was retired on one round's evidence and un-retired two rounds later).
`pi_local_calls` was 0 across all 168 platform episodes — the D24 seam ran its pump path and
never its suppressing path, so extension tools and sub-agents remain available but unexercised
in a graded round.

**Validate:** the primary is decided mechanically from `batch_curve.json`'s endpoint pair
against the frozen `reading_key`; no cell is adjudicated off-key; every improvement record
validates at schema v3 with per-clause falsifiers and a backlog transition stamp.

### Phase 5.9 — Seq-8 post-reveal review + D29–D32 groundwork (landed 2026-08-17)

- [x] Independent post-reveal review committed
      (`results/experiment_008_stratb-bm25-luna56/INDEPENDENT_REVIEW.md`): the saturation
      reading (15/15 reachable cells at peak under a null primary), the second noise
      measurement in the held-out churn, seven narration-gap errata, the why-only-hooks
      analysis (§7), and the 21-item §8 change list (2026-08-17)
- [x] Loop rules landed per D29: surface-general ladder + adoption-first + preflight slot
      5b + revert/retirement bars + approval-gate reconciliation (`contract/protocol.md`);
      schema v4 (`adoption_stage`/`adoption_criteria`/`host_facts`, version-gated;
      `records.py` + tests, seq-8 records green) (2026-08-17)
- [x] Instrument landed per D30: `identity_generations` (lock + reveal refusal +
      `noise_floor` + pooled baseline), `strata:`/`walled:` manifest support +
      reachable-harvest + diagnostic batch trend (`batch_curve.py`), churn narration
      (`reveal.py`), `power_envelope.py`, suppression-canary mode
      (`gate_seam_canary.py --suppression`, `make gate_suppression`),
      `benchmark/probes/host_facts.yaml` + `check_extension_facts.py` in `make check`
      (2026-08-17)
- [x] sia skill updated: `recipe-growth.md` reconciled to the D24 seam (the mapping table
      and trap 4 had steered "prefer a no-tool-call hook" through all of seq 8), surface
      ledger at project scope in the recall digest, adoption-first + host-facts craft in
      `record-craft.md` (2026-08-17)
- [x] Growth zero-state parity per D31: `noop-tool.ts` (probe_note) + `noop-subagent.yaml`
      committed-undeclared; recipe reset to H0; `h0-baseline` re-tagged at `047f9bf`,
      byte-identity verified (2026-08-17)
- [x] Seq-10 design recorded as D32: `010_adopt-bm25-luna56` — designed identity round
      at gen-001, reachability-screened strata, adoption-first surface-exercise
      obligation, harvest-aware reading key (2026-08-17; sizes superseded same day —
      D33 reset the held-out to T=36, D34 reset G to 8 and B to 12)
- [x] Cross-experiment held-out firewall recorded as D33 (user-directed): in-loop
      decisions batch-grounded forever, reveal analyses quarantined from recall, sia
      recall rescoped, closure structure + §29 attestation added; seq-10 held-out
      redesigned to T=36 pure-holdout carrying a claim on the procedural basis
      (2026-08-17)

**Validate:** full adapter suite green after every slice; `make check` green (including
the new extension lint and `--verify-current` over seq-8's v3 records); `reset_h0`
reports byte-identity to the re-tagged anchor.

### Phase 5.10 — Seq-10 freeze runbook (D34; execute in a fresh session under the D33 recall scope)

- [ ] Preconditions: `make reset_h0` byte-identity to the D31 anchor; model pair + keys
      live; user-sim screen currency confirmed (pair unchanged since the 2026-08-15
      97/97 luna screen; `task_034` stays excluded); `make check` green.
- [ ] **Batch candidate screen** (~24 candidates × 3 local trials under the incumbent H0,
      ~72 episodes ≈ $1.5): candidates from burned batch stock per D34 — **never any of
      the intended held-out 36** (the screen runs pre-partition, before the manifest
      guard re-arms, so this exclusion is the screen's own responsibility; verified
      2026-08-17: the full 60-task candidate stock is disjoint from the 36); commit
      evidence under `benchmark/probes/<date>-seq10-screen/`; classify every 0/3 candidate's
      terminal failing step harness-reachable vs domain-walled (D30 wall taxonomy) by
      reading its trajectories; select 10 (marginal band preferred, reachable fills,
      walls excluded), targeting ≥15 reachable failing cells; anchors `task_006`,
      `task_032` re-verified 3/3 in the same screen (`task_037` reserve).
- [ ] **Partition**: `make propose_split` fixed mode with the 12 batch tasks, `strata:` +
      `walled:` in the manifest header; held-out = the legacy 28 + seq-2's 8;
      `partition_reuse.yaml` declarations (held_out_from_held_out vs 002/004/005/006/008
      with the D33 procedural-basis reason; batch reuse reports); `--verify` +
      `check_partition_isolation.py` green.
- [ ] **Suppression canary** (D30): temporary PR declaring `extensions/noop-tool.ts` +
      its `tools: probe_note` entry + a one-line usage nudge; merge; `make
      gate_suppression EXPECT_TOOL=probe_note` (≥1 platform episode; expect
      `pi_local_calls ≥ 1`, tool absent from τ's trajectory, seam counters clean);
      commit `gates/suppression_canary.json`; revert the declaration; re-verify
      `reset_h0` byte-identity.
- [ ] **Cut the lock**: seq 10, `010_adopt-bm25-luna56`; `protocol:` block G=8,
      `identity_generations: [1]`, B=12, T=36, `num_trials: 3`, `batch_mode: fixed`,
      `allow_within_batch_verification: true`, `require_human_approval: false`
      (ratified); nine-cell `reading_key` naming the sig-up × sig-up cell as the
      pre-registered success and reading every flat-primary cell against the
      reachable-harvest co-metric (≥90% = objective exhausted → pool/domain decision;
      low = loop found nothing); `operational.process_metric_tools` reviewed; **both
      concurrency defaults carried from seq 6/8 unchanged** (lock
      `operational.max_concurrency: 3`, `make batch` pinned 3 — the values that ran
      seq 8's 168 platform episodes with zero disconnect/timeout/stall incidents;
      operational, outside the fingerprint, droppable per run if provisioning churn
      shows).
- [ ] **Gates**: `make gate_a0a` (blocking; full adapter suite + mock smoke); platform
      seam canary; `power_envelope.py --write` (must be REACHABLE); commit all PASS
      records; first run writes the freeze snapshot.
- [ ] **Go**: H0 held-out → `batch_01` → gen-001 identity record → `batch_02` (the A/A
      noise measurement) → seven mutation slots under the D29 ladder and the
      surface-exercise obligation → endpoint `batch_09` → reveal → §29 walk with the
      D33 attestation → closure split into batch-derived vs held-out sections.

**Validate:** every gate verdict committed before the first graded episode; the
envelope REACHABLE; strata restated in the freeze snapshot; the identity
pre-registration honored at reveal (mechanical).

### Phase 5.11 — Seq-12 stage (D36; Phase 0 first, and the freeze waits on its result)

**Nothing here is frozen yet, and that is deliberate**: the lock cannot be cut until Phase 0
says which retrieval backend seq 12 runs on. Execute in order, in a fresh session under the
D33 recall scope.

- [ ] **Preconditions.** `make check` green; `make reset_h0` reports byte-identity (the
      recipe was returned to `h0-baseline` at seq 10's close, so this should say "the recipe
      already was H0"); model-pair keys live; `make weather` clean.

- [ ] **Phase 0 — the ceiling probe. This decides whether seq 12 runs at all.**
      Build **H-expert**: a harness hand-built with full access to the candidate tasks and
      unlimited effort. It is never shipped, never `h0-baseline`, and never part of the loop
      — it exists only to bound the range, so it MAY do things a loop change may not (encode
      procedure specific to the observed failure modes). It must still respect the frozen
      surfaces: no `<policy>` edit, no model change, no reading `benchmark/vendor/` at
      runtime, no gold values.
      Run **H0-current** and **H-expert** over ~30 candidate tasks × 3 trials on the local
      lane, **under both `bm25` and `openai_embeddings`** (switching needs `make policy` to
      regenerate the frozen region and refresh the lock's tool catalogue).
      Score with `scripts/headroom.py --h0 … --expert … --label <backend> --write …`.
      Roughly 360 episodes ≈ $8 per backend.

- [ ] **The two pre-registered decisions Phase 0 makes, written down BEFORE it runs.**
      (a) **Backend**: freeze whichever yields the larger *harness headroom*
      (`H_expert − H0`), not the larger absolute score; a tie goes to `openai_embeddings`
      (what τ² publishes, restoring comparability, and the key is already required at grading
      time). (b) **Go / no-go**: if headroom ≤ 5 pp under both backends, **seq 12 is not run**
      — the objective offers too little for any harness to win, the loop would reproduce the
      prior nulls without being able to explain them, and the next move is a domain decision
      (`telecom-workflow` is the candidate: procedural and multi-step, where harness
      discipline should actually bite). That outcome is a result, costs ~$16, and is written
      up as one.

- [ ] **Compose the partition** (only if Phase 0 says go). **B = 30**, using the probe as the
      *empirical* reachability oracle — a task H-expert passes is provably harness-reachable,
      which is what makes a batch larger than the marginal band safe. **T = 36, and it is
      forced**: the pool holds exactly 36 tasks never used as a batch task by any experiment,
      and D33 keeps batch-used tasks burnt for held-out use forever. They are the same 36
      seq 10 used, so the reuse declarations carry over per source with the D33 procedural
      basis restated.
      - batch-eligible stock, proven walls excluded (54): `task_001 task_002 task_003
        task_004 task_005 task_006 task_008 task_010 task_014 task_015 task_020 task_023
        task_024 task_027 task_029 task_032 task_037 task_038 task_040 task_041 task_043
        task_045 task_046 task_047 task_050 task_053 task_054 task_055 task_056 task_057
        task_058 task_060 task_061 task_062 task_063 task_064 task_065 task_066 task_069
        task_071 task_074 task_076 task_077 task_079 task_080 task_081 task_083 task_087
        task_088 task_089 task_090 task_094 task_101 task_102`
      - held-out (36, forced): `task_007 task_012 task_016 task_017 task_018 task_019
        task_021 task_022 task_025 task_031 task_033 task_035 task_036 task_039 task_044
        task_048 task_049 task_051 task_052 task_059 task_067 task_068 task_073 task_075
        task_078 task_084 task_085 task_086 task_091 task_092 task_093 task_095 task_097
        task_098 task_099 task_100`

- [ ] **Cut the lock**: seq 12; `protocol:` **G=7**, `identity_generations: [1]`, **`heldout_generations: [0, 4, 7]`**, B=30, T=36, `num_trials: 3`,
      `batch_mode: fixed`, `identity_generations: [1]`, `require_human_approval` per the
      D23 envelope, the nine-cell reading key **restated for the gap-closure primary**, and
      the retrieval backend Phase 0 chose. `make policy` if the backend moved.

- [ ] **Gates**: `make gate_a0a`; platform seam canary; suppression canary; power envelope.
      Commit every verdict before the first graded episode.

- [ ] **Go**: H0 held-out → `batch_01` → gen-001 identity → `batch_02` → mutation slots under
      the D36 composition policy (bundle 3–5 non-interacting changes, ≥3-task-or-structural
      targets, delta-stated counters, ≤2 reverts, one slot reserved for `sub-agent`) with the
      **futility check** from the midpoint on → endpoint round → reveal → §29 walk with the
      D33 attestation → closure split batch-derived vs held-out.

**Validate:** headroom measured and committed before the first generation; the backend
decision traceable to the probe rather than to preference; the primary reported as
gap-closure with the raw endpoint test beside it.

### Phase 6 — Full experiment + reporting (deferred; contingent on the § 8 groundwork)

> **Amended by D32/D33 (2026-08-17):** the pool ledger shows **zero virgin tasks**, so a
> zero-exposure partition is impossible in `banking_knowledge` — the "47 + 50 > ~61"
> caveat below is now an impossibility, not a squeeze. Under D33's cross-experiment
> firewall, seq 10 carries a capability claim on the **procedural basis** (T=36
> pure-holdout, quarantined reveal record); the **unqualified zero-exposure claim** is a
> **domain decision** (new task oracle), user-owned, pencilled for seq 12. This phase's
> checklist stands for whichever experiment next runs at full scale.

- [ ] Freeze the next even seq (per D15; seq 6 was consumed by the fixed-batch-at-depth run,
      D23): sizes per D11 revisited against the seq-6 independent review's instrument rules
      (stratified batch, fresh holdout, full-quadrant reading key); `reset_h0`; A.0a PASS;
      partition frozen. Note the fresh-pool discipline cannot fully hold at T=47
      (47 + 50 > ~61 never-used tasks) — the freeze decision must state which reuse it
      accepts.
- [ ] Run the six held-out evaluations and five generations (~282 local + 50 platform
      episodes ≈ $210–230 at measured seq-2 rates — supersedes the pre-run $75–90
      estimate — ~20–28 h spread over ~a week of sessions; budget
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
| Debug experiment (seq 2, D10 sizes) — **recorded** | 32 local + 12 platform | **≈ $29 on manifests** ($19.92 local, agent + user-sim; $9.05 platform conversation billing — the τ-side user-sim on the platform lane is not manifest-captured) + ~$3 screens/probes | — | **≈ 3.5 h** incl. review latency (recorded) |
| Luna calibration pilot (D12) — **recorded** | 28 local | **$1.06** ($0.038 mean / $0.026 median per episode) | — | ≈ 7 min at 10-wide (recorded) |
| Haiku calibration pilot (D13) — **recorded** | 28 local | **$6.22** ($0.283 mean / $0.252 median per episode) | — | ≈ 9 min at 10-wide (recorded) |
| Powered experiment (now seq 4; D11 sizes, D13 haiku pair) | 168 local + 40 platform | ≈ **$55–65 at haiku pilot rates** (local $0.283/ep; platform $0.218/ep measured). If D12's luna returns: ≈ $10–20. Sonnet basis ($132–165) superseded | ~7–9 h | ≈ 3–5 h compute, ~2–3 days elapsed with review gates |
| Full experiment (T=47 scale, deferred past seq 10; the fresh-pool framing is superseded by D33) | 282 local + 50 platform | local side ≈ $11 at luna rates — cost no longer separates the tiers; wall-clock and the D33 claim basis decide | ~9–12 h | ≈ 3–5 h compute, ~2–3 days elapsed |
| Endpoint reliability addendum (conditional, D11) | 112 local (+2 trials × H0/H5 × 28) | ≈ $70 (scales with trial count) | ~5 h | ≈ 1–2 h |

Basis (pre-run estimates replaced by seq-2 recorded actuals, 2026-08-14, per the
Conventions): **$0.62 mean / $0.53 median per local episode** (n=32, agent + user-sim,
held-out manifests) and **$0.70 mean / $0.50 median per platform episode** (n=13
manifest rows, conversation billing; long episodes dominate). This is ~2.3× the
original $0.20-median basis — the correction, not the estimate, prices future
experiments. Concurrent columns
assume the lock default of 10 with rounds self-capped at their episode count: local
held-out rounds run T-wide up to that default (2.80× already measured at N=3 on the mock round);
platform batch rounds run at `--max-concurrency 2` (the `make batch` default) to
bound concurrent-start provisioning contention (the "~2-sandbox quota" was corrected
2026-08-14 — no such quota; slow starts are tolerated by the runner
rather than converted into retries). Concurrency changes wall-clock only — cost is
per-episode and unchanged.

## 7. Risks

| Risk | Mitigation |
|---|---|
| Single-trial noise read as signal | D2 noise band in every rendering; transition tables distinguish net movement from churn; optional endpoint study. |
| Platform stalls recur in batch rounds, polluting diagnosis | Phase 2 platform-health check gates the debug run; incident counters ride every manifest row; `make fidelity` on demand. |
| Held-out leak via habit (grep/glob/dashboard sweep) | Out-of-tree vault; muted wrapper is the only button; dashboard never walks the vault; leak-check is an explicit Phase 4 validation item. |
| Observation/pattern harvest not eligible in cadence | 30-min eligibility + 10-min scan confirmed from platform docs — schedule harvest 2 accordingly; metrics-over-spans fallback with evidence tier stated. |
| H0 secretly broken (or saturated) under the firewall | D8: the B1 read is visible by design; halt on 0/B or B/B. |
| Batch of 8–10 too thin for a confident diagnosis | Prevalence stated as n/B; prior batches' evidence remains queryable (protocol §13); a directional hypothesis is a legitimate, recorded outcome. D11 sized B=8 so a 25%-prevalence mode shows ≥2 in-batch witnesses 63% of the time (vs 26% at the debug B=4). |
| Rejected mutations stall progress | D5 identity generations keep the experiment moving and are first-class results (protocol §25). |

## 8. Conventions

- One phase in flight at a time; scope growth ⇒ stop and re-plan here first.
- Check a box by appending the landing date: `- [x] … (2026-08-15)`.
- Estimates above are replaced by recorded actuals as phases close.
- Every writeup that touches held-out data states the enforcement boundary
  (structural on the platform, procedural on local artifacts) — no exceptions.

## 9. Lessons learned

Distilled from Phases 0–4 and the seq-3 sizing pass — the claim first, then the
evidence and where the full rationale lives. Nothing here changes a decision; the
D-rows and cited analyses stay authoritative.

- **Screen the pool with a real agent before freezing.** The cheap screens (first-turn
  probe, scripted agent) passed 97/97; the crash class that voided seq 1 needed a real
  agent's replies to trigger (task_034, upstream tau2-bench#470). Screening is now a
  freeze step (`contract/protocol.md` §0); the void-and-reseq procedure is the fallback.
- **A green reward can hide a broken seam.** One stalled episode still graded 1.0 on
  answers already landed. Completeness reporting, incident counters on every manifest
  row, and `STALL_WARN_SECONDS` exist because of this; a score is trusted only alongside
  its seam-health row (README § Two transports; `contract/constraints.md` § divergences).
- **Estimates do not survive contact with episodes.** Recorded per-episode cost ran
  ~2.3× the planning basis ($0.62/$0.53 mean/median local vs the assumed $0.20 median),
  and episodes grew ~8%/generation with instruction size. §6 now prices from manifest
  actuals only.
- **Witness representation drives held-out sizing.** A mutation can only move the curve
  if its failure mode has witnesses in T: at T=8 a ~10-task mode had 60%/19% odds of
  ≥1/≥2 witnesses — half of seq 2's real fixes were likely invisible by construction
  (D10 chose T=8 knowingly; D11's power analysis made the cost explicit and sized T=28).
- **Statistical honesty scales with T.** The debug-era "+2 tasks reads directional"
  eyeball bar does not carry: at T=28 the null produces a ≥2-task gain 29% of the time
  and the bar is ≥4–5 tasks. Bands and bars are restated per scale, everywhere a curve
  renders (D11; `results/experiment_002_bm25-sonnet46/SIZING_ANALYSIS.md`).
- **A carried measurement is not a new draw.** Identity generations repeat their
  predecessor's held-out outcomes; the pre-registered trend test excludes them rather
  than counting one measurement twice (`tau_adapter/reveal.py`).
- **Diagnosis quality is the binding constraint on the loop.** The observation harvest
  returned zero rows in-window every time; full-transcript reads carried every seq-2
  diagnosis, and B=4 quoted prevalence in quarters. B=8 (D11) is the cheapest lever on
  mutation quality — the variable that separates a working loop from a flat curve.
- **Mutations over-fire.** The "thoroughness" instructions plausibly broke a passing
  task by adding unrequested state changes (task_036 over-action). Over-action is a
  first-class failure mode for future diagnosis
  (`results/experiment_002_bm25-sonnet46/held_out/ANALYSIS_partial_metrics.md`).
- **Process metrics move before reward does.** Retrieval intensity +20%, transfers
  −67%, tool usage +18% across seq 2 while the pass count fell — tracked since as
  pre-declared directional secondaries, never significance claims (same analysis; D11).
- **Tasks are burnt for held-out use once a loop tunes on them or a reveal exposes
  them.** Seq 3's partition excludes all 20 seq-2 tasks for exactly this reason — a
  fresh-pool discipline feasible at T=28 and arithmetically impossible at T=47 (D11).
- **The environment breaks too, and the remedy is never a local patch.** Benchmark
  defects travel upstream (`.ai-state/UPSTREAM_ISSUES.md`); the freeze is voided and
  re-cut under a new seq with exclusions documented (seq 1 → seq 2).
- **Per-episode reward is a draw; pool across tasks.** Ten trials of one frozen
  configuration split 6/10 — repeated trials buy little for generation comparison, and
  D2's single-trial-pooled design held through both the run and the D11 re-examination.
- **A model swap re-prices everything, and a $1 pilot re-measures it.** The tasks in
  nobody's partition (stratification leftovers + prior-experiment burnt tasks) form a
  firewall-clean calibration set; the luna pilot measured baseline 25% (no
  saturation), 16× cheaper episodes, and verified the D11 sizing at the measured
  baseline — all before the freeze, for $1.06
  (`results/experiment_003_powered-bm25-luna56/CALIBRATION_PILOT.md`).
