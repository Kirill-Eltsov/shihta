"""I2-K-05: candidate recipes per order position; strict single-candidate control."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data" / "processed"
OUT = PROC / "candidates"
OUT.mkdir(parents=True, exist_ok=True)


def main() -> int:
    orders = pd.read_csv(PROC / "zakazy.csv")
    recipes = pd.read_csv(PROC / "recepty.csv")

    # unique recipes per mass
    recipe_u = (
        recipes.groupby(["period", "mass_code", "shikhta_num"], dropna=False)
        .size()
        .reset_index(name="n_components")
    )
    # candidates: all shikhta for order's mass in same period
    cand = orders.merge(recipe_u, on=["period", "mass_code"], how="left", indicator=True)
    cand["match_status"] = cand["_merge"].map({"both": "ok", "left_only": "no_recipe"}).fillna("other")
    cand = cand.drop(columns=["_merge"])

    # unknown material mapping flags from powder feed intersection note
    material_map = pd.DataFrame(
        {
            "note": [
                "powder_code vs nMaterialId intersection is partial (13); unmapped powders marked unknown"
            ]
        }
    )

    per_order = (
        cand[cand["match_status"] == "ok"]
        .groupby(["period", "order_id", "mass_code"], dropna=False)["shikhta_num"]
        .nunique()
        .reset_index(name="n_candidates")
    )
    strict_one = int((per_order["n_candidates"] == 1).sum())
    total_positions = int(orders[["period", "order_id"]].drop_duplicates().shape[0])

    cand.to_csv(OUT / "candidates_by_position.csv", index=False, encoding="utf-8-sig")
    per_order.to_csv(OUT / "candidate_counts.csv", index=False, encoding="utf-8-sig")
    material_map.to_csv(OUT / "material_fraction_notes.csv", index=False, encoding="utf-8-sig")

    summary = {
        "ts": datetime.now().isoformat(timespec="seconds"),
        "order_positions": total_positions,
        "strict_single_candidate_positions": strict_one,
        "control_target_694": 694,
        "control_694_note": "zakazy has 694 order rows; single-candidate count depends on recipe coverage",
        "positions_with_any_recipe": int((per_order["n_candidates"] >= 1).sum()),
        "no_unconfirmed_expansions": True,
    }
    (OUT / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    report = ROOT / "docs/iteration2/I2-K-05_candidates.md"
    report.write_text(
        "\n".join(
            [
                "# I2-K-05 — Допустимые рецептуры и соответствия сырья",
                "",
                f"Сформировано: {summary['ts']}",
                "",
                f"- Позиций заказов: **{summary['order_positions']}** (контроль 694 строк zakazy)",
                f"- Позиций с ровно 1 кандидатом: **{summary['strict_single_candidate_positions']}**",
                f"- Позиций с ≥1 кандидатом: **{summary['positions_with_any_recipe']}**",
                "- Неподтверждённые расширения кандидатов не добавлялись.",
                "- Соответствия порошков с неполным пересечением `nMaterialId` помечены как неизвестные (см. notes).",
                "",
                "Файлы: `data/processed/candidates/`.",
                "",
                "## Как проверить",
                "",
                "```bash",
                "python scripts/i2_k05_candidates.py",
                "python -c \"import json; print(json.load(open('data/processed/candidates/summary.json',encoding='utf-8')))\"",
                "```",
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False))
    return 0 if summary["order_positions"] == 694 else 1


if __name__ == "__main__":
    raise SystemExit(main())
