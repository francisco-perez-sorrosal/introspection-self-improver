/* The growth zero-state: a committed, UNDECLARED extension template.
 *
 * This file is deliberately absent from `package.json` `pi.extensions`, which makes it
 * genuinely inert — extensions have no convention discovery, and agent YAML cannot select
 * or gate them (`tools: []` limits model-callable tools, not hook execution). It exists so
 * the first structural mutation is a small, reviewable diff against a template instead of
 * a novel artifact class: every prose mutation has had sixteen predecessors; this is the
 * structural surface's first.
 *
 * To enable: add "extensions/noop-hook.ts" (the explicit path — an unmatched glob fails
 * `introspection check`) to `pi.extensions`, as its own coherent change with its own
 * falsifiable prediction (one branch, one commit, one record entry; see
 * skills/sia/references/recipe-growth.md for the full wiring and traps).
 *
 * Semantics to design against (upstream-verified + probe-measured 2026-08-16,
 * benchmark/probes/2026-08-16-surface-probes/):
 *   - the extension closure loads for EVERY session in the package once declared;
 *   - a `before_agent_start` handler fires each agent start, sees the fully composed
 *     system prompt (Recipes' own SYSTEM.md composition runs first), and `undefined`
 *     leaves the prompt unchanged;
 *   - extension LOAD failure is fatal before any model call, while handler RUNTIME errors
 *     are logged and swallowed (`tool_call` excepted) — a hook cannot signal through an
 *     exception, so log markers instead;
 *   - dev-lane iteration: an extension edit needs a NEW chat, not a new turn;
 *   - registered tools become model-callable only when allowlisted in `agents/agent.yaml`
 *     `tools:`, which doubles as the seam's Pi-local suppression registry (D24) — a
 *     registered-and-allowlisted tool call is executed by Pi and suppressed from τ;
 *   - hook code runs with the Pi host's authority: keep filesystem reach inside the
 *     recipe via PI_RECIPE_DIR, and never touch benchmark/vendor/ or results/.
 */
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

export default function noopHook(pi: ExtensionAPI): void {
  pi.on("before_agent_start", () => undefined);
}
