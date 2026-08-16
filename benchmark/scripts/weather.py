#!/usr/bin/env python3
"""Provider-weather probe for the frozen user-simulator surface. Diagnostic, never a gate.

The user simulator is a frozen surface served by a live provider, and its failures are
weather: on 2026-08-15, 3 of 6 canary trials died on empty completions ("UserMessage must
have either content or tool_calls") — luna returning nothing on the opening turn, four
τ retries exhausted each time, a sandbox provisioned and orphaned per retry. Discovering
that weather by burning sandbox provisions is the expensive way. This probe makes N direct
calls with the lock's exact user-sim configuration (model + llm args, via litellm — the
same client τ's user simulator uses) and counts empty completions, so a round's go/no-go
costs seconds and cents.

An imperfect leading indicator by design: the real user sim carries a task scenario prompt
this probe only approximates, so a clean probe does not guarantee a clean round — but a
dirty probe reliably predicts a stormy one.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tau_adapter.lock import load_lock

#: Shaped like the user simulator's opening turn: a persona system prompt and a request to
#: produce the first customer message. Content is irrelevant — emptiness is the signal.
_SYSTEM = (
    "You are simulating a bank customer talking to a support agent. Stay in character, be "
    "concise, and pursue your goal across turns."
)
_OPENING = (
    "Your goal: find out which credit card gives the best cash back for everyday purchases "
    "with no annual fee. Write your opening message to the support agent."
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-n", "--calls", type=int, default=6, help="probe calls (default 6)")
    args = parser.parse_args()

    lock = load_lock()
    llm_args = dict(lock.user_llm_args)
    print(f"── weather: {args.calls} × {lock.user_llm} {llm_args} (user-sim surface)")

    import litellm

    empties = 0
    failures = 0
    for i in range(args.calls):
        started = time.time()
        try:
            response = litellm.completion(
                model=lock.user_llm,
                messages=[
                    {"role": "system", "content": _SYSTEM},
                    {"role": "user", "content": _OPENING},
                ],
                **llm_args,
            )
            content = (response.choices[0].message.content or "").strip()
            if not content:
                empties += 1
            label = "EMPTY" if not content else f"{len(content)} chars"
        except Exception as exc:  # noqa: BLE001 — every provider failure is the datum here
            failures += 1
            label = f"{type(exc).__name__}: {str(exc)[:80]}"
        print(f"   call {i + 1}/{args.calls}: {label} ({time.time() - started:.1f}s)")

    dirty = empties + failures
    if dirty:
        print(
            f"\n✗ weather is dirty: {empties} empty completion(s), {failures} failure(s) "
            f"out of {args.calls} — a round started now will burn retries and orphan "
            f"sandboxes. Hold, and re-probe before spending episodes."
        )
        return 1
    print(f"\n✓ weather is clear: {args.calls}/{args.calls} calls returned content")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
