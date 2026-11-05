"""I2-K-06: executable assignment MILP on prepared CSV (educational March slice)."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import Bounds, LinearConstraint, milp

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data" / "processed"
OUT = PROC / "milp"
OUT.mkdir(parents=True, exist_ok=True)


def main() -> int:
    period = "2022-03"
    orders = pd.read_csv(PROC / "zakazy.csv")
    recipes = pd.read_csv(PROC / "recepty.csv")
    quality = pd.read_csv(PROC / "kachestvo.csv")

    orders = orders[orders["period"] == period].copy()
    recipes = recipes[recipes["period"] == period].copy()
    quality = quality[quality["period"] == period].copy()
    orders = orders.sort_values("demand_t", ascending=False).head(25)

    recipe_u = recipes[["mass_code", "shikhta_num"]].drop_duplicates()
    qmap = quality.set_index(["mass_code", "shikhta_num"])["q2_press_yield"].to_dict()

    pairs: list[tuple[int, int, int, float, float]] = []
    for _, o in orders.iterrows():
        cands = recipe_u[recipe_u["mass_code"] == o["mass_code"]]["shikhta_num"].tolist()
        for sn in cands:
            q = qmap.get((o["mass_code"], sn))
            if pd.isna(q):
                q = 0.5
            pairs.append((int(o["order_id"]), int(o["mass_code"]), int(sn), float(o["demand_t"]), float(q)))

    n = len(pairs)
    c = -np.array([dem * q for *_, dem, q in pairs], dtype=float)  # maximize -> minimize negative
    # one recipe per order
    order_ids = sorted({p[0] for p in pairs})
    A = np.zeros((len(order_ids), n))
    for j, (oid, *_rest) in enumerate(pairs):
        A[order_ids.index(oid), j] = 1.0
    constraints = LinearConstraint(A, lb=np.ones(len(order_ids)), ub=np.ones(len(order_ids)))
    bounds = Bounds(lb=np.zeros(n), ub=np.ones(n))

    res = milp(c=c, constraints=constraints, bounds=bounds, integrality=np.ones(n))
    assign = []
    if res.success and res.x is not None:
        for j, (oid, mc, sn, dem, q) in enumerate(pairs):
            if res.x[j] > 0.5:
                assign.append(
                    {"order_id": oid, "mass_code": mc, "shikhta_num": sn, "demand_t": dem, "q_used": q}
                )

    result = {
        "ts": datetime.now().isoformat(timespec="seconds"),
        "period": period,
        "n_orders": int(len(orders)),
        "n_vars": n,
        "status": "Optimal" if res.success else str(res.message),
        "objective": float(-res.fun) if res.success else None,
        "solver": "scipy.optimize.milp (HiGHS)",
        "data_separation": "educational March slice from processed CSV; not mixed with Colab notebook outputs",
        "model_basis": "assignment MILP: one recipe per order; obj = sum demand*q; q2 or fallback 0.5",
        "awaiting_A_model_spec": True,
    }
    pd.DataFrame(assign).to_csv(OUT / "edu_assign.csv", index=False, encoding="utf-8-sig")
    (OUT / "edu_solve.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    report = ROOT / "docs/iteration2/I2-K-06_milp.md"
    report.write_text(
        "\n".join(
            [
                "# I2-K-06 — Исполняемая MILP по подготовленным входам",
                "",
                f"Сформировано: {result['ts']}",
                "",
                f"- Период: {period}, заказов в срезе: {result['n_orders']}, переменных: {result['n_vars']}",
                f"- Статус: **{result['status']}**, objective={result['objective']}",
                f"- Solver: {result['solver']}",
                "- Учебные/processed CSV отделены от Colab-путей notebook Данила.",
                "- Полный промышленный model_spec от A ещё ожидается (`awaiting_A_model_spec=true`).",
                "",
                "## Как проверить",
                "",
                "```bash",
                "python scripts/i2_k06_milp.py",
                "python -c \"import json; print(json.load(open('data/processed/milp/edu_solve.json',encoding='utf-8')))\"",
                "```",
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(json.dumps(result, ensure_ascii=False))
    return 0 if res.success else 1


if __name__ == "__main__":
    raise SystemExit(main())
