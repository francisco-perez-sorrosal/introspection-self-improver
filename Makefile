# Lane entry points. Each target belongs to exactly one lane, and the lanes do not reach into
# each other: benchmark/ drives target-agent/ by path, never the reverse.

.PHONY: help bootstrap check policy propose_split smoke single_task bench batch heldout reset_h0 reveal fidelity gate_a0a gate_seam weather grade dashboard batch_curve

BENCH  := benchmark
VENDOR := $(BENCH)/vendor/tau2-bench
GEN    ?= generation_000

# One experiment is one freeze. The id derives from benchmark_lock.yaml (experiment.seq +
# experiment.name → <seq>_<name>, e.g. 001_bm25-sonnet46), so the results path is derived —
# results/experiment_<id>/$(GEN)/<run> — never chosen per invocation.
# run.py additionally refuses any results/ path outside the lock's experiment, so a stale or
# empty value here cannot land a run in the wrong experiment's record.
EXPDIR  := $(shell python3 $(BENCH)/scripts/experiment_id.py --dir)
RESULTS := results/$(EXPDIR)/$(GEN)

# Where the agent runs. `local` is a Pi subprocess here and produces no Introspection evidence.
# `platform` runs every episode as a task in the development environment — conversations, traces,
# spans, cost and commit lineage — and starts `introspection dev` itself so the cloud sandbox can
# reach the tau bridge on this machine. It needs a Runtime, a development API-key agent, and the
# `tau` MCP binding left disconnected; the runner checks all three and says what is missing.
TRANSPORT ?= local

# Platform records land beside local ones instead of on top of them. The lanes host the agent
# differently, so their trajectories are not interchangeable and must stay separable.
# Deferred (`=`, not `:=`) so the round targets' target-specific TRANSPORT reaches it.
SUFFIX = $(if $(filter platform,$(TRANSPORT)),_platform,)

# How the recipe is started locally. `pi` spawns it directly. `introspection` routes through
# `introspection local`, which resolves the recipe through the Runtime manifest and validates it
# per episode, at about +5.5s each. Either way the recipe is validated once per run. Ignored by
# TRANSPORT=platform, where the runtime resolves the recipe.
LAUNCHER ?= pi

# The tau2 console script is a separate process and does not import tau_adapter, so it needs
# the data directory named explicitly. Python entry points get it from tau_adapter/__init__.py.
TAU_ENV := TAU2_DATA_DIR=$(CURDIR)/$(VENDOR)/data
RUN     := cd $(BENCH) && $(TAU_ENV) uv run

help:
	@echo "make bootstrap   reproduce the benchmark lane from benchmark/benchmark_lock.yaml"
	@echo "make check       validate the recipe, every frozen surface, and partition isolation"
	@echo "make policy      write tau's domain policy into the recipe's frozen <policy> region"
	@echo "make propose_split  propose the experiment's task partition from the lock (WRITE=1 freezes it)"
	@echo "make smoke       one mock-domain task through the seam (diagnostic, not reportable)"
	@echo "make single_task one locked-domain task, then grade it: make single_task TASK=task_001"
	@echo "make bench       the WHOLE locked task split, then grade it (long and costly)"
	@echo "make batch       improvement batch round, platform lane: make batch B=1 GEN=generation_000"
	@echo "make heldout     hidden held-out round into the vault: make heldout GEN=generation_000"
	@echo "make reset_h0    restore the recipe to the h0-baseline tag (replace, not merge)"
	@echo "make reveal      end-of-experiment: unseal the vault into results/ (final tag required)"
	@echo "make batch_curve fixed-batch saturation curve + paired endpoint test (batch_mode fixed)"
	@echo "make fidelity    run one task in BOTH lanes and check the adapter invariants"
	@echo "make gate_a0a    A.0a gate: adapter suite + mock smoke, verdict under gates/"
	@echo "make gate_seam   platform seam canary; batch rounds refuse to start without a fresh PASS"
	@echo "make weather     probe the user-sim provider for empty completions before spending a round"
	@echo "make grade       re-grade an existing run: make grade OUT=results/.../mock_smoke"
	@echo "make dashboard   local read-only results viewer over results/ (dashboard/)"
	@echo ""
	@echo "TRANSPORT=local|platform   where the agent runs (default local)"
	@echo "LAUNCHER=pi|introspection  how to start it locally (default pi)"
	@echo "GEN=generation_NNN         generation directory under results/$(EXPDIR)/"
	@echo ""
	@echo "The experiment comes from benchmark_lock.yaml (experiment.seq + experiment.name):"
	@echo "results land under results/$(EXPDIR)/$(GEN)/ and the runner refuses any other"
	@echo "results/ path."
	@echo ""
	@echo "  make single_task                     one task, agent on this machine"
	@echo "  make single_task TRANSPORT=platform  same task, agent on a dev runtime,"
	@echo "                                       observable via 'introspection conversations'"

