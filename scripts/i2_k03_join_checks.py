"""I2-K-03: row-count and join diagnostics; references must not become events."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
LOADER_REG = ROOT / "data" / "processed" / "loader" / "registry.json"
NORM = ROOT / "data" / "processed" / "normalized"
OUT = ROOT / "docs" / "iteration2" / "I2-K-03_join_checks.md"


def main() -> int:
    reg = json.loads(LOADER_REG.read_text(encoding="utf-8"))
    assert reg["loaded_sheets"] == 36, reg["loaded_sheets"]

    # March events for join probe
    orders = pd.read_csv(NORM / "Заказы__март_2022__events.csv")
    shihta = pd.read_csv(NORM / "Шихта__март_2022__events.csv")
    lines = pd.read_csv(NORM / "Линии дозирования__март_2022__events.csv")

    n_orders = len(orders)
    n_shihta = len(shihta)
    # recipes uniqueness by mass+shikhta (reference), not exploded as new events
    recipe_keys = shihta.groupby(["Марка массы, код", "Номер шихты"], dropna=False).size().reset_index(name="n_comp")
    # join orders to recipe existence (left) — should not multiply order rows if we aggregate recipes first
    orders_u = orders.drop_duplicates(subset=["src_row"])  # already event rows
    has_recipe = orders_u.merge(
        recipe_keys[["Марка массы, код", "Номер шихты"]].drop_duplicates().assign(_has=1),
        left_on="Марка массы, код",
        right_on="Марка массы, код",
        how="left",
    )
    # Wrong join demo avoided: we only flag masses with >=1 recipe, without expanding components onto orders
    mass_with_recipes = set(recipe_keys["Марка массы, код"].unique())
    orders_with = orders_u["Марка массы, код"].isin(mass_with_recipes).sum()

    # lines vs press bridge keys
    press = pd.read_csv(NORM / "Прессовка__март_2022__events.csv")
    # treat lines mass+shikhta as events, recipe dict as reference
    lines_before = len(lines)
    lines_after_dedupe_ref = lines.drop_duplicates(subset=["Марка массы, код", "Номер шихты", "Компонент, код", "src_row"])
    multiply_risk = len(lines_after_dedupe_ref) != lines_before

    journal = {
        "ts": datetime.now().isoformat(timespec="seconds"),
        "sheets_accounted": reg["loaded_sheets"],
        "march": {
            "orders_events": int(n_orders),
            "shihta_component_rows": int(n_shihta),
            "recipe_keys": int(len(recipe_keys)),
            "orders_with_any_recipe_mass": int(orders_with),
            "lines_events": int(lines_before),
            "press_events": int(len(press)),
            "lines_row_multiply_on_self_dedupe": bool(multiply_risk),
        },
        "rules": [
            "all 36 sheets listed in loader registry",
            "recipe component rows are reference, not new demand events",
            "order↔recipe checked at mass level without exploding components onto orders",
        ],
    }
    (NORM / "join_journal.json").write_text(json.dumps(journal, ensure_ascii=False, indent=2), encoding="utf-8")

    lines_md = [
        "# I2-K-03 — Проверки объединений, пропусков и справочников",
        "",
        f"Сформировано: {journal['ts']}",
        "",
        f"- Учтено листов загрузчика: **{journal['sheets_accounted']} / 36**",
        f"- Заказы (март, events): {journal['march']['orders_events']}",
        f"- Шихта component rows (март): {journal['march']['shihta_component_rows']}",
        f"- Уникальных ключей рецепта (марка+шихта): {journal['march']['recipe_keys']}",
        f"- Заказов с маркой, у которой есть рецепт: {journal['march']['orders_with_any_recipe_mass']}",
        f"- Линии events: {journal['march']['lines_events']}",
        f"- Прессовка events: {journal['march']['press_events']}",
        "",
        "Справочник рецептов не разворачивался в новые события спроса.",
        "Журнал: `data/processed/normalized/join_journal.json`.",
        "",
        "## Как проверить",
        "",
        "```bash",
        "python scripts/i2_k03_join_checks.py",
        "python -c \"import json; j=json.load(open('data/processed/normalized/join_journal.json',encoding='utf-8')); print(j['sheets_accounted'], j['march'])\"",
        "```",
        "",
    ]
    OUT.write_text("\n".join(lines_md), encoding="utf-8")
    print(json.dumps(journal["march"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
