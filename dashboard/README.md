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
`experiment_<seq>_<name>` directories read as `exp_001 · bm25-sonnet46`, legacy
pre-sequence ones (`experiment_dummy`) by their bare id.

## What it shows

- **Freeze strip + status** — the experiment's `experiment.yaml` snapshot (domain,
  retrieval config, models, trials × seed, τ² commit), or a PROVISIONAL bring-up banner
  when no snapshot exists.
- **Generation curve** — pass¹ per split with ≈95% intervals over per-task rates,
  candidate arms as hollow marks; click a generation to inspect it. A table view twin is
  one toggle away. Splits are grouped dynamically from each round's recorded
  `run_metadata.json` value (no taxonomy is hard-coded; unlabeled rounds form an ad-hoc
  bucket); when no round carries a split, the curve falls back to per-round bars.
- **Efficiency small multiples** — cost, messages, `KB_search` calls, duration per
  episode across generations (tracked, not optimized).
- **Generation ribbon** — one card per improvement cycle: pass¹, Δ vs previous, the
  learning record's candidate/decision when present, episode counts, cost, recipe SHAs.
- **Task × generation heatmap** — per-task trial pass fractions on a sequential ramp,
  within-task instability (0 < c < n) dotted, not-run cells distinct from zero; sortable
  by id or trend.
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
