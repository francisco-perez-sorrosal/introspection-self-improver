"""The two local launch vectors.

The `--` separator is the load-bearing detail: `introspection local` consumes its own flags
before it and passes everything after it to Pi unchanged. Put `--mode rpc` on the wrong side
and the CLI either rejects it or interprets it as its own `--mode` (which accepts only
text/json and requires `--print`) — either way the RPC protocol never starts, and the failure
looks like a hung episode rather than a bad argument.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tau_adapter.transport_local import (
    LAUNCHER_CLI,
    LAUNCHER_PI,
    LocalPiTransport,
)


def _transport(tmp_path: Path, **kwargs) -> LocalPiTransport:
    workspace = tmp_path / "workspace"
    recipe = workspace / "target-agent"
    recipe.mkdir(parents=True, exist_ok=True)
    kwargs.setdefault("workspace_dir", workspace)
    return LocalPiTransport(recipe_dir=recipe, **kwargs)


def test_cli_launcher_passes_rpc_mode_after_the_separator(tmp_path: Path) -> None:
    argv = _transport(tmp_path, launcher=LAUNCHER_CLI).argv()

    assert argv[:2] == ["introspection", "local"]
    separator = argv.index("--")
    before, after = argv[:separator], argv[separator + 1 :]

    # The CLI's own flags stay on its side; Pi's stay on Pi's.
    assert "--work-dir" in before
    assert "--agent" in before
    assert after[:2] == ["--mode", "rpc"]
    assert "--mode" not in before


def test_pi_launcher_addresses_the_recipe_directly(tmp_path: Path) -> None:
    argv = _transport(tmp_path, launcher=LAUNCHER_PI).argv()

    assert argv[0] == "pi"
    assert "--recipe" in argv
    assert "--mode" in argv
    # No separator: there is no wrapper to consume flags, so nothing needs shielding.
    assert "--" not in argv
    assert "--work-dir" not in argv


@pytest.mark.parametrize("launcher", [LAUNCHER_CLI, LAUNCHER_PI])
def test_session_storage_is_explicit_under_either_launcher(launcher: str, tmp_path: Path) -> None:
    """A session file is the local lane's only record, so its absence must be deliberate."""
    with_session = _transport(tmp_path, launcher=launcher, session_dir=tmp_path / "sessions").argv()
    assert "--session-dir" in with_session
    assert "--no-session" not in with_session

    without = _transport(tmp_path, launcher=launcher).argv()
    assert "--no-session" in without
    assert "--session-dir" not in without


def test_unknown_launcher_is_refused_at_construction(tmp_path: Path) -> None:
    """Fail before spawning anything, rather than after an episode's cost is sunk."""
    with pytest.raises(ValueError, match="launcher must be one of"):
        _transport(tmp_path, launcher="pipenv-but-typoed")


def test_workspace_defaults_to_the_recipe_parent(tmp_path: Path) -> None:
    """The CLI discovers `.introspection/` by walking up, so the default must be its holder."""
    workspace = tmp_path / "workspace"
    recipe = workspace / "target-agent"
    recipe.mkdir(parents=True)

    argv = LocalPiTransport(recipe_dir=recipe, launcher=LAUNCHER_CLI).argv()
    assert argv[argv.index("--work-dir") + 1] == str(workspace.resolve())
