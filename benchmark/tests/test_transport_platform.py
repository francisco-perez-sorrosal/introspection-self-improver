"""The AG-UI event contract, pinned to shapes captured from a live development-lane run.

Nothing upstream documents these events, so this file is the record of what the platform
actually emits. Every payload below was copied from `tasks stream` output rather than invented;
if the platform changes the vocabulary, these tests are what notices.
"""

from __future__ import annotations

import json

from tau_adapter.transport import AssistantTurn, TransportFailure
from tau_adapter.transport_platform import (
    PlatformTransport,
    StreamAssembler,
    _StreamSession,
    original_title_of,
)

RUN = "019ff8c7-8167-711a-8eb4-3d07ee88b44f"
TASK = "019ff8c7-8167-711a-8eb4-3d08870f89b9"


def envelope(event: dict) -> dict:
    """The outer wrapper every streamed line carries."""
    return {"event": event, "event_id": None, "run_id": RUN, "task_id": TASK}


def feed_all(assembler: StreamAssembler, events: list[dict]) -> list:
    out = []
    for event in events:
        out.extend(assembler.feed(envelope(event)))
    return out


def test_text_message_assembles_from_its_deltas_and_flushes_at_run_end() -> None:
    turns = feed_all(
        StreamAssembler(),
        [
            {"type": "TEXT_MESSAGE_START", "messageId": f"{RUN}:text:0", "role": "assistant"},
            {"type": "TEXT_MESSAGE_CONTENT", "messageId": f"{RUN}:text:0", "delta": "Hello, "},
            {"type": "TEXT_MESSAGE_CONTENT", "messageId": f"{RUN}:text:0", "delta": "world"},
            {"type": "TEXT_MESSAGE_END", "messageId": f"{RUN}:text:0"},
            {"type": "RUN_FINISHED", "runId": RUN, "threadId": TASK},
        ],
    )
    assert turns == [AssistantTurn(text="Hello, world", tool_calls=())]


def test_tool_call_keeps_the_name_the_model_saw() -> None:
    """The stream carries Recipes' mangled name; mapping it back to τ's is the agent's job."""
    turns = feed_all(
        StreamAssembler(),
        [
            {
                "type": "TOOL_CALL_START",
                "toolCallId": "toolu_01QU3wFb9rmkZe4sK3L9qG1z",
                "toolCallName": "mcp_tau_KB_search_77c5623a9f",
            },
            {
                "type": "TOOL_CALL_ARGS",
                "toolCallId": "toolu_01QU3wFb9rmkZe4sK3L9qG1z",
                "delta": '{"query": "personal credit cards no annual fee',
            },
            {
                "type": "TOOL_CALL_ARGS",
                "toolCallId": "toolu_01QU3wFb9rmkZe4sK3L9qG1z",
                "delta": '"}',
            },
            {"type": "TOOL_CALL_END", "toolCallId": "toolu_01QU3wFb9rmkZe4sK3L9qG1z"},
        ],
    )
    assert len(turns) == 1
    (call,) = turns[0].tool_calls
    assert turns[0].text is None
    assert call.id == "toolu_01QU3wFb9rmkZe4sK3L9qG1z"
    assert call.pi_name == "mcp_tau_KB_search_77c5623a9f"
    # The whole point: the arguments must survive delta reassembly exactly, because the result
    # is posted back under a key derived from them.
    assert call.arguments == {"query": "personal credit cards no annual fee"}


def test_unparseable_arguments_fail_loudly() -> None:
    """A truncated delta stream must not become `{}`.

    Posting a result under empty arguments leaves the sandbox's MCP call parked on a key nobody
    answers, and the episode dies of a daemon timeout with no indication why. Observed for real
    while probing the lane, which is why it is a test.
    """
    turns = feed_all(
        StreamAssembler(),
        [
            {"type": "TOOL_CALL_START", "toolCallId": "c1", "toolCallName": "mcp_tau_x_0000000000"},
            {"type": "TOOL_CALL_ARGS", "toolCallId": "c1", "delta": '{"query": "half'},
            {"type": "TOOL_CALL_END", "toolCallId": "c1"},
        ],
    )
    assert len(turns) == 1
    assert isinstance(turns[0], TransportFailure)
    assert "reassemble" in turns[0].reason


