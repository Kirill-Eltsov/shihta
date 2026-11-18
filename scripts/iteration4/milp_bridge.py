# -*- coding: utf-8 -*-
"""I4-K-03: bridge — pass explicit q into resource MILP and journal the handoff.

Warm-start is NOT used (not confirmed in G2 / I3-K-08).
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from resource_milp import result_to_dict, solve_resource_milp

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT = ROOT / "data" / "processed" / "i4" / "milp_bridge_trace.json"


def _q_pairs(q_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {"order_id": str(r["order_id"]), "recipe_id": str(r["recipe_id"]), "value": float(r["value"])}
        for r in q_rows
    ]


def run_with_trace(
    scenario: dict[str, Any],
    *,
    time_limit_s: float | None = 120.0,
    warm_start: bool = False,
) -> dict[str, Any]:
    if warm_start:
        raise RuntimeError("warm_start requested but not confirmed; refuse per G2")

    case = scenario["case"]
    q_rows = scenario["q"]
    q_payload = _q_pairs(q_rows)
    n_pairs = sum(len(meta["candidates"]) for meta in case["orders"].values())

    result = solve_resource_milp(case, q_rows, time_limit_s=time_limit_s)
    return {
        "scenario_id": scenario.get("scenario_id"),
        "input": {
            "q_explicit": q_payload,
            "n_assignment_vars": n_pairs,
            "stocks": case.get("stocks"),
            "orders": {
                oid: {"demand_t": meta["demand_t"], "candidates": list(meta["candidates"])}
                for oid, meta in case["orders"].items()
            },
            "warm_start": False,
            "warm_start_status": "not_confirmed_not_used",
        },
        "output": result_to_dict(result),
    }


def main() -> int:
    scenarios_path = ROOT / "data" / "processed" / "i4" / "scenarios_v1.json"
    raw = scenarios_path.read_bytes()
    payload = json.loads(raw)
    traces = []
    for s in payload["scenarios"]:
        traces.append(run_with_trace(s))
    out = {
        "scope": "I4-K-03 milp bridge with explicit q",
        "scenarios_sha256": hashlib.sha256(raw).hexdigest(),
        "warm_start": "not_used",
        "traces": traces,
    }
    DEFAULT_OUT.parent.mkdir(parents=True, exist_ok=True)
    DEFAULT_OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"out": str(DEFAULT_OUT), "n": len(traces)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
