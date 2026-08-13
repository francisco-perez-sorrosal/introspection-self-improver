"""The frozen `<policy>` region inside the Recipe's SYSTEM.md.

τ's domain policy is benchmark text: `--retrieval-config` decides both the agent's tool set
and the policy it is graded against. It has to reach the agent as a system prompt, and a
Recipe's system prompt can only come from committed files — Pi ignores
`--append-system-prompt` under `--recipe`. So the policy lives in a delimited region of
SYSTEM.md, which keeps it in the commit (exact runtime↔commit lineage), keeps it out of the
conversation (a system prompt is never compacted away mid-episode), and reproduces stock τ's
placement exactly.

Its being inside an otherwise-mutable file is made safe mechanically, not by convention:
`scripts/check_policy_region.py` compares its hash to benchmark_lock.yaml in the pre-commit
hook and in CI, and the adapter compares the region against the live `env.get_policy()`
before an episode starts.

The delimiters are τ's own `<policy>` tags rather than bespoke markers, so nothing extra
enters the prompt.
"""

from __future__ import annotations

import hashlib
import re

OPEN_TAG = "<policy>"
CLOSE_TAG = "</policy>"

_REGION = re.compile(
    rf"{re.escape(OPEN_TAG)}\n(?P<body>.*?)\n{re.escape(CLOSE_TAG)}",
    re.DOTALL,
)

PLACEHOLDER = "NOT YET GENERATED"


class PolicyRegionError(RuntimeError):
    pass


def extract_policy(system_md: str) -> str:
    """Return the region's body verbatim, without the surrounding tags."""
    match = _REGION.search(system_md)
    if match is None:
        raise PolicyRegionError(
            f"SYSTEM.md has no {OPEN_TAG} … {CLOSE_TAG} region on its own lines"
        )
    if _REGION.search(system_md, match.end()) is not None:
        raise PolicyRegionError(
            f"SYSTEM.md has more than one {OPEN_TAG} region; which one is frozen is ambiguous"
        )
    return match.group("body")


def replace_policy(system_md: str, policy: str) -> str:
    """Substitute the region body, leaving every other byte of the file untouched."""
    if _REGION.search(system_md) is None:
        raise PolicyRegionError(f"SYSTEM.md has no {OPEN_TAG} … {CLOSE_TAG} region to write into")
    body = policy.strip("\n")
    return _REGION.sub(lambda _: f"{OPEN_TAG}\n{body}\n{CLOSE_TAG}", system_md, count=1)


def policy_sha256(policy: str) -> str:
    """Hash of the region body. Normalises only the trailing newline."""
    return hashlib.sha256(policy.strip("\n").encode("utf-8")).hexdigest()


def is_placeholder(policy: str) -> bool:
    return PLACEHOLDER in policy


def assert_matches_environment(region_policy: str, live_policy: str, domain: str) -> None:
    """Refuse to run when the prompt's policy is not the policy τ will grade against.

    The last line of defence, and the only one that sees both sides at once: it catches a
    stale lock, a τ² version bump, and a frozen-region edit that reached main anyway.
    """
    if is_placeholder(region_policy):
        raise PolicyRegionError(
            "the <policy> region in target-agent/SYSTEM.md is still a placeholder; "
            "run `make policy` before running the benchmark"
        )
    if region_policy.strip("\n") != live_policy.strip("\n"):
        raise PolicyRegionError(
            "the <policy> region in target-agent/SYSTEM.md does not match "
            f"env.get_policy() for domain {domain!r}.\n"
            f"  region: {len(region_policy)} chars, sha256 {policy_sha256(region_policy)[:16]}\n"
            f"  live:   {len(live_policy)} chars, sha256 {policy_sha256(live_policy)[:16]}\n"
            "Regenerate with `make policy`, or check that the domain and retrieval config "
            "match benchmark_lock.yaml."
        )
