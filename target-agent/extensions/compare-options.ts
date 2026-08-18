/* Constrained option selection: filter candidates by stated requirements, then rank them
 * by the customer's stated preference order.
 *
 * WHY THIS IS A TOOL AND NOT A SENTENCE. Measured at H0 over two rounds (batch_01 and the
 * identity round batch_02, 36 episodes each): when a customer states hard requirements AND
 * a preference ordering, the agent optimises the salient attribute instead of the stated
 * ordering. task_003's customer asks for no foreign transaction fees, purchase protection
 * and a >=$100k limit, then says "if there are multiple cards that fulfil the requirements,
 * you prefer the one with the smallest annual fee" — and the agent applied for the Gold
 * Rewards Card in 6 of 6 episodes where gold is the Silver Rewards Card. Three prior
 * experiments measured that an instruction added to a prompt does not inherit the scope its
 * author reasoned about; filtering-then-ordering is arithmetic, not judgment, so it belongs
 * on a deterministic surface.
 *
 * WHAT IT DOES NOT KNOW. Nothing about banking, cards, accounts, or this benchmark. It has
 * no document ids, no product names, no thresholds, no gold values — it cannot, because
 * task-specific artifacts in tool code are answer-hardcoding (recipe-growth trap 5). Every
 * candidate, attribute and value is supplied by the caller from what it retrieved; this
 * code only compares. Feed it wrong values and it returns a wrong ranking, correctly.
 *
 * REACH: none. No filesystem, no network, no subprocess, no state between calls. It reads
 * its arguments and returns text.
 *
 * D24 SEAM: `compare_options` is listed in agents/agent.yaml `tools:`, which IS the
 * Pi-local suppression registry — the call is executed by Pi and never forwarded to tau, so
 * it costs no tau step and none of the ten max_errors, and it is logged in
 * raw_data.pi_suppressed_tool_names with the manifest deriving pi_local_calls. Registering
 * here WITHOUT the agent.yaml entry would ship a surface that leaks to the evaluator as a
 * graded invalid call; both halves land in the same commit.
 */
import { Type } from "@earendil-works/pi-ai";
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

const OPERATORS = ["at_least", "at_most", "equals", "not_equals", "is_true", "is_false"];
const DIRECTIONS = ["lowest", "highest"];

type Attribute = { attribute: string; value: unknown };
type Candidate = { name: string; attributes: Attribute[] };
type Requirement = { attribute: string; operator: string; value?: unknown };
type Preference = { attribute: string; direction: string };

/** Attribute lookup is case- and space-insensitive: callers paraphrase document wording. */
function normalize(name: string): string {
  return String(name).trim().toLowerCase().replace(/[\s_-]+/g, " ");
}

function lookup(candidate: Candidate, attribute: string): unknown {
  const wanted = normalize(attribute);
  for (const entry of candidate.attributes || []) {
    if (normalize(entry.attribute) === wanted) return entry.value;
  }
  return undefined;
}

/** Numbers arrive as "$0.00", "2.5%", "100,000" as often as as numbers. */
function asNumber(value: unknown): number | null {
  if (typeof value === "number") return Number.isFinite(value) ? value : null;
  if (typeof value !== "string") return null;
  const cleaned = value.replace(/[$,%\s,]/g, "");
  const parsed = Number(cleaned);
  return Number.isFinite(parsed) && cleaned !== "" ? parsed : null;
}

function asBoolean(value: unknown): boolean | null {
  if (typeof value === "boolean") return value;
  if (typeof value !== "string") return null;
  const text = value.trim().toLowerCase();
  if (["true", "yes", "y", "included", "available"].includes(text)) return true;
  if (["false", "no", "n", "none", "not included", "unavailable"].includes(text)) return false;
  return null;
}

type Check = { ok: boolean | null; detail: string };

function check(actual: unknown, requirement: Requirement): Check {
  const { operator, value: wanted, attribute } = requirement;
  if (actual === undefined) {
    return { ok: null, detail: `${attribute}: NOT SUPPLIED — retrieve it before deciding` };
  }
  const shown = JSON.stringify(actual);
  if (operator === "is_true" || operator === "is_false") {
    const flag = asBoolean(actual);
    if (flag === null) return { ok: null, detail: `${attribute}: ${shown} is not yes/no` };
    const want = operator === "is_true";
    return { ok: flag === want, detail: `${attribute}: ${shown} (needs ${want ? "yes" : "no"})` };
  }
  if (operator === "equals" || operator === "not_equals") {
    const same = normalize(String(actual)) === normalize(String(wanted));
    const ok = operator === "equals" ? same : !same;
    return { ok, detail: `${attribute}: ${shown} (needs ${operator} ${JSON.stringify(wanted)})` };
  }
  const actualNumber = asNumber(actual);
  const wantedNumber = asNumber(wanted);
  if (actualNumber === null || wantedNumber === null) {
    return { ok: null, detail: `${attribute}: ${shown} is not numeric` };
  }
  const ok = operator === "at_least" ? actualNumber >= wantedNumber : actualNumber <= wantedNumber;
  return { ok, detail: `${attribute}: ${actualNumber} (needs ${operator} ${wantedNumber})` };
}

