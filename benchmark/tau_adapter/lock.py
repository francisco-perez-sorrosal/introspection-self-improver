"""Read benchmark_lock.yaml, and hold the recipe to it.

The lock is the single place frozen values live. Reading it is not enough — every value here
is asserted before a run, because a frozen surface that is only documented is not frozen.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

BENCHMARK_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = BENCHMARK_DIR.parent
LOCK_PATH = BENCHMARK_DIR / "benchmark_lock.yaml"
RECIPE_DIR = REPO_ROOT / "target-agent"
# The Runtime manifest `introspection local` and `introspection dev` resolve the Recipe from.
RUNTIME_MANIFEST = REPO_ROOT / ".introspection" / "target-agent.yaml"
RECIPE_AGENT_YAML = RECIPE_DIR / "agents" / "agent.yaml"
RECIPE_SYSTEM_MD = RECIPE_DIR / "SYSTEM.md"
VENDOR_DIR = BENCHMARK_DIR / "vendor" / "tau2-bench"


class LockError(RuntimeError):
    pass


# The experiment name becomes part of a results/ path component, so it is validated where
# it is read.
_EXPERIMENT_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9_-]*$")

_HOLDOUT_VISIBILITY_KEYS = (
    "expose_tasks_to_orchestrator",
    "expose_traces_to_orchestrator",
    "expose_per_task_results_to_orchestrator",
    "expose_aggregate_score_to_orchestrator",
)
_PROTOCOL_INT_KEYS = ("generations", "improvement_tasks_per_generation", "held_out_tasks")
_PROTOCOL_BOOL_KEYS = ("allow_within_batch_verification", "require_human_approval")
_PROTOCOL_KEYS = (*_PROTOCOL_INT_KEYS, *_PROTOCOL_BOOL_KEYS, "holdout_visibility")


@dataclass(frozen=True)
class HoldoutVisibility:
    """The firewall flags, spelled out so the configuration states the isolation explicitly."""

    expose_tasks_to_orchestrator: bool
    expose_traces_to_orchestrator: bool
    expose_per_task_results_to_orchestrator: bool
    expose_aggregate_score_to_orchestrator: bool


@dataclass(frozen=True)
class ProtocolConfig:
    """The experiment's generation-protocol configuration, validated on read.

    G batches of B tasks drive generations H_0 → H_G; T held-out tasks measure them. The
    sizes here are what the partition manifest is proposed from and verified against.
    Deliberately absent: `held_out_trials_per_task` — held-out trials are `frozen.num_trials`,
    one knob, and a second key claiming to be that knob is refused rather than reconciled.
    """

    generations: int
    improvement_tasks_per_generation: int
    held_out_tasks: int
    allow_within_batch_verification: bool
    holdout_visibility: HoldoutVisibility
    require_human_approval: bool


def _protocol_positive_int(section: dict, key: str) -> int:
    value = section.get(key)
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise LockError(f"protocol.{key} {value!r} must be a positive integer")
    return value


def _protocol_bool(section: dict, key: str, parent: str = "protocol") -> bool:
    value = section.get(key)
    if not isinstance(value, bool):
        raise LockError(f"{parent}.{key} {value!r} must be a bool")
    return value


def _parse_holdout_visibility(section: dict) -> HoldoutVisibility:
    visibility = section.get("holdout_visibility")
    if not isinstance(visibility, dict):
        raise LockError("protocol.holdout_visibility must be a mapping of the four expose flags")
    unknown = sorted(set(visibility) - set(_HOLDOUT_VISIBILITY_KEYS))
    if unknown:
        raise LockError(f"protocol.holdout_visibility has unknown keys: {', '.join(unknown)}")
    flags = {
        key: _protocol_bool(visibility, key, parent="protocol.holdout_visibility")
        for key in _HOLDOUT_VISIBILITY_KEYS
    }
    return HoldoutVisibility(**flags)


@dataclass(frozen=True)
class Lock:
    raw: dict[str, Any]

    @property
    def domain(self) -> str:
        return self._benchmark("domain")

    @property
    def retrieval_config(self) -> str | None:
        value = self.raw.get("benchmark", {}).get("retrieval_config")
        return value or None

    @property
    def task_set_name(self) -> str:
        return self._benchmark("task_set_name")

    @property
    def task_split_name(self) -> str:
        return self._benchmark("task_split_name")

    @property
    def commit(self) -> str:
        return self._benchmark("commit")

    @property
    def provisional(self) -> bool:
        return str(self._frozen("status", default="")).upper() == "PROVISIONAL"

    @property
    def experiment_seq(self) -> int:
        """The experiment's sequence number, disambiguating same-named configurations.

        Two freezes may share a descriptive name (a second bm25 + Sonnet 4.6 experiment is
        still a new freeze), so the name alone cannot be the identity — the sequence is.
        """
        value = (self.raw.get("experiment") or {}).get("seq")
        if value is None:
            raise LockError("benchmark_lock.yaml is missing experiment.seq")
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise LockError(f"experiment.seq {value!r} must be a positive integer")
        return value

    @property
    def experiment_name(self) -> str:
        """The experiment's descriptive slug (configuration nickname, not the identity)."""
        value = str((self.raw.get("experiment") or {}).get("name") or "")
        if not value:
            raise LockError("benchmark_lock.yaml is missing experiment.name")
        if not _EXPERIMENT_NAME_RE.match(value):
            raise LockError(
                f"experiment.name {value!r} is not a directory slug: lowercase letters, "
                "digits, '-' and '_' only, starting with a letter or digit"
            )
        return value

    @property
    def experiment_id(self) -> str:
        """The experiment the frozen values define, e.g. `001_bm25-sonnet46`.

        One experiment is one freeze. The id is derived — zero-padded sequence + name —
        so every consumer (results paths, snapshots, manifests, refusal messages) agrees
        on the one unique string that names this freeze.
        """
        return f"{self.experiment_seq:03d}_{self.experiment_name}"

    @property
    def agent_model(self) -> str:
        return self._frozen("agent_model")

    @property
    def agent_thinking_level(self) -> str:
        return self._frozen("agent_thinking_level")

    @property
    def agent_llm_declared(self) -> str:
        return self._frozen("agent_llm_declared")

    @property
    def user_llm(self) -> str:
        return self._frozen("user_llm")

    @property
    def user_llm_args(self) -> dict:
        return self._frozen("user_llm_args", default={}) or {}

    @property
    def num_trials(self) -> int:
        return int(self._frozen("num_trials"))

    @property
    def seed(self) -> int:
        return int(self._frozen("seed"))

    @property
    def max_steps(self) -> int:
        return int(self._frozen("max_steps"))

    @property
    def max_errors(self) -> int:
        return int(self._frozen("max_errors"))

    @property
    def timeout_seconds(self) -> float:
        return float(self._frozen("timeout_seconds"))

    @property
    def max_concurrency(self) -> int:
        """Episodes in flight at once — an operational default, never a frozen budget.

        Lives in the lock's `operational:` block, which the freeze fingerprint excludes
        (re-decided 2026-08-13): parallelism moves wall-clock, never what the agent can do
        inside an episode, so changing this default mid-experiment is not freeze drift.
        Any round may override it with --max-concurrency; the effective value is recorded
        in run_metadata.json.
        """
        section = self.raw.get("operational") or {}
        if "max_concurrency" not in section:
            raise LockError("benchmark_lock.yaml is missing operational.max_concurrency")
        return int(section["max_concurrency"])

    @property
    def enforce_communication_protocol(self) -> bool:
        return bool(self._frozen("enforce_communication_protocol"))

    @property
    def protocol(self) -> ProtocolConfig:
        """The generation-protocol block, parsed and validated as one unit.

        Frozen for the experiment's duration like everything else here — it rides the
        freeze fingerprint automatically through `raw`. Unknown keys are refused so a typo
        cannot silently configure nothing.
        """
        section = self.raw.get("protocol")
        if not isinstance(section, dict):
            raise LockError(
                "benchmark_lock.yaml is missing the protocol block (generations, "
                "improvement_tasks_per_generation, held_out_tasks, "
                "allow_within_batch_verification, holdout_visibility, require_human_approval)"
            )
        if "held_out_trials_per_task" in section:
            raise LockError(
                "protocol.held_out_trials_per_task is not a knob: held-out trials are "
                "frozen.num_trials — one knob, never two. Remove the protocol key."
            )
        unknown = sorted(set(section) - set(_PROTOCOL_KEYS))
        if unknown:
            raise LockError(f"protocol block has unknown keys: {', '.join(unknown)}")
        return ProtocolConfig(
            **{key: _protocol_positive_int(section, key) for key in _PROTOCOL_INT_KEYS},
            **{key: _protocol_bool(section, key) for key in _PROTOCOL_BOOL_KEYS},
            holdout_visibility=_parse_holdout_visibility(section),
        )

    @property
    def policy_sha256(self) -> str | None:
        return self.raw.get("policy", {}).get("sha256")

    @property
    def tool_catalog(self) -> list[str]:
        return list(self.raw.get("tool_catalog") or [])

    def _benchmark(self, key: str) -> Any:
        section = self.raw.get("benchmark") or {}
        if key not in section:
            raise LockError(f"benchmark_lock.yaml is missing benchmark.{key}")
        return section[key]

    def _frozen(self, key: str, default: Any = ...) -> Any:
        section = self.raw.get("frozen") or {}
        if key not in section:
            if default is ...:
                raise LockError(f"benchmark_lock.yaml is missing frozen.{key}")
            return default
        return section[key]


