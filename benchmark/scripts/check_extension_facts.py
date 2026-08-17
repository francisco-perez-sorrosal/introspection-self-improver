#!/usr/bin/env python3
"""Lint target-agent extension code against the measured host vocabulary.

Extension hooks observe the Pi session, and the Pi session's message-role vocabulary is a
measured fact (`benchmark/probes/host_facts.yaml`), not something to remember: seq 8 spent
a generation on a hook keyed to role "tool" where this host spells it "toolResult" — the
truth was sitting in the experiment's own committed probe evidence, and the hook was
measured inert. This check makes that consultation mechanical: any role string literal in
`target-agent/extensions/*.ts` outside the measured vocabulary fails the commit, naming
the file, line, literal, and the probe evidence that establishes the real vocabulary.

Stdlib only (pre-commit runs it under bare python3, beside check_policy_region.py). The
vocabulary file uses a deliberately restricted YAML shape parsed here without PyYAML.
A line containing `extension-facts:ignore` is exempt.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_VOCABULARY = REPO_ROOT / "benchmark" / "probes" / "host_facts.yaml"
DEFAULT_EXTENSIONS_DIR = REPO_ROOT / "target-agent" / "extensions"
IGNORE_MARKER = "extension-facts:ignore"

#: `message?.role === "tool"`, `msg.role !== 'user'` — comparisons against a role property.
_ROLE_COMPARISON = re.compile(r"""\.\s*role\s*(?:===|!==|==|!=)\s*(["'])(?P<literal>[^"']*)\1""")
#: `role: "tool"` — a role property literal (message construction or matcher objects).
_ROLE_PROPERTY = re.compile(r"""\brole\s*:\s*(["'])(?P<literal>[^"']*)\1""")


def load_vocabulary(path: Path) -> dict[str, object]:
    """Parse the restricted host-facts shape: comments, `key: scalar`, `key:` + `- item`.

    Anything outside that shape raises ValueError — a vocabulary that cannot be trusted to
    parse cannot be trusted to lint against.
    """
    data: dict[str, object] = {}
    current_list: list[str] | None = None
    for lineno, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        item = re.fullmatch(r"\s+-\s+(?P<value>\S.*?)\s*", line)
        if item:
            if current_list is None:
                raise ValueError(f"{path}:{lineno}: list item outside a `key:` block")
            current_list.append(item.group("value"))
            continue
        key_value = re.fullmatch(r"(?P<key>[A-Za-z_][A-Za-z0-9_]*):\s*(?P<value>.*?)\s*", line)
        if key_value is None:
            raise ValueError(f"{path}:{lineno}: unsupported syntax {raw!r}")
        key, value = key_value.group("key"), key_value.group("value")
        if value:
            data[key] = value
            current_list = None
        else:
            current_list = []
            data[key] = current_list
    roles = data.get("message_roles")
    if not isinstance(roles, list) or not roles:
        raise ValueError(f"{path}: `message_roles:` must be a non-empty list")
    return data


def problems(source_text: str, filename: str, roles: list[str]) -> list[str]:
    """Role literals in the source outside the measured vocabulary, as file:line findings."""
    allowed = set(roles)
    findings: list[str] = []
    for lineno, line in enumerate(source_text.splitlines(), start=1):
        if IGNORE_MARKER in line:
            continue
        for pattern in (_ROLE_COMPARISON, _ROLE_PROPERTY):
            for match in pattern.finditer(line):
                literal = match.group("literal")
                if literal not in allowed:
                    findings.append(
                        f'{filename}:{lineno}: role literal "{literal}" is not in the '
                        f"measured host vocabulary {sorted(allowed)}"
                    )
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dir", type=Path, default=DEFAULT_EXTENSIONS_DIR)
    parser.add_argument("--vocab", type=Path, default=DEFAULT_VOCABULARY)
    args = parser.parse_args()

    try:
        vocabulary = load_vocabulary(args.vocab)
    except (OSError, ValueError) as error:
        print(f"✗ host vocabulary unreadable: {error}", file=sys.stderr)
        return 2
    roles = list(vocabulary["message_roles"])  # type: ignore[arg-type]
    evidence = vocabulary.get("message_roles_evidence", "<no evidence path recorded>")

    findings: list[str] = []
    for source in sorted(args.dir.glob("*.ts")) if args.dir.is_dir() else []:
        findings.extend(
            problems(
                source.read_text(encoding="utf-8"),
                str(source.relative_to(REPO_ROOT)),
                roles,
            )
        )
    if findings:
        for finding in findings:
            print(f"✗ {finding}", file=sys.stderr)
        print(
            f"  measured vocabulary: {args.vocab.relative_to(REPO_ROOT)} "
            f"(evidence: {evidence}); fix the literal or mark the line {IGNORE_MARKER}",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
