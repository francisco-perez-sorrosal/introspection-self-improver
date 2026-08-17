/* Report which knowledge-base-named tools have not been unlocked yet.
 *
 * Mechanism (one, and only one): a `context` hook lists, as a factual state line, the
 * discoverable-tool names that appeared in knowledge-base results in this conversation and
 * have not been unlocked or handed over. It states an unmet procedural state; it gives no
 * instruction, names no task, and forbids nothing.
 *
 * Why this is not a repeat of the reverted C1. C1 appended the tool names a single KB_search
 * result contained — a bare list, with no reference to what had or had not been done — and its
 * counter did not move: task_026 0/3 -> 0/3, task_096 2/3 -> 2/3. D2 then took the same
 * surface family and framed the injection as an UNMET PROCEDURAL CONDITION ("the customer has
 * asked and no lookup has been issued"), and its counter moved 0/3 -> 3/3 on the task where it
 * could fire, carrying task_014 to 3/3 with the gold reason code. The measured difference
 * between the two is the framing, not the surface: a list of facts changed nothing, a
 * statement of what remains undone changed behaviour. This change applies D2's framing to
 * C1's target.
 *
 * Evidence for the target. task_026 has failed 12/12 episodes across four harnesses with one
 * binding constraint: gold requires correcting the rewards ledger through
 * update_transaction_rewards_3847, that exact name is returned by KB_search, and the agent has
 * never once unlocked it — including under C1, which put the name in front of it.
 *
 * Scope discipline:
 *   - names are harvested from KB_search RESULTS only, never invented, and matched by the
 *     domain's discoverable-tool naming convention (lowercase snake_case, four-digit suffix;
 *     `doc_` excluded because knowledge-base document ids share the shape);
 *   - a name is dropped from the list as soon as it is unlocked or handed to the user, so the
 *     line reports remaining work rather than restating history;
 *   - silent when nothing remains, so it cannot become ambient noise;
 *   - capped, so a pathological result cannot grow the context without bound;
 *   - no task, gold value, document id or answer is encoded; pure string work on messages
 *     already in the episode; try/catch fails closed to unmodified behaviour.
 *
 * Seam facts designed against (measured, generation_001/context_probe/): `context` fires
 * before every LLM call, `event.messages` is the growing conversation with `content` an ARRAY
 * of blocks, injections do not accumulate across calls, and an appended message reaches the
 * model while never appearing in tau's graded trajectory.
 */
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

const TOOL_NAME = /\b(?!doc_)[a-z][a-z0-9]*(?:_[a-z0-9]+)*_\d{4}\b/g;
const MAX_NAMES = 8;
const CLAIMED = new Set(["unlock_discoverable_agent_tool", "give_discoverable_user_tool"]);

function blocks(message: any): any[] {
  const content = message?.content;
  return Array.isArray(content) ? content : [];
}

export default function unlockedState(pi: ExtensionAPI): void {
  pi.on("context", (event: any) => {
    try {
      const messages = event?.messages;
      if (!Array.isArray(messages)) return undefined;

      const seen: string[] = [];
      const claimed = new Set<string>();

      for (const message of messages) {
        for (const block of blocks(message)) {
          // Names the knowledge base returned.
          if (message?.role === "tool" && typeof block?.text === "string") {
            for (const match of block.text.matchAll(TOOL_NAME)) {
              if (!seen.includes(match[0])) seen.push(match[0]);
            }
          }
          // Names already unlocked or handed over.
          const args = block?.input ?? block?.arguments;
          if (args && typeof args === "object") {
            const name = (args as any).agent_tool_name ?? (args as any).discoverable_tool_name;
            if (typeof name === "string") claimed.add(name);
            if (typeof (args as any).name === "string" && CLAIMED.has((args as any).name)) {
              claimed.add(String((args as any).name));
            }
          }
        }
      }

      const outstanding = seen.filter((name) => !claimed.has(name)).slice(0, MAX_NAMES);
      if (outstanding.length === 0) return undefined;

      const lastUser = [...messages].reverse().find((m: any) => m?.role === "user");
      if (!lastUser) return undefined;

      const text = `Tools named in knowledge-base results and not yet unlocked or handed over in this conversation: ${outstanding.join(", ")}.`;
      const injected: any = Array.isArray(lastUser.content)
        ? { ...lastUser, content: [{ type: "text", text }] }
        : { ...lastUser, content: text };
      delete injected.id;
      delete injected.timestamp;

      return { messages: [...messages, injected] };
    } catch {
      return undefined;
    }
  });
}