def load_lock(path: Path = LOCK_PATH) -> Lock:
    return Lock(raw=yaml.safe_load(path.read_text(encoding="utf-8")) or {})


def _display(path: Path) -> str:
    """Repo-relative when possible, absolute otherwise.

    `Path.relative_to` raises for anything outside the repository, which would replace a
    frozen-surface violation with a pathlib traceback — the least useful moment to lose the
    real message.
    """
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def assert_recipe_matches_lock(lock: Lock, agent_yaml: Path = RECIPE_AGENT_YAML) -> None:
    """The model the agent actually runs on must be the model the lock froze.

    Without this, a later generation could raise its own model or thinking level and post a
    better score without touching the harness at all — the single easiest way to make the
    whole experiment meaningless.
    """
    spec = yaml.safe_load(agent_yaml.read_text(encoding="utf-8")) or {}
    model = spec.get("model") or spec.get("ai") or {}
    name = model.get("name") or model.get("model")
    thinking = model.get("thinking_level")

    problems = []
    if name != lock.agent_model:
        problems.append(f"model is {name!r}, lock says {lock.agent_model!r}")
    if thinking != lock.agent_thinking_level:
        problems.append(f"thinking_level is {thinking!r}, lock says {lock.agent_thinking_level!r}")
    if problems:
        raise LockError(
            f"{_display(agent_yaml)} disagrees with benchmark_lock.yaml: " + "; ".join(problems)
        )


