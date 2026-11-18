# -*- coding: utf-8 -*-
"""I4-K-04: run Kirill resource MILP (+ greedy) on Alexey control scenarios."""
from __future__ import annotations

import hashlib
import json
import math
import platform
import sys
from pathlib import Path

import scipy

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from resource_milp import (  # noqa: E402
    result_to_dict,
    score_plan,
    solve_greedy_quality,
    solve_resource_milp,
    validate_plan,
)

SCENARIOS = ROOT / "data" / "processed" / "i4" / "scenarios_v1.json"
OUT = ROOT / "data" / "processed" / "i4" / "k_control_results.json"
EXPECTED_SHA = "4d6b9ee09651c418987e40e94c1810365afbe91bdc52f063b59c16e11375b8c2"


def main() -> int:
    raw = SCENARIOS.read_bytes()
    sha = hashlib.sha256(raw).hexdigest()
    if sha != EXPECTED_SHA:
        raise SystemExit(f"scenarios hash mismatch: {sha} != {EXPECTED_SHA}")

    payload = json.loads(raw)
    checks = []
    all_ok = True

    for s in payload["scenarios"]:
        case = s["case"]
        q_rows = s["q"]
        milp_res = solve_resource_milp(case, q_rows)
        greedy_res = solve_greedy_quality(case, q_rows)
        expected_status = s.get("expected_status")
        expected_obj = s.get("expected_objective")

        ok = True
        detail = {
            "scenario_id": s["scenario_id"],
            "milp": result_to_dict(milp_res),
            "greedy": result_to_dict(greedy_res),
        }

        if expected_status == "infeasible":
            if milp_res.status != "infeasible":
                ok = False
        else:
            if milp_res.status not in {"optimal", "feasible"}:
                ok = False
            if expected_obj is not None and milp_res.objective is not None:
                if not math.isclose(milp_res.objective, float(expected_obj), abs_tol=1e-8, rel_tol=1e-9):
                    ok = False
            elif expected_obj is not None:
                ok = False

        detail["passed"] = ok
        checks.append(detail)
        all_ok = all_ok and ok

    # Extra controls from I4-A-02
    base = payload["scenarios"][0]
    case = base["case"]
    q = {(r["order_id"], r["recipe_id"]): r["value"] for r in base["q"]}
    old = [{"order_id": str(i), "recipe_id": r} for i, r in enumerate(["H", "L", "L"], 1)]
    assert math.isclose(score_plan(case, old, q), 2.5)

    banned = json.loads(json.dumps(case))
    banned["orders"]["1"]["candidates"] = ["L"]
    v = validate_plan(banned, old)
    assert not v["valid"] and any("forbidden_recipe" in e for e in v["errors"])
    checks.append({"id": "forbidden_candidate", "status": "invalid_plan", "passed": True})

    changed = dict(q)
    changed[("1", "H")] = 0.1
    assert math.isclose(score_plan(case, old, changed), 1.65)
    checks.append({"id": "explicit_changed_q_old_plan", "objective": 1.65, "passed": True})

    empty = solve_resource_milp(case, base["q"])
    # empty plan classification via validator path
    checks.append(
        {
            "id": "milp_base_optimal",
            "status": empty.status,
            "objective": empty.objective,
            "passed": empty.status == "optimal" and math.isclose(empty.objective or -1, 2.5),
        }
    )
    all_ok = all_ok and checks[-1]["passed"]

    result = {
        "scope": "Kirill I4-K resource MILP controls on Alexey scenarios_v1",
        "method": "resource_milp + greedy_quality control",
        "input_sha256": sha,
        "python": platform.python_version(),
        "scipy": scipy.__version__,
        "checks_run": len(checks),
        "all_passed": all_ok,
        "checks": checks,
    }
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"all_passed": all_ok, "checks_run": len(checks), "out": str(OUT)}, ensure_ascii=False))
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
