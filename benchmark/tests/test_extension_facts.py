"""The extension host-fact lint: role literals against the measured Pi-side vocabulary.

Seq 8's gen-004 keyed a hook on message role "tool" where this host spells it
"toolResult" — a fact recorded in the experiment's own probe evidence — and the change was
measured inert. These tests pin the mechanism that makes probe-fact consultation
mechanical at commit time.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import check_extension_facts as facts

ROLES = ["user", "assistant", "toolResult"]


def test_flags_a_role_comparison_outside_the_vocabulary_with_file_and_line():
    source = 'const a = 1;\nif (message?.role === "tool") { seen.add(x); }\n'
    findings = facts.problems(source, "extensions/broken.ts", ROLES)
    assert len(findings) == 1
    assert findings[0].startswith("extensions/broken.ts:2:")
    assert '"tool"' in findings[0]


def test_passes_measured_vocabulary_comparisons():
    source = 'if (m.role === "toolResult" || m.role !== "assistant") { x(); }\n'
    assert facts.problems(source, "ok.ts", ROLES) == []


def test_flags_a_role_property_literal_outside_the_vocabulary():
    source = 'const matcher = { role: "tool", text: /x/ };\n'
    findings = facts.problems(source, "matcher.ts", ROLES)
    assert len(findings) == 1 and '"tool"' in findings[0]


def test_ignore_marker_exempts_the_line():
    source = 'if (m.role === "tool") { legacy(); } // extension-facts:ignore — τ-side shape\n'
    assert facts.problems(source, "legacy.ts", ROLES) == []


def test_loose_equality_is_caught_too():
    source = 'if (m.role == "toolMessage") { x(); }\n'
    assert len(facts.problems(source, "loose.ts", ROLES)) == 1


def test_malformed_vocabulary_raises(tmp_path):
    bad = tmp_path / "host_facts.yaml"
    bad.write_text("message_roles:\n  nested:\n    - user\n", encoding="utf-8")
    with pytest.raises(ValueError):
        facts.load_vocabulary(bad)


def test_vocabulary_without_roles_raises(tmp_path):
    bad = tmp_path / "host_facts.yaml"
    bad.write_text("message_roles_evidence: somewhere.json\n", encoding="utf-8")
    with pytest.raises(ValueError, match="message_roles"):
        facts.load_vocabulary(bad)


def test_committed_vocabulary_parses_and_carries_the_measured_roles():
    """Pins the committed file's restricted shape and its measured content — the file is
    the lint's ground truth, so its parseability is part of the contract."""
    vocabulary = facts.load_vocabulary(facts.DEFAULT_VOCABULARY)
    assert vocabulary["message_roles"] == ROLES
    assert "hook_firings.json" in str(vocabulary["message_roles_evidence"])


def test_live_extensions_are_clean():
    """The current recipe's hooks use the measured vocabulary — the lint must pass on the
    tree it lands in."""
    for source in sorted(facts.DEFAULT_EXTENSIONS_DIR.glob("*.ts")):
        assert facts.problems(source.read_text(encoding="utf-8"), source.name, ROLES) == []
