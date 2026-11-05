"""I3-K-07/08: check whether current solver stack accepts a feasible start."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import numpy as np
import scipy
from scipy.optimize import Bounds, LinearConstraint, milp

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "processed" / "milp"
DOCS = ROOT / "docs" / "iteration3"


def main() -> int:
    # tiny ILP
    c = -np.array([3.0, 2.0], dtype=float)
    A = np.array([[1.0, 1.0]])
    cons = LinearConstraint(A, [1], [1])
    bounds = Bounds([0, 0], [1, 1])
    res = milp(c=c, constraints=cons, bounds=bounds, integrality=[1, 1])

    # Probe API for start / warm start options
    import inspect

    sig = str(inspect.signature(milp))
    supports_x0 = "x0" in sig
    # scipy milp currently: no reliable mip_start in public signature for all versions
    evidence = {
        "ts": datetime.now().isoformat(timespec="seconds"),
        "scipy_version": scipy.__version__,
        "milp_signature": sig,
        "supports_x0_param": supports_x0,
        "tiny_solve_status": bool(res.success),
        "tiny_objective": float(-res.fun) if res.success else None,
        "conclusion": (
            "not_confirmed"
            if not supports_x0
            else "parameter_present_but_usage_not_proven"
        ),
        "note": "Presence of a parameter alone is not treated as proof the solver consumes the start",
        "fallback_if_unsupported": "compare heuristics vs MILP honestly as separate tracks",
    }
    (OUT / "solver_api_check.json").write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
    (DOCS / "I3-K-07_solver_api.md").write_text(
        "# I3-K-07\n\nМинимальный пример scipy.optimize.milp. Версия и signature сохранены.\n"
        f"supports_x0={supports_x0}. См. `solver_api_check.json`.\n",
        encoding="utf-8",
    )
    (DOCS / "I3-K-08_solver_api_result.md").write_text(
        f"# I3-K-08\n\nВывод: **{evidence['conclusion']}**.\n"
        "Подкреплено журналом API, не только догадкой. При отсутствии поддержки — отдельное сравнение эвристики с MILP.\n",
        encoding="utf-8",
    )
    print(json.dumps(evidence, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
