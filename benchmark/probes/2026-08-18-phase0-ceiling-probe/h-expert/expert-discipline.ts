/* H-EXPERT ONLY — the ceiling probe's harness (plan D36, Phase 0). NEVER SHIPPED.
 *
 * This file exists on a throwaway branch that is never merged and never tagged. It is one
 * half of H-expert, the hand-built harness whose only job is to bound the range: how much
 * better could ANY harness be on this objective? It is not a candidate mutation, it carries
 * no improvement record, and nothing here is evidence about what the loop can find.
 *
 * WHAT IT DOES. Two deterministic appends, keyed on the tool a result came back from:
 *
 *   after a KB_search return   — restate the selection discipline at the moment it is used.
 *                                Instructions about how to ACT ON WHAT WAS RETRIEVED have
 *                                failed to hold four times in this project's history when
 *                                they lived only in the system prompt; the measured delivery
 *                                for that class is `tool_result` interception.
 *   after a state-changing     — a completed-state note: name what just landed and point at
 *   call returns                 the customer's remaining requests. Completed-state framing
 *                                is the shape measured safe; a missing-state claim can read
 *                                as a bar to acting and suppress the next step unasked.
 *
 * WHAT IT DOES NOT KNOW. Nothing about banking or this benchmark: no corpus, no document
 * contents, no document ids, no option names, no per-task procedure, no answers. It keys on
 * the frozen tool catalogue's own tool names — the environment's public surface — and
 * appends fixed general text. It cannot name anything the episode has not already seen.
 *
 * REACH: none. No filesystem, no network, no subprocess, no state of any kind.
 */
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

/* HOST FACTS this code keys on, each measured on this seam:
 *  - `tool_result` fires on every tau tool return (56 firings over three banking-domain
 *    episodes, every tau tool) — benchmark/probes/2026-08-16-surface-probes/;
 *  - the tool NAME arrives mangled as `mcp_tau_<tau name>_<hash>`, so a handler must match
 *    on a SUBSTRING and never on equality;
 *  - `event.content` is an ARRAY of `{type:"text"}` blocks, and a returned `content` patch
 *    reached the model in 24/24 firings while appearing 0 times in tau's graded trajectory.
 * Verified in production by seq 10's gen-006 hook (results/experiment_010_adopt-bm25-luna56,
 * commit 7103d81), whose injected line was present in every fetched session log.
 * No message ROLE literal appears in this file, so check_extension_facts.py's role lint has
 * nothing to bind.
 */
const SEARCH_TOOL = "KB_search";

/* State-changing surfaces from the frozen tool catalogue (benchmark/benchmark_lock.yaml
 * `tool_catalog`) — the environment's public tool names, not task data. */
const ACTING_TOOLS = [
  "call_discoverable_agent_tool",
  "give_discoverable_user_tool",
  "change_user_email",
  "log_verification",
];

const SEARCH_NOTE =
  "\n\n[procedure, appended by the harness — not part of the search result]\n" +
  "Every exact string you send next — an option or product name, a tool name, an " +
  "argument name, an account or transaction identifier, a reason code — is copied " +
  "verbatim from a retrieved document or a tool result, never paraphrased, never " +
  "shortened to a display fragment.\n" +
  "If this request needs you to choose among bank-defined named options: retrieve the " +
  "FULL candidate list rather than the first document naming one candidate; retrieve, " +
  "per candidate, the attribute values the customer's stated requirements refer to, " +
  "searching again for any you are missing; eliminate the candidates that fail a hard " +
  "requirement; then rank the survivors by the customer's stated preferences in the " +
  "order given.\n" +
  "The figure that decides is the one that applies to THIS customer. A phrase like " +
  "\"outside top categories\", \"base rate\", \"standard rate\", \"enhanced rate\", " +
  "\"excluding\" or \"with a premium subscription\" is evidence that a different figure " +
  "exists for some category or some customer, usually in a different document about the " +
  "same candidate. Rank on the figure that matches what the customer told you about " +
  "themselves, and never rank a candidate on an attribute you have not retrieved.";

const ACTING_NOTE =
  "\n\n[procedure, appended by the harness — not part of the tool result]\n" +
  "That step is on record. Before you reply, walk the customer's stated requests again: " +
  "they often asked for more than one thing in a single message, and a conversation that " +
  "ends with a stated request unaddressed counts as a failure even when every step taken " +
  "was correct.\n" +
  "If anything on that list closes, cancels, removes or transfers away, do it LAST: check " +
  "first whether the thing being removed is what satisfies an eligibility condition, a " +
  "minimum, a tenure or a linkage for another outstanding request. A closure cannot be " +
  "undone, and an action you are blocked from taking because of one you already took is " +
  "an ordering mistake rather than an answer.";

export default function expertDiscipline(pi: ExtensionAPI): void {
  pi.on("tool_result", (event: any) => {
    const name = String(event?.toolName ?? event?.name ?? "");
    const note = name.includes(SEARCH_TOOL)
      ? SEARCH_NOTE
      : ACTING_TOOLS.some((t) => name.includes(t))
        ? ACTING_NOTE
        : "";
    if (!note) return undefined;

    const blocks = Array.isArray(event?.content) ? event.content : [];
    if (blocks.length === 0) return undefined;

    return { content: [...blocks, { type: "text", text: note }] };
  });
}
