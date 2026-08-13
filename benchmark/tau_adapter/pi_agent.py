"""The seam: an Introspection Recipe presented to τ as a `HalfDuplexAgent`.

The adapter's one rule is that it is a pipe, not a participant. It translates message shapes
and tool names, and it does nothing else — no repair, no retry, no reformatting of what the
agent produced. Every place an adapter helps the agent is a place the harness stops being
measurable, and an unmeasurable harness cannot be improved. τ keeps tool execution, step
counting, trajectory construction, termination, and grading.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from loguru import logger
from tau2.agent.base_agent import HalfDuplexAgent
from tau2.data_model.message import (
    AssistantMessage,
    Message,
    MultiToolMessage,
    ToolCall,
    ToolMessage,
    UserMessage,
)

from tau_adapter.policy_region import assert_matches_environment
from tau_adapter.tool_bridge import ToolBridge
from tau_adapter.transport import AgentTransport, AssistantTurn, TransportFailure

# A turn covers one model call plus Pi's own overhead. Generous on purpose: this is plumbing,
# and τ's --max-steps-seconds is what bounds the episode.
TURN_TIMEOUT_SECONDS = 300.0


class TransportError(RuntimeError):
    """The host failed to produce a turn.

    Raised rather than converted into a bad assistant message. An infrastructure failure is
    not agent behaviour, and grading it as though it were would quietly attribute flakiness
    to the harness under test.
    """


@dataclass
class PiAgentState:
    # tau tool-call id -> (tau tool name, arguments), so a returning ToolMessage can be routed
    # to the handler still parked on that exact invocation. The tau name is what the bridge
    # keys on, because that is the name the MCP request carried.
    pending: dict[str, tuple[str, dict]] = field(default_factory=dict)
    assistant_turns: int = 0


class PiRecipeAgent(HalfDuplexAgent[PiAgentState]):
    """Runs one τ episode against one hosted Recipe session."""

    def __init__(
        self,
        tools: list[Any],
        domain_policy: str,
        *,
        bridge: ToolBridge,
        transport: AgentTransport,
        recipe_policy: str,
        domain: str,
        base_env: dict[str, str],
    ) -> None:
        super().__init__(tools=tools, domain_policy=domain_policy)
        self._bridge = bridge
        self._transport = transport
        self._recipe_policy = recipe_policy
        self._domain = domain
        self._base_env = base_env
        self._started = False

    # ------------------------------------------------------------------ lifecycle

    def get_init_state(self, message_history: list[Message] | None = None) -> PiAgentState:
        # Before anything else: the policy the agent will actually read must be the policy τ
        # will grade it against. Checked here because it is the only point that sees both.
        assert_matches_environment(self._recipe_policy, self.domain_policy, self._domain)

        if not self._started:
            # The bridge is started by the runner and shared by every episode: the development
            # lane's `introspection dev` attachment is handed one URL before the first episode
            # and holds it for the whole run, so a per-episode bridge could not be reached.
            # Safe at max_concurrency 1, where only one episode is ever in flight.
            # What must NOT be shared is rendezvous state — see reset_for_episode.
            self._bridge.reset_for_episode()
            env = dict(self._base_env)
            env.update(self._bridge.env())
            self._transport.start(env)
            self._transport_request_session_ref()
            self._started = True
            logger.info(
                f"seam ready: {len(self._bridge.tau_tool_names)} τ tools bridged at "
                f"{self._bridge.url}"
            )

        # τ seeds the trajectory with a canned agent greeting and passes it here as history.
        # It is recorded by τ but not replayed into the agent session, which starts empty —
        # a divergence from stock, whose message list contains it.
        return PiAgentState()

    def stop(
        self,
        message: Message | None = None,
        state: PiAgentState | None = None,
    ) -> None:
        # Only the transport: the bridge outlives this episode and is stopped by the runner.
        self._transport.close()

    # -------------------------------------------------------------------- stepping

    def generate_next_message(
        self, message: Any, state: PiAgentState
    ) -> tuple[AssistantMessage, PiAgentState]:
        if isinstance(message, UserMessage):
            self._transport.send_user_text(message.content or "")
        elif isinstance(message, MultiToolMessage):
            for tool_message in message.tool_messages:
                self._deliver_tool_result(tool_message, state)
        elif isinstance(message, ToolMessage):
            self._deliver_tool_result(message, state)
        elif message is None:
            raise TransportError(
                "solo mode is not supported: this agent has no way to open a conversation"
            )
        else:
            raise TransportError(f"unexpected input message type {type(message).__name__}")

        item = self._transport.next_turn(TURN_TIMEOUT_SECONDS)
        if isinstance(item, TransportFailure):
            raise TransportError(item.reason)

        state.assistant_turns += 1
        return self._to_tau_message(item, state), state

    # ------------------------------------------------------------------- internals

    def _deliver_tool_result(self, tool_message: ToolMessage, state: PiAgentState) -> None:
        invocation = state.pending.pop(tool_message.id, None)
        if invocation is None:
            # τ returned a result for a call we never registered. Log rather than guess:
            # posting it under the wrong key would unblock the wrong handler.
            logger.warning(f"tool result {tool_message.id!r} has no pending invocation; dropping")
            return
        tau_name, arguments = invocation
        self._bridge.post_result(
            tool_name=tau_name,
            arguments=arguments,
            content=tool_message.content or "",
            is_error=bool(tool_message.error),
        )

    def _to_tau_message(self, turn: AssistantTurn, state: PiAgentState) -> AssistantMessage:
        tau_calls: list[ToolCall] = []
        for call in turn.tool_calls:
            # An unmapped name means the agent called something outside τ's tool set. Passed
            # through as-is so τ reports it as the invalid call it is.
            tau_name = self._bridge.name_map.get(call.pi_name, call.pi_name)
            tau_calls.append(
                ToolCall(
                    id=call.id,
                    name=tau_name,
                    arguments=call.arguments,
                    requestor="assistant",
                )
            )
            state.pending[call.id] = (tau_name, call.arguments)

        return AssistantMessage(
            role="assistant",
            content=turn.text,
            tool_calls=tau_calls or None,
            cost=turn.cost,
            usage=turn.usage,
            # Additive only: τ ignores raw_data when grading, and it is what lets a
            # conclusion drawn later point back at the session that produced it.
            raw_data={
                "pi_model": turn.model,
                "pi_session_ref": self._transport.session_ref,
                "pi_tool_names": [c.pi_name for c in turn.tool_calls],
            },
        )

    def _transport_request_session_ref(self) -> None:
        requester = getattr(self._transport, "request_session_ref", None)
        if callable(requester):
            requester()
