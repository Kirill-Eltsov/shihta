"""I2-K-02: normalize key tables; separate event rows from totals; keep provenance."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
LOADER = ROOT / "data" / "processed" / "loader"
OUT = ROOT / "data" / "processed" / "normalized"
OUT.mkdir(parents=True, exist_ok=True)

# Key columns used to detect empty-key "glue" and summary-like rows
SPECS = {
    "Заказы": ["Марка массы, код"],
    "Шихта": ["Марка массы, код", "Номер шихты", "Компонент, код"],
    "Линии дозирования": ["Марка массы, код", "Номер шихты", "Компонент, код"],
    "Прессовка": ["Распоряжение, код", "№ шихты"],
    "Подача порошков": ["nMaterialId"],
}


def classify(df: pd.DataFrame, key_cols: list[str]) -> pd.Series:
    """event = all keys present; total_or_incomplete = any key missing."""
    present = pd.Series(True, index=df.index)
    for c in key_cols:
        if c not in df.columns:
            present &= False
        else:
            present &= df[c].notna() & (df[c].astype(str).str.strip() != "")
    return present.map({True: "event", False: "total_or_incomplete"})


def main() -> int:
    transforms: list[dict] = []
    for csv_path in sorted(LOADER.glob("*.csv")):
        book = csv_path.name.split("__")[0]
        if book not in SPECS:
            continue
        df = pd.read_csv(csv_path)
        keys = SPECS[book]
        kind = classify(df, keys)
        df = df.copy()
        df["row_kind"] = kind
        # Do NOT join/merge rows that miss keys together
        events = df[df["row_kind"] == "event"].copy()
        other = df[df["row_kind"] != "event"].copy()
        sheet = str(df["src_sheet"].iloc[0]) if len(df) else ""
        base = f"{book}__{sheet.replace(' ', '_')}"
        events_path = OUT / f"{base}__events.csv"
        other_path = OUT / f"{base}__excluded.csv"
        events.to_csv(events_path, index=False, encoding="utf-8-sig")
        other.to_csv(other_path, index=False, encoding="utf-8-sig")
        transforms.append(
            {
                "source": str(csv_path.relative_to(ROOT)).replace("\\", "/"),
                "book": book,
                "sheet": sheet,
                "n_in": int(len(df)),
                "n_events": int(len(events)),
                "n_excluded": int(len(other)),
                "key_cols": keys,
                "rule": "exclude rows with any empty key; do not glue missing keys",
                "events_csv": str(events_path.relative_to(ROOT)).replace("\\", "/"),
                "excluded_csv": str(other_path.relative_to(ROOT)).replace("\\", "/"),
            }
        )

    summary = {"ts": datetime.now().isoformat(timespec="seconds"), "transforms": transforms}
    (OUT / "transforms.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    report = ROOT / "docs" / "iteration2" / "I2-K-02_normalize.md"
    lines = [
        "# I2-K-02 — Нормализация и отделение событий от итогов",
        "",
        f"Сформировано: {summary['ts']}",
        "",
        "Правило: строки без полного набора ключей → `total_or_incomplete` (исключены из событий).",
        "Строки с пустыми ключами **не склеиваются** между собой.",
        "Происхождение `src_file/src_sheet/src_row` сохранено.",
        "",
        "| Книга | Лист | Вход | События | Исключено |",
        "|-------|------|------|---------|-----------|",
    ]
    for t in transforms:
        lines.append(
            f"| {t['book']} | {t['sheet']} | {t['n_in']} | {t['n_events']} | {t['n_excluded']} |"
        )
    lines.extend(
        [
            "",
            "## Как проверить",
            "",
            "```bash",
            "python scripts/i2_k02_normalize.py",
            "python -c \"import json; t=json.load(open('data/processed/normalized/transforms.json',encoding='utf-8')); print(len(t['transforms'])); print(sum(x['n_events'] for x in t['transforms']), sum(x['n_excluded'] for x in t['transforms']))\"",
            "```",
            "",
        ]
    )
    report.write_text("\n".join(lines), encoding="utf-8")
    print(f"transforms={len(transforms)} wrote {report}")
    return 0 if transforms else 1


if __name__ == "__main__":
    raise SystemExit(main())