def test_a_tool_call_with_no_arguments_is_an_empty_object() -> None:
    turns = feed_all(
        StreamAssembler(),
        [
            {
                "type": "TOOL_CALL_START",
                "toolCallId": "c1",
                "toolCallName": "mcp_tau_now_0000000000",
            },
            {"type": "TOOL_CALL_END", "toolCallId": "c1"},
        ],
    )
    assert turns[0].tool_calls[0].arguments == {}


def test_reasoning_results_and_heartbeats_are_not_turns() -> None:
    """τ has nowhere to put reasoning, and the tool result is our own post echoed back."""
    assembler = StreamAssembler()
    turns = feed_all(
        assembler,
        [
            {"type": "CUSTOM", "name": "run_lifecycle", "value": {"phase": "starting"}},
            {"type": "RUN_STARTED", "runId": RUN, "threadId": TASK},
            {"type": "REASONING_START", "messageId": f"{RUN}:reasoning:0"},
            {
                "type": "REASONING_MESSAGE_START",
                "messageId": f"{RUN}:reasoning:0",
                "role": "reasoning",
            },
            {
                "type": "REASONING_MESSAGE_CONTENT",
                "messageId": f"{RUN}:reasoning:0",
                "delta": "Let me search.",
            },
            {"type": "REASONING_MESSAGE_END", "messageId": f"{RUN}:reasoning:0"},
            {"type": "REASONING_END", "messageId": f"{RUN}:reasoning:0"},
            {"runId": RUN},  # untyped heartbeat
            {
                "type": "TOOL_CALL_RESULT",
                "toolCallId": "c1",
                "messageId": f"{RUN}:result:0",
                "role": "tool",
                "content": '{"content":[{"type":"text","text":"..."}]}',
            },
        ],
    )
    assert turns == []
    assert not assembler.finished


def test_run_finished_and_run_error_are_distinguished() -> None:
    done = StreamAssembler()
    assert feed_all(done, [{"type": "RUN_FINISHED", "runId": RUN, "threadId": TASK}]) == []
    assert done.finished is True

    broken = StreamAssembler()
    turns = feed_all(
        broken, [{"type": "RUN_ERROR", "message": "Task sandbox is not ready (status=failed)"}]
    )
    assert isinstance(turns[0], TransportFailure)
    assert "sandbox is not ready" in turns[0].reason
    assert broken.finished is False


def test_an_empty_text_message_yields_no_turn() -> None:
    """Otherwise τ records a contentless assistant message and gives the user the floor."""
    turns = feed_all(
        StreamAssembler(),
        [
            {"type": "TEXT_MESSAGE_START", "messageId": f"{RUN}:text:0", "role": "assistant"},
            {"type": "TEXT_MESSAGE_END", "messageId": f"{RUN}:text:0"},
            {"type": "RUN_FINISHED", "runId": RUN, "threadId": TASK},
        ],
    )
    assert turns == []


def test_narration_reassembles_with_its_tool_call() -> None:
    """The message τ receives is the message Pi produced — one turn, text AND call.

    Pi emits a single assistant message carrying narration and a tool call; AG-UI streams
    them as separate event groups. Forwarding that split let τ take the narration alone and
    hand the floor to its user simulator while the sandbox sat parked on the bridge — the
    A.0b gate measured 3/12 platform episodes burning their whole 600s budget that way
    (gates/a0b.json, 2026-08-13). The call must still surface the moment TOOL_CALL_END
    arrives, not at RUN_FINISHED: the sandbox's MCP daemon abandons a parked call in ~15s.
    """
    turns = feed_all(
        StreamAssembler(),
        [
            {"type": "TEXT_MESSAGE_START", "messageId": f"{RUN}:text:0", "role": "assistant"},
            {"type": "TEXT_MESSAGE_CONTENT", "messageId": f"{RUN}:text:0", "delta": "Let me look."},
            {"type": "TEXT_MESSAGE_END", "messageId": f"{RUN}:text:0"},
            {
                "type": "TOOL_CALL_START",
                "toolCallId": "c1",
                "toolCallName": "mcp_tau_KB_search_77c5623a9f",
            },
            {"type": "TOOL_CALL_ARGS", "toolCallId": "c1", "delta": '{"query": "fees"}'},
            {"type": "TOOL_CALL_END", "toolCallId": "c1"},
        ],
    )
    assert len(turns) == 1
    assert turns[0].text == "Let me look."
    assert [c.pi_name for c in turns[0].tool_calls] == ["mcp_tau_KB_search_77c5623a9f"]


