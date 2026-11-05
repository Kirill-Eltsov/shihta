"""I2-K-08: compare MILP vs full enumeration on a tiny toy instance (8 variants)."""
from __future__ import annotations

import itertools
import json
from datetime import datetime
from pathlib import Path

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "processed" / "milp"


def enumerate_best(orders, recipes, q):
    # recipes: order_index -> list of recipe indices
    best_obj = -1e18
    best = None
    for choice in itertools.product(*[range(len(recipes[i])) for i in range(len(orders))]):
        obj = 0.0
        plan = []
        for oi, ri in enumerate(choice):
            r = recipes[oi][ri]
            obj += orders[oi] * q[oi][ri]
            plan.append(r)
        if obj > best_obj:
            best_obj = obj
            best = plan
    return best_obj, best


def milp_best(orders, recipes, q):
    pairs = []
    for oi, dem in enumerate(orders):
        for ri, r in enumerate(recipes[oi]):
            pairs.append((oi, ri, dem, q[oi][ri], r))
    n = len(pairs)
    c = -np.array([dem * qq for _, _, dem, qq, _ in pairs], dtype=float)
    A = np.zeros((len(orders), n))
    for j, (oi, *_rest) in enumerate(pairs):
        A[oi, j] = 1.0
    res = milp(
        c=c,
        constraints=LinearConstraint(A, np.ones(len(orders)), np.ones(len(orders))),
        bounds=Bounds(0, 1),
        integrality=np.ones(n),
    )
    plan = [None] * len(orders)
    obj = 0.0
    if res.success:
        for j, (oi, ri, dem, qq, r) in enumerate(pairs):
            if res.x[j] > 0.5:
                plan[oi] = r
                obj += dem * qq
    return float(-res.fun) if res.success else None, plan, res.success


def validate_plan(plan, n_orders):
    return plan is not None and len(plan) == n_orders and all(p is not None for p in plan)


def main() -> int:
    # Toy: 3 orders, candidates giving 2*2*2 = 8 variants
    orders = [10.0, 5.0, 7.0]
    recipes = [["A1", "A2"], ["B1", "B2"], ["C1", "C2"]]
    q = [[0.9, 0.4], [0.8, 0.7], [0.6, 0.95]]

    enum_obj, enum_plan = enumerate_best(orders, recipes, q)
    milp_obj, milp_plan, ok = milp_best(orders, recipes, q)
    same_obj = ok and abs(enum_obj - milp_obj) < 1e-6
    valid = validate_plan(milp_plan, len(orders))

    result = {
        "ts": datetime.now().isoformat(timespec="seconds"),
        "toy_variants": 8,
        "enum_objective": enum_obj,
        "milp_objective": milp_obj,
        "objectives_match": same_obj,
        "validate_plan_ok": valid,
        "enum_plan": enum_plan,
        "milp_plan": milp_plan,
        "note": "Independent toy check; industrial Danila baseline still blocked locally",
    }
    (OUT / "validate_toy.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    report = ROOT / "docs/iteration2/I2-K-08_validate.md"
    report.write_text(
        "\n".join(
            [
                "# I2-K-08 — Сопоставление MILP с перебором и валидатором",
                "",
                f"Сформировано: {result['ts']}",
                "",
                f"- Учебный пример: **{result['toy_variants']}** вариантов",
                f"- Enum obj={result['enum_objective']}, MILP obj={result['milp_objective']}, match={result['objectives_match']}",
                f"- validate_plan: {result['validate_plan_ok']}",
                "",
                "## Как проверить",
                "",
                "```bash",
                "python scripts/i2_k08_validate.py",
                "```",
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(json.dumps(result, ensure_ascii=False))
    return 0 if same_obj and valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
