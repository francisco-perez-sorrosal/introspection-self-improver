/* The growth zero-state, tool half: a committed, UNDECLARED extension-tool template.
 *
 * This file is deliberately absent from `package.json` `pi.extensions`, and its tool name
 * is deliberately absent from `agents/agent.yaml` `tools:` — doubly inert. It exists for
 * the same reason as `noop-hook.ts`: so the first registered-tool mutation is a small,
 * reviewable diff against a template instead of a novel artifact class. Seq 8 measured
 * what the absence of this template costs — the hook surface had a template and received
 * six changes; the tool surface had none and received zero, while the D24 seam built to
 * unlock it ran pump-path-only (`pi_local_calls` = 0 across 168 platform episodes).
 *
 * To enable — ONE coherent change, never riders (recipe-growth §Checklist):
 *   1. add "extensions/noop-tool.ts" to `package.json` `pi.extensions` (explicit path);
 *   2. add the tool name to `agents/agent.yaml` `tools:` — the same list IS the D24
 *      Pi-local suppression registry: with the entry, a model call to this tool is
 *      executed by Pi and suppressed from τ's graded trajectory (logged in raw_data +
 *      manifest `pi_local_calls`); WITHOUT it, the call leaks to τ as a graded invalid
 *      step. Registering here and forgetting the allowlist ships a surface that leaks.
 *   3. the change is adoption-first (contract/protocol.md step 4): its falsifiable
 *      prediction targets adoption and correct invocation (`pi_local_calls` ≥ k,
 *      well-formed arguments, latency inside τ's frozen `timeout_seconds`), the
 *      reward-level prediction is deferred to the following round, and the tool may
 *      bundle its minimal usage instruction in SYSTEM.md as part of the same mechanism.
 *
 * Semantics to design against (measured + upstream-verified; recipe-growth §Wiring, trap 4):
 *   - suppression is measured end-to-end on the local lane, mock domain (probe P6:
 *     `probe_note` called 3/3 episodes, invisible to τ, `pi_local_calls: 1` logged);
 *     the platform-lane engagement is certified by the pre-freeze suppression canary
 *     (`make gate_suppression`) — re-verify there before any graded round relies on it;
 *   - `execute` runs with the Pi host's authority: keep any filesystem reach inside the
 *     recipe via PI_RECIPE_DIR, never touch benchmark/vendor/ or results/, and state the
 *     tool's actual reach (filesystem, network, subprocess) in the PR and the record;
 *   - Pi-local execution still spends wall-clock and tokens inside τ's frozen episode
 *     budget — measure dev-lane episode latency before landing anything heavier;
 *   - an extension edit needs a NEW dev-lane chat; extension LOAD failure is fatal,
 *     handler runtime errors are logged and swallowed;
 *   - re-verify the import names against current upstream docs at enable time (standing
 *     guardrail) — the ambient `.pi/extensions/traces.ts` exemplar carries older package
 *     names; the recipe's peer dependencies are the authority.
 */
import { Type } from "@earendil-works/pi-ai";
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

export default function noopTool(pi: ExtensionAPI): void {
  pi.registerTool({
    name: "probe_note",
    description:
      "Record a short working note. Deterministic, side-effect-free; returns an " +
      "acknowledgment of the recorded text.",
    parameters: Type.Object({
      note: Type.String({ description: "The note to record." }),
    }),
    async execute(_toolCallId, params) {
      const { note } = params as { note: string };
      return { content: [{ type: "text", text: `noted: ${note}` }] };
    },
  });
}
