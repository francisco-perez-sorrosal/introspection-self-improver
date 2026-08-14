"""Generation identity: the H0 anchor, and the tags that name every generation after it.

A generation is an approved merge commit on main, tagged ``exp<seq>-g<NNN>`` (decision
D5); H0 is the recipe state under the annotated ``h0-baseline`` tag, and every experiment
starts by restoring it (decision D6) — replace, not merge. The restore here is stricter
than a path checkout: the recipe tree is removed first, so a file *committed* into
``target-agent/`` after the tag is staged for deletion rather than silently surviving —
the one case ``git checkout <tag> -- <path>`` plus ``git clean`` both miss. The
machine-local runtime binding ``.introspection/local.json`` is CLI-written and is never
restored or removed.

Nothing here runs ``make bootstrap`` or ``introspection check`` — those are the reset
*script*'s later steps; this module owns only the git mechanics, so they stay testable in
a scratch repository.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from tau_adapter.lock import REPO_ROOT, Lock

H0_TAG = "h0-baseline"
#: The recipe surface the h0-baseline tag anchors. Restore and verification are scoped to
#: exactly this — dirt anywhere else is not H0's business.
ANCHORED_PATHS = ("target-agent", ".introspection/target-agent.yaml")
#: Machine-local runtime binding, written by the Introspection CLI. Preserved, never restored.
PRESERVED_LOCAL_BINDING = ".introspection/local.json"


class GenerationError(RuntimeError):
    pass


def generation_tag(seq: int, generation: int) -> str:
    """The tag naming H_<generation> of experiment <seq>, e.g. ``exp2-g001``."""
    return f"exp{seq}-g{generation:03d}"


def final_generation_tag(lock: Lock) -> str:
    return generation_tag(lock.experiment_seq, lock.protocol.generations)


def tag_exists(tag: str, repo_root: Path = REPO_ROOT) -> bool:
    listed = _git(["tag", "--list", tag], repo_root)
    return listed.strip() == tag


def restore_h0(repo_root: Path = REPO_ROOT) -> None:
    """Reset the anchored recipe surface to the h0-baseline tag, staged and ready to commit.

    Removes ``target-agent/`` outright (untracked and ignored runtime state included — the
    generated ``.pi`` files are ``make bootstrap``'s job to regrow), checks the tag's tree
    back out, and stages the difference so files added after the tag record as deletions.
    """
    if not tag_exists(H0_TAG, repo_root):
        raise GenerationError(
            f"tag {H0_TAG!r} does not exist here: it is the H0 anchor (D6), created when "
            "the baseline recipe was frozen — without it there is no defined H0 to restore"
        )
    recipe_dir = repo_root / ANCHORED_PATHS[0]
    if recipe_dir.exists():
        shutil.rmtree(recipe_dir)
    _git(["checkout", H0_TAG, "--", *ANCHORED_PATHS], repo_root)
    _git(["add", "-A", "--", *ANCHORED_PATHS], repo_root)


def verify_against_tag(tag: str, repo_root: Path = REPO_ROOT) -> list[str]:
    """Byte-identity of the anchored surface against a tag. Problems; empty means it holds."""
    problems: list[str] = []
    diff = subprocess.run(  # noqa: S603 - operator's git on this repo
        ["git", "diff", "--stat", tag, "--", *ANCHORED_PATHS],  # noqa: S607
        cwd=repo_root,
        capture_output=True,
        text=True,
        timeout=30,
        check=True,
    ).stdout.strip()
    if diff:
        problems.append(f"the work tree differs from {tag}:\n{diff}")
    untracked = [
        line
        for line in _git(["status", "--porcelain", "--", ANCHORED_PATHS[0]], repo_root).splitlines()
        if line.startswith("??")
    ]
    if untracked:
        problems.append(
            "untracked files under the anchored surface (not part of any generation): "
            + ", ".join(line[3:] for line in untracked)
        )
    return problems


def verify_h0(repo_root: Path = REPO_ROOT) -> list[str]:
    """Byte-identity of the anchored surface against the H0 tag."""
    return verify_against_tag(H0_TAG, repo_root)


def heldout_generation_tag(seq: int, generation_name: str) -> str:
    """The tag a held-out round for `generation_NNN` must measure: H0's anchor, or exp<seq>-gNNN."""
    index = int(generation_name.removeprefix("generation_"))
    return H0_TAG if index == 0 else generation_tag(seq, index)


def assert_heldout_measures_a_generation(
    seq: int, generation_name: str, repo_root: Path = REPO_ROOT
) -> str:
    """Refuse a held-out round whose recipe surface is not exactly the named generation.

    A held-out measurement is attributable only if the recipe that runs is byte-identical
    to the generation it claims to measure (guardrails 12/13): H0 is the `h0-baseline`
    tag, H_n (n ≥ 1) is the approved merge tagged `exp<seq>-gNNN` — created before the
    round, per the generation loop's order. Returns the verified tag for the run banner.
    """
    tag = heldout_generation_tag(seq, generation_name)
    if not tag_exists(tag, repo_root):
        raise GenerationError(
            f"a held-out round for {generation_name} measures the recipe under tag {tag!r}, "
            "which does not exist: tag the approved generation first (the loop order is "
            "merge → tag → held-out), or fix GEN if it names the wrong generation."
        )
    problems = verify_against_tag(tag, repo_root)
    if problems:
        raise GenerationError(
            f"the recipe surface is not byte-identical to {tag!r}, so this held-out round "
            f"would measure something other than {generation_name}:\n  ✗ " + "\n  ✗ ".join(problems)
        )
    return tag


def _git(args: list[str], repo_root: Path) -> str:
    proc = subprocess.run(  # noqa: S603 - operator's git on this repo
        ["git", *args],  # noqa: S607 - operator's git
        cwd=repo_root,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    if proc.returncode != 0:
        raise GenerationError(
            f"git {' '.join(args)} failed: {(proc.stderr or proc.stdout).strip()}"
        )
    return proc.stdout
