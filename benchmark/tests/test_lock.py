"""The frozen-surface guards, and the real lock's own consistency.

Each guard exists to stop one specific way a generation could post a better score without
improving the harness.
"""

from __future__ import annotations

import pytest
import yaml

from tau_adapter import lock as lockmod
from tau_adapter import split as splitmod
from tau_adapter.lock import Lock, LockError, assert_recipe_matches_lock, assert_tool_catalog

TOOLS = ["KB_search", "get_current_time"]


def _protocol_block(**overrides) -> dict:
    block = {
        "generations": 3,
        "improvement_tasks_per_generation": 3,
        "held_out_tasks": 5,
        "allow_within_batch_verification": False,
        "holdout_visibility": {
            "expose_tasks_to_orchestrator": False,
            "expose_traces_to_orchestrator": False,
            "expose_per_task_results_to_orchestrator": False,
            "expose_aggregate_score_to_orchestrator": False,
        },
        "require_human_approval": True,
    }
    block.update(overrides)
    return block


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


def test_experiment_id_derives_from_seq_and_name() -> None:
    # Zero-padded so two freezes of the same configuration sort and read as a sequence:
    # 001_bm25-sonnet46, 002_bm25-sonnet46, …
    lock = Lock(raw={"experiment": {"seq": 1, "name": "bm25-sonnet46"}})
    assert lock.experiment_id == "001_bm25-sonnet46"


def test_missing_experiment_seq_is_refused() -> None:
    with pytest.raises(LockError, match=r"experiment\.seq"):
        _ = Lock(raw={"experiment": {"name": "dummy"}}).experiment_id


def test_missing_experiment_name_is_refused() -> None:
    with pytest.raises(LockError, match=r"experiment\.name"):
        _ = Lock(raw={"experiment": {"seq": 1}}).experiment_id


@pytest.mark.parametrize("bad_seq", [0, -3, "1", True])
def test_experiment_seq_must_be_a_positive_integer(bad_seq) -> None:
    with pytest.raises(LockError, match="positive integer"):
        _ = Lock(raw={"experiment": {"seq": bad_seq, "name": "dummy"}}).experiment_id


def test_experiment_name_must_be_a_directory_slug() -> None:
    # The name becomes part of a results/ path component, so anything a filesystem or a
    # reader could mis-handle is refused at the source rather than becoming a strange
    # directory name.
    with pytest.raises(LockError, match="slug"):
        _ = Lock(raw={"experiment": {"seq": 1, "name": "Bad Name"}}).experiment_id


def test_protocol_block_parses_into_config() -> None:
    protocol = Lock(raw={"protocol": _protocol_block()}).protocol
    assert protocol.generations == 3
    assert protocol.improvement_tasks_per_generation == 3
    assert protocol.held_out_tasks == 5
    assert protocol.allow_within_batch_verification is False
    assert protocol.require_human_approval is True
    assert protocol.holdout_visibility.expose_aggregate_score_to_orchestrator is False


def test_missing_protocol_block_is_refused() -> None:
    with pytest.raises(LockError, match="missing the protocol block"):
        _ = Lock(raw={}).protocol


@pytest.mark.parametrize(
    "key", ["generations", "improvement_tasks_per_generation", "held_out_tasks"]
)
@pytest.mark.parametrize("bad", [0, -1, "3", True, None])
def test_protocol_sizes_must_be_positive_integers(key, bad) -> None:
    with pytest.raises(LockError, match=rf"protocol\.{key}"):
        _ = Lock(raw={"protocol": _protocol_block(**{key: bad})}).protocol


@pytest.mark.parametrize("key", ["allow_within_batch_verification", "require_human_approval"])
def test_protocol_flags_must_be_bools(key) -> None:
    with pytest.raises(LockError, match=rf"protocol\.{key}.*must be a bool"):
        _ = Lock(raw={"protocol": _protocol_block(**{key: "false"})}).protocol


def test_protocol_unknown_key_is_refused() -> None:
    with pytest.raises(LockError, match="unknown keys: batch_size"):
        _ = Lock(raw={"protocol": _protocol_block(batch_size=10)}).protocol


def test_a_second_trials_knob_is_refused() -> None:
    # Held-out trials are frozen.num_trials; a protocol key claiming to be that knob would
    # let the two disagree silently.
    with pytest.raises(LockError, match=r"frozen\.num_trials"):
        _ = Lock(raw={"protocol": _protocol_block(held_out_trials_per_task=1)}).protocol


def test_holdout_visibility_requires_the_exact_flag_set() -> None:
    incomplete = _protocol_block(
        holdout_visibility={"expose_tasks_to_orchestrator": False, "expose_scores": False}
    )
    with pytest.raises(LockError, match="unknown keys: expose_scores"):
        _ = Lock(raw={"protocol": incomplete}).protocol
    missing_one = _protocol_block()
    del missing_one["holdout_visibility"]["expose_traces_to_orchestrator"]
    with pytest.raises(LockError, match=r"holdout_visibility\.expose_traces_to_orchestrator"):
        _ = Lock(raw={"protocol": missing_one}).protocol


def test_holdout_visibility_must_be_a_mapping() -> None:
    with pytest.raises(LockError, match="holdout_visibility must be a mapping"):
        _ = Lock(raw={"protocol": _protocol_block(holdout_visibility=False)}).protocol


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
    # Parsing is the validation: the generation protocol's configuration must be present
    # and well-formed in the committed lock.
    assert real.protocol.generations >= 1


def test_the_committed_manifest_matches_the_committed_lock() -> None:
    """Structure only — content checks against task data are scripts/propose_split.py --verify.

    The vendored checkout is gitignored, so this guards what a fresh clone can guard: the
    committed partition carries exactly the batches and sizes the committed lock's
    protocol block promises, with no task assigned twice.
    """
    real = lockmod.load_lock()
    manifest = splitmod.load_manifest()
    lists = splitmod.partition_lists(manifest)
    sizes = splitmod.partition_sizes(
        real.protocol.generations,
        real.protocol.improvement_tasks_per_generation,
        real.protocol.held_out_tasks,
    )
    assert manifest["version"] == splitmod.MANIFEST_VERSION
    assert manifest["domain"] == real.domain
    assert {name: len(ids) for name, ids in lists.items()} == sizes
    all_ids = [task_id for ids in lists.values() for task_id in ids]
    assert len(all_ids) == len(set(all_ids))


def test_max_concurrency_reads_the_operational_block():
    # An operational default, deliberately outside frozen: (and the freeze fingerprint).
    assert Lock(raw={"operational": {"max_concurrency": 5}}).max_concurrency == 5


def test_a_missing_operational_block_is_named():
    with pytest.raises(LockError, match=r"operational\.max_concurrency"):
        _ = Lock(raw={}).max_concurrency


def test_the_committed_lock_keeps_concurrency_out_of_the_frozen_block():
    real = lockmod.load_lock()
    assert "max_concurrency" not in (real.raw.get("frozen") or {})
    assert real.max_concurrency >= 1