def test_narration_after_a_result_attaches_forward_or_flushes() -> None:
    """Text landing after the first call buffers for the run's next call, else flushes at end."""
    assembler = StreamAssembler()
    first = feed_all(
        assembler,
        [
            {"type": "TEXT_MESSAGE_START", "messageId": f"{RUN}:text:0", "role": "assistant"},
            {"type": "TEXT_MESSAGE_CONTENT", "messageId": f"{RUN}:text:0", "delta": "Checking."},
            {"type": "TEXT_MESSAGE_END", "messageId": f"{RUN}:text:0"},
            {
                "type": "TOOL_CALL_START",
                "toolCallId": "c1",
                "toolCallName": "mcp_tau_KB_search_77c5623a9f",
            },
            {"type": "TOOL_CALL_ARGS", "toolCallId": "c1", "delta": "{}"},
            {"type": "TOOL_CALL_END", "toolCallId": "c1"},
        ],
    )
    assert len(first) == 1 and first[0].text == "Checking."
    rest = feed_all(
        assembler,
        [
            {"type": "TEXT_MESSAGE_START", "messageId": f"{RUN}:text:1", "role": "assistant"},
            {"type": "TEXT_MESSAGE_CONTENT", "messageId": f"{RUN}:text:1", "delta": "Found it."},
            {"type": "TEXT_MESSAGE_END", "messageId": f"{RUN}:text:1"},
            {"type": "RUN_FINISHED", "runId": RUN, "threadId": TASK},
        ],
    )
    assert rest == [AssistantTurn(text="Found it.", tool_calls=())]


def test_interleaved_tool_calls_do_not_cross_contaminate() -> None:
    """Two calls in flight must keep their own argument buffers, keyed by toolCallId."""
    turns = feed_all(
        StreamAssembler(),
        [
            {
                "type": "TOOL_CALL_START",
                "toolCallId": "a",
                "toolCallName": "mcp_tau_one_0000000000",
            },
            {
                "type": "TOOL_CALL_START",
                "toolCallId": "b",
                "toolCallName": "mcp_tau_two_0000000000",
            },
            {"type": "TOOL_CALL_ARGS", "toolCallId": "a", "delta": '{"x": 1}'},
            {"type": "TOOL_CALL_ARGS", "toolCallId": "b", "delta": '{"y": 2}'},
            {"type": "TOOL_CALL_END", "toolCallId": "b"},
            {"type": "TOOL_CALL_END", "toolCallId": "a"},
        ],
    )
    assert [t.tool_calls[0].arguments for t in turns] == [{"y": 2}, {"x": 1}]


def test_the_settle_gate_opens_only_when_the_run_finishes() -> None:
    """τ must not be allowed to prompt a task whose run is still streaming.

    τ hands the floor to its user simulator as soon as it holds an assistant message, which on
    this lane can happen several messages before the run ends. Prompting then is refused with
    `409 Task is already processing`, τ calls that an infrastructure error, and the whole episode
    is retried — observed as "stuck in turn 2" until the gate existed.
    """
    transport = PlatformTransport(runtime_id="rt", repo_root=".")
    # Open before the first turn: there is no run to wait for.
    assert transport._settled.is_set()

    transport._settled.clear()
    assert not transport._settled.is_set()

    # A completed text message alone must NOT reopen it — that is the mistake being guarded.
    assembler = StreamAssembler()
    feed_all(
        assembler,
        [
            {"type": "TEXT_MESSAGE_START", "messageId": f"{RUN}:text:0", "role": "assistant"},
            {"type": "TEXT_MESSAGE_CONTENT", "messageId": f"{RUN}:text:0", "delta": "done"},
            {"type": "TEXT_MESSAGE_END", "messageId": f"{RUN}:text:0"},
        ],
    )
    assert not assembler.finished

    feed_all(assembler, [{"type": "RUN_FINISHED", "runId": RUN, "threadId": TASK}])
    assert assembler.finished


def _session(drop_run_id: str | None = None, reattaches_left: int = 1) -> _StreamSession:
    return _StreamSession(
        proc=None,
        assembler=StreamAssembler(),
        drop_run_id=drop_run_id,
        reattaches_left=reattaches_left,
    )


def _make_current(transport: PlatformTransport, session: _StreamSession) -> None:
    with transport._session_lock:
        transport._session = session


