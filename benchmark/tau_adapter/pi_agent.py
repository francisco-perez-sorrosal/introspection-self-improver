"""The seam: an Introspection Recipe presented to τ as a `HalfDuplexAgent`.

The adapter's one rule is that it is a pipe, not a participant. It translates message shapes
and tool names, and it does nothing else — no repair, no retry, no reformatting of what the
agent produced. Every place an adapter helps the agent is a place the harness stops being
measurable, and an unmeasurable harness cannot be improved. τ keeps tool execution, step
counting, trajectory construction, termination, and grading.

The one DECLARED exception (2026-08-16 seam re-decision, plan D24): tool calls the recipe
registers as Pi-local (`tau_adapter.pi_local`) are executed by Pi and never forwarded to τ —
τ's step and error budgets meter benchmark-environment interactions, not harness-internal
cognition. Suppression is deterministic (registry membership, no heuristics), bounded
(`MAX_SUPPRESSED_TURNS_PER_STEP`, after which forwarding resumes unfiltered so a runaway
harness pays its own cost), and fully evidenced: every consumed turn's tool names land in
`raw_data.pi_tool_names`, the suppressed subset in `raw_data.pi_suppressed_tool_names`, and
the manifest derives a per-episode `pi_local_calls` count. Nothing is hidden from diagnosis
— only from grading, which is the declared point.
"""

from __future__ import annotations

from collections.abc import Callable
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
from tau_adapter.tool_bridge import EpisodeChannel
from tau_adapter.transport import AgentTransport, AssistantTurn, TransportFailure

#: Opens this episode's rendezvous channel; the keyword argument is the stall sink.
#: Both lanes open a fresh channel per episode (`ToolBridge.open_channel`); they differ
#: only in how requests find it — the channel's URL locally, the sandbox-session binding
#: (adopted and bound by the platform transport) through the development tunnel.
ChannelOpener = Callable[..., EpisodeChannel]

# A turn covers one model call plus Pi's own overhead. Generous on purpose: this is plumbing,
# and τ's --max-steps-seconds is what bounds the episode.
TURN_TIMEOUT_SECONDS = 300.0

