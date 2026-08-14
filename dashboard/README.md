# dashboard — read-only results viewer

A local web page over the committed record in `results/`: experiments → generations →
rounds → episodes, rendered as the improvement story the repository exists to produce.
Stdlib-only server, no dependencies, loopback only, strictly read-only.

```bash
make dashboard            # serves http://127.0.0.1:8787/
python3 dashboard/serve.py --open --results-root ../results --port 8787
```

## Configuration

`config.json` holds the pointer to the results tree and the port:

```json
{ "results_root": "../results", "port": 8787 }
```

`results_root` is resolved relative to `dashboard/`; CLI flags override it. The
experiment dropdown lists every `results/experiment_*/` directory found there —
`experiment_<seq>_<name>` directories read as `exp_001 · bm25-sonnet46`; a directory
without the sequence prefix falls back to its bare id.

## What it shows

- **Freeze strip + status** — the experiment's `experiment.yaml` snapshot (domain,
  retrieval config, models, trials × seed, τ² commit), or a PROVISIONAL bring-up banner
  when no snapshot exists.
- **Held-out progression** — the experiment's metric, rendered exclusively from the
  revealed artifacts `make reveal` writes under `results/experiment_<id>/held_out/`
  (`results_by_generation.csv`, `task_generation_matrix.csv`, `transitions.csv`,
  `retention.csv`) plus `summary.md`: the tasks-solved/T curve with the D2 noise band
  as whiskers, identity generations as hollow marks, the ever-solved retention
  diagnostic as a dashed line, progression and transition tables, and the binary
  task × generation matrix with gain/regression change dots. Until the reveal, the
  card states that the measurement is sealed in the vault.
- **Observable-rounds curve** — pass¹ per split for batch and diagnostic rounds (fully
  observable by design), with ≈95% intervals over per-task rates; click a generation to
  inspect it. A table view twin is one toggle away. Splits are grouped dynamically from
  each round's recorded `run_metadata.json` value (no taxonomy is hard-coded; unlabeled
  rounds form an ad-hoc bucket); when no round carries a split, the curve falls back to
  per-round bars.
- **Efficiency small multiples** — cost, messages, `KB_search` calls, duration per
  episode across generations (tracked, not optimized).
- **Generation ribbon** — one card per improvement cycle: pass¹, Δ vs previous, the
  improvement record's outcome and hypothesis when present, episode counts, cost,
  recipe SHAs.
- **Improvement record panel** — the selected generation's transition record
  (`improvement_records/gen_<g>_to_<g+1>.yaml`): outcome badge, owning layer,
  hypothesis, and the raw YAML.
- **Task × generation heatmap** — per-task pass fractions for observable rounds on a
  sequential ramp, not-run cells distinct from zero; sortable by id or trend.
- **Round and episode detail** — completeness flags (diagnostic, interrupted, infra
  errors, abnormal terminations, incomplete evidence), per-episode rewards and costs,
  conversation ids with copy buttons, and full **transcripts** (messages, tool calls,
  arguments) fetched on demand.

## Honesty rules it inherits

Rewards shown are τ's own recorded in-run evaluations read from `results.json` — the
reportable number remains `make grade` (tau2 evaluate-trajs); nothing is regraded here.
Rates follow τ's metric convention (infrastructure errors excluded and counted
separately); diagnostic-mode rounds are visibly muted and labeled not reportable; runs
without `run_metadata.json` are flagged as interrupted rather than averaged in.
Held-out data appears only after `make reveal` and only from the revealed artifacts
under `results/` — the dashboard never reads the vault (SIA_EVALUATION_PLAN.md D9).
