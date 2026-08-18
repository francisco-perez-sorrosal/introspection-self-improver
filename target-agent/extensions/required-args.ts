/* Restate an unlocked discoverable tool's REQUIRED argument set at the moment it is unlocked.
 *
 * Why this exists, and why it is a hook rather than a sentence. Generation 2 landed the same
 * rule as prose in SYSTEM.md ("send a tool's required parameters, and an optional one only
 * when the customer's request calls for it"). Its counter did not move at all: calls to
 * close_bank_account_7392 carrying the optional `reason` / `waive_early_closure_fee` keys
 * stood at 9 episodes / 10 calls in batch_01, batch_02 AND batch_03 — three rounds, two of
 * them without the instruction and one with it, identical. The pre-registered adversarial
 * reading of that sentence is what happened: the customer usually does state a motive, so
 * "only if the customer's request calls for it" reads as permission rather than restriction.
 *
 * The rule is unchanged here; only its delivery is. Prose cannot name a specific tool's
 * parameters, and it arrives thousands of tokens before the call. This hook names them, from
 * the unlock result the agent is reading at that moment, with no escape clause attached.
 *
 * Deterministic and domain-blind: every parameter name and every required/optional verdict is
 * PARSED OUT OF THE UNLOCK TEXT ITSELF, which tau just returned. Nothing about which tools,
 * parameters or values are correct is encoded here — that would be answer-hardcoding.
 *
 * HOST FACTS this code keys on, each measured and cited (see benchmark/probes/host_facts.yaml
 * and the checklist in skills/sia/references/recipe-growth.md):
 *   - `tool_result` fires for every tau tool, and the tool name arrives MANGLED as
 *     `mcp_tau_<tau name>_<hash>` — so this matches on a SUBSTRING and never on equality.
 *     Evidence: results/experiment_008_stratb-bm25-luna56/generation_001/ tool_result probe,
 *     56 firings across three banking-domain episodes covering every tau tool.
 *   - `event.content` is an ARRAY of `{type:"text"}` blocks, and a returned `content` patch
 *     reached the model in 24/24 firings while appearing 0 times in tau's graded trajectory.
 *     Same evidence.
 *   - A handler runtime error is logged and swallowed, so this returns `undefined` on any
 *     shape it does not recognise rather than throwing.
 */
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

// "  - account_id: string (required) - The ID of the bank account to close"
const PARAM = /^\s*-\s*([A-Za-z_][A-Za-z0-9_]*)\s*:\s*[^(]*\((required|optional)\)/;

export default function requiredArgs(pi: ExtensionAPI): void {
  pi.on("tool_result", (event: any) => {
    // Substring match: the host mangles tau tool names to mcp_tau_<name>_<hash>.
    if (typeof event?.toolName !== "string") return undefined;
    if (!event.toolName.includes("unlock_discoverable_agent_tool")) return undefined;

    const blocks = Array.isArray(event.content) ? event.content : [];
    const text = blocks
      .map((b: any) => (b && b.type === "text" && typeof b.text === "string" ? b.text : ""))
      .join("\n");
    if (!text) return undefined;

    const unlocked = /Tool unlocked:\s*(\S+)/.exec(text);
    if (!unlocked) return undefined;

    const required: string[] = [];
    const optional: string[] = [];
    for (const line of text.split("\n")) {
      const m = PARAM.exec(line);
      if (!m) continue;
      (m[2] === "required" ? required : optional).push(m[1]);
    }
    if (required.length === 0 && optional.length === 0) return undefined;

    const note =
      `\n\nArgument set for ${unlocked[1]} — required: ` +
      `${required.length ? required.join(", ") : "(none)"}. ` +
      (optional.length
        ? `The remaining parameters (${optional.join(", ")}) are optional; this call sends the required arguments and nothing else.`
        : `Send exactly these.`);

    return { content: [...blocks, { type: "text", text: note }] };
  });
}
