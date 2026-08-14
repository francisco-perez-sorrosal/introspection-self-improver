"""Round types: what --batch and --heldout mean, resolved before any money is spent.

The generation protocol runs exactly two kinds of measured rounds (SIA_EVALUATION_PLAN.md
D1): improvement batches on the platform lane, where every episode must leave Introspection
evidence for `operate` to read, and held-out evaluations on the local lane, where no platform
evidence may exist at all — that absence is the firewall. The lane is therefore not a
preference a round type combines with; it is part of the round's meaning, and the wrong
pairing is refused rather than corrected. Ad-hoc rounds (neither flag) keep their free choice
of transport, task ids and domain: they are the bring-up and diagnostic path, never a
protocol round.

Resolution also re-verifies the frozen partition against the lock's protocol config, with the
same machinery that froze it, so a manifest that no longer matches the freeze stops the round
here — not after the budget is spent.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from tau_adapter import split as splitmod
from tau_adapter.lock import Lock

TRANSPORT_LOCAL = "local"
TRANSPORT_PLATFORM = "platform"
TRANSPORTS = (TRANSPORT_LOCAL, TRANSPORT_PLATFORM)

KIND_BATCH = "batch"
KIND_HELDOUT = "heldout"
KIND_ADHOC = "adhoc"


class RoundError(RuntimeError):
    pass


@dataclass(frozen=True)
class RoundSpec:
    """One resolved round: everything the runner varies by round type, in one place."""

    kind: str
    transport: str
    #: Partition name recorded on every artifact (`batch_NN` / `held_out`); None for ad-hoc.
    split: str | None
    #: Selected task ids. None means the whole locked split (ad-hoc only).
    task_ids: list[str] | None
    #: Platform title token for batch evidence (` b01`); empty when there is nothing to tag.
    label_token: str


def resolve_max_concurrency(flag: int | None, *, locked_mode: bool, lock_value: int) -> int:
    """The run's episode concurrency, refused before any money is spent when it lies.

    `max_concurrency` is a frozen execution budget (CLAUDE.md): a later generation must not
    "improve" by being allowed more parallelism, so locked-mode runs — protocol rounds
    included — always read the lock and refuse the flag outright. Diagnostic rounds are not
    comparable to anything by definition, which is what makes the override safe there; it is
    how the concurrency machinery is exercised while the frozen VALUE stays 1.
    """
    if flag is None:
        return int(lock_value)
    if locked_mode:
        raise RoundError(
            "--max-concurrency is refused on the locked domain: max_concurrency is a frozen "
            f"execution budget and this run reads the lock's value ({lock_value}). The flag "
            "exists for diagnostic-mode rounds only."
        )
    if flag < 1:
        raise RoundError(f"--max-concurrency must be at least 1, got {flag}")
    return flag


def assert_transport_supports_concurrency(transport: str, max_concurrency: int) -> None:
    """The platform lane is pinned at one episode in flight; refuse anything else.

    Every development-lane episode rendezvouses at the single URL `introspection dev
    --mcp tau=<url>` was handed, so N in flight would share one bridge channel and cross
    results between episodes — the exact contamination the channels exist to prevent. The
    platform's own affordance for N>1 (one named `dev --as <worker>` attachment per
    worker, tasks routed fail-closed via INTROSPECTION_DEV_TARGET) is documented but
    deliberately not built: it cannot be live-exercised while the frozen value is 1, and
    machinery this repo cannot prove is machinery it does not ship. See
    `contract/constraints.md` § Platform-lane concurrency.
    """
    if transport == TRANSPORT_PLATFORM and max_concurrency > 1:
        raise RoundError(
            f"the platform lane runs one episode at a time, not {max_concurrency}: every "
            "episode rendezvouses at the one URL `introspection dev` was handed, so N in "
            "flight would share a single bridge channel and cross results between episodes. "
            "Raising the frozen value for platform batches first needs the N-attachment "
            "path (`introspection dev --as <worker>` + INTROSPECTION_DEV_TARGET routing) "
            "built and proven — contract/constraints.md § Platform-lane concurrency."
        )


def resolve_round(
    *,
    batch: int | None,
    heldout: bool,
    transport: str | None,
    task_ids: list[str] | None,
    domain: str | None,
    overwrite: bool,
    lock: Lock,
    manifest: dict[str, Any] | None = None,
    rows: list[splitmod.TaskRow] | None = None,
) -> RoundSpec:
    """Resolve CLI intent into a RoundSpec, refusing every combination that lies.

    ``manifest`` and ``rows`` are required for protocol rounds (the caller loads them; this
    stays pure) and ignored for ad-hoc ones.
    """
    if batch is not None and heldout:
        raise RoundError("--batch and --heldout name different round types; pick one")
    if batch is None and not heldout:
        return RoundSpec(
            kind=KIND_ADHOC,
            transport=transport or TRANSPORT_LOCAL,
            split=None,
            task_ids=task_ids,
            label_token="",
        )

    _refuse_adhoc_flags(task_ids=task_ids, domain=domain)
    if manifest is None or rows is None:
        raise RoundError("internal: a protocol round needs the partition manifest and task rows")
    _verify_partition(manifest, rows, lock)

    if batch is not None:
        return _batch_spec(batch, transport, manifest, lock)
    return _heldout_spec(transport, overwrite, manifest)


def _refuse_adhoc_flags(task_ids: list[str] | None, domain: str | None) -> None:
    if task_ids:
        raise RoundError(
            "a protocol round's task selection comes from the frozen partition manifest, "
            "never per invocation. Drop --task-ids, or drop --batch/--heldout for an "
            "ad-hoc round."
        )
    if domain:
        raise RoundError(
            "protocol rounds run the locked domain only; --domain is for ad-hoc diagnostic runs."
        )


def _verify_partition(manifest: dict[str, Any], rows: list[splitmod.TaskRow], lock: Lock) -> None:
    protocol = lock.protocol
    sizes = splitmod.partition_sizes(
        protocol.generations,
        protocol.improvement_tasks_per_generation,
        protocol.held_out_tasks,
    )
    problems = splitmod.verify(manifest, rows, lock.domain, sizes)
    if problems:
        raise RoundError(
            "the frozen partition no longer verifies against the lock's protocol config, "
            "so no episode was spent:\n  ✗ " + "\n  ✗ ".join(problems)
        )


def _batch_spec(
    batch: int, transport: str | None, manifest: dict[str, Any], lock: Lock
) -> RoundSpec:
    if transport == TRANSPORT_LOCAL:
        raise RoundError(
            "an improvement batch is a platform-lane round by definition "
            "(SIA_EVALUATION_PLAN.md D1): its episodes must leave Introspection evidence "
            "for `operate` to read. Drop --transport local, or run an ad-hoc round with "
            "--task-ids for a local diagnostic."
        )
    name = splitmod.batch_name(batch)
    batches = manifest.get("batches") or {}
    if name not in batches:
        held = ", ".join(sorted(batches)) or "none"
        raise RoundError(
            f"the partition holds [{held}]; there is no {name} "
            f"(protocol.generations = {lock.protocol.generations})"
        )
    return RoundSpec(
        kind=KIND_BATCH,
        transport=TRANSPORT_PLATFORM,
        split=name,
        task_ids=list(batches[name]),
        label_token=f" b{batch:02d}",
    )


def _heldout_spec(transport: str | None, overwrite: bool, manifest: dict[str, Any]) -> RoundSpec:
    if transport == TRANSPORT_PLATFORM:
        raise RoundError(
            "a held-out round is local-lane by definition (SIA_EVALUATION_PLAN.md D1): "
            "platform evidence for held-out tasks must never exist — that absence is the "
            "firewall, not a preference. Drop --transport platform."
        )
    if overwrite:
        raise RoundError(
            "a held-out round is measured once per generation; --overwrite would replace a "
            "measurement. If this round must truly be redone, that is an experiment-level "
            "decision: delete the vault directory by hand and record why."
        )
    return RoundSpec(
        kind=KIND_HELDOUT,
        transport=TRANSPORT_LOCAL,
        split=splitmod.HELD_OUT,
        task_ids=list(manifest.get(splitmod.HELD_OUT) or []),
        label_token="",
    )
