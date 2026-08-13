#!/usr/bin/env python3
"""Run τ's stock LLMAgent natively under the lock's configuration — the A.0c anchor.

Informational, never blocking (v2 §4 W4): the agent differs from the recipe by design, so
this measures the *scaffold delta* between τ's own agent and the Pi harness rather than
testing the adapter. It is also the only configuration in the experiment where τ's --seed
reaches the agent's sampling (§3.1). Under the bm25 freeze it anchors the scaffold
comparison only — nothing here is comparable with published τ-Knowledge numbers, and no
claim to the contrary may be recorded.

No seam is involved: no recipe, no bridge, no transport. τ owns everything, litellm speaks
to the provider directly, and the stock agent runs with τ's own default agent args
(temperature 0.0). The lock still governs models, trials, seed, budgets and retrieval, and
the round lands in the results tree like any other — manifest included — so the dashboard
renders it beside the recipe's rounds.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tau_adapter import lock as lockmod
from tau_adapter import manifest as manifestmod
from tau_adapter import split as splitmod
from tau_adapter.experiment import enforce_snapshot, generation_of, prepare_round_dir

STOCK_AGENT = "llm_agent"  # τ's own registry name for its stock agent
TRANSPORT_NATIVE = "native"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, help="directory for τ's results.json")
    parser.add_argument(
        "--split",
        choices=("discovery", "validation"),
        default="discovery",
        help="frozen split to anchor on (default: discovery — inspectable by definition)",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="replace a completed anchor run instead of refusing (interrupted runs resume)",
    )
    args = parser.parse_args()

    lock = lockmod.load_lock()
    lockmod.assert_vendor_commit(lock)

    manifest_doc = splitmod.load_manifest()
    problems = splitmod.verify(manifest_doc, splitmod.load_task_rows(lock.domain), lock.domain)
    if problems:
        raise SystemExit(
            "split manifest failed verification; no episode was spent:\n  " + "\n  ".join(problems)
        )
    task_ids = list(manifest_doc[args.split])

    out_dir = Path(args.out).resolve()
    enforce_snapshot(lock, out_dir)
    round_status = prepare_round_dir(out_dir, args.overwrite)
    generation = generation_of(out_dir)
    results_path = out_dir / "results.json"

    from tau2.data_model.simulation import TextRunConfig
    from tau2.metrics.agent_metrics import compute_metrics
    from tau2.runner import get_tasks, run_tasks
    from tau2.utils.display import ConsoleDisplay

    config = TextRunConfig(
        domain=lock.domain,
        agent=STOCK_AGENT,
        # Unlike the seam, the model here is real configuration: the stock agent calls it.
        llm_agent=lock.agent_model,
        # τ's own stock default (DEFAULT_LLM_ARGS_AGENT). The recipe's thinking level has no
        # stock equivalent — that absence is part of the scaffold delta being measured.
        llm_args_agent={"temperature": 0.0},
        user="user_simulator",
        llm_user=lock.user_llm,
        llm_args_user=lock.user_llm_args,
        task_set_name=lock.task_set_name,
        task_split_name=lock.task_split_name,
        task_ids=task_ids,
        num_trials=lock.num_trials,
        seed=lock.seed,
        max_steps=lock.max_steps,
        max_errors=lock.max_errors,
        timeout=lock.timeout_seconds,
        max_concurrency=lock.max_concurrency,
        enforce_communication_protocol=lock.enforce_communication_protocol,
        auto_resume=True,
        save_to=None,
        retrieval_config=lock.retrieval_config,
    )
    config.validate()
    tasks = get_tasks(
        task_set_name=config.task_set_name,
        task_split_name=config.task_split_name,
        task_ids=task_ids,
    )

    episodes = len(tasks) * lock.num_trials
    print(f"\n── stock anchor (A.0c): {lock.domain} [{args.split} split, native τ agent]")
    print(f"   experiment    {lock.experiment_id}")
    if round_status:
        print(f"   round         {round_status}")
    print(f"   agent         {STOCK_AGENT} on {lock.agent_model} (τ default args)")
    print(f"   user model    {lock.user_llm}")
    print(f"   retrieval     {lock.retrieval_config}")
    print(
        f"   episodes      {len(tasks)} task(s) × {lock.num_trials} trial(s) = {episodes}, serial"
    )
    print("   seed          the one configuration where τ's --seed reaches the agent (§3.1)")
    print()

    started = time.monotonic()
    results = run_tasks(config, tasks, save_path=results_path, save_dir=out_dir)
    elapsed = time.monotonic() - started
    episode_summaries = [manifestmod.episode_summary(sim) for sim in results.simulations]

    payload = json.loads(results_path.read_text(encoding="utf-8")) if results_path.exists() else {}
    context = manifestmod.RoundContext(
        experiment_id=lock.experiment_id,
        transport=TRANSPORT_NATIVE,
        generation=generation,
        split=args.split,
    )
    manifest_rows = manifestmod.build_rows(payload, context)
    manifest_path = manifestmod.write_manifest(out_dir, manifest_rows)

    (out_dir / "run_metadata.json").write_text(
        json.dumps(
            {
                "mode": "anchor_stock",
                "experiment": lock.experiment_id,
                "domain": lock.domain,
                "generation": generation,
                "split": args.split,
                "num_trials": lock.num_trials,
                "transport": TRANSPORT_NATIVE,
                "agent": STOCK_AGENT,
                "agent_llm": lock.agent_model,
                "agent_llm_args": {"temperature": 0.0},
                "launch_argv": sys.argv,
                "episodes": episode_summaries,
                "platform": None,
                "elapsed_seconds": round(elapsed, 1),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    if not results.simulations:
        print(f"\n── NO simulations were produced in {elapsed:.0f}s; this run is not a record")
        return 1

    ConsoleDisplay.display_agent_metrics(compute_metrics(results))
    completed = sum(1 for e in episode_summaries if e["completed"])
    print(f"\n── {len(results.simulations)} simulation(s) in {elapsed:.0f}s → {results_path}")
    print(f"   completed     {completed}/{len(episode_summaries)}")
    print(f"   manifest      {manifest_path.name}: {len(manifest_rows)} episode row(s)")
    print(
        "\n   Reward above is tau's own in-run evaluation. The reported number comes from\n"
        f"   `tau2 evaluate-trajs {results_path}`."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
