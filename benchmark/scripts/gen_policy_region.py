#!/usr/bin/env python3
"""Write τ's domain policy into the Recipe's frozen `<policy>` region.

Run for the locked domain and retrieval config, which is where the value comes from — never
hand-authored. It also records the policy hash and the τ tool surface in benchmark_lock.yaml,
which is what lets the pre-commit hook and CI verify the region without importing τ² at all.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tau_adapter import lock as lockmod
from tau_adapter.policy_region import (
    extract_policy,
    policy_sha256,
    replace_policy,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="report what would change and exit non-zero if anything would, writing nothing",
    )
    args = parser.parse_args()

    lock = lockmod.load_lock()
    lockmod.assert_vendor_commit(lock)

    from tau2.registry import registry

    kwargs = {}
    if lock.retrieval_config:
        # τ names this `retrieval_variant` on the environment constructor and
        # `retrieval_config` on the CLI. Same value, two spellings.
        kwargs["retrieval_variant"] = lock.retrieval_config
    env = registry.get_env_constructor(lock.domain)(**kwargs)

    live_policy = env.get_policy()
    tool_names = [t.name for t in env.get_tools()]
    digest = policy_sha256(live_policy)

    system_md = lockmod.RECIPE_SYSTEM_MD.read_text(encoding="utf-8")
    current = extract_policy(system_md)
    updated = replace_policy(system_md, live_policy)

    region_ok = policy_sha256(current) == digest
    lock_ok = lock.policy_sha256 == digest
    catalog_ok = sorted(lock.tool_catalog) == sorted(tool_names)

    if args.check:
        drift = [
            name
            for name, ok in (
                ("SYSTEM.md <policy> region", region_ok),
                ("benchmark_lock.yaml policy.sha256", lock_ok),
                ("benchmark_lock.yaml tool_catalog", catalog_ok),
            )
            if not ok
        ]
        if drift:
            print("policy region is stale: " + ", ".join(drift), file=sys.stderr)
            print("run `make policy` to regenerate", file=sys.stderr)
            return 1
        print(f"✓ policy region current for {lock.domain} ({lock.retrieval_config or 'default'})")
        return 0

    if not region_ok:
        lockmod.RECIPE_SYSTEM_MD.write_text(updated, encoding="utf-8")
    lockmod.update_policy_fields(digest, lock.domain, lock.retrieval_config)
    lockmod.update_tool_catalog(tool_names)

    print(f"✓ domain {lock.domain} / retrieval {lock.retrieval_config or 'default'}")
    print(f"  <policy> region: {len(live_policy)} chars, sha256 {digest[:16]}…")
    print(f"  tool_catalog:    {len(tool_names)} tools")
    if not region_ok:
        print("  SYSTEM.md updated — review the diff before committing")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
