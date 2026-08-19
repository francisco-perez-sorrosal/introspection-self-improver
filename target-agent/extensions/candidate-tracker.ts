/* A deterministic scratchpad for a choice among the bank's named options.
 *
 * Target: wrong-named-class, the mechanism this experiment has attacked three times and never
 * moved. C3 (search a candidate by its exact name) moved the retrieval counter and its
 * stratum; C6 (check coverage before committing) was denied and reverted for cost; C9 (apply
 * the rule the knowledge base states) was denied and its counter went the WRONG way, 5 -> 8.
 *
 * Why a state tool, and why now. The only mechanism this experiment has confirmed in its back
 * half is C8's: a tool that HOLDS state the model cannot silently lose. Its own counter fell
 * 15 -> 13 -> 10 across the two rounds carrying it, while five successive instruction changes
 * asking the model to remember, verify or withhold were all denied — two of them through a
 * verified point-of-use structural injection as well as through prose. This applies C8's
 * confirmed pattern to the mechanism that has resisted every instruction aimed at it.
 *
 * The decisive transcripts say the same thing twice, in the agent's own words. task_002:
 * "the available data is insufficient. So, I'll recommend the EcoCard." task_056: "ATM
 * rebates are unclear... I might only recommend Hunter Green conditionally", then recommends
 * it unconditionally. In both the gap is KNOWN and then lost. A tool that reports the gap
 * back, computed, is the one delivery this experiment has not tried for it.
 *
 * Reach, stated for the record and the review: this tool touches NOTHING — no filesystem, no
 * network, no subprocess. Its whole state is a per-session in-memory Map, per-episode by
 * construction because every episode is a fresh Pi session. It stores and returns the strings
 * the model gives it and computes only set difference, so it cannot encode a benchmark answer:
 * it has no domain content at all, and it never says which option is correct.
 *
 * Suppression: `compare_candidates` is allowlisted in agents/agent.yaml `tools:`, which under
 * the D24 seam IS the Pi-local suppression registry — measured in this experiment at 578 calls
 * across batch_05 with zero occurrences in tau's graded trajectory.
 */
import { Type } from "@earendil-works/pi-ai";
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

export default function candidateTracker(pi: ExtensionAPI): void {
  const requirements = new Set<string>();
  const known = new Map<string, Set<string>>(); // candidate -> requirements with a value

  pi.registerTool({
    name: "compare_candidates",
    description:
      "Track a choice among the bank's named options. Call with `requirement` and the " +
      "requirement the customer stated; with `candidate` and an option's exact name to " +
      "start tracking it; with `value` plus a candidate and a requirement once you have " +
      "retrieved that option's figure for it; and with `gaps` to get back which " +
      "candidate/requirement pairs you have not retrieved yet.",
    parameters: Type.Object({
      action: Type.String({ description: "One of: requirement, candidate, value, gaps." }),
      candidate: Type.String({ description: "The option's exact name.", default: "" }),
      requirement: Type.String({ description: "The customer's stated requirement.", default: "" }),
    }),
    async execute(_toolCallId, params) {
      const p = params as { action: string; candidate?: string; requirement?: string };
      const cand = (p.candidate || "").trim();
      const req = (p.requirement || "").trim();
      if (p.action === "requirement" && req) requirements.add(req);
      else if (p.action === "candidate" && cand && !known.has(cand)) known.set(cand, new Set());
      else if (p.action === "value" && cand && req) {
        if (!known.has(cand)) known.set(cand, new Set());
        known.get(cand)!.add(req);
        requirements.add(req);
      }
      const gaps: string[] = [];
      for (const [c, have] of known)
        for (const r of requirements) if (!have.has(r)) gaps.push(`${c} / ${r}`);
      const text = known.size === 0
        ? "No candidates tracked yet."
        : gaps.length
          ? `Not yet retrieved (${gaps.length}): ${gaps.join("; ")}`
          : `All ${known.size} candidate(s) have a value for all ${requirements.size} requirement(s).`;
      return { content: [{ type: "text", text }] };
    },
  });
}