def test_a_stale_run_replay_is_dropped_whole() -> None:
    """An overlapped attach can resolve `current` to the previous, already-consumed run.

    Its replay must produce no turns and — critically — its RUN_FINISHED must not reopen the
    settle gate: the *new* run is still streaming, and an early prompt is refused with 409.
    """
    transport = PlatformTransport(runtime_id="rt", repo_root=".")
    transport._settled.clear()
    session = _session(drop_run_id=RUN)
    _make_current(transport, session)
    for event in [
        {"type": "TEXT_MESSAGE_START", "messageId": "m", "role": "assistant"},
        {"type": "TEXT_MESSAGE_CONTENT", "messageId": "m", "delta": "stale"},
        {"type": "TEXT_MESSAGE_END", "messageId": "m"},
        {"type": "RUN_FINISHED", "runId": RUN, "threadId": TASK},
    ]:
        transport._ingest_line(session, json.dumps(envelope(event)))
    assert session.emitted == 0
    assert session.dropped == 4
    assert transport._turns.empty()
    assert not transport._settled.is_set()


def test_events_from_the_new_run_pass_the_stale_filter() -> None:
    transport = PlatformTransport(runtime_id="rt", repo_root=".")
    transport._settled.clear()
    session = _session(drop_run_id="run-previous")
    _make_current(transport, session)
    for event in [
        {"type": "TEXT_MESSAGE_START", "messageId": "m", "role": "assistant"},
        {"type": "TEXT_MESSAGE_CONTENT", "messageId": "m", "delta": "fresh"},
        {"type": "TEXT_MESSAGE_END", "messageId": "m"},
        {"type": "RUN_FINISHED", "runId": RUN, "threadId": TASK},
    ]:
        transport._ingest_line(session, json.dumps(envelope(event)))
    assert session.emitted == 1
    assert transport._turns.get_nowait() == AssistantTurn(text="fresh", tool_calls=())
    assert transport._settled.is_set()


def test_a_superseded_stream_cannot_touch_the_gate_or_the_queue() -> None:
    """Lines drained from a replaced stream must be invisible.

    Without this, a buffered heartbeat arriving after the old run's RUN_FINISHED re-opens the
    settle gate while the next run is already streaming — the 409-then-retry failure again.
    """
    transport = PlatformTransport(runtime_id="rt", repo_root=".")
    transport._settled.clear()
    session = _session()  # never installed as transport._session: already superseded
    for event in [
        {"type": "TEXT_MESSAGE_START", "messageId": "m", "role": "assistant"},
        {"type": "TEXT_MESSAGE_CONTENT", "messageId": "m", "delta": "late"},
        {"type": "TEXT_MESSAGE_END", "messageId": "m"},
        {"type": "RUN_FINISHED", "runId": RUN, "threadId": TASK},
    ]:
        transport._ingest_line(session, json.dumps(envelope(event)))
    transport._on_stream_end(session)
    assert transport._turns.empty()
    assert not transport._settled.is_set()


def test_a_streamless_exit_reattaches_once_by_explicit_run_id(monkeypatch) -> None:
    """A lost attach race is recovered under the run id `tasks prompt` returned."""
    transport = PlatformTransport(runtime_id="rt", repo_root=".")
    transport._settled.clear()
    transport._set_run_id("run-new")
    session = _session(drop_run_id="run-previous", reattaches_left=1)
    _make_current(transport, session)
    respawns: list[dict] = []
    monkeypatch.setattr(transport, "_spawn_stream", lambda **kwargs: respawns.append(kwargs))
    transport._on_stream_end(session)
    assert respawns == [{"run_ref": "run-new", "drop_run_id": None, "reattaches_left": 0}]
    assert transport._turns.empty()
    assert not transport._settled.is_set()


def test_a_dead_stream_that_already_emitted_fails_loudly_instead_of_reattaching() -> None:
    """Replaying from event 0 after emitting turns would double-feed the episode."""
    transport = PlatformTransport(runtime_id="rt", repo_root=".")
    transport._settled.clear()
    transport._set_run_id("run-new")
    session = _session(reattaches_left=1)
    session.emitted = 1
    _make_current(transport, session)
    transport._on_stream_end(session)
    failure = transport._turns.get_nowait()
    assert isinstance(failure, TransportFailure)
    assert "without RUN_FINISHED" in failure.reason
    assert transport._settled.is_set()