function rank(candidates: Candidate[], preferences: Preference[]): Candidate[] {
  return [...candidates].sort((left, right) => {
    for (const preference of preferences || []) {
      const a = asNumber(lookup(left, preference.attribute));
      const b = asNumber(lookup(right, preference.attribute));
      if (a === null && b === null) continue;
      if (a === null) return 1;
      if (b === null) return -1;
      if (a === b) continue;
      return preference.direction === "highest" ? b - a : a - b;
    }
    return 0;
  });
}

export default function compareOptions(pi: ExtensionAPI): void {
  pi.registerTool({
    name: "compare_options",
    description:
      "Decide which of several options a customer's stated requirements and preferences " +
      "select. Give it every candidate you retrieved with the attribute values you found, " +
      "the customer's hard requirements, and their preference order (most important " +
      "first). It reports which candidates qualify, why each excluded one failed, which " +
      "attributes you have not supplied, and the qualifying candidates ranked by the " +
      "stated preferences. It knows nothing about any product — it only compares what you " +
      "give it, so retrieve each candidate's specification first.",
    parameters: Type.Object({
      candidates: Type.Array(
        Type.Object({
          name: Type.String({ description: "The option's exact name, as the source states it." }),
          attributes: Type.Array(
            Type.Object({
              attribute: Type.String({ description: "Attribute name, e.g. 'annual fee'." }),
              value: Type.Any({ description: "Value as retrieved; '$0.00' and 0 both work." }),
            }),
          ),
        }),
        { description: "Every candidate under consideration." },
      ),
      requirements: Type.Array(
        Type.Object({
          attribute: Type.String(),
          operator: Type.String({
            description: "at_least | at_most | equals | not_equals | is_true | is_false",
          }),
          value: Type.Optional(Type.Any({ description: "Omit for is_true / is_false." })),
        }),
        { description: "Hard requirements. A candidate failing any one does not qualify." },
      ),
      preferences: Type.Array(
        Type.Object({
          attribute: Type.String(),
          direction: Type.String({ description: "lowest | highest" }),
        }),
        { description: "Tie-breaks in priority order, most important first." },
      ),
    }),
    async execute(_toolCallId, params) {
      const { candidates, requirements, preferences } = params as {
        candidates: Candidate[];
        requirements: Requirement[];
        preferences: Preference[];
      };

      const badOperator = (requirements || []).find((r) => !OPERATORS.includes(r.operator));
      const badDirection = (preferences || []).find((p) => !DIRECTIONS.includes(p.direction));
      if (badOperator || badDirection) {
        const problem = badOperator
          ? `operator '${badOperator.operator}' (use ${OPERATORS.join(", ")})`
          : `direction '${badDirection?.direction}' (use ${DIRECTIONS.join(", ")})`;
        return { content: [{ type: "text", text: `compare_options: unknown ${problem}.` }] };
      }
      if (!candidates || candidates.length === 0) {
        return {
          content: [{ type: "text", text: "compare_options: no candidates supplied." }],
        };
      }

      const qualifying: Candidate[] = [];
      const lines: string[] = [];
      const unknowns: string[] = [];
      for (const candidate of candidates) {
        const checks = (requirements || []).map((r) => check(lookup(candidate, r.attribute), r));
        const failed = checks.filter((c) => c.ok === false);
        const missing = checks.filter((c) => c.ok === null);
        if (missing.length > 0) {
          unknowns.push(`${candidate.name}: ${missing.map((c) => c.detail).join("; ")}`);
        }
        if (failed.length === 0 && missing.length === 0) {
          qualifying.push(candidate);
        } else if (failed.length > 0) {
          lines.push(`EXCLUDED ${candidate.name} — ${failed.map((c) => c.detail).join("; ")}`);
        }
      }

      const ranked = rank(qualifying, preferences || []);
      const shownPreferences = (preferences || [])
        .map((p) => `${p.attribute} ${p.direction}`)
        .join(", then ");
      const report: string[] = [];
      if (ranked.length > 0) {
        report.push(
          `QUALIFYING, ranked by ${shownPreferences || "no stated preference"}:`,
          ...ranked.map((candidate, index) => {
            const shown = (preferences || [])
              .map((p) => `${p.attribute}=${JSON.stringify(lookup(candidate, p.attribute))}`)
              .join(", ");
            return `  ${index + 1}. ${candidate.name}${shown ? ` (${shown})` : ""}`;
          }),
          `SELECTED by the stated preferences: ${ranked[0].name}`,
        );
      } else {
        report.push("QUALIFYING: none of the supplied candidates met every requirement.");
      }
      if (lines.length > 0) report.push("", ...lines);
      if (unknowns.length > 0) {
        report.push(
          "",
          "UNDECIDABLE without more retrieval — these candidates are missing attributes " +
            "and were not ranked:",
          ...unknowns.map((u) => `  ${u}`),
        );
      }
      return { content: [{ type: "text", text: report.join("\n") }] };
    },
  });
}
