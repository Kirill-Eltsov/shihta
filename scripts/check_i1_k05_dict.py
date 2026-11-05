"""I1-K-05: compare keys.md expectations to raw Excel columns."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
OUT = ROOT / "docs" / "iteration1" / "I1-K-05_dict_notes.md"
MONTH = "март 2022"

CHECKS = [
    ("Заказы.xls", MONTH, ["Марка массы, код"]),
    ("Шихта.xls", MONTH, ["Марка массы, код", "Номер шихты", "Компонент, код"]),
    ("Линии дозирования.xls", MONTH, ["Марка массы, код", "Номер шихты", "Распоряжение, код", "Компонент, код"]),
    ("Прессовка.xls", MONTH, ["Распоряжение, код", "№ шихты"]),
    ("Подача порошков.xls", MONTH, ["nMaterialId"]),
]


def main() -> int:
    lines: list[str] = [
        "# I1-K-05 — Замечания к словарю по исходным таблицам",
        "",
        "Исполнитель: Кирилл Ельцов  ",
        "База словаря: `docs/keys.md` (технический) + фактические заголовки XLS.",
        "",
        "## Метод",
        f"Лист проверки: `{MONTH}`. Для каждого ожидаемого поля — файл, лист, пример значения.",
        "",
        "## Проверки полей и ключей",
        "",
    ]

    questions: list[str] = []

    for fname, sheet, fields in CHECKS:
        path = RAW / fname
        df = pd.read_excel(path, sheet_name=sheet, engine="xlrd")
        cols = list(df.columns.astype(str))
        lines.append(f"### {fname} / `{sheet}`")
        lines.append("")
        lines.append(f"Колонок в листе: {len(cols)}")
        lines.append("")
        for field in fields:
            if field in df.columns:
                sample = df[field].dropna().head(1)
                sample_val = sample.iloc[0] if len(sample) else None
                # find first row index with value
                idx = int(sample.index[0]) + 2 if len(sample) else None  # +2 ~ excel-ish with header
                lines.append(
                    f"- **OK** `{field}` — пример строки ~{idx}: `{sample_val}`"
                )
            else:
                # fuzzy: contains
                fuzzy = [c for c in cols if field.lower() in c.lower() or c.lower() in field.lower()]
                lines.append(f"- **MISS** `{field}` — точного заголовка нет. Похожие: {fuzzy[:5]}")
                questions.append(f"{fname}/{sheet}: нет точного поля `{field}`")
        lines.append("")

    # CSV keys presence
    lines.append("## Согласованность processed CSV с keys.md")
    lines.append("")
    for csv_name, need in (
        ("zakazy.csv", ["order_id", "mass_code"]),
        ("recepty.csv", ["mass_code", "shikhta_num", "powder_code", "order_code"]),
        ("kachestvo.csv", ["mass_code", "shikhta_num", "press_yield", "has_press_history"]),
    ):
        df = pd.read_csv(ROOT / "data" / "processed" / csv_name)
        missing = [c for c in need if c not in df.columns]
        if missing:
            lines.append(f"- **MISS** `{csv_name}`: нет {missing}")
            questions.append(f"CSV {csv_name}: отсутствуют {missing}")
        else:
            lines.append(f"- **OK** `{csv_name}`: поля {need} на месте (строк {len(df)})")
    lines.append("")

    lines.append("## Противоречия и вопросы Алексею (без догадок)")
    lines.append("")
    lines.append(
        "1. В `Линии дозирования.xls` и `Проценты.xls` имя листа апреля = `аперль 2022` (опечатка) — подтвердить, что это официальный ярлык, а не другой период."
    )
    lines.append(
        "2. Пересечение `powder_code` (рецепты) и `nMaterialId` (подача) = 13 из 96/125 — полное соответствие материалов **не подтверждено**; нужен аналитический разбор (A), не техническая склейка вслепую."
    )
    lines.append(
        "3. Полный организационный словарь критичных полей предприятия (I1-A-03…05) в репозитории отсутствует — техническая сверка сделана по `keys.md` и факту заголовков XLS."
    )
    if questions:
        lines.append("4. Дополнительно из автопроверки:")
        for q in questions:
            lines.append(f"   - {q}")
    lines.append("")
    lines.append("## Критерии I1-K-05")
    lines.append("")
    lines.append("- [x] Замечания привязаны к файлу и листу.")
    lines.append("- [x] Неизвестные соответствия записаны как вопросы, без угадывания.")
    lines.append("")
    lines.append("## Как проверить")
    lines.append("")
    lines.append("```bash")
    lines.append("python scripts/check_i1_k05_dict.py")
    lines.append("```")
    lines.append("")

    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
