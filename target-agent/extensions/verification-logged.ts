/* Report that verification has been logged, at the moment it is logged.
 *
 * Mechanism (one, and only one): after `log_verification` returns successfully, a
 * `tool_result` hook appends one factual line saying verification is now on record for this
 * conversation. It reports a state; it gives no instruction and forbids nothing.
 *
 * Evidence. `log_verification` writes a row to the verification records, and a DB-graded task
 * fails on a duplicate row. Across 72 episodes of batch_01..batch_03, exactly two called it
 * twice — task_076 t0 in batch_02 and in batch_03 — and both failed, while every other trial
 * of that task called it once and passed. The two failing trials are otherwise call-for-call
 * identical to the passing ones: same account opened, same class, same arguments. The
 * duplicate is the whole difference.
 *
 * Why a result-time state report rather than a block. A `tool_call` hook cannot prevent the
 * second write: this seam forwards the call to tau regardless, so tau performs the write while
 * the agent believes it was stopped, and the two histories diverge (recipe-growth trap 4). The
 * only legal lever is what the model reads after the FIRST call succeeds, which is exactly
 * where the redundancy becomes knowable.
 *
 * Prevalence is deliberately thin — 2 of 72 episodes — and the change is landed anyway
 * because the causal chain is airtight rather than statistical, and because protecting a
 * reliable marginal task from a mechanical regression is what the stratified batch exists to
 * make visible.
 *
 * Scope discipline: fires only on a successful `log_verification` result; states a fact with
 * no imperative and no alternative; encodes no task, user, or gold value; pure string work,
 * no filesystem/network/subprocess reach; try/catch fails closed to unmodified behaviour.
 */
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

export default function verificationLogged(pi: ExtensionAPI): void {
  pi.on("tool_result", (event: any) => {
    try {
      if (!/log_verification/.test(String(event?.toolName ?? ""))) return undefined;
      const content = event?.content;
      if (!Array.isArray(content) || event?.isError) return undefined;

      return {
        content: [
          ...content,
          {
            type: "text",
            text: "\nIdentity verification is now on record for this conversation.",
          },
        ],
      };
    } catch {
      return undefined;
    }
  });
}
