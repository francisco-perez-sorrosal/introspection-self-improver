/* Report that verification has been logged, at the moment it is logged.
 *
 * Mechanism (one, and only one): after `log_verification` returns successfully, a
 * `tool_result` hook appends one factual line saying verification is on record AND what a
 * further log would do. It states a fact and its consequence; it gives no instruction and
 * forbids nothing.
 *
 * The consequence half was added at gen-006 on measured evidence. The first version stated the
 * state alone ("verification is now on record"), and task_057 t2 in batch_06 logged twice
 * anyway — with the two calls in SEPARATE turns (#38 and #40), so the note was delivered
 * between them and ignored. Across six rounds the duplicate has now cost three episodes
 * (task_076 in batch_02 and batch_03, task_057 in batch_06) and every one of them failed.
 *
 * This is also the closing test of the framing sequence this experiment measured: a bare LIST
 * of facts changed nothing (C1, reverted); a MISSING-state note changed behaviour and carried
 * suppression risk (D2, which moved a transfer-reason counter 0/3 -> 3/3 and also dropped the
 * transfer rate 9/24 -> 6/24 unasked); a COMPLETED-state note was safe and inert outside its
 * own target (E1). A CONSEQUENCE-stating note is the untested fourth point, and it is
 * structurally safe here in a way D2 was not: the note can only appear AFTER a successful log,
 * so it cannot suppress the first one — only a redundant second.
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
            text:
              "\nIdentity verification is on record for this conversation; logging it again would write a duplicate verification record.",
          },
        ],
      };
    } catch {
      return undefined;
    }
  });
}
