"""Recover τ's canonical tool names from the names Pi exposes.

Pi never shows the model a τ tool under its own name. `@introspection-ai/recipes` rewrites
each one to ``mcp_<serverId>_<tool>_<sha256(serverId.tool)[:10]>``, capped at 64 characters
(`dist/mcp-tools.js`, `piMcpToolName`). τ's evaluator matches expected actions by tool name,
so the mangling has to be undone before a tool call is handed back to τ.

The transform is reproduced here and applied *forwards* over a known tool set, rather than
parsed backwards out of a mangled string: the 64-character cap truncates the readable part,
which makes the reverse direction ambiguous in general.

That the prefix is visible to the model at all is a fidelity divergence from a stock τ run,
recorded as such. It is constant across generations, so it cannot bias a cross-generation
comparison; it can only affect comparability with published τ numbers.
"""

from __future__ import annotations

import hashlib
import re

MAX_NAME_LEN = 64
HASH_LEN = 10

_NON_NAME_CHARS = re.compile(r"[^A-Za-z0-9_-]+")
_LEADING_SEPARATORS = re.compile(r"^[_-]+")
_TRAILING_SEPARATORS = re.compile(r"[_-]+$")


def _sanitize_name_part(value: str) -> str:
    """Port of `sanitizeNamePart`. Case is preserved; only separators are touched."""
    normalized = _NON_NAME_CHARS.sub("_", value)
    normalized = _LEADING_SEPARATORS.sub("", normalized)
    normalized = _TRAILING_SEPARATORS.sub("", normalized)
    return normalized or "tool"


def pi_mcp_tool_name(server_id: str, tool_name: str) -> str:
    """Port of `piMcpToolName`. Must stay byte-identical to the JS implementation."""
    canonical = f"{server_id}.{tool_name}"
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:HASH_LEN]
    readable = f"mcp_{_sanitize_name_part(server_id)}_{_sanitize_name_part(tool_name)}"
    # JS: readable.slice(0, 64 - hash.length - 1).replace(/_+$/g, "") — underscores only.
    prefix = readable[: MAX_NAME_LEN - HASH_LEN - 1].rstrip("_")
    return f"{prefix}_{digest}"


def build_name_map(server_id: str, tau_tool_names: list[str]) -> dict[str, str]:
    """Map the names Pi will use back to τ's names.

    Raises on a collision rather than resolving one. Two τ tools sharing a Pi name would
    silently misattribute tool calls in the graded trajectory, which is precisely the class
    of adapter defect that changes scores without touching the evaluator.
    """
    mapping: dict[str, str] = {}
    for tau_name in tau_tool_names:
        pi_name = pi_mcp_tool_name(server_id, tau_name)
        clash = mapping.get(pi_name)
        if clash is not None:
            raise ValueError(
                f"τ tools {clash!r} and {tau_name!r} both map to Pi name {pi_name!r}; "
                "the trajectory could not attribute their calls correctly"
            )
        mapping[pi_name] = tau_name
    return mapping
