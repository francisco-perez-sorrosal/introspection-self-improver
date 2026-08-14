"""Runtime resolution and the connected-binding guard.

The guard exists because of a failure that is expensive to diagnose from its symptom: a
*connected* `tau` MCP binding replaces the `introspection dev --mcp` route with the binding's own
URL, and since binding URLs must be `https` or `host.docker.internal`, the cloud sandbox then
tries to reach something that is not this machine. Every episode dies as
`Required MCP catalog discovery failed: tau: timed out after 4998ms`, which says nothing about
bindings. Refusing up front, with the disconnect command in the message, is the whole point.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tau_adapter import dev_lane


def test_runtime_id_resolves_by_name(monkeypatch, tmp_path) -> None:
    monkeypatch.delenv("TAU_RUNTIME_ID", raising=False)
    monkeypatch.setattr(
        dev_lane,
        "_cli_json",
        lambda *a, **k: [
            {"name": "everyday-muse", "id": "other"},
            {"name": "target-agent", "id": "wanted"},
        ],
    )
    assert dev_lane.resolve_runtime_id("target-agent", tmp_path) == "wanted"


def test_env_override_wins_without_calling_the_cli(monkeypatch, tmp_path) -> None:
    """Several Runtime versions can share a name, so pinning one has to be possible."""

    def explode(*a, **k):
        raise AssertionError("the CLI must not be consulted when the id is pinned")

    monkeypatch.setattr(dev_lane, "_cli_json", explode)
    monkeypatch.setenv("TAU_RUNTIME_ID", "pinned-id")
    assert dev_lane.resolve_runtime_id("target-agent", tmp_path) == "pinned-id"


def test_missing_runtime_names_what_exists_and_how_to_fix_it(monkeypatch, tmp_path) -> None:
    monkeypatch.delenv("TAU_RUNTIME_ID", raising=False)
    monkeypatch.setattr(
        dev_lane, "_cli_json", lambda *a, **k: [{"name": "everyday-muse", "id": "x"}]
    )
    with pytest.raises(dev_lane.DevLaneError) as excinfo:
        dev_lane.resolve_runtime_id("target-agent", tmp_path)
    assert "everyday-muse" in str(excinfo.value)
    assert "runtimes create" in str(excinfo.value)


def test_a_connected_tau_binding_is_refused(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(
        dev_lane,
        "_cli_json",
        lambda *a, **k: [
            {"mcp_server_id": "tau", "connected": True, "endpoint_id": "endpoint-123"}
        ],
    )
    with pytest.raises(dev_lane.DevLaneError) as excinfo:
        dev_lane.assert_no_connected_binding("rt", "development", tmp_path)
    # The message has to carry the remedy: the symptom points nowhere near the cause.
    assert "endpoint-123" in str(excinfo.value)
    assert "disconnect" in str(excinfo.value)


def test_a_disconnected_binding_is_fine(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(
        dev_lane, "_cli_json", lambda *a, **k: [{"mcp_server_id": "tau", "connected": False}]
    )
    assert dev_lane.assert_no_connected_binding("rt", "development", tmp_path) is None


def test_dev_target_is_read_off_the_startup_banner() -> None:
    """`dev` prints the value a caller must set to route tasks to this attachment."""
    attachment = dev_lane.DevAttachment(mcp_url="http://127.0.0.1:1/mcp/t", repo_root=".")
    attachment._lines = [
        "╭─ Development ready\n",
        "│  ✓ Runtime: target-agent\n",
        "│    For your app: INTROSPECTION_DEV_TARGET=fperez\n",
        "╰─\n",
    ]
    assert attachment._parse_dev_target() == "fperez"


def test_dev_target_is_none_when_absent() -> None:
    attachment = dev_lane.DevAttachment(mcp_url="http://127.0.0.1:1/mcp/t", repo_root=".")
    attachment._lines = ["╭─ Development ready\n"]
    assert attachment._parse_dev_target() is None


def test_as_name_reaches_the_dev_launch_vector() -> None:
    attachment = dev_lane.DevAttachment(
        mcp_url="http://127.0.0.1:1/mcp/t", repo_root=".", as_name="tau-w01-ab12"
    )
    argv = attachment.argv()
    assert "--as" in argv
    assert argv[argv.index("--as") + 1] == "tau-w01-ab12"


def test_a_misnamed_attachment_is_refused_at_startup() -> None:
    """Episode routing is fail-closed on the dev target; serving under the wrong name
    would strand every task aimed at the requested one."""
    attachment = dev_lane.DevAttachment(
        mcp_url="http://127.0.0.1:1/mcp/t", repo_root=".", as_name="tau-w01-ab12"
    )
    attachment._lines = ["│    For your app: INTROSPECTION_DEV_TARGET=fperez\n"]
    with pytest.raises(dev_lane.DevLaneError, match="fail closed"):
        attachment._resolve_dev_target()


def test_a_matching_attachment_name_is_adopted() -> None:
    attachment = dev_lane.DevAttachment(
        mcp_url="http://127.0.0.1:1/mcp/t", repo_root=".", as_name="tau-w01-ab12"
    )
    attachment._lines = ["│    For your app: INTROSPECTION_DEV_TARGET=tau-w01-ab12\n"]
    assert attachment._resolve_dev_target() == "tau-w01-ab12"


class _StubAttachment:
    def __init__(self, alive: bool = True) -> None:
        self._alive = alive
        self.stops = 0

    @property
    def alive(self) -> bool:
        return self._alive

    def stop(self) -> None:
        self.stops += 1


def _pool(slot_count: int, alive: bool = True) -> dev_lane.AttachmentPool:
    slots = [
        dev_lane.AttachmentSlot(
            name=f"tau-w{i:02d}-ab12", channel_token=f"token-{i}", attachment=_StubAttachment(alive)
        )
        for i in range(slot_count)
    ]
    return dev_lane.AttachmentPool(slots)


def test_leases_hand_out_distinct_slots_and_exhaustion_blocks() -> None:
    pool = _pool(2)
    first = pool.lease(timeout=0.05)
    second = pool.lease(timeout=0.05)
    assert first is not second
    with pytest.raises(dev_lane.DevLaneError, match="no attachment slot became free"):
        pool.lease(timeout=0.05)
    pool.release(first)
    assert pool.lease(timeout=0.05) is first


def test_a_double_release_cannot_requeue_a_slot() -> None:
    """A slot queued twice would hand one attachment to two episodes at once — the
    cross-episode contamination the whole design forbids."""
    pool = _pool(2)
    first = pool.lease(timeout=0.05)
    second = pool.lease(timeout=0.05)
    pool.release(first)
    pool.release(first)
    assert pool.lease(timeout=0.05) is first
    with pytest.raises(dev_lane.DevLaneError, match="no attachment slot became free"):
        pool.lease(timeout=0.05)
    pool.release(second)


def test_a_dead_attachment_is_refused_and_retired_at_lease() -> None:
    pool = _pool(2, alive=False)
    with pytest.raises(dev_lane.DevLaneError, match="has exited"):
        pool.lease(timeout=0.05)
    # The dead slot never re-enters the free queue; the next lease gets the other slot,
    # which is equally dead here and equally refused.
    with pytest.raises(dev_lane.DevLaneError, match="has exited"):
        pool.lease(timeout=0.05)
    with pytest.raises(dev_lane.DevLaneError, match="no attachment slot became free"):
        pool.lease(timeout=0.05)


def test_pool_stop_is_idempotent_across_slots() -> None:
    pool = _pool(3)
    pool.stop()
    pool.stop()
    assert [slot.attachment.stops for slot in pool.slots] == [2, 2, 2]


def test_a_started_pool_names_slots_with_one_nonce_and_slot_zero_rides_the_run_token(
    monkeypatch,
) -> None:
    from tau_adapter.tool_bridge import ToolBridge

    bridge = ToolBridge(tau_tools=[])
    bridge.start()
    try:
        monkeypatch.setattr(dev_lane.DevAttachment, "start", lambda self, timeout=180.0: None)
        pool = dev_lane.start_attachment_pool(
            bridge=bridge, size=3, repo_root=Path("."), runtime_name="target-agent"
        )
        names = [slot.name for slot in pool.slots]
        nonces = {name.rsplit("-", 1)[1] for name in names}
        assert len(set(names)) == 3
        assert len(nonces) == 1
        assert pool.slots[0].channel_token == bridge.token
        assert len({slot.channel_token for slot in pool.slots}) == 3
        # Every slot's attachment was handed the URL of ITS token, not a shared one.
        urls = {slot.attachment._mcp_url for slot in pool.slots}
        assert len(urls) == 3
        assert bridge.url_for(pool.slots[1].channel_token) in urls
    finally:
        bridge.stop()
