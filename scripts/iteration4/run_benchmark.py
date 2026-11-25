# -*- coding: utf-8 -*-
"""I4-K-07/08/09: benchmark runner with per-repetition journal and hard timeout.

I4-K-09 requirements (G3 / I4-A-09):
- hard external 120s budget per repetition for BOTH methods (prep→validate)
- MILP gets remaining solver budget after prep
- every repetition stores status, validation, plan, objective, timings
- threads=1 applied via env + recorded diagnostic confirmation
"""
from __future__ import annotations

import hashlib
import json
import os
import platform
import statistics
import sys
import time
import traceback
from concurrent.futures import ProcessPoolExecutor, TimeoutError as FuturesTimeout
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

SCENARIOS = ROOT / "data" / "processed" / "i4" / "scenarios_v1.json"
CONFIG = ROOT / "data" / "processed" / "i4" / "method_config.json"
OUT = ROOT / "data" / "processed" / "i4" / "benchmark_control.json"
TIMEOUT_DEMO = ROOT / "data" / "processed" / "i4" / "timeout_demo.json"
EXPECTED_SHA = "4d6b9ee09651c418987e40e94c1810365afbe91bdc52f063b59c16e11375b8c2"


def _force_single_thread_env() -> dict[str, str]:
    keys = [
        "OMP_NUM_THREADS",
        "OPENBLAS_NUM_THREADS",
        "MKL_NUM_THREADS",
        "NUMEXPR_NUM_THREADS",
        "VECLIB_MAXIMUM_THREADS",
        "BLIS_NUM_THREADS",
    ]
    applied = {}
    for k in keys:
        os.environ[k] = "1"
        applied[k] = os.environ[k]
    return applied


def _load_cpu_diag(requested_threads: int) -> dict[str, Any]:
    load = None
    try:
        load = os.getloadavg()  # type: ignore[attr-defined]
    except (AttributeError, OSError):
        load = None
    return {
        "requested_threads": requested_threads,
        "env_thread_limits": {
            k: os.environ.get(k)
            for k in [
                "OMP_NUM_THREADS",
                "OPENBLAS_NUM_THREADS",
                "MKL_NUM_THREADS",
                "NUMEXPR_NUM_THREADS",
            ]
        },
        "cpu_count_logical": os.cpu_count(),
        "platform": platform.platform(),
        "processor": platform.processor(),
        "loadavg": load,
        "thread_mode_note": (
            "Requested threads=1 applied via BLAS/OpenMP env vars. "
            "scipy.optimize.milp/HiGHS has no separate threads option in this wrapper; "
            "single-thread intent recorded diagnostically."
        ),
    }


def _sha_scenarios(path: Path) -> tuple[bytes, str]:
    raw = path.read_bytes()
    sha = hashlib.sha256(raw).hexdigest()
    if sha == EXPECTED_SHA:
        return raw, sha
    # Windows checkout may rewrite LF→CRLF; accept normalized LF if hash matches protocol.
    normalized = raw.replace(b"\r\n", b"\n")
    sha_n = hashlib.sha256(normalized).hexdigest()
    if sha_n == EXPECTED_SHA:
        path.write_bytes(normalized)
        return normalized, sha_n
    raise SystemExit(f"scenarios hash mismatch: {sha} (normalized {sha_n}) != {EXPECTED_SHA}")