def test_close_retitles_and_archives_the_task_never_deletes(monkeypatch) -> None:
    """The dashboard shows the task's title as the conversation's summary line.

    Deleting the task keeps the conversation export intact but demotes the row to a bare
    conversation id in the UI — observed on real episodes. Close must retitle and archive,
    and it must be idempotent: a second close repeats nothing. The platform's auto-title is
    read first and preserved after ` - `, so the interim label loses nothing.
    """
    label = "[exp_001:bm25-sonnet46] τ²-bench banking_knowledge task_001"
    transport = PlatformTransport(runtime_id="rt", repo_root=".", episode_label=label)
    transport._task_id = "task-1"
    calls: list[list[str]] = []

    def cli(args, timeout):
        calls.append(args)
        return {"title": "Wanted to change the email address"} if args[1] == "get" else {}

    monkeypatch.setattr(transport, "_cli", cli)
    transport.close()
    transport.close()
    assert calls == [
        ["tasks", "get", "task-1"],
        ["tasks", "update", "task-1", "--title", f"{label} - Wanted to change the email address"],
        ["tasks", "archive", "task-1", "-y"],
    ]
    assert transport.original_title == "Wanted to change the email address"


def test_close_without_a_platform_title_labels_bare(monkeypatch) -> None:
    # A task whose title is empty (or already one of the harness's own labels) contributes
    # no ` - ` suffix; the interim label stands alone rather than trailing a dash.
    label = "[exp_001:bm25-sonnet46] τ²-bench banking_knowledge"
    transport = PlatformTransport(runtime_id="rt", repo_root=".", episode_label=label)
    transport._task_id = "task-1"
    calls: list[list[str]] = []
    monkeypatch.setattr(transport, "_cli", lambda args, timeout: calls.append(args) or {})
    transport.close()
    assert calls == [
        ["tasks", "get", "task-1"],
        ["tasks", "update", "task-1", "--title", label],
        ["tasks", "archive", "task-1", "-y"],
    ]
    assert transport.original_title == ""


def test_close_without_a_label_still_archives(monkeypatch) -> None:
    transport = PlatformTransport(runtime_id="rt", repo_root=".")
    transport._task_id = "task-1"
    calls: list[list[str]] = []
    monkeypatch.setattr(transport, "_cli", lambda args, timeout: calls.append(args) or {})
    transport.close()
    assert calls == [
        ["tasks", "get", "task-1"],
        ["tasks", "archive", "task-1", "-y"],
    ]


def test_original_title_is_recovered_from_under_harness_labels() -> None:
    # The three label shapes the runner writes all start with the experiment tag (legacy
    # rows with `τ²-bench`) and keep the platform's own title after ` - `; anything else is
    # the platform's title itself.
    assert original_title_of("Wanted to change the email address") == (
        "Wanted to change the email address"
    )
    assert (
        original_title_of(
            "[exp_001:bm25-sonnet46] τ²-bench banking task_004 trial 3 gen_000 - Wanted to change"
        )
        == "Wanted to change"
    )
    assert original_title_of("[exp_001:bm25-sonnet46] τ²-bench banking_knowledge") == ""
    assert original_title_of("τ²-bench banking task_004 trial0 gen000 [exp:bm25-sonnet46]") == ""
    assert original_title_of("") == ""


def test_close_releases_the_attachment_slot_exactly_once(monkeypatch) -> None:
    """The slot goes back to the pool on close and only once — a double release that
    re-queued it would hand one attachment to two episodes at the same time."""
    releases: list[int] = []
    transport = PlatformTransport(
        runtime_id="rt", repo_root=".", release=lambda: releases.append(1)
    )
    transport._task_id = "task-1"
    monkeypatch.setattr(transport, "_cli", lambda args, timeout: {})
    transport.close()
    transport.close()
    assert releases == [1]


def test_close_releases_the_slot_even_when_the_platform_cli_fails(monkeypatch) -> None:
    """Retitle/archive failures are logged and non-fatal; a leaked lease would starve the
    pool, so the release must not depend on the CLI cooperating."""

    def failing_cli(args, timeout):
        raise RuntimeError("platform unreachable")

    releases: list[int] = []
    transport = PlatformTransport(
        runtime_id="rt", repo_root=".", release=lambda: releases.append(1)
    )
    transport._task_id = "task-1"
    monkeypatch.setattr(transport, "_cli", failing_cli)
    transport.close()
    assert releases == [1]
