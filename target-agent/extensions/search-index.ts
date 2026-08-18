/* An episode-scoped index of what the knowledge base has already returned.
 *
 * WHY. Measured across six rounds, KB_search calls per episode rose 9.4 (batch_05) -> 12.3
 * (batch_06) while mean messages rose 43.6 -> 48.7 and round cost $1.00 -> $1.26; gen-005's
 * instruction to search again per candidate confirmed its own retrieval counter and fired
 * its cost falsifier doing it. Separately, halving the compare_options calls at gen-004
 * changed episode length not at all, which ruled the tool out as the driver. What is left
 * is retrieval volume, and a re-search the agent makes because it cannot see what it
 * already holds.
 *
 * WHAT IT DOES. After every KB_search return, append a compact list of the document ids
 * this episode has already received, newest search last. Nothing is removed, rewritten or
 * hidden — the model reads exactly what tau returned, plus one line telling it what it
 * already has.
 *
 * WHAT IT DOES NOT KNOW. Nothing about banking or this benchmark: no corpus, no document
 * contents, no answers, no task-specific strings. It observes ids as they pass and echoes
 * them back. It cannot name a document the episode has not already seen, which is exactly
 * the line between helping the agent track its own retrieval and handing it the answer.
 *
 * REACH: none. No filesystem, no network, no subprocess. State is a per-session Map, and it
 * is dropped with the session.
 */
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

/* HOST FACTS this code keys on, each measured on this seam and cited in the improvement
 * record (benchmark/probes/2026-08-16-surface-probes/ and seq 8's tool_result probe):
 *  - `tool_result` fires on every tau tool return, 56 firings over three banking episodes
 *    across every tau tool;
 *  - the tool NAME arrives mangled as `mcp_tau_<tau name>_<10-hex>`, so a handler must
 *    match on a SUBSTRING and never on equality (recipe-growth trap: name shape);
 *  - `event.content` is an ARRAY of `{type: "text"}` blocks, and a returned `content` patch
 *    reached the model in 24/24 firings while appearing 0 times in tau's graded trajectory.
 * No message ROLE literal appears in this file, so check_extension_facts.py's role lint has
 * nothing to bind — the roles vocabulary is not a fact this hook depends on.
 */
const KB_TOOL = "KB_search";
const DOC_ID = /\bID:\s*(doc_[A-Za-z0-9_()]+)/g;
const MAX_SHOWN = 40;

export default function searchIndex(pi: ExtensionAPI): void {
  const seen: string[] = [];

  pi.on("tool_result", (event: any) => {
    const name = String(event?.toolName ?? event?.name ?? "");
    if (!name.includes(KB_TOOL)) return undefined;

    const blocks = Array.isArray(event?.content) ? event.content : [];
    const text = blocks
      .filter((b: any) => b && b.type === "text" && typeof b.text === "string")
      .map((b: any) => b.text)
      .join("\n");
    if (!text) return undefined;

    let match: RegExpExecArray | null;
    DOC_ID.lastIndex = 0;
    while ((match = DOC_ID.exec(text)) !== null) {
      if (!seen.includes(match[1])) seen.push(match[1]);
    }
    if (seen.length === 0) return undefined;

    const shown = seen.slice(-MAX_SHOWN);
    const omitted = seen.length - shown.length;
    const note =
      `\n\n[Already retrieved this conversation — ${seen.length} document(s)` +
      (omitted > 0 ? `, showing the ${MAX_SHOWN} most recent` : "") +
      `]\n${shown.join("\n")}`;

    return {
      content: [...blocks, { type: "text", text: note }],
    };
  });
}
