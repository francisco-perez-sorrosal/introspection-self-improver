"""What the seam needs from whatever is hosting the agent.

Two hosts are in scope. Locally the agent is a `pi --mode rpc` subprocess; in the
development lane it is a cloud sandbox driven through `introspection tasks`. Only this
narrow contract differs between them, because the rendezvous that carries tool calls and
results runs through the MCP bridge in both cases — a tool call reaches the bridge whichever
way the agent is hosted. A transport therefore only has to deliver a user turn and surface
the assistant message that answers it.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class PiToolCall:
    """A tool call as the host emitted it, still under Pi's mangled tool name."""

    id: str
    pi_name: str
    arguments: dict


@dataclass(frozen=True)
class AssistantTurn:
    """One assistant message, exactly as the host produced it.

    Deliberately capable of carrying `text` and `tool_calls` at the same time. τ rejects
    that combination and ends the episode as AGENT_ERROR, and the adapter passes it through
    rather than repairing it: a defect the adapter silently corrects is a defect the harness
    can never be measured on, and therefore never improved. Reasoning quietly rewritten here
    would be a change to graded behaviour that leaves the evaluator untouched.

    Thinking blocks are not represented, because τ's `AssistantMessage` has no field for
    them — a stock τ agent loses them too.
    """

    text: str | None = None
    tool_calls: tuple[PiToolCall, ...] = ()
    model: str | None = None
    usage: dict | None = None
    cost: float | None = None
    generation_seconds: float | None = None


@dataclass(frozen=True)
class TransportFailure:
    """The host could not produce a turn. Distinct from an agent that behaved badly."""

    reason: str


TurnItem = AssistantTurn | TransportFailure


class AgentTransport(Protocol):
    """Half-duplex access to a hosted agent."""

    def start(self, env: Mapping[str, str]) -> None:
        """Bring the host up. `env` carries the bridge endpoint and its bearer token."""

    def send_user_text(self, text: str) -> None:
        """Deliver one user turn."""

    def next_turn(self, timeout: float) -> TurnItem:
        """Block until the host completes its next assistant message.

        Callable without a preceding `send_user_text`: after a tool result is delivered
        through the bridge, the agent continues on its own and produces a further message
        with no new user input.
        """
        ...

    def close(self) -> None:
        """Release the host. Must be safe to call twice, and safe after a failure."""

    @property
    def session_ref(self) -> str | None:
        """Host-side identifier for this episode, recorded for evidence linking."""
        ...
