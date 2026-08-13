"""The seam between τ²-bench and an Introspection Recipe.

τ² is the task oracle and the only source of reward. This package carries messages and tool
calls between it and a hosted Recipe, and does nothing else — see `pi_agent` for why that
restraint is the design rather than an omission.

Importing this package points τ² at the vendored data directory. That has to happen here, and
not in an entry point, because τ² resolves its data directory *once at import time*
(`tau2/utils/utils.py` reads TAU2_DATA_DIR into a module constant) and several modules in this
package import τ² at their own module level. Setting it in `main()` is too late, and the
failure is a confusing FileNotFoundError deep inside a domain loader rather than anything
that names the real cause.
"""

from __future__ import annotations

import os
from pathlib import Path

#: The vendored τ²-bench checkout, reproduced by `make bootstrap` at the pinned commit.
VENDOR_DIR = Path(__file__).resolve().parents[1] / "vendor" / "tau2-bench"

# An explicit setting wins: the caller may be pointing at a different checkout deliberately.
if not os.environ.get("TAU2_DATA_DIR"):
    os.environ["TAU2_DATA_DIR"] = str(VENDOR_DIR / "data")
