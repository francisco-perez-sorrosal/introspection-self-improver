"""The frozen `<policy>` region, and the two gates that hold it in place.

A defect here would let the agent be graded against a policy it was never shown, or let an edit
to benchmark text pass as a harness change — both change scores while leaving the evaluator
untouched.
"""

from __future__ import annotations

import pytest

from tau_adapter.policy_region import (
    PolicyRegionError,
    assert_matches_environment,
    extract_policy,
    is_placeholder,
    policy_sha256,
    replace_policy,
)

SYSTEM_MD = """<instructions>
Harness instructions, mutable.
</instructions>

<policy>
Frozen benchmark text.
Second line.
</policy>
"""


def test_extracts_the_body_without_the_tags() -> None:
    assert extract_policy(SYSTEM_MD) == "Frozen benchmark text.\nSecond line."


def test_replace_touches_nothing_outside_the_region() -> None:
    updated = replace_policy(SYSTEM_MD, "Replacement.")
    assert extract_policy(updated) == "Replacement."
    assert "Harness instructions, mutable." in updated
    assert updated.startswith("<instructions>")


def test_replace_is_idempotent() -> None:
    once = replace_policy(SYSTEM_MD, "Replacement.")
    assert replace_policy(once, "Replacement.") == once


def test_missing_region_is_an_error_not_a_silent_skip() -> None:
    with pytest.raises(PolicyRegionError, match="no <policy>"):
        extract_policy("<instructions>nothing else</instructions>\n")


def test_two_regions_are_ambiguous_and_rejected() -> None:
    doubled = SYSTEM_MD + "\n<policy>\nA second one.\n</policy>\n"
    with pytest.raises(PolicyRegionError, match="more than one"):
        extract_policy(doubled)


def test_hash_ignores_only_surrounding_blank_lines() -> None:
    assert policy_sha256("body") == policy_sha256("\nbody\n")
    assert policy_sha256("body") != policy_sha256("body ")


def test_placeholder_is_detected() -> None:
    assert is_placeholder("NOT YET GENERATED — run `make policy`")
    assert not is_placeholder("Frozen benchmark text.")


def test_environment_mismatch_refuses_to_run() -> None:
    with pytest.raises(PolicyRegionError, match="does not match"):
        assert_matches_environment("what the agent reads", "what tau grades", "mock")


def test_environment_match_permits_the_run() -> None:
    assert assert_matches_environment("same text", "same text", "mock") is None


def test_placeholder_refuses_before_comparing() -> None:
    # A placeholder must be reported as such rather than as a generic mismatch: the fix is
    # `make policy`, not an investigation into which side drifted.
    with pytest.raises(PolicyRegionError, match="placeholder"):
        assert_matches_environment("NOT YET GENERATED", "real policy", "mock")