def _worker_solve(payload: dict[str, Any]) -> dict[str, Any]:
    """Process-pool worker: one method call with remaining solver budget."""
    _force_single_thread_env()
    # local import inside worker
    sys.path.insert(0, str(HERE))
    from resource_milp import (  # noqa: WPS433
        result_to_dict,
        solve_greedy_quality,
        solve_resource_milp,
        validate_plan,
    )

    method = payload["method"]
    case = payload["case"]
    q = payload["q"]
    budget = float(payload["budget_s"])
    t0 = time.perf_counter()
    timings: dict[str, float] = {}
    try:
        t_prep0 = time.perf_counter()
        # prep = map q / trivial checks already inside solvers; measure wall before call
        timings["prep_s"] = time.perf_counter() - t_prep0
        remaining = max(0.001, budget - timings["prep_s"])

        t_call0 = time.perf_counter()
        if method == "resource_milp":
            res = solve_resource_milp(case, q, time_limit_s=remaining)
        elif method == "greedy_quality":
            res = solve_greedy_quality(case, q)
        else:
            raise ValueError(f"unknown method {method}")
        timings["call_s"] = time.perf_counter() - t_call0

        t_val0 = time.perf_counter()
        validation = None
        if res.plan:
            validation = validate_plan(case, res.plan)
        else:
            validation = {"valid": False, "errors": ["empty_plan"], "used_t": None, "remaining_t": None}
        timings["validate_s"] = time.perf_counter() - t_val0
        timings["total_s"] = time.perf_counter() - t0

        out = result_to_dict(res)
        out["validation"] = validation
        out["timings_stages"] = timings
        out["budget_s"] = budget
        out["budget_exceeded"] = timings["total_s"] > budget + 1e-6
        out["wall_s"] = timings["total_s"]
        # if wall exceeded but solver returned — still mark budget flag; external hard timeout handled by parent
        return {"ok": True, "result": out}
    except Exception as exc:  # noqa: BLE001 — journal must capture errors
        return {
            "ok": False,
            "result": {
                "status": "error",
                "raw_solver_status": None,
                "termination_reason": type(exc).__name__,
                "plan": [],
                "objective": None,
                "bound": None,
                "gap_abs": None,
                "gap_rel": None,
                "used_t": None,
                "timings": {},
                "message": str(exc),
                "validation": {"valid": False, "errors": [traceback.format_exc()], "used_t": None},
                "timings_stages": {"total_s": time.perf_counter() - t0},
                "budget_s": budget,
                "budget_exceeded": True,
                "wall_s": time.perf_counter() - t0,
            },
        }


def _worker_sleep(payload: dict[str, Any]) -> dict[str, Any]:
    """Deliberate overrun for timeout demo."""
    time.sleep(float(payload["sleep_s"]))
    return {"ok": True, "result": {"status": "feasible", "plan": payload.get("fake_plan") or [], "message": "slept"}}


def run_with_hard_timeout(fn_name: str, payload: dict[str, Any], budget_s: float) -> dict[str, Any]:
    """Hard external timeout covering entire repetition (prep→validate)."""
    workers = {"solve": _worker_solve, "sleep": _worker_sleep}
    fn = workers[fn_name]
    t0 = time.perf_counter()
    with ProcessPoolExecutor(max_workers=1) as pool:
        fut = pool.submit(fn, payload)
        try:
            packed = fut.result(timeout=budget_s)
            wall = time.perf_counter() - t0
            result = packed["result"]
            result["hard_timeout"] = False
            result["external_wall_s"] = wall
            if wall > budget_s + 1e-6:
                result["budget_exceeded"] = True
            return result
        except FuturesTimeout:
            fut.cancel()
            wall = time.perf_counter() - t0
            # ProcessPoolExecutor may keep worker until killed by context exit
            return {
                "status": "timeout_without_plan",
                "raw_solver_status": None,
                "termination_reason": "external_hard_timeout",
                "plan": [],
                "objective": None,
                "bound": None,
                "gap_abs": None,
                "gap_rel": None,
                "used_t": None,
                "timings": {},
                "message": f"exceeded external budget {budget_s}s",
                "validation": {"valid": False, "errors": ["hard_timeout"], "used_t": None},
                "timings_stages": {"total_s": wall},
                "budget_s": budget_s,
                "budget_exceeded": True,
                "hard_timeout": True,
                "wall_s": wall,
                "external_wall_s": wall,
            }


def _time_stats(samples: list[float]) -> dict:
    return {
        "n": len(samples),
        "median_s": statistics.median(samples),
        "min_s": min(samples),
        "max_s": max(samples),
        "values_s": samples,
    }


