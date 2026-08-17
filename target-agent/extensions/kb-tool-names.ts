/* Salience for discoverable-tool names the knowledge base returned.
 *
 * Mechanism (one, and only one): a `KB_search` result is a multi-thousand-character blob,
 * and the tool names it prescribes are ordinary words inside it. This handler re-states
 * those names, deduplicated, at the end of the result the model reads. It adds no
 * instruction, no judgement, and no alternative — it changes where the information sits,
 * not what the agent is told to do with it.
 *
 * Why deterministic rather than a sentence in SYSTEM.md: the frozen <policy> already says
 * "You must search the knowledge base to find tools that you can unlock", and the agent
 * already searches. The gap measured in batch_01 is between retrieved and read: in 6 of 6
 * episodes on two tasks, the exact gold tool name was inside the text KB_search returned
 * and was never unlocked. A restatement of the policy would compete with the policy; this
 * changes the text the model actually reads.
 *
 * Scope discipline:
 *   - It matches a NAMING CONVENTION, never a task: a lowercase snake_case identifier with
 *     a four-digit suffix, which is how this domain spells discoverable tools. No document
 *     id, no gold value, no per-task procedure, no answer is encoded here — the same file
 *     runs unchanged whatever the episode asks.
 *   - `doc_`-prefixed tokens are excluded: knowledge-base document ids share the shape.
 *   - Only `KB_search` results are touched, so the effect is attributable to retrieval
 *     reading and nothing else.
 *   - The list is capped so a pathological result cannot grow the context without bound.
 *   - No filesystem, network, or subprocess reach. Pure string work on content already in
 *     the episode.
 *
 * Seam facts this is designed against (measured, results/experiment_008_stratb-bm25-luna56
 * /generation_000/toolresult_probe/): `tool_result` fires for every tau tool as
 * `mcp_tau_<tau name>_<hash>` — match on substring, never equality; `event.content` is an
 * array of {type:"text"} blocks; a returned `content` patch reaches the model and is
 * absent from tau's graded trajectory, costing no step and producing no invalid call.
 */
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

/** Lowercase snake_case identifier ending in a four-digit suffix — this domain's
 *  discoverable-tool spelling. `doc_` is excluded: KB document ids share the shape. */
const TOOL_NAME = /\b(?!doc_)[a-z][a-z0-9]*(?:_[a-z0-9]+)*_\d{4}\b/g;
const MAX_NAMES = 12;

export default function kbToolNames(pi: ExtensionAPI): void {
  pi.on("tool_result", (event: any) => {
    try {
      if (!/KB_search/.test(String(event?.toolName ?? ""))) return undefined;
      const content = event?.content;
      if (!Array.isArray(content) || event?.isError) return undefined;

      const text = content
        .map((block: any) => (typeof block?.text === "string" ? block.text : ""))
        .join("\n");

      const names: string[] = [];
      for (const match of text.matchAll(TOOL_NAME)) {
        const name = match[0];
        if (!names.includes(name)) names.push(name);
        if (names.length >= MAX_NAMES) break;
      }
      if (names.length === 0) return undefined;

      return {
        content: [
          ...content,
          {
            type: "text",
            text: `\nTool names appearing in these knowledge-base results: ${names.join(", ")}`,
          },
        ],
      };
    } catch {
      // A handler runtime error is swallowed by the host, so failing closed here keeps the
      // episode identical to H0 rather than silently half-applied.
      return undefined;
    }
  });
}
