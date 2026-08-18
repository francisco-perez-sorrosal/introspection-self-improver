# Experiment 011_ceiling-probe — Phase 0, the ceiling probe

**Not an experiment.** An odd seq under D15's parity convention, cut PROVISIONAL because
probes are what an unenforced status is for. No generation is measured here, no partition is
frozen, no improvement record is written, and nothing under this directory is reportable as a
curve. Its whole output is three decisions and a reachability map.

Plan **D36**, runbook **Phase 5.11**. Written and committed **before the first episode ran**;
every number arrives later, into a design that already says what it will do with it.

## Why

Four experiments (seq 4, 5, 6, 8, 10) asked "did the score go up" against an **unknown
maximum**, so four nulls left *the loop failed* and *there was nothing to find* equally
alive. Nobody has ever measured how much better **any** harness could be on this objective.
Phase 0 measures it.

Three harnesses are not needed — two are. **H0-current** (the incumbent, byte-identical to
`h0-baseline`) and **H-expert**, hand-built with full access to the candidate tasks and
unlimited effort, **never shipped, never tagged, never part of any loop**, existing only to
bound the range. It buys three things at once:

- **headroom** — `H_expert − H0`, the number the project has never had;
- **a normalized primary** — gap-closure against a measured ceiling, meaningful where
  "+4 pp against an unknown maximum" is not;
- **an empirical reachability oracle** — a task H-expert passes is *provably*
  harness-reachable, which is far better evidence than trajectory reading and is what makes
  a batch beyond the marginal band safe to compose.

## The three decisions, pre-registered

Copied from Phase 5.11, not composed here. They are **not relitigated after the numbers
exist**.

**(a) Backend.** Freeze whichever retrieval config yields the larger **harness headroom**
(`H_expert − H0`), *not* the larger absolute score. A tie goes to `openai_embeddings` — what
τ² publishes, restoring comparability, and its key is already required at grading time.

**(b) Go / no-go.** If headroom ≤ **5 pp** under **both** backends, **seq 12 is not run.**
The objective offers too little for any harness to win, the finding is written up, the ledger
is updated, and the next move is a domain decision (`telecom-workflow` — procedural and
multi-step, where harness discipline should bite), not a fifth attempt here.

**(c) Envelope.** `power_envelope.py --headroom-pp <measured>` must return **REACHABLE**: the
smallest effect the episode-level primary can detect must sit inside the measured headroom.
At B = 30, `num_trials` 3 and a pooled two-round baseline that is **10.6 pp**, so a headroom
below ~11 pp fails this gate even if it clears (b). The response to a failure is more trials
or more tasks — **never a softer test**.

## The candidate pool — 35 tasks, defined before any episode ran

