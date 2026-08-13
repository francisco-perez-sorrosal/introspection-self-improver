"""Runtime resolution and the connected-binding guard.

The guard exists because of a failure that is expensive to diagnose from its symptom: a
*connected* `tau` MCP binding replaces the `introspection dev --mcp` route with the binding's own
URL, and since binding URLs must be `https` or `host.docker.internal`, the cloud sandbox then
tries to reach something that is not this machine. Every episode dies as
`Required MCP catalog discovery failed: tau: timed out after 4998ms`, which says nothing about
bindings. Refusing up front, with the disconnect command in the message, is the whole point.
"""

from __future__ import annotations

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
