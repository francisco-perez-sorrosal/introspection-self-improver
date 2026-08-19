/* A deterministic scratchpad for the customer's outstanding requests.
 *
 * Target: the largest remaining mechanism in this experiment. Across batch_04, 15 failing
 * episodes across 10 tasks lost reward to a gold action that was never performed at all —
 * more than any other single mechanism — and the shape is consistently a multi-request
 * conversation where the agent completes the first request and never returns to the rest.
 * task_060 closed the account and never opened the replacement; task_063 applied for the
 * card and never logged the verification or opened the savings account.
 *
 * Why a tool and not a sentence. This experiment has now measured the same rule failing
 * through prose (C1) AND through a point-of-use structural injection with no escape clause
 * (C4), on an identical counter: 9, 9, 9, 8 episodes across four rounds. Both delivery
 * channels tell the model something it must then remember and apply. A tool instead holds
 * state the model cannot silently lose — the outstanding list is returned to it, computed,
 * every time it asks.
 *
 * FIRST USE OF extension-tool IN THIS EXPERIMENT, so the prediction is ADOPTION-FIRST
 * (contract/protocol.md step 4): it targets pi_local_calls and correct invocation, and the
 * reward-level prediction is deferred one round and stated as deferred.
 *
 * Reach, stated for the record and the review: this tool touches NOTHING. No filesystem, no
 * network, no subprocess. Its entire state is a per-session in-memory Map, and it is
 * per-episode by construction because every episode is a fresh Pi session.
 *
 * No task-specific artifact appears here: it stores whatever strings the model gives it and
 * returns them. It cannot encode an answer because it has no domain content at all.
 *
 * Suppression: the tool name is allowlisted in agents/agent.yaml `tools:`, which under the
 * D24 seam IS the Pi-local suppression registry — the call is executed by Pi and never
 * forwarded to tau (measured end to end by this experiment's own gates/suppression_canary
 * and by the g=0 sub-agent probe, where `agent` calls appeared 0 times in tau's trajectory).
 * Registering without the allowlist entry would leak the call to tau as an invalid action.
 */
import { Type } from "@earendil-works/pi-ai";
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

export default function requestTracker(pi: ExtensionAPI): void {
  const open = new Map<string, boolean>();

  pi.registerTool({
    name: "track_requests",
    description:
      "Keep track of everything the customer has asked for in this conversation, so none " +
      "is forgotten. Call it with `add` and the request text when the customer asks for " +
      "something, with `done` and the same text once you have completed it, and with " +
      "`list` at any time to get back what is still outstanding. Call `list` before you " +
      "tell the customer you are finished.",
    parameters: Type.Object({
      action: Type.String({ description: "One of: add, done, list." }),
      request: Type.String({
        description: "The request, in a few words. Required for add and done; ignored for list.",
        default: "",
      }),
    }),
    async execute(_toolCallId, params) {
      const { action, request } = params as { action: string; request?: string };
      const key = (request || "").trim();
      if (action === "add" && key) open.set(key, true);
      else if (action === "done" && key) open.set(key, false);
      const outstanding = [...open.entries()].filter(([, v]) => v).map(([k]) => k);
      const text = outstanding.length
        ? `Still outstanding (${outstanding.length}): ${outstanding.join("; ")}`
        : "Nothing outstanding.";
      return { content: [{ type: "text", text }] };
    },
  });
}
