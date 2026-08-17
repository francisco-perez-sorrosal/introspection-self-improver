/* Report whether the prescribed transfer-reason lookup has happened yet.
 *
 * Mechanism (one, and only one): when the customer has asked to be handed to a human and no
 * knowledge-base query about transfer reason codes has been issued in this conversation, a
 * `context` hook appends one factual line stating exactly that. It reports a procedural
 * state; it does not say whether to transfer, which reason to choose, or what to search.
 *
 * Why this shape. The transfer tool's OWN description already says the reason enum "can be
 * found in the knowledge base: search it before calling this tool to select the proper
 * applicable reason", and the `reason` parameter carries a hard enum — so the instruction
 * exists and the vocabulary is in front of the model. What is missing is that the agent does
 * not track whether it has done the lookup: across batch_01 and batch_02, only 6 of 18
 * transfer-carrying episodes issued such a query, and on task_014 every pass (2/2) issued
 * one while the trial that transferred without one chose a legal-but-wrong reason.
 *
 * Why not a sentence in SYSTEM.md. Six mutations across three prior experiments moved the
 * transfer RATE and none moved DISCRIMINATION, and one closed experiment recorded the
 * condition for a seventh attempt: a mechanism that is "procedural and counted rather than a
 * judgment about when transfer is appropriate". A counted state report is that mechanism; a
 * sentence would be the seventh attempt at the thing that failed six times.
 *
 * Scope discipline:
 *   - It fires only once the customer has asked, and only while the lookup is absent — so it
 *     is silent on every episode that has already searched, and on every episode with no
 *     transfer request at all.
 *   - It states a fact and gives no instruction, so it carries no escape clause and no
 *     licensed alternative — the seq-6 lesson applied by construction rather than by wording.
 *   - It encodes no task, no reason code, no document, and no gold value. The phrase lists
 *     below are ordinary English for "the customer asked for a human" and "a query about
 *     transfer reason codes"; the same file runs unchanged on any episode.
 *   - No filesystem, network or subprocess reach; pure string work on messages already in
 *     the episode; try/catch fails closed to unmodified behaviour.
 *
 * Seam facts this is designed against (measured, generation_001/context_probe/): `context`
 * fires before every LLM call; `event.messages` is the growing conversation as
 * {role, content, timestamp} with `content` an ARRAY of blocks; injections do NOT accumulate
 * across calls, so the hook must re-decide every time; an appended message reaches the model
 * (3/3 episodes) while the injection itself is absent from tau's graded trajectory.
 */
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

const HANDOFF_REQUEST =
  /\b(transfer(red)?\s+(me|us)|human (agent|representative|being)|speak (to|with) (a|an|someone)|real person|talk to (a|someone))\b/i;
const REASON_LOOKUP = /\b(transfer|escalat\w+)\b[\s\S]{0,60}\b(reason|code)\b|\breason code\b/i;
const NOTE_PREFIX = "Transfer-reason lookup:";

/** Plain prose of a message — narration only, never tool-call arguments. */
function textOf(message: any): string {
  const content = message?.content;
  if (typeof content === "string") return content;
  if (!Array.isArray(content)) return "";
  return content.map((block: any) => (typeof block?.text === "string" ? block.text : "")).join(" ");
}

/** Serialized arguments of every tool call in a message. A LOOKUP is a query the agent
 *  actually issued — narration mentioning "transfer reason" is not one, and counting it
 *  would silence the hook on exactly the episodes it exists for. */
function toolCallArguments(message: any): string {
  const content = message?.content;
  if (!Array.isArray(content)) return "";
  return content
    .map((block: any) => {
      const args = block?.input ?? block?.arguments;
      return args === undefined ? "" : JSON.stringify(args);
    })
    .join(" ");
}

export default function transferReasonLookup(pi: ExtensionAPI): void {
  pi.on("context", (event: any) => {
    try {
      const messages = event?.messages;
      if (!Array.isArray(messages) || messages.length === 0) return undefined;

      let asked = false;
      let lookedUp = false;
      for (const message of messages) {
        if (message?.role === "user" && HANDOFF_REQUEST.test(textOf(message))) asked = true;
        const args = toolCallArguments(message);
        if (args && REASON_LOOKUP.test(args)) lookedUp = true;
      }
      if (!asked || lookedUp) return undefined;

      const lastUser = [...messages].reverse().find((m: any) => m?.role === "user");
      if (!lastUser) return undefined;

      const text = `${NOTE_PREFIX} the customer has asked to be handed to a human, and no knowledge-base query about transfer reason codes has been issued in this conversation.`;
      const injected: any = Array.isArray(lastUser.content)
        ? { ...lastUser, content: [{ type: "text", text }] }
        : { ...lastUser, content: text };
      delete injected.id;
      delete injected.timestamp;

      return { messages: [...messages, injected] };
    } catch {
      // Fail closed: an unmodified context is H1's behaviour, not a half-applied change.
      return undefined;
    }
  });
}
