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


# The experiment id becomes a results/ path component, so it is validated where it is read.
_EXPERIMENT_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]*$")


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
    def experiment_id(self) -> str:
        """The experiment the frozen values define. One experiment is one freeze."""
        value = str((self.raw.get("experiment") or {}).get("id") or "")
        if not value:
            raise LockError("benchmark_lock.yaml is missing experiment.id")
        if not _EXPERIMENT_ID_RE.match(value):
            raise LockError(
                f"experiment.id {value!r} is not a directory slug: lowercase letters, "
                "digits, '-' and '_' only, starting with a letter or digit"
            )
        return value

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
        return int(self._frozen("max_concurrency"))

    @property
    def enforce_communication_protocol(self) -> bool:
        return bool(self._frozen("enforce_communication_protocol"))

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
