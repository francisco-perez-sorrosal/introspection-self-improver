#!/usr/bin/env python3
"""Pre-partition environment screen: can τ's user simulator survive every task?

Seq 1 died at H0 on a τ-side defect the harness can never reach: a scenario that
instructs the simulated user to speak AND fire a tracking-only user tool in one turn
(task_034's "do BOTH together, 8 times"). τ routes the tool-carrying user message to the
environment first, then asks the simulator to speak again after the silent tool result —
and having already said everything, at the frozen `temperature: 0.0` it returns an empty
completion, which `UserMessage.validate()` books as `infrastructure_error`
(orchestrator.py:844). The opening turn alone cannot reveal this class, so this screen
runs τ's OWN orchestrator over every pool task with a scripted, LLM-free agent: real
routing, real user-tool execution, real validation — bounded by a small step cap.

Run BEFORE proposing a partition, so no held-out set exists yet and no firewall applies.
Scratch trajectories go to --scratch (outside the repo); the committed report carries
crash verdicts only — termination classes and τ's recorded causes, never rewards.
`propose_split.py --exclude` consumes the crashers.

Honest limit: a scripted agent probes the user-sim side of the conversation, not the
locked agent's real behavior. A crash conditioned on rich agent output can still escape;
the seq-1 evidence (12/12 across varied agent replies) says this class does not.
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tau_adapter import lock as lockmod

REPORT_PATH = Path(__file__).resolve().parents[1] / "data" / "user_sim_screen.json"
AGENT_KEY = "screen_scripted_agent"
SCRIPT_LINE = (
    "I understand — let me look into that for you. Could you tell me a little more "
    "about what you need?"
)
#: Steps, not turns: enough for the opening, several combo/tool cycles, and the crash
#: window seq 1 observed (turn ~2-4), while bounding cost on the 8-demand scenarios.
MAX_STEPS = 16


def register_scripted_agent() -> None:
    from tau2.agent.base_agent import HalfDuplexAgent
    from tau2.data_model.message import AssistantMessage
    from tau2.registry import registry

    class _State:
        pass

    class ScriptedAgent(HalfDuplexAgent):
        """Fixed neutral reply every turn; no LLM, no tools, never stops on its own."""

        def get_init_state(self, message_history=None):
            return _State()

        def generate_next_message(self, message, state):
            return AssistantMessage(role="assistant", content=SCRIPT_LINE, cost=0.0), state

    registry.register_agent_factory(
        lambda tools, domain_policy, **kwargs: ScriptedAgent(tools, domain_policy), AGENT_KEY
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=REPORT_PATH, help="report destination")
    parser.add_argument(
        "--scratch",
        type=Path,
        default=None,
        help="scratch dir for τ's results.json (default: a fresh temp dir outside the repo)",
    )
    parser.add_argument("--workers", type=int, default=8, help="concurrent episodes")
    args = parser.parse_args()

    lock = lockmod.load_lock()
    register_scripted_agent()
    from tau2.data_model.simulation import TextRunConfig
    from tau2.evaluator.evaluator import EvaluationType
    from tau2.runner import get_tasks, run_tasks

    tasks = get_tasks(task_set_name=lock.task_set_name, task_split_name=lock.task_split_name)
    print(f"── user-sim screen: {len(tasks)} task(s), user sim {lock.user_llm}, scripted agent")

    config = TextRunConfig(
        domain=lock.domain,
        agent=AGENT_KEY,
        # Declared-and-unused, like the locked runner: the scripted agent calls no LLM.
        llm_agent=lock.agent_llm_declared,
        llm_args_agent={},
        user="user_simulator",
        llm_user=lock.user_llm,
        llm_args_user=dict(lock.user_llm_args),
        task_set_name=lock.task_set_name,
        task_split_name=lock.task_split_name,
        num_trials=1,
        seed=lock.seed,
        max_steps=MAX_STEPS,
        max_errors=lock.max_errors,
        timeout=lock.timeout_seconds,
        max_concurrency=args.workers,
        # One retry: a transient provider blip self-heals; the scenario-conditional
        # crash fails every attempt anyway, so it still lands as infrastructure_error.
        max_retries=1,
        retrieval_config=lock.retrieval_config,
        auto_resume=True,
    )
    config.validate()

    scratch = args.scratch or Path(tempfile.mkdtemp(prefix="sia-user-sim-screen-"))
    scratch.mkdir(parents=True, exist_ok=True)
    results = run_tasks(
        config,
        tasks,
        save_path=scratch / "results.json",
        evaluation_type=EvaluationType.ENV,
        console_display=False,
    )

    verdicts: dict[str, dict] = {}
    for sim in results.simulations:
        termination = str(sim.termination_reason)
        crashed = "infrastructure_error" in termination
        verdict: dict = {"ok": not crashed, "termination": termination}
        if crashed:
            info = sim.info or {}
            verdict["cause"] = {
                "error_type": info.get("error_type"),
                "error": str(info.get("error"))[:300],
                "failed_after_attempts": info.get("failed_after_attempts"),
            }
        verdicts[str(sim.task_id)] = verdict

    crashers = sorted(task_id for task_id, verdict in verdicts.items() if not verdict["ok"])
    report = {
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "mechanism": "tau orchestrator + scripted LLM-free agent, real user-sim and user tools",
        "domain": lock.domain,
        "task_set": lock.task_set_name,
        "task_split": lock.task_split_name,
        "user_llm": lock.user_llm,
        "user_llm_args": dict(lock.user_llm_args),
        "max_steps": MAX_STEPS,
        "screened": len(verdicts),
        "crashers": crashers,
        "tasks": verdicts,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    for task_id in crashers:
        print(f"   ✗ {task_id}: {verdicts[task_id]['cause']}")
    print(f"   {len(verdicts) - len(crashers)}/{len(verdicts)} tasks survive the walk")
    print(f"   report → {args.out}   (scratch trajectories: {scratch})")
    if crashers:
        print(f"   exclude with: propose_split.py --exclude {','.join(crashers)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