# Idempotent. Fetches the pinned tau2-bench checkout, verifies its commit, syncs the Python
# environment, and derives the recipe's MCP binding from its committed example.
bootstrap:
	@python3 $(BENCH)/scripts/bootstrap.py

# What the pre-commit hook and CI run. Recipe validity plus every surface that must not drift.
check:
	@introspection check -o report
	@python3 $(BENCH)/scripts/check_policy_region.py
	@$(RUN) python scripts/check_partition_isolation.py
	@$(RUN) python scripts/improvement_record.py --verify-current

# Regenerates the frozen region and records its hash and tool catalogue in the lock. Run after
# changing the locked domain or retrieval config, and never to "fix" a failing check without
# understanding why it failed.
policy:
	@$(RUN) python scripts/gen_policy_region.py

# Propose — and with WRITE=1 freeze — the current experiment's task partition, sizes and
# batch mode from the lock's protocol block. Under batch_mode fresh this stratifies over
# the pool (EXCLUDE drops screened-out tasks); under batch_mode fixed the lists are
# explicit freeze decisions — pass BATCH_TASKS and HELD_OUT_TASKS (comma-separated ids)
# and record the composition rationale in NOTE. Seq 5 froze this way: the 8 known-fail
# fixed-batch tasks plus seq-4's T reused verbatim (plan D17/D19; the manifest header
# carries the full rationale). Check a frozen manifest any time with
# `scripts/propose_split.py --verify`. A later experiment re-decides these through its
# own decision row and a seq bump, never by editing a frozen manifest.
EXCLUDE ?=
BATCH_TASKS ?=
HELD_OUT_TASKS ?=
NOTE ?=
propose_split:
	@$(RUN) python scripts/propose_split.py \
		$(if $(EXCLUDE),--exclude "$(EXCLUDE)",) \
		$(if $(BATCH_TASKS),--batch-tasks "$(BATCH_TASKS)",) \
		$(if $(HELD_OUT_TASKS),--held-out-tasks "$(HELD_OUT_TASKS)",) \
		$(if $(WRITE),--write --force --note "$(NOTE)",)

# Diagnostic: the mock domain is not the locked domain, so the recipe is materialised with
# mock's policy and the result is not comparable to anything. This is the cheap seam gate.
# TRANSPORT=platform is refused here rather than silently ignored: `introspection dev` serves the
# recipe from the work-tree, and diagnostic mode materialises a modified one elsewhere.
smoke:
	@$(RUN) python tau_adapter/run.py --domain mock --task-ids create_task_1 \
		--transport $(TRANSPORT) --launcher $(LAUNCHER) \
		--out ../$(RESULTS)/mock_smoke --overwrite
	@$(MAKE) --no-print-directory grade OUT=$(RESULTS)/mock_smoke

# One task on the locked domain — the working loop while iterating on the harness.
TASK ?= task_001
single_task:
	@$(RUN) python tau_adapter/run.py --task-ids $(TASK) \
		--transport $(TRANSPORT) --launcher $(LAUNCHER) \
		--out ../$(RESULTS)/$(TASK)$(SUFFIX) --overwrite
	@$(MAKE) --no-print-directory grade OUT=$(RESULTS)/$(TASK)$(SUFFIX)

# The whole locked task split. Omitting --task-ids is what selects every task; the runner
# prints the episode count and the concurrency it will use before starting.
#
# This is the expensive target: 97 tasks in the banking_knowledge base split, run at the
# lock's max_concurrency default. Budget accordingly and expect it to be the input to
# the per-generation cost estimate rather than something to run casually.
bench:
	@$(RUN) python tau_adapter/run.py --transport $(TRANSPORT) --launcher $(LAUNCHER) \
		--out ../$(RESULTS)/bench_full$(SUFFIX) --overwrite
	@$(MAKE) --no-print-directory grade OUT=$(RESULTS)/bench_full$(SUFFIX)

# One improvement batch from the frozen partition (SIA_EVALUATION_PLAN.md D1): the platform
# lane is the round's meaning, not a preference — a command-line TRANSPORT=local reaches
# run.py and is refused there with the reason. Resume-friendly: no --overwrite, ever, so a
# rerun re-runs only the missing (trial, task, seed) pairs. Graded immediately, because
# batch evidence is fully observable by design — it is what `operate` diagnoses from —
# and the graded artifact persists under graded/ so records cite a file, not a terminal.
B ?= 1
BATCH_DIR = batch_$(shell printf '%02d' $(B))
batch: TRANSPORT = platform
# --max-concurrency 3 (4 -> 3, 2026-08-16, seq-6 freeze, user-directed): no sandbox
# quota exists (the "~2 concurrent" reading was a misdiagnosis, corrected 2026-08-14 —
# contract/constraints.md § Platform-lane concurrency), and 4-wide ran clean on
# 2026-08-15. 3 is margin taken deliberately for an unattended seven-round run, not a
# response to an incident: batch rounds ARE the diagnosis evidence, and a seam-timeout
# cell costs a diagnosis, while the extra wall-clock costs only wall-clock. Operational,
# outside the freeze fingerprint. If a round shows start-latency churn (the 100-650s
# provisioning tail returning), drop it further per run rather than editing this
# default, so the record `operate` reads stays clean.
batch:
	@$(RUN) python tau_adapter/run.py --batch $(B) --transport $(TRANSPORT) \
		--max-concurrency 3 \
		--out ../$(RESULTS)/$(BATCH_DIR)
	@$(RUN) python scripts/grade.py $(CURDIR)/$(RESULTS)/$(BATCH_DIR)/results.json \
		--output-dir $(CURDIR)/$(RESULTS)/$(BATCH_DIR)/graded

