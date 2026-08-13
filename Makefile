# Lane entry points. Each target belongs to exactly one lane, and the lanes do not reach into
# each other: benchmark/ drives target-agent/ by path, never the reverse.

.PHONY: help bootstrap check policy smoke single_task bench grade

BENCH  := benchmark
VENDOR := $(BENCH)/vendor/tau2-bench
GEN    := generation_000

# How the recipe is started. `pi` spawns it directly. `introspection` routes through
# `introspection local`, which resolves the recipe through the Runtime manifest and validates it
# per episode, at about +5.5s each. Either way the recipe is validated once per run.
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
	@echo "make grade       re-grade an existing run: make grade OUT=results/.../mock_smoke"
	@echo ""
	@echo "LAUNCHER=pi|introspection  how to start the recipe (default pi)"

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
smoke:
	@$(RUN) python tau_adapter/run.py --domain mock --task-ids create_task_1 \
		--launcher $(LAUNCHER) --out ../results/$(GEN)/mock_smoke --overwrite
	@$(MAKE) --no-print-directory grade OUT=results/$(GEN)/mock_smoke

# One task on the locked domain — the working loop while iterating on the harness.
TASK ?= task_001
single_task:
	@$(RUN) python tau_adapter/run.py --task-ids $(TASK) \
		--launcher $(LAUNCHER) --out ../results/$(GEN)/$(TASK) --overwrite
	@$(MAKE) --no-print-directory grade OUT=results/$(GEN)/$(TASK)

# The whole locked task split. Omitting --task-ids is what selects every task; the runner
# prints the episode count and the concurrency it will use before starting.
#
# This is the expensive target: 97 tasks in the banking_knowledge base split, run serially
# because max_concurrency is frozen at 1. Budget accordingly and expect it to be the input to
# the per-generation cost estimate rather than something to run casually.
bench:
	@$(RUN) python tau_adapter/run.py --launcher $(LAUNCHER) \
		--out ../results/$(GEN)/bench_full --overwrite
	@$(MAKE) --no-print-directory grade OUT=results/$(GEN)/bench_full

# The only sanctioned way to produce a number. Calls tau's own evaluate_trajectories; the wrapper
# exists solely to grade against the retrieval config the run recorded, instead of letting the
# evaluator fall back to a config the run never used. See scripts/grade.py.
grade:
	@test -n "$(OUT)" || (echo "usage: make grade OUT=results/<gen>/<run>" && exit 1)
	@$(RUN) python scripts/grade.py $(CURDIR)/$(OUT)/results.json
