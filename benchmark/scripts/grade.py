#!/usr/bin/env python3
"""Grade a run with τ's own evaluator, against the environment the run actually used.

This calls τ's `evaluate_trajectories` — the same function `tau2 evaluate-trajs` calls. No reward
is computed here, and no grading logic is reimplemented.

The one thing it adds is the retrieval config. τ's re-grading path builds the environment through
`_build_eval_env_kwargs`, which passes only `read_log_allowlist` for `banking_knowledge` and never
the retrieval variant, so `get_environment` falls back to `DEFAULT_RETRIEVAL_VARIANT` — `alltools`.
That has two consequences:

  * it constructs an OpenAI-embeddings pipeline before comparing two database states, so a
    `reward_basis: ['DB']` task cannot be graded without an embeddings key it never needed;
  * more seriously, it grades against a *different tool surface* than the run used. Retrieval
    configs expose different tool names — `KB_search` under `bm25`, `KB_search_bm25` and
    `KB_search_dense` under `alltools` — so an `ACTION`-basis task's expected actions can silently
    stop matching.

So this is a fidelity fix rather than a convenience: the value injected is the one the results file
itself recorded, which is by definition the environment the trajectory was produced in. Nothing
here chooses a configuration; it only stops the evaluator from choosing a different one.

Worth reporting upstream. Until then the patch is deliberately as narrow as possible: it wraps the
kwargs builder, calls the original, and adds one key.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tau_adapter import lock as lockmod


def _resolve_recorded_retrieval(results_path: Path) -> tuple[str | None, dict | None]:
    """What retrieval configuration produced this trajectory."""
    info = json.loads(results_path.read_text(encoding="utf-8")).get("info") or {}
    return info.get("retrieval_config"), info.get("retrieval_config_kwargs")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("results", help="path to a run's results.json")
    parser.add_argument(
        "--output-dir",
        default=None,
        help="write updated trajectories with recomputed rewards here (default: display only)",
    )
    parser.add_argument(
        "--fresh-tasks",
        action="store_true",
        help="re-grade against current task definitions instead of the embedded ones",
    )
    args = parser.parse_args()

    results_path = Path(args.results).resolve()
    if not results_path.is_file():
        raise SystemExit(f"no results file at {results_path}")

    variant, variant_kwargs = _resolve_recorded_retrieval(results_path)

    if variant is not None:
        # A results file whose retrieval config disagrees with the lock did not come from this
        # experiment's configuration. Grading it against the lock would attach this experiment's
        # name to someone else's conditions.
        lock = lockmod.load_lock()
        if variant != lock.retrieval_config:
            raise SystemExit(
                f"{results_path.name} was produced with retrieval_config={variant!r} but the lock "
                f"says {lock.retrieval_config!r}. Grade it against the lock it was run under."
            )

        from tau2.scripts import evaluate_trajectories as et

        original = et._build_eval_env_kwargs

        def with_recorded_retrieval(domain: str, task):
            kwargs = dict(original(domain, task) or {})
            kwargs["retrieval_variant"] = variant
            if variant_kwargs:
                kwargs["retrieval_kwargs"] = variant_kwargs
            return kwargs

        et._build_eval_env_kwargs = with_recorded_retrieval
        print(f"grading with the run's own retrieval config: {variant}")
    else:
        from tau2.scripts import evaluate_trajectories as et

        print("no retrieval config recorded (domain has no knowledge base); grading as-is")

    et.evaluate_trajectories(
        [str(results_path)],
        output_dir=args.output_dir,
        fresh_tasks=args.fresh_tasks,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