# The hidden held-out evaluation (D1/D9): local lane only, outputs sealed out of tree in
# the vault (~/.sia_vault), terminal shows completeness alone. GEN names the generation
# being measured. The lane guard here catches an exported TRANSPORT before any process
# starts; scripts/run_heldout.py owns everything else.
heldout:
	@test "$(TRANSPORT)" = "local" || (echo "✗ held-out runs on the local lane only (SIA_EVALUATION_PLAN.md D1): platform evidence for held-out tasks must never exist" && exit 1)
	@$(RUN) python scripts/run_heldout.py --generation $(GEN)

# Restore the recipe to the H0 baseline (D6): replace, not merge; byte-identity asserted;
# the machine-local .introspection/local.json preserved. Leaves the restore staged for the
# operator to review and commit — the commit is the experiment's record of starting at H0.
reset_h0:
	@python3 $(BENCH)/scripts/reset_h0.py

# End-of-experiment reveal (D9): runnable only once the final generation tag exists. Copies
# the vault into results/experiment_<id>/held_out/, computes the progression artifacts, and
# fills every improvement record's held_out_result. The one sanctioned read of the vault.
reveal:
	@$(RUN) python scripts/reveal.py

# Runs the same task in both lanes and compares them. Adapter-owned properties are asserted; the
# reward is not, because a per-task reward here is a draw and comparing two of them proves nothing.
# On-demand cross-lane diagnostic (SIA_EVALUATION_PLAN.md D4) — not a gate.
fidelity:
	@$(MAKE) --no-print-directory single_task TASK=$(TASK) TRANSPORT=local
	@$(MAKE) --no-print-directory single_task TASK=$(TASK) TRANSPORT=platform
	@$(RUN) python fidelity/compare_lanes.py \
		$(CURDIR)/$(RESULTS)/$(TASK) $(CURDIR)/$(RESULTS)/$(TASK)_platform

# A.0a gate (blocking): the adapter suite plus the mock smoke, verdict recorded under
# $(RESULTS)/gates/ so the gate's pass is citable, not just a green terminal.
gate_a0a:
	@$(RUN) python scripts/gate_a0a.py --gen-dir $(CURDIR)/$(RESULTS)

# Platform seam canary (blocking for batch rounds): one non-partition task through the real
# tunnel, judged on the sandbox seam counters, verdict under results/$(EXPDIR)/gates/.
# run.py refuses a batch when this verdict is missing, FAILED, or older than the last
# change under benchmark/tau_adapter — the failure domain A.0a's local lane cannot reach.
gate_seam:
	@$(RUN) python scripts/gate_seam_canary.py $(if $(TASK),--task $(TASK),)

# Provider-weather probe for the frozen user-sim surface: N direct calls with the lock's
# exact model+args, counting empty completions. Seconds and cents, instead of discovering a
# storm by orphaning sandboxes. Diagnostic — exits nonzero on dirty weather, gates nothing.
weather:
	@$(RUN) python scripts/weather.py

# The fixed-batch saturation curve + its pre-registered paired endpoint test (seq 5's
# primary instrument, plan D17). Refuses under batch_mode fresh. Batch evidence is fully
# observable, so this runs any time; interim invocations are descriptive — the primary
# statistic is the endpoint pair (H0's and HG's batch rounds) only.
batch_curve:
	@$(RUN) python scripts/batch_curve.py

# Read-only viewer over results/ — its own lane, never a pipeline participant. Stdlib only;
# reads dashboard/config.json for the results pointer and port.
dashboard:
	@python3 dashboard/serve.py

# The only sanctioned way to produce a number. Calls tau's own evaluate_trajectories; the wrapper
# exists solely to grade against the retrieval config the run recorded, instead of letting the
# evaluator fall back to a config the run never used. See scripts/grade.py.
grade:
	@test -n "$(OUT)" || (echo "usage: make grade OUT=results/<experiment>/<gen>/<run>" && exit 1)
	@$(RUN) python scripts/grade.py $(CURDIR)/$(OUT)/results.json