Start from the **54 batch-eligible tasks** enumerated in Phase 5.11 (the pool minus the
held-out 36, minus `task_034`'s frozen-surface user-sim crash, minus the six proven walls),
then apply **one filter, on complexity and not on outcome**: keep tasks with **≤ 9 gold
actions**.

That filter is the seq-10 screen's recorded band ("the productive complexity band, 2–9 gold
actions, where every task ever measured in the marginal band sits"), and its justification is
a *frozen budget* rather than a guess about the harness: τ's frozen `max_steps: 200` and
600-second `timeout_seconds` make a 25-to-37-gold-action task a **budget** wall, not a harness
one, and including tasks where both arms fail for reasons no mutation can reach would deflate
measured headroom toward a false no-go. The excluded 19 are overwhelmingly that class — 14 of
the 16 never-screened eligible tasks carry ≥ 13 gold actions.

The 35:

```
task_001 task_002 task_003 task_004 task_005 task_006 task_008 task_010 task_014 task_015
task_020 task_023 task_024 task_027 task_029 task_032 task_037 task_038 task_046 task_055
task_056 task_057 task_058 task_060 task_061 task_063 task_064 task_065 task_066 task_069
task_071 task_076 task_094 task_101 task_102
```

Thirty-three of the 35 carry a 3-trial H0 rate from the 2026-08-17 seq-10 screen under bm25
(`benchmark/probes/2026-08-17-seq10-screen/`), which makes the probe's own H0/bm25 arm a
replication check on a byte-identical harness one day apart. `task_001` and `task_056` have
never been screened.

**None of the 35 is a member of the intended held-out 36** (enumerated in Phase 5.11), none is
`task_034`, and none is a proven wall (`task_026`, `task_028`, `task_070`, `task_072`,
`task_082`, `task_096`). Verified mechanically before launch.

## The B = 30 composition rule, registered before the numbers exist

A rule written after the data exists is not a rule. From the 35 probed candidates, under the
**chosen backend only**:

1. **Exclude** any task H-expert never passes in 3 trials — *empirically walled*, whatever a
   transcript might suggest.
2. Rank the remainder: tasks with an H0 rate in **1/3–2/3** first (the band where
   `num_trials` resolves movement), then **0/3 tasks H-expert passes** (proven-reachable
   headroom — the tier seq 10's batch never got to admit), then **3/3 anchors**, of which at
   most **four** are admitted as the regression channel.
3. Fill to **30**. If fewer than 30 qualify, **B shrinks (floor 24) rather than admitting an
   empirically-walled task**, and the shrink is recorded with its count.

## Arms, lanes, budget

| | |
|---|---|
| arms | H0-current (`h0-baseline`, byte-identical) · H-expert (throwaway branch) |
| backends | `bm25` **and** `openai_embeddings`, same 35 tasks, same trials |
| lane | local — the work-tree-faithful lane; `introspection dev` serves pushed main and cannot serve H-expert's branch |
| trials | 3 |
| episodes | 35 × 3 × 2 arms × 2 backends = **420** |
| grading | `tau2 evaluate-trajs` via `scripts/grade.py`, against the retrieval config each run recorded — never recomputed here |
| estimate | ≈ **$16** (H0 arms ≈ $4.7 at the measured $0.0225/episode local rate; H-expert arms longer) |

## What H-expert may and may not do

It is built with full access to the candidate tasks and unlimited effort, so it **may** encode
procedure specific to the failure modes visible in them. It still respects every frozen
surface:

- no `<policy>` edit — the frozen benchmark text is not harness;
- no model or thinking-level change;
- no `read`/`bash`-class capability;
- no reading `benchmark/vendor/` at runtime;
- **no gold values, no document ids, no per-task procedure** — general procedure only.

It is built on a **throwaway branch, never merged and never tagged**. A tagged H-expert would
silently become H0, which is the one mistake that would void the whole experiment.

## `h0-baseline` is not re-tagged during Phase 0

Two things move the tree here and neither touches the tag. H-expert lives on a branch that is
deleted. And the `openai_embeddings` arm needs `make policy` to regenerate the frozen
`<policy>` region to run at all, so during that arm the recipe is legitimately not
byte-identical to `h0-baseline` — harmless, because Phase 0 rounds are probes under a
PROVISIONAL lock, not generations, and no cadence gate applies to them. **The tag decision is
the first step of the seq-12 freeze**, and takes exactly one of the three forms Phase 5.11
enumerates.

---

# OUTCOME (2026-08-18) — GO, on `openai_embeddings`

| backend | H0 | H-expert | **harness headroom** |
|---|---|---|---|
| `bm25` | 28.6% | 35.2% | +6.7 pp |
| **`openai_embeddings`** | **23.8%** | **39.1%** | **+15.2 pp** |

The three pre-registered decisions, applied unchanged:

- **(a) Backend → `openai_embeddings`** — larger *harness headroom*, and the two criteria
  disagree: embeddings has the **lower** absolute H0 and more than **twice** the headroom.
  Choosing on absolute score would have frozen bm25 and halved the room the loop can move in.
- **(b) GO** — 15.2 pp against the 5 pp no-go bar.
- **(c) Envelope → REACHABLE** — smallest detectable effect 11.4 pp at the frozen B=26
  (10.6 pp at B=30) sits inside 15.2 pp. No trial increase, no softer test.

**B = 26, not 30.** Only 26 of the 35 candidates carry an empirical reachability certificate
under embeddings, and the rule above says shrink rather than admit a wall. Recorded as a
shrink with its count, per that rule. One widening, made with numbers visible and named here
rather than buried: the rule's letter reads "exclude any task H-expert never passes", which
would drop `task_063` (H0 **3/3**) and `task_010` (H0 2/3) as walled — calling a task H0
passes every time unreachable is false, so the certificate is read as *either arm passes*.
It affects exactly those two tasks and changes no verdict: the strict letter gives B=24,
which also clears the envelope.

Full evidence, method, and the two unplanned findings — H-expert regressing tasks H0 passes
(so this ceiling is a lower bound, gross gain +21.0 pp), and a third identical-harness noise
measurement (12 of 33 task rates moving on a byte-identical recipe) — are in
`benchmark/probes/2026-08-18-phase0-ceiling-probe/README.md`. Run directories were deleted
after extraction: 325 MB of session logs is not a committable record.

**Spend: $12.82**, against ~$16 budgeted. 416/420 episodes, zero stall warnings.
