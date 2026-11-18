# -*- coding: utf-8 -*-
"""I4-K-07/08: automatic benchmark runner + result collection on control set.

Respects I4-A-03: 120s budget, deterministic reps for timing, statuses, journal.
Does NOT claim a large-scale production series — only control scenarios_v1.
"""
from __future__ import annotations

import hashlib
import json
import platform
import statistics
import sys
import time
from pathlib import Path

import scipy

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from resource_milp import result_to_dict, solve_greedy_quality, solve_resource_milp  # noqa: E402

SCENARIOS = ROOT / "data" / "processed" / "i4" / "scenarios_v1.json"
CONFIG = ROOT / "data" / "processed" / "i4" / "method_config.json"
OUT = ROOT / "data" / "processed" / "i4" / "benchmark_control.json"
EXPECTED_SHA = "4d6b9ee09651c418987e40e94c1810365afbe91bdc52f063b59c16e11375b8c2"


def _time_stats(samples: list[float]) -> dict:
    return {
        "n": len(samples),
        "median_s": statistics.median(samples),
        "min_s": min(samples),
        "max_s": max(samples),
        "values_s": samples,
    }


def run_method(name: str, fn, case, q, reps: int, budget: float) -> dict:
    primary = None
    times = []
    for i in range(reps):
        t0 = time.perf_counter()
        res = fn(case, q, time_limit_s=budget) if name == "resource_milp" else fn(case, q)
        elapsed = time.perf_counter() - t0
        times.append(elapsed)
        if i == 0:
            primary = result_to_dict(res)
            primary["wall_s"] = elapsed
            if elapsed > budget + 1e-6:
                primary["budget_exceeded"] = True
    return {"primary": primary, "time": _time_stats(times)}


def main() -> int:
    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    raw = SCENARIOS.read_bytes()
    sha = hashlib.sha256(raw).hexdigest()
    if sha != EXPECTED_SHA:
        raise SystemExit(f"scenarios hash mismatch: {sha}")

    payload = json.loads(raw)
    reps = int(cfg.get("repetitions_deterministic", 4))
    budget = float(cfg.get("time_budget_s", 120))

    rows = []
    ok = True
    for s in payload["scenarios"]:
        case, q = s["case"], s["q"]
        milp = run_method("resource_milp", solve_resource_milp, case, q, reps, budget)
        greedy = run_method("greedy_quality", solve_greedy_quality, case, q, reps, budget)

        expected_status = s.get("expected_status")
        expected_obj = s.get("expected_objective")
        milp_status = milp["primary"]["status"]
        milp_obj = milp["primary"]["objective"]

        passed = True
        if expected_status == "infeasible":
            passed = milp_status == "infeasible"
        else:
            passed = milp_status in {"optimal", "feasible"}
            if expected_obj is not None:
                passed = passed and milp_obj is not None and abs(milp_obj - float(expected_obj)) <= 1e-8

        rows.append(
            {
                "scenario_id": s["scenario_id"],
                "expected_status": expected_status,
                "expected_objective": expected_obj,
                "resource_milp": milp,
                "greedy_quality": greedy,
                "passed": passed,
            }
        )
        ok = ok and passed

    journal = {
        "scope": "I4-K-07/08 control benchmark collection",
        "config_id": cfg.get("config_id"),
        "scenarios_sha256": sha,
        "python": platform.python_version(),
        "scipy": scipy.__version__,
        "platform": platform.platform(),
        "reps": reps,
        "time_budget_s": budget,
        "all_passed": ok,
        "n_scenarios": len(rows),
        "rows": rows,
    }
    OUT.write_text(json.dumps(journal, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"all_passed": ok, "out": str(OUT), "n": len(rows)}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