def assert_tool_catalog(lock: Lock, live_tool_names: list[str]) -> None:
    """The graded tool surface must be the one the lock recorded.

    The agent's MCP policy is `include: ["*"]`, which deliberately takes whatever the bridge
    advertises. This is what pins that set, so a change to τ's tool surface cannot slip
    through unnoticed.
    """
    expected = lock.tool_catalog
    if not expected:
        raise LockError(
            "benchmark_lock.yaml has an empty tool_catalog; run `make policy` to record the "
            "tool surface before running the benchmark"
        )
    if sorted(expected) != sorted(live_tool_names):
        missing = sorted(set(expected) - set(live_tool_names))
        added = sorted(set(live_tool_names) - set(expected))
        raise LockError(
            "τ's tool surface does not match benchmark_lock.yaml tool_catalog.\n"
            f"  missing: {missing or 'none'}\n"
            f"  added:   {added or 'none'}"
        )


def assert_vendor_commit(lock: Lock) -> None:
    head = (VENDOR_DIR / ".git" / "HEAD").read_text(encoding="utf-8").strip()
    if head.startswith("ref:"):
        ref = head.split(" ", 1)[1].strip()
        head = (VENDOR_DIR / ".git" / ref).read_text(encoding="utf-8").strip()
    if head != lock.commit:
        raise LockError(
            f"vendored tau2-bench is at {head[:12]}, lock says {lock.commit[:12]}. "
            "Run `make bootstrap`."
        )


# ---------------------------------------------------------------- surgical writes


def update_policy_fields(
    sha256: str, domain: str, retrieval_config: str | None, path: Path = LOCK_PATH
) -> None:
    """Rewrite the `policy:` block in place, preserving the file's comments byte for byte."""
    text = path.read_text(encoding="utf-8")
    replacements = {
        "sha256": sha256,
        "source_domain": domain,
        "source_retrieval_config": retrieval_config if retrieval_config else "null",
    }
    for key, value in replacements.items():
        pattern = re.compile(rf"^(  {key}:).*$", re.MULTILINE)
        if not pattern.search(text):
            raise LockError(f"benchmark_lock.yaml has no policy.{key} line to update")
        text = pattern.sub(rf"\1 {value}", text, count=1)
    path.write_text(text, encoding="utf-8")


def update_tool_catalog(tool_names: list[str], path: Path = LOCK_PATH) -> None:
    """Rewrite the trailing `tool_catalog:` block, preserving everything above it."""
    text = path.read_text(encoding="utf-8")
    match = re.search(r"^tool_catalog:.*$", text, re.MULTILINE)
    if match is None:
        raise LockError("benchmark_lock.yaml has no tool_catalog key")
    if "\n" in text[match.end() :].strip() and re.search(
        r"^[a-z_]+:", text[match.end() :], re.MULTILINE
    ):
        raise LockError(
            "tool_catalog is no longer the last key in benchmark_lock.yaml; "
            "update_tool_catalog rewrites to end of file"
        )
    body = "".join(f"\n  - {name}" for name in tool_names) or " []"
    path.write_text(text[: match.start()] + f"tool_catalog:{body}\n", encoding="utf-8")
