# Lane entry points. Each target belongs to exactly one lane, and the lanes do not reach into
# each other: benchmark/ drives target-agent/ by path, never the reverse.

.PHONY: help bootstrap check policy smoke single_task bench discovery validation checkpoint \
	fidelity fidelity_gate gate_a0a anchor_stock grade dashboard

BENCH  := benchmark
VENDOR := $(BENCH)/vendor/tau2-bench
GEN    ?= generation_000

# One experiment is one freeze. The id comes from benchmark_lock.yaml (experiment.id), so the
# results path is derived — results/experiment_<id>/$(GEN)/<run> — never chosen per invocation.
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

# Which harness arm a round belongs to. G0 has only a baseline; G1+ candidate rounds pass
# ARM=candidate so the two arms' records never collide (v2 §2.7's <purpose>_<arm> naming).
ARM ?= baseline

# The A.0b gate's task set — deterministic, derived from the frozen split manifest
# (first ACTION task + first DB tasks of the discovery list). Lazy: only evaluated when a
# fidelity_gate run actually needs it.
FID_TASKS ?= $(shell cd $(BENCH) && uv run python scripts/propose_split.py --fidelity-set 2>/dev/null)

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
	@echo "make check       validate the recipe and every frozen surface"
	@echo "make policy      write tau's domain policy into the recipe's frozen <policy> region"
	@echo "make smoke       one mock-domain task through the seam (diagnostic, not reportable)"
	@echo "make single_task one locked-domain task, then grade it: make single_task TASK=task_001"
	@echo "make bench       the WHOLE locked task split, then grade it (long and costly)"
	@echo "make discovery   the frozen discovery split as an experiment round (platform lane)"
	@echo "make validation  the frozen validation split as an experiment round (platform lane)"
	@echo "make checkpoint  the full-domain checkpoint at x1 trial (H2 decision; platform lane)"
	@echo "make fidelity    run one task in BOTH lanes and check the adapter invariants"
	@echo "make gate_a0a    A.0a gate: adapter suite + mock smoke, verdict under gates/"
	@echo "make fidelity_gate  A.0b gate: the gate task set x frozen trials in BOTH lanes"
	@echo "make anchor_stock   A.0c anchor: tau's stock agent natively on the discovery split"
	@echo "make grade       re-grade an existing run: make grade OUT=results/.../mock_smoke"
	@echo "make dashboard   local read-only results viewer over results/ (dashboard/)"
	@echo ""
	@echo "TRANSPORT=local|platform   where the agent runs (default local; rounds default platform)"
	@echo "LAUNCHER=pi|introspection  how to start it locally (default pi)"
	@echo "GEN=generation_NNN         generation directory under results/$(EXPDIR)/"
	@echo "ARM=baseline|candidate     which harness arm a round belongs to (default baseline)"
	@echo ""
	@echo "The experiment comes from benchmark_lock.yaml (experiment.id): results land under"
	@echo "results/$(EXPDIR)/$(GEN)/ and the runner refuses any other results/ path."
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

# Regenerates the frozen region and records its hash and tool catalogue in the lock. Run after
# changing the locked domain or retrieval config, and never to "fix" a failing check without
# understanding why it failed.
policy:
	@$(RUN) python scripts/gen_policy_region.py

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
# This is the expensive target: 97 tasks in the banking_knowledge base split, run serially
# because max_concurrency is frozen at 1. Budget accordingly and expect it to be the input to
# the per-generation cost estimate rather than something to run casually.
bench:
	@$(RUN) python tau_adapter/run.py --transport $(TRANSPORT) --launcher $(LAUNCHER) \
		--out ../$(RESULTS)/bench_full$(SUFFIX) --overwrite
	@$(MAKE) --no-print-directory grade OUT=$(RESULTS)/bench_full$(SUFFIX)

# Experiment rounds. They default to the platform lane — the only lane that leaves platform
# evidence, and where every G0+ round runs — while an explicit TRANSPORT=local on the command
# line still wins for debugging. No --overwrite: an interrupted round resumes, re-spending
# nothing, and a completed round refuses rather than being silently replaced.
discovery validation checkpoint: TRANSPORT = platform

