"""Round-type resolution: lane forcing, manifest-driven selection, pre-spend verification.

The refusals here are the D1 firewall's front door — a wrong lane pairing or a hand-picked
task list must stop before an episode is spent, with a message that says why.
"""

from __future__ import annotations

import pytest

from tau_adapter.lock import Lock
from tau_adapter.rounds import (
    KIND_ADHOC,
    KIND_BATCH,
    KIND_HELDOUT,
    TRANSPORT_LOCAL,
    TRANSPORT_PLATFORM,
    RoundError,
    resolve_max_concurrency,
    resolve_round,
)
from tau_adapter.split import HELD_OUT, MANIFEST_VERSION, TaskRow, partition_sizes, propose

_DOMAIN = "banking_knowledge"


def _lock() -> Lock:
    return Lock(
        raw={
            "benchmark": {"domain": _DOMAIN},
            "protocol": {
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
            },
        }
    )


def _rows() -> list[TaskRow]:
    rows = [TaskRow(f"task_{i:03d}", ("DB",), "credit_cards", 1 + i % 5) for i in range(88)]
    rows += [TaskRow(f"task_{900 + j}", ("ACTION",), "bank_accounts", 2) for j in range(9)]
    return rows


def _manifest(rows: list[TaskRow]) -> dict:
    assignment = propose(rows, partition_sizes(3, 3, 5))
    return {
        "version": MANIFEST_VERSION,
        "domain": _DOMAIN,
        "batches": {name: ids for name, ids in assignment.items() if name != HELD_OUT},
        HELD_OUT: assignment[HELD_OUT],
    }


def _resolve(**overrides):
    rows = _rows()
    kwargs = {
        "batch": None,
        "heldout": False,
        "transport": None,
        "task_ids": None,
        "domain": None,
        "overwrite": False,
        "lock": _lock(),
        "manifest": _manifest(rows),
        "rows": rows,
    }
    kwargs.update(overrides)
    return resolve_round(**kwargs)


def test_adhoc_defaults_to_local_and_passes_selection_through():
    spec = _resolve(task_ids=["task_001"], domain="mock", manifest=None, rows=None)
    assert spec.kind == KIND_ADHOC
    assert spec.transport == TRANSPORT_LOCAL
    assert spec.split is None
    assert spec.task_ids == ["task_001"]
    assert spec.label_token == ""


def test_adhoc_keeps_an_explicit_transport():
    spec = _resolve(transport=TRANSPORT_PLATFORM, manifest=None, rows=None)
    assert spec.transport == TRANSPORT_PLATFORM


def test_batch_round_forces_the_platform_lane():
    spec = _resolve(batch=1)
    assert spec.kind == KIND_BATCH
    assert spec.transport == TRANSPORT_PLATFORM
    assert spec.split == "batch_01"
    assert len(spec.task_ids) == 3
    assert spec.label_token == " b01"  # noqa: S105 - a title token, not a secret


def test_batch_round_refuses_the_local_lane():
    with pytest.raises(RoundError, match="platform-lane round by definition"):
        _resolve(batch=1, transport=TRANSPORT_LOCAL)


def test_heldout_round_forces_the_local_lane():
    spec = _resolve(heldout=True)
    assert spec.kind == KIND_HELDOUT
    assert spec.transport == TRANSPORT_LOCAL
    assert spec.split == HELD_OUT
    assert len(spec.task_ids) == 5
    assert spec.label_token == ""


def test_heldout_round_refuses_the_platform_lane():
    with pytest.raises(RoundError, match="local-lane by definition"):
        _resolve(heldout=True, transport=TRANSPORT_PLATFORM)


def test_heldout_round_refuses_overwrite():
    # A held-out round is measured once per generation; replacing a measurement is an
    # experiment-level decision, not a CLI flag.
    with pytest.raises(RoundError, match="measured once"):
        _resolve(heldout=True, overwrite=True)


def test_protocol_rounds_refuse_hand_picked_tasks():
    with pytest.raises(RoundError, match="never per invocation"):
        _resolve(batch=1, task_ids=["task_001"])
    with pytest.raises(RoundError, match="never per invocation"):
        _resolve(heldout=True, task_ids=["task_001"])


def test_protocol_rounds_refuse_a_domain_override():
    with pytest.raises(RoundError, match="locked domain only"):
        _resolve(batch=1, domain="mock")


def test_both_round_flags_together_are_refused():
    with pytest.raises(RoundError, match="pick one"):
        _resolve(batch=1, heldout=True)


def test_an_unknown_batch_number_names_the_available_batches():
    with pytest.raises(RoundError, match=r"there is no batch_04.*generations = 3"):
        _resolve(batch=4)


def test_a_partition_that_no_longer_verifies_stops_the_round():
    rows = _rows()
    manifest = _manifest(rows)
    manifest["batches"]["batch_02"] = manifest["batches"]["batch_02"][:-1]
    with pytest.raises(RoundError, match=r"no longer verifies.*no episode was spent") as excinfo:
        _resolve(batch=1, manifest=manifest, rows=rows)
    assert "batch_02 holds 2 ids, expected 3" in str(excinfo.value)


def test_the_legacy_manifest_stops_a_round_loudly():
    rows = _rows()
    legacy = {"version": 1, "domain": _DOMAIN, "discovery": ["task_001"]}
    with pytest.raises(RoundError, match="retired three-way split"):
        _resolve(heldout=True, manifest=legacy, rows=rows)


def test_without_the_flag_every_run_reads_the_locks_concurrency():
    assert resolve_max_concurrency(None, locked_mode=True, lock_value=1) == 1
    assert resolve_max_concurrency(None, locked_mode=False, lock_value=1) == 1


def test_a_locked_run_refuses_the_concurrency_flag():
    """max_concurrency is a frozen execution budget: a later generation must not "improve"
    by being allowed more parallelism, so the override exists for diagnostic rounds only."""
    with pytest.raises(RoundError, match="frozen execution budget"):
        resolve_max_concurrency(3, locked_mode=True, lock_value=1)


def test_a_diagnostic_run_may_override_concurrency():
    assert resolve_max_concurrency(3, locked_mode=False, lock_value=1) == 3


def test_a_nonpositive_concurrency_is_refused():
    with pytest.raises(RoundError, match="at least 1"):
        resolve_max_concurrency(0, locked_mode=False, lock_value=1)
