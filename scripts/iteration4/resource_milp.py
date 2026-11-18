# -*- coding: utf-8 -*-
"""I4-K: resource-constrained assignment MILP + one greedy control.

Contract aligned with alexey/iteration4/scenarios_v1.json and model_spec:
- one recipe per order
- resource balance stocks
- objective max sum demand * q (explicit q only; no silent 0.5 fallback)
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from math import isfinite
from typing import Any

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp


@dataclass
class SolveResult:
    status: str
    raw_solver_status: int | None
    termination_reason: str | None
    plan: list[dict[str, str]]
    objective: float | None
    bound: float | None
    gap_abs: float | None
    gap_rel: float | None
    used_t: dict[str, float] | None
    timings: dict[str, float]
    message: str | None = None


def _q_map(q_rows: list[dict[str, Any]] | dict[tuple[str, str], float]) -> dict[tuple[str, str], float]:
    if isinstance(q_rows, dict):
        return {(str(o), str(r)): float(v) for (o, r), v in q_rows.items()}
    out: dict[tuple[str, str], float] = {}
    for row in q_rows:
        key = (str(row["order_id"]), str(row["recipe_id"]))
        val = float(row["value"])
        if not isfinite(val):
            raise ValueError(f"nonfinite q for {key}")
        out[key] = val
    return out


def _usage(case: dict, order_id: str, recipe_id: str, component: str) -> float:
    demand = float(case["orders"][order_id]["demand_t"])
    coef = float(case["recipes"][recipe_id]["usage_t_per_t"].get(component, 0.0))
    return demand * coef


def validate_plan(case: dict, plan: list[dict[str, str]], atol: float = 1e-8, rtol: float = 1e-9) -> dict:
    """Independent validator (same rules as alexey/validate_plan.py)."""
    from collections import Counter

    errors: list[str] = []
    orders, recipes, stocks = case["orders"], case["recipes"], case["stocks"]
    counts = Counter(row["order_id"] for row in plan)
    for oid in orders:
        if counts[oid] != 1:
            errors.append(f"order_count:{oid}:{counts[oid]}")
    used = {c: 0.0 for c in stocks}
    for row in plan:
        oid, rid = str(row["order_id"]), str(row["recipe_id"])
        if oid not in orders:
            errors.append(f"unknown_order:{oid}")
            continue
        if rid not in orders[oid]["candidates"] or rid not in recipes:
            errors.append(f"forbidden_recipe:{oid}:{rid}")
            continue
        demand = float(orders[oid]["demand_t"])
        if not isfinite(demand) or demand <= 0:
            raise ValueError("demand_t must be finite and positive")
        for c, a in recipes[rid]["usage_t_per_t"].items():
            if not isfinite(a) or a < 0:
                raise ValueError("Invalid usage coefficient")
            if c not in stocks:
                errors.append(f"missing_stock:{c}")
                continue
            used[c] += demand * float(a)
    for c, stock in stocks.items():
        if not isfinite(stock) or stock < 0:
            raise ValueError("Invalid stock")
        if used[c] > stock + atol + rtol * abs(stock):
            errors.append(f"stock_exceeded:{c}")
    return {
        "valid": not errors,
        "errors": errors,
        "used_t": used,
        "remaining_t": {c: stocks[c] - used[c] for c in stocks},
    }


def score_plan(case: dict, plan: list[dict[str, str]], q: dict[tuple[str, str], float]) -> float:
    from math import fsum

    check = validate_plan(case, plan)
    if not check["valid"]:
        raise ValueError("Invalid plan: " + "; ".join(check["errors"]))
    terms = []
    for row in plan:
        key = (str(row["order_id"]), str(row["recipe_id"]))
        if key not in q or not isfinite(q[key]):
            raise ValueError(f"Missing/nonfinite q for {key}")
        terms.append(float(case["orders"][key[0]]["demand_t"]) * q[key])
    return fsum(terms)


def solve_resource_milp(
    case: dict,
    q_rows: list[dict[str, Any]] | dict[tuple[str, str], float],
    *,
    time_limit_s: float | None = 120.0,
) -> SolveResult:
    """Primary method (G2): MILP with resource constraints."""
    t0 = time.perf_counter()
    q = _q_map(q_rows)
    pairs: list[tuple[str, str]] = []
    for oid, meta in case["orders"].items():
        for rid in meta["candidates"]:
            key = (str(oid), str(rid))
            if key not in q:
                raise ValueError(f"explicit q required for {key}; silent fallback forbidden")
            pairs.append(key)

    t_build0 = time.perf_counter()
    matrix: list[list[float]] = []
    lb: list[float] = []
    ub: list[float] = []
    for oid in case["orders"]:
        matrix.append([1.0 if oo == oid else 0.0 for oo, _rid in pairs])
        lb.append(1.0)
        ub.append(1.0)
    for component, stock in case["stocks"].items():
        matrix.append([_usage(case, oo, rid, component) for oo, rid in pairs])
        lb.append(-np.inf)
        ub.append(float(stock))
    c = -np.array([float(case["orders"][o]["demand_t"]) * q[(o, r)] for o, r in pairs], dtype=float)
    t_build = time.perf_counter() - t_build0

    options = {}
    if time_limit_s is not None:
        options["time_limit"] = float(time_limit_s)

    t_sol0 = time.perf_counter()
    res = milp(
        c=c,
        integrality=np.ones(len(pairs)),
        bounds=Bounds(0, 1),
        constraints=LinearConstraint(np.array(matrix, dtype=float), lb, ub),
        options=options or None,
    )
    t_solve = time.perf_counter() - t_sol0

    plan: list[dict[str, str]] = []
    if res.x is not None:
        plan = [{"order_id": o, "recipe_id": r} for (o, r), x in zip(pairs, res.x) if x > 0.5]

    # scipy milp: status 0 success; 1 iteration/time limit; 2 infeasible; ...
    raw = int(res.status) if res.status is not None else None
    obj = None
    bound = None
    gap_abs = None
    gap_rel = None
    used = None
    status = "error"
    reason = res.message

    if raw == 2:
        status = "infeasible"
        plan = []
    elif plan:
        v = validate_plan(case, plan)
        if not v["valid"]:
            status = "invalid_plan"
            obj = None
        else:
            obj = score_plan(case, plan, q)
            used = v["used_t"]
            # dual bound for maximization: U = -mip_dual_bound when minimizing -F
            dual = getattr(res, "mip_dual_bound", None)
            if dual is not None and isfinite(dual):
                bound = float(-dual)
                gap_abs = bound - obj
                if abs(gap_abs) < 1e-8:
                    gap_abs = 0.0
                gap_rel = gap_abs / max(abs(obj), 1e-9)
            if raw == 0 and (gap_abs is None or gap_abs <= 1e-8):
                status = "optimal"
            elif raw == 1:
                status = "timeout_with_plan"
            else:
                status = "feasible"
    else:
        if raw == 1:
            status = "timeout_without_plan"
        else:
            status = "no_solution_found"

    return SolveResult(
        status=status,
        raw_solver_status=raw,
        termination_reason=str(reason) if reason is not None else None,
        plan=plan,
        objective=obj,
        bound=bound,
        gap_abs=gap_abs,
        gap_rel=gap_rel,
        used_t=used,
        timings={
            "build_s": t_build,
            "solve_s": t_solve,
            "total_s": time.perf_counter() - t0,
        },
        message=str(reason) if reason is not None else None,
    )


def solve_greedy_quality(
    case: dict,
    q_rows: list[dict[str, Any]] | dict[tuple[str, str], float],
) -> SolveResult:
    """Control method (G2): deterministic greedy by quality, then feasibility repair."""
    t0 = time.perf_counter()
    q = _q_map(q_rows)
    # initial: for each order pick highest-q candidate
    plan = []
    for oid, meta in case["orders"].items():
        cands = list(meta["candidates"])
        for rid in cands:
            if (str(oid), str(rid)) not in q:
                raise ValueError(f"explicit q required for {(oid, rid)}")
        best = max(cands, key=lambda rid: q[(str(oid), str(rid))])
        plan.append({"order_id": str(oid), "recipe_id": str(best)})

    check = validate_plan(case, plan)
    if not check["valid"]:
        # simple repair: try swapping orders with stock violations to next-best q
        order_ids = [row["order_id"] for row in plan]
        improved = list(plan)
        for _ in range(len(order_ids) * 3):
            check = validate_plan(case, improved)
            if check["valid"]:
                break
            # drop one violated order to next candidate by q
            for i, row in enumerate(improved):
                oid = row["order_id"]
                cands = sorted(
                    case["orders"][oid]["candidates"],
                    key=lambda rid: q[(oid, str(rid))],
                    reverse=True,
                )
                cur = row["recipe_id"]
                if cur in cands:
                    idx = cands.index(cur)
                    if idx + 1 < len(cands):
                        improved[i] = {"order_id": oid, "recipe_id": str(cands[idx + 1])}
                        break
            else:
                break
        plan = improved
        check = validate_plan(case, plan)

    if not check["valid"]:
        return SolveResult(
            status="no_solution_found",
            raw_solver_status=None,
            termination_reason="greedy_no_feasible",
            plan=[],
            objective=None,
            bound=None,
            gap_abs=None,
            gap_rel=None,
            used_t=None,
            timings={"total_s": time.perf_counter() - t0},
            message="; ".join(check["errors"]),
        )

    obj = score_plan(case, plan, q)
    return SolveResult(
        status="feasible",
        raw_solver_status=None,
        termination_reason="greedy_quality",
        plan=plan,
        objective=obj,
        bound=None,
        gap_abs=None,
        gap_rel=None,
        used_t=check["used_t"],
        timings={"total_s": time.perf_counter() - t0},
    )


def result_to_dict(res: SolveResult) -> dict[str, Any]:
    return {
        "status": res.status,
        "raw_solver_status": res.raw_solver_status,
        "termination_reason": res.termination_reason,
        "plan": res.plan,
        "objective": res.objective,
        "bound": res.bound,
        "gap_abs": res.gap_abs,
        "gap_rel": res.gap_rel,
        "used_t": res.used_t,
        "timings": res.timings,
        "message": res.message,
    }