# Runaway guard for Pi-local suppression: after this many consecutive fully-suppressed turns
# inside ONE τ step, suppression stops and calls forward unfiltered (τ then grades the
# invalid calls). Chosen over raising: a TransportError would be booked as infrastructure
# and retried, hiding a harness defect; forwarding keeps the cost on the harness that
# caused it. τ's episode timeout bounds the wall-clock either way.
MAX_SUPPRESSED_TURNS_PER_STEP = 32


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
        open_channel: ChannelOpener,
        transport: AgentTransport,
        recipe_policy: str,
        domain: str,
        base_env: dict[str, str],
        pi_local_tools: frozenset[str] = frozenset(),
    ) -> None:
        super().__init__(tools=tools, domain_policy=domain_policy)
        self._open_channel = open_channel
        self._channel: EpisodeChannel | None = None
        self._transport = transport
        self._recipe_policy = recipe_policy
        self._domain = domain
        self._base_env = base_env
        self._pi_local_tools = pi_local_tools
        self._started = False

    # ------------------------------------------------------------------ lifecycle

    def get_init_state(self, message_history: list[Message] | None = None) -> PiAgentState:
        # Before anything else: the policy the agent will actually read must be the policy τ
        # will grade it against. Checked here because it is the only point that sees both.
        assert_matches_environment(self._recipe_policy, self.domain_policy, self._domain)

        if not self._started:
            # The bridge is started by the runner and shared by every episode; what is NOT
            # shared is rendezvous state. Each episode opens its own channel — its own
            # mailbox at its own URL — which is what keeps τ's concurrent workers, and a τ
            # retry of this same task, from ever exchanging results (see EpisodeChannel).
            # The transport's incident sink (when it keeps one) receives this episode's
            # stall warnings, so a stalled rendezvous reaches the episode manifest.
            sink = getattr(self._transport, "incidents", None)
            self._channel = self._open_channel(
                on_stall=sink.count_stall if sink is not None else None
            )
            # A transport that routes through the development tunnel binds the channel to
            # its sandbox session once known; the local transport has no such hook — its
            # episode is routed by the channel URL in its environment.
            adopt = getattr(self._transport, "adopt_channel", None)
            if callable(adopt):
                adopt(self._channel)
            env = dict(self._base_env)
            env.update(self._channel.env())
            self._transport.start(env)
            self._transport_request_session_ref()
            self._started = True
            logger.info(
                f"seam ready: {len(self._channel.tau_tool_names)} τ tools bridged at "
                f"{self._channel.url}"
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
        # Reverse acquisition order: the transport (started after the channel opened) closes
        # first, then the channel retires. The bridge itself outlives the episode and is
        # stopped by the runner. τ calls stop from its orchestrator's finally block, so a
        # failed attempt's channel is retired before the retry opens its own.
        self._transport.close()
        if self._channel is not None:
            self._channel.close()

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

        # Pi-local suppression is a TURN-LEVEL pump, never a message filter: the platform
        # assembler emits one AssistantTurn per tool call, so filtering a lone Pi-local
        # call out of its message would hand τ an empty assistant message — exactly the
        # A.0b deadlock the narration reassembler exists to prevent. A fully-suppressed
        # turn instead holds its narration and pumps the transport again; Pi has already
        # executed the local call and will produce a further turn on its own.
        held_text: list[str] = []
        consumed_pi_names: list[str] = []
        suppressed_names: list[str] = []
        cost_total: float | None = None
        usage_total: dict | None = None
        suppressed_turns = 0
        while True:
            item = self._transport.next_turn(TURN_TIMEOUT_SECONDS)
            if isinstance(item, TransportFailure):
                raise TransportError(item.reason)
            state.assistant_turns += 1
            consumed_pi_names.extend(call.pi_name for call in item.tool_calls)
            cost_total = _add_cost(cost_total, item.cost)
            usage_total = _merge_usage(usage_total, item.usage)

            suppress_active = suppressed_turns < MAX_SUPPRESSED_TURNS_PER_STEP
            local_calls = [
                call
                for call in item.tool_calls
                if suppress_active and call.pi_name in self._pi_local_tools
            ]
            forwardable = [call for call in item.tool_calls if call not in local_calls]
            suppressed_names.extend(call.pi_name for call in local_calls)

            if forwardable or not item.tool_calls:
                # A τ-visible action or a pure message: forward (any Pi-local siblings in
                # this same turn are suppressed alongside, mirroring the pump).
                break

            # Every call in this turn was Pi-local: nothing for τ. Hold the narration so
            # it reaches τ with the next forwardable turn (the reassembly rule), and pump.
            suppressed_turns += 1
            if item.text:
                held_text.append(item.text)
            if suppressed_turns == MAX_SUPPRESSED_TURNS_PER_STEP:
                logger.warning(
                    f"pi-local suppression cap hit after {suppressed_turns} turns; "
                    "forwarding resumes unfiltered so the runaway is graded, not hidden"
                )

        return (
            self._assemble_tau_message(
                item,
                state,
                forwardable=forwardable,
                held_text=held_text,
                cost=cost_total,
                usage=usage_total,
                pi_names=consumed_pi_names,
                suppressed=suppressed_names,
            ),
            state,
        )

    # ------------------------------------------------------------------- internals

    def _deliver_tool_result(self, tool_message: ToolMessage, state: PiAgentState) -> None:
        invocation = state.pending.pop(tool_message.id, None)
        if invocation is None:
            # τ returned a result for a call we never registered. Log rather than guess:
            # posting it under the wrong key would unblock the wrong handler.
            logger.warning(f"tool result {tool_message.id!r} has no pending invocation; dropping")
            return
        assert self._channel is not None  # results only flow inside a started episode
        tau_name, arguments = invocation
        self._channel.post_result(
            tool_name=tau_name,
            arguments=arguments,
            content=tool_message.content or "",
            is_error=bool(tool_message.error),
        )

    def _assemble_tau_message(
        self,
        turn: AssistantTurn,
        state: PiAgentState,
        *,
        forwardable: list[Any],
        held_text: list[str],
        cost: float | None,
        usage: dict | None,
        pi_names: list[str],
        suppressed: list[str],
    ) -> AssistantMessage:
        assert self._channel is not None  # turns only flow inside a started episode
        tau_calls: list[ToolCall] = []
        for call in forwardable:
            # An unmapped name means the agent called something outside τ's tool set (and
            # outside the Pi-local registry). Passed through as-is so τ reports it as the
            # invalid call it is.
            tau_name = self._channel.name_map.get(call.pi_name, call.pi_name)
            tau_calls.append(
                ToolCall(
                    id=call.id,
                    name=tau_name,
                    arguments=call.arguments,
                    requestor="assistant",
                )
            )
            state.pending[call.id] = (tau_name, call.arguments)

        # Narration held from fully-suppressed turns rides with the next forwardable turn,
        # the same reassembly rule the platform lane applies to narration and its own call.
        texts = [text for text in (*held_text, turn.text) if text]
        return AssistantMessage(
            role="assistant",
            content="\n\n".join(texts) if texts else None,
            tool_calls=tau_calls or None,
            cost=cost,
            usage=usage,
            # Additive only: τ ignores raw_data when grading, and it is what lets a
            # conclusion drawn later point back at the session that produced it. The
            # suppressed subset is the evidence stream for the D24 seam semantics —
            # everything Pi did that τ was not shown.
            raw_data={
                "pi_model": turn.model,
                "pi_session_ref": self._transport.session_ref,
                "pi_tool_names": pi_names,
                "pi_suppressed_tool_names": suppressed,
            },
        )

    def _transport_request_session_ref(self) -> None:
        requester = getattr(self._transport, "request_session_ref", None)
        if callable(requester):
            requester()


def _add_cost(total: float | None, cost: float | None) -> float | None:
    """Sum turn costs across a pumped step; suppressed turns' spend still counts."""
    if cost is None:
        return total
    return cost if total is None else total + cost


def _merge_usage(total: dict | None, usage: dict | None) -> dict | None:
    """Merge usage dicts across a pumped step: numeric values sum, others last-write-win."""
    if usage is None:
        return total
    if total is None:
        return dict(usage)
    merged = dict(total)
    for key, value in usage.items():
        prior = merged.get(key)
        if isinstance(prior, (int, float)) and isinstance(value, (int, float)):
            merged[key] = prior + value
        else:
            merged[key] = value
    return merged