discovery:
	@$(RUN) python tau_adapter/run.py --split discovery --transport $(TRANSPORT) --launcher $(LAUNCHER) \
		--out ../$(RESULTS)/discovery_$(ARM)$(SUFFIX)
	@$(MAKE) --no-print-directory grade OUT=$(RESULTS)/discovery_$(ARM)$(SUFFIX)

validation:
	@$(RUN) python tau_adapter/run.py --split validation --transport $(TRANSPORT) --launcher $(LAUNCHER) \
		--out ../$(RESULTS)/validation_$(ARM)$(SUFFIX)
	@$(MAKE) --no-print-directory grade OUT=$(RESULTS)/validation_$(ARM)$(SUFFIX)

# The full-domain checkpoint (97 tasks, x1 trial by the H2 decision — the recognizable
# number at a quarter of the cost, labeled single-trial). Its output includes test-split
# tasks; per the held-out enforcement decision, those episodes are not to be inspected.
checkpoint:
	@$(RUN) python tau_adapter/run.py --checkpoint --transport $(TRANSPORT) --launcher $(LAUNCHER) \
		--out ../$(RESULTS)/checkpoint_full_domain$(SUFFIX)
	@$(MAKE) --no-print-directory grade OUT=$(RESULTS)/checkpoint_full_domain$(SUFFIX)

# Runs the same task in both lanes and compares them. Adapter-owned properties are asserted; the
# reward is not, because a per-task reward here is a draw and comparing two of them proves nothing.
# This is the §15 Phase A.0 instrument aimed at the two transports.
fidelity:
	@$(MAKE) --no-print-directory single_task TASK=$(TASK) TRANSPORT=local
	@$(MAKE) --no-print-directory single_task TASK=$(TASK) TRANSPORT=platform
	@$(RUN) python fidelity/compare_lanes.py \
		$(CURDIR)/$(RESULTS)/$(TASK) $(CURDIR)/$(RESULTS)/$(TASK)_platform

# A.0a gate (blocking): the adapter suite plus the mock smoke, verdict recorded under
# $(RESULTS)/gates/ so the gate's pass is citable, not just a green terminal.
gate_a0a:
	@$(RUN) python scripts/gate_a0a.py --gen-dir $(CURDIR)/$(RESULTS)

# A.0b gate (blocking): the deterministic gate task set x the frozen trial count, both
# lanes, adapter invariants per episode plus aggregate agreement within trial noise.
# Interruptions resume; a completed lane refuses (delete the round dirs to re-run).
fidelity_gate:
	@test -n "$(FID_TASKS)" || (echo "cannot derive the A.0b task set — is the split manifest frozen?" && exit 1)
	@$(RUN) python tau_adapter/run.py --task-ids $(FID_TASKS) --transport local --launcher $(LAUNCHER) \
		--out ../$(RESULTS)/fidelity_gate
	@$(MAKE) --no-print-directory grade OUT=$(RESULTS)/fidelity_gate
	@$(RUN) python tau_adapter/run.py --task-ids $(FID_TASKS) --transport platform \
		--out ../$(RESULTS)/fidelity_gate_platform
	@$(MAKE) --no-print-directory grade OUT=$(RESULTS)/fidelity_gate_platform
	@$(RUN) python fidelity/compare_lanes.py \
		$(CURDIR)/$(RESULTS)/fidelity_gate $(CURDIR)/$(RESULTS)/fidelity_gate_platform \
		--gate --verdict-out $(CURDIR)/$(RESULTS)/gates/a0b.json

# A.0c anchor (informational): tau's stock LLMAgent natively under the lock's exact
# configuration — the scaffold delta, and the only configuration where tau's seed reaches
# the agent. Under the bm25 freeze it anchors nothing about published comparability.
anchor_stock:
	@$(RUN) python scripts/run_stock_anchor.py --out ../$(RESULTS)/anchor_stock
	@$(MAKE) --no-print-directory grade OUT=$(RESULTS)/anchor_stock

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
