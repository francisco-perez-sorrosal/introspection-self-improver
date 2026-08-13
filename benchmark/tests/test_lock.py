"""The frozen-surface guards, and the real lock's own consistency.

Each guard exists to stop one specific way a generation could post a better score without
improving the harness.
"""

from __future__ import annotations

import pytest
import yaml

from tau_adapter import lock as lockmod
from tau_adapter.lock import Lock, LockError, assert_recipe_matches_lock, assert_tool_catalog

TOOLS = ["KB_search", "get_current_time"]


def _lock(**frozen_overrides) -> Lock:
    frozen = {
        "status": "PROVISIONAL",
        "agent_model": "anthropic/claude-sonnet-4-6",
        "agent_thinking_level": "low",
        "agent_llm_declared": "anthropic/claude-sonnet-4-6",
        "user_llm": "anthropic/claude-sonnet-4-5",
        "enforce_communication_protocol": False,
    }
    frozen.update(frozen_overrides)
    return Lock(raw={"frozen": frozen, "tool_catalog": list(TOOLS)})


def test_tool_catalog_accepts_any_order() -> None:
    assert_tool_catalog(_lock(), list(reversed(TOOLS)))


def test_tool_catalog_rejects_an_added_tool() -> None:
    # The agent's MCP policy is include: ["*"], so a new tool would otherwise reach the model
    # silently and change the graded tool surface.
    with pytest.raises(LockError, match="added"):
        assert_tool_catalog(_lock(), [*TOOLS, "surprise_tool"])


def test_tool_catalog_rejects_a_missing_tool() -> None:
    with pytest.raises(LockError, match="missing"):
        assert_tool_catalog(_lock(), TOOLS[:1])


def test_empty_catalog_is_refused_rather_than_treated_as_no_constraint() -> None:
    empty = Lock(raw={"frozen": {}, "tool_catalog": []})
    with pytest.raises(LockError, match="empty tool_catalog"):
        assert_tool_catalog(empty, TOOLS)


def test_missing_frozen_field_names_itself() -> None:
    with pytest.raises(LockError, match=r"frozen\.num_trials"):
        _ = Lock(raw={"frozen": {}}).num_trials


def test_experiment_id_reads_from_the_lock() -> None:
    assert Lock(raw={"experiment": {"id": "dummy"}}).experiment_id == "dummy"


def test_missing_experiment_id_is_refused() -> None:
    with pytest.raises(LockError, match=r"experiment\.id"):
        _ = Lock(raw={}).experiment_id


def test_experiment_id_must_be_a_directory_slug() -> None:
    # The id becomes a results/ path component, so anything a filesystem or a reader could
    # mis-handle is refused at the source rather than becoming a strange directory name.
    with pytest.raises(LockError, match="slug"):
        _ = Lock(raw={"experiment": {"id": "Bad Name"}}).experiment_id


def test_recipe_model_mismatch_is_refused(tmp_path) -> None:
    agent_yaml = tmp_path / "agent.yaml"
    agent_yaml.write_text(
        yaml.safe_dump(
            {"name": "agent", "model": {"name": "anthropic/bigger", "thinking_level": "max"}}
        ),
        encoding="utf-8",
    )
    with pytest.raises(LockError, match="model is"):
        assert_recipe_matches_lock(_lock(), agent_yaml)


def test_thinking_level_mismatch_is_refused(tmp_path) -> None:
    # Raising thinking level is a score improvement with no harness change, so it is caught
    # separately from the model name rather than folded into it.
    agent_yaml = tmp_path / "agent.yaml"
    agent_yaml.write_text(
        yaml.safe_dump(
            {
                "name": "agent",
                "model": {"name": "anthropic/claude-sonnet-4-6", "thinking_level": "high"},
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(LockError, match="thinking_level is"):
        assert_recipe_matches_lock(_lock(), agent_yaml)


def test_the_committed_recipe_agrees_with_the_committed_lock() -> None:
    """Guards the pair that actually ships, not a fixture."""
    assert_recipe_matches_lock(lockmod.load_lock())


def test_the_committed_lock_is_internally_consistent() -> None:
    real = lockmod.load_lock()
    assert real.experiment_id, "the lock must name the experiment its freeze defines"
    assert real.policy_sha256, "run `make policy`"
    assert real.tool_catalog, "run `make policy`"
    assert real.raw["policy"]["source_domain"] == real.domain
    assert real.raw["policy"]["source_retrieval_config"] == real.retrieval_config
    # Declared-and-unused, but it must not read misleadingly.
    assert real.agent_llm_declared == real.agent_model