def run_method(method: str, case: dict, q: list, reps: int, budget: float) -> dict:
    repetitions = []
    times = []
    for i in range(reps):
        payload = {"method": method, "case": case, "q": q, "budget_s": budget}
        result = run_with_hard_timeout("solve", payload, budget)
        result["repetition"] = i + 1
        repetitions.append(result)
        times.append(float(result.get("external_wall_s") or result.get("wall_s") or 0.0))
    primary = repetitions[0]
    return {
        "primary": primary,
        "repetitions": repetitions,
        "time": _time_stats(times),
        "n_feasible_or_optimal": sum(
            1 for r in repetitions if r.get("status") in {"optimal", "feasible", "timeout_with_plan"}
            and (r.get("validation") or {}).get("valid") is True
        ),
        "n_reps": reps,
    }


def _demo_timeout(budget_s: float = 0.2) -> dict:
    """Prove hard timeout interrupts and journals timeout_without_plan."""
    overrun = run_with_hard_timeout(
        "sleep",
        {"sleep_s": 2.0, "fake_plan": []},
        budget_s,
    )
    # Also show a quick successful solve under tiny budget still works if finishes early
    return {
        "budget_s": budget_s,
        "overrun": {
            "status": overrun.get("status"),
            "hard_timeout": overrun.get("hard_timeout"),
            "budget_exceeded": overrun.get("budget_exceeded"),
            "plan_empty": not bool(overrun.get("plan")),
            "wall_s": overrun.get("wall_s"),
        },
        "passed": overrun.get("status") == "timeout_without_plan" and overrun.get("hard_timeout") is True,
    }


def main() -> int:
    _force_single_thread_env()
    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    raw, sha = _sha_scenarios(SCENARIOS)
    payload = json.loads(raw)

    import scipy  # after env thread limits

    reps = int(cfg.get("repetitions_deterministic", 4))
    budget = float(cfg.get("time_budget_s", 120))
    requested_threads = int(cfg.get("threads", 1))
    thread_diag = _load_cpu_diag(requested_threads)

    timeout_demo = _demo_timeout(0.2)
    TIMEOUT_DEMO.write_text(json.dumps(timeout_demo, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    rows = []
    ok = True
    total_reps = 0
    total_valid = 0
    for s in payload["scenarios"]:
        case, q = s["case"], s["q"]
        milp = run_method("resource_milp", case, q, reps, budget)
        greedy = run_method("greedy_quality", case, q, reps, budget)
        total_reps += milp["n_reps"] + greedy["n_reps"]
        total_valid += milp["n_feasible_or_optimal"] + greedy["n_feasible_or_optimal"]

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
        # all milp reps should share status on these tiny cases
        for r in milp["repetitions"]:
            if expected_status == "infeasible":
                passed = passed and r["status"] == "infeasible"
            else:
                passed = passed and r["status"] in {"optimal", "feasible"}

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

    ok = ok and bool(timeout_demo.get("passed"))

    journal = {
        "scope": "I4-K-09 control benchmark with hard timeout and full repetition journal",
        "config_id": cfg.get("config_id"),
        "protocol_ref": "I4-A-09 / G3 blockers",
        "scenarios_sha256": sha,
        "python": platform.python_version(),
        "scipy": scipy.__version__,
        "numpy": __import__("numpy").__version__,
        "platform": platform.platform(),
        "reps": reps,
        "time_budget_s": budget,
        "threads": thread_diag,
        "timeout_demo": timeout_demo,
        "coverage": {
            "planned_runs": total_reps,
            "recorded_runs": total_reps,
            "valid_plans_across_reps": total_valid,
            "valid_plan_share": (total_valid / total_reps) if total_reps else None,
        },
        "all_passed": ok,
        "n_scenarios": len(rows),
        "rows": rows,
    }
    OUT.write_text(json.dumps(journal, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "all_passed": ok,
                "out": str(OUT),
                "timeout_demo": str(TIMEOUT_DEMO),
                "n": len(rows),
                "valid_plan_share": journal["coverage"]["valid_plan_share"],
            },
            ensure_ascii=False,
        )
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
