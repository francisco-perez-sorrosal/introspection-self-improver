"""Improvement records: the per-transition evidence chain, held to the contract.

One YAML per transition H_g → H_(g+1) under results/experiment_<id>/improvement_records/,
written while the transition happens. The field list lives in
contract/improvement_record.schema.yaml — data, not code — and this module enforces it
plus the rules a field list cannot state (decision D5): an accepted mutation names a
candidate commit distinct from its source, a rejected or identity transition is pinned to
H_(g+1) = H_g, every record cites at least one Introspection conversation, and
held_out_result stays empty until reveal fills it. A record that fails validation is a
broken link in the evidence → signal → hypothesis → mutation → result chain, which is the
research artifact itself — not paperwork around it.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from tau_adapter.lock import REPO_ROOT, Lock

SCHEMA_PATH = REPO_ROOT / "contract" / "improvement_record.schema.yaml"
RECORDS_DIRNAME = "improvement_records"

OUTCOME_ACCEPTED = "accepted"

_KIND_CHECKS = {
    "str": lambda value: isinstance(value, str),
    "int": lambda value: isinstance(value, int) and not isinstance(value, bool),
    "mapping": lambda value: isinstance(value, dict),
    "list": lambda value: isinstance(value, list),
}


def load_schema(path: Path = SCHEMA_PATH) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def record_name(from_generation: int) -> str:
    return f"gen_{from_generation:03d}_to_{from_generation + 1:03d}.yaml"


def records_dir(lock: Lock, results_root: Path) -> Path:
    return results_root / f"experiment_{lock.experiment_id}" / RECORDS_DIRNAME


def load_record(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def validate(
    record: dict[str, Any],
    *,
    filename: str | None = None,
    revealed: bool = False,
    schema: dict[str, Any] | None = None,
    results_root: Path | None = None,
) -> list[str]:
    """Mechanical checks on one record. Returns problems; empty means it holds.

    ``results_root`` scopes the provenance check (default: the repo's results/). Callers
    operating on an injected tree — reveal, tests — pass their own, so provenance
    resolves against the same experiment the rest of the validation is looking at.
    """
    schema = schema or load_schema()
    problems = _field_problems(record, schema)
    outcome = record.get("outcome")
    if outcome not in (schema.get("outcomes") or []):
        problems.append(f"outcome {outcome!r} is not one of {schema.get('outcomes')}")
        return problems
    problems += _transition_problems(record, filename)
    problems += _mutation_problems(record, outcome)
    problems += _changes_problems(record, outcome)
    problems += _evidence_problems(record, results_root or REPO_ROOT / "results")
    problems += _prose_problems(record, outcome, schema)
    if not revealed and record.get("held_out_result") is not None:
        problems.append(
            "held_out_result is filled, but the experiment has not revealed: this field "
            "is written by `make reveal`, never during optimization"
        )
    return problems


def _field_problems(record: dict[str, Any], schema: dict[str, Any]) -> list[str]:
    problems: list[str] = []
    for name, spec in (schema.get("fields") or {}).items():
        value = record.get(name)
        if value is None:
            if spec.get("required"):
                problems.append(f"missing required field: {name}")
            continue
        kind = spec.get("kind", "str")
        if not _KIND_CHECKS[kind](value):
            problems.append(f"{name} must be a {kind}, got {type(value).__name__}")
            continue
        if kind == "str" and spec.get("required") and _is_placeholder(value):
            problems.append(
                f"{name} still carries the scaffold's TODO placeholder — the record is "
                "written while the transition happens, not left as a template"
            )
        for key in spec.get("required_keys") or []:
            if isinstance(value, dict) and value.get(key) is None:
                problems.append(f"{name}.{key} is missing")
    unknown = sorted(set(record) - set(schema.get("fields") or {}))
    if unknown:
        problems.append(f"unknown fields: {', '.join(unknown)}")
    return problems


def _transition_problems(record: dict[str, Any], filename: str | None) -> list[str]:
    transition = record.get("transition") or {}
    src, dst = transition.get("from_generation"), transition.get("to_generation")
    if not isinstance(src, int) or not isinstance(dst, int):
        return []  # the field check above already reported the shape
    problems: list[str] = []
    if dst != src + 1:
        problems.append(f"transition {src}→{dst} must advance exactly one generation")
    if filename is not None and filename != record_name(src):
        problems.append(f"filename {filename!r} does not match transition ({record_name(src)})")
    return problems


def _mutation_problems(record: dict[str, Any], outcome: str) -> list[str]:
    mutation = record.get("mutation") or {}
    source, candidate = mutation.get("source_commit"), mutation.get("candidate_commit")
    if outcome == OUTCOME_ACCEPTED:
        if not candidate or candidate == source:
            return [
                "an accepted mutation must name a candidate_commit distinct from "
                "source_commit — the merge commit is the next generation"
            ]
        return []
    if candidate and candidate != source:
        return [
            f"outcome {outcome!r} pins the next generation to its source (D5): "
            "candidate_commit must be null or equal to source_commit"
        ]
    return []


#: What every item of a composite improvement set must state for itself (plan D22).
#: `mechanism` keeps the CLI improve discipline per change — one coherent mechanism —
#: while the generation carries any number of them; `expected_effect` is the item's own
#: falsifiable prediction, the only per-change attribution a composite set has.
_CHANGE_REQUIRED_KEYS = ("mechanism", "surface", "expected_effect")


def _changes_problems(record: dict[str, Any], outcome: str) -> list[str]:
    """The composite-set rules (plan D22), keyed on schema_version so history validates.

    Seq ≤ 5 records carry no `schema_version` and ran one-mutation-per-generation; they
    validate untouched. A version-2 record that accepted or rejected a mutation must
    itemize its set — a set-level prose summary alone cannot be scored per change by the
    next batch, and unscoreable changes are how a loop stops learning from itself.
    """
    problems: list[str] = []
    changes = record.get("changes")
    if changes is not None:
        for index, item in enumerate(changes):
            if not isinstance(item, dict):
                problems.append(f"changes[{index}] must be a mapping")
                continue
            for key in _CHANGE_REQUIRED_KEYS:
                value = item.get(key)
                if not isinstance(value, str) or not value.strip() or _is_placeholder(value):
                    problems.append(
                        f"changes[{index}].{key} must be non-empty prose (no TODO): each "
                        "change states its own mechanism, surface and falsifiable "
                        "prediction — per-change attribution is mechanistic, and an "
                        "unstated prediction cannot be scored by the next batch"
                    )
    version = record.get("schema_version")
    if (
        isinstance(version, int)
        and version >= 2
        and outcome in (OUTCOME_ACCEPTED, "rejected")
        and not changes
    ):
        problems.append(
            "a schema_version 2 record with a landed-or-declined mutation must itemize "
            "its improvement set in `changes` (plan D22) — one item per coherent change"
        )
    return problems


def _is_placeholder(value: Any) -> bool:
    return isinstance(value, str) and value.strip().upper().startswith("TODO")


def _evidence_problems(record: dict[str, Any], results_root: Path) -> list[str]:
    conversations = (record.get("evidence") or {}).get("conversation_ids")
    if not conversations:
        return [
            "evidence.conversation_ids is empty: every claim cites the executions behind "
            "it, and the batch ran regardless of the outcome"
        ]
    if any(_is_placeholder(conversation) for conversation in conversations):
        return [
            "evidence.conversation_ids still carries the scaffold's TODO placeholder — "
            "cite the real Introspection conversation ids behind the claim"
        ]
    return _provenance_problems(record, conversations, results_root)


def _known_conversation_ids(experiment_id: str, results_root: Path) -> set[str]:
    """Every conversation this experiment's own batch rounds actually produced."""
    experiment_dir = results_root / f"experiment_{experiment_id}"
    known: set[str] = set()
    for manifest_path in experiment_dir.glob("generation_*/batch_*/episode_manifest.jsonl"):
        for line in manifest_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            # Manifest rows carry the conversation as `introspection_task_id` — on the
            # platform lane the task id doubles as the conversation id (manifest.py).
            # This function briefly grepped a `conversation_id` key no row has ever
            # carried, which — combined with the old skip-on-empty — made the whole
            # provenance gate silently inert. Found 2026-08-16 the moment the hard-fail
            # ran against real records; `conversation_id` stays as a fallback only.
            identity = row.get("introspection_task_id") or row.get("conversation_id")
            if identity:
                known.add(str(identity))
    return known


def _provenance_problems(
    record: dict[str, Any], conversations: list[Any], results_root: Path
) -> list[str]:
    """Every cited conversation must come from THIS experiment's own batch rounds.

    Experiments are isolated: a record for experiment X may not borrow evidence from
    experiment Y, however revealed Y is. A prior experiment is legitimate *context* in prose
    ("experiment 004 found …") and never evidence in a record — the distinction being that a
    record's claims are what a reader re-derives from the cited executions, and those
    executions must belong to the harness the record is about.

    Enforced against the episode manifests rather than trusted to discipline, because the
    failure is silent: a plausible-looking id from a prior experiment reads exactly like a
    real one, and nothing downstream would ever resolve it.

    No manifests yet is a FAILURE, not a skip. By the time this runs the record carries
    real-looking conversation ids (the scaffold's TODO placeholder fails earlier), and before
    any batch round has written a manifest there is nowhere legitimate such ids can have come
    from — only a prior experiment or thin air, which are exactly the two cases this check
    exists to refuse. "Cannot verify" must never validate as "verified".
    """
    # The schema's field is `experiment`. This function briefly read `experiment_id` — a
    # key no real record carries — which silently disabled the whole check on every real
    # record while the unit tests (whose fixtures used the wrong key too) stayed green.
    # Found 2026-08-16; the fixtures now use the schema name, so a key drift here fails.
    experiment_id = str(record.get("experiment") or "").strip()
    if not experiment_id:
        return []
    known = _known_conversation_ids(experiment_id, results_root)
    if not known:
        return [
            f"evidence.conversation_ids cannot be provenance-checked: experiment "
            f"{experiment_id} has no batch episode manifests yet, so no conversation can "
            "legitimately be cited. Run the batch round first; the record is not done until "
            "its evidence verifies against the round that produced it."
        ]
    foreign = sorted({str(c) for c in conversations} - known)
    if not foreign:
        return []
    return [
        "evidence.conversation_ids cites conversation(s) absent from this experiment's own "
        f"batch manifests: {', '.join(foreign[:5])}"
        f"{' …' if len(foreign) > 5 else ''}. Record evidence is the current experiment's "
        "batch conversations, nothing else — a prior experiment belongs in prose as labelled "
        "context, never as a cited execution."
    ]


def _prose_problems(record: dict[str, Any], outcome: str, schema: dict[str, Any]) -> list[str]:
    problems: list[str] = []
    for name, spec in (schema.get("fields") or {}).items():
        required_for = spec.get("prose_required_for") or []
        if outcome in required_for:
            value = record.get(name)
            if isinstance(value, str) and not value.strip():
                problems.append(f"{name} must not be empty for an {outcome} transition")
    return problems


def scaffold(
    lock: Lock,
    from_generation: int,
    batch_name: str,
    batch_task_ids: list[str],
    source_commit: str,
    date: str | None = None,
) -> str:
    """A record template with everything derivable prefilled and TODOs where prose belongs."""
    body = {
        "transition": {
            "from_generation": from_generation,
            "to_generation": from_generation + 1,
        },
        "experiment": lock.experiment_id,
        "outcome": "TODO: accepted | rejected | identity",
        "batch": {"name": batch_name, "task_ids": list(batch_task_ids)},
        "evidence": {
            "conversation_ids": ["TODO: conv_..."],
            "summary": "TODO: what was inspected, via which operate queries",
        },
        "signals": [{"description": "TODO", "prevalence": "TODO: n/B"}],
        "counterevidence": "TODO: what argued against the hypothesis, or 'none found'",
        "hypothesis": "TODO",
        "owning_layer": "TODO: set-level summary of the surfaces targeted",
        "proposed_change": (
            "TODO: the SET-level summary — why these changes compose "
            "(independently justified, non-conflicting)"
        ),
        "schema_version": 2,
        # One item per coherent change (plan D22): any number, each individually
        # evidenced, each with its own falsifiable prediction the next batch will score.
        # Duplicate the template item as needed; delete none of its keys.
        "changes": [
            {
                "mechanism": "TODO: the one coherent mechanism this change encodes",
                "surface": (
                    "TODO: instructions | pi-skill | extension-tool | sub-agent | "
                    "retrieval-usage | revert | other"
                ),
                "evidence": "TODO: conversation ids / backlog target id behind this change",
                "expected_effect": "TODO: this change's own falsifiable prediction",
                "risk": "TODO: how this change could make things worse, or 'none identified'",
                "commit": None,
            }
        ],
        "mutation": {
            "branch": f"gen-{from_generation + 1:03d}/TODO-slug",
            "pr_url": "TODO",
            "source_commit": source_commit,
            "candidate_commit": None,
        },
        "expected_effect": "TODO: the SET-level predicted direction, not a number",
        "human_approval": {
            "approved_by": "TODO",
            "date": date or datetime.now(UTC).strftime("%Y-%m-%d"),
        },
        "held_out_result": None,
    }
    header = (
        "# Improvement record for one generation transition (protocol §24; schema:\n"
        "# contract/improvement_record.schema.yaml). Written while the transition happens.\n"
        "# held_out_result stays null — `make reveal` fills it after the final generation.\n"
        "# Verify with: scripts/improvement_record.py --verify <this file>\n"
    )
    return header + yaml.safe_dump(body, sort_keys=False, allow_unicode=True, width=96)
