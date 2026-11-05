"""I2-K-01: load 12 XLS books / 36 sheets with file/sheet/row provenance."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
OUT_DIR = ROOT / "data" / "processed" / "loader"
OUT_DIR.mkdir(parents=True, exist_ok=True)

EXPECTED_BOOKS = [
    "Заказы.xls",
    "Шихта.xls",
    "Линии дозирования.xls",
    "Прессовка.xls",
    "Подача порошков.xls",
    "Проценты.xls",
    "Сдача.xls",
    "Садка.xls",
    "Печи.xls",
    "Простои.xls",
    "Нормы прессовки.xls",
    "Доп операции.xls",
]


def main() -> int:
    registry: list[dict] = []
    errors: list[dict] = []
    missing_files: list[str] = []

    for book in EXPECTED_BOOKS:
        path = RAW / book
        if not path.exists():
            missing_files.append(book)
            errors.append({"file": book, "error": "missing_file"})
            continue
        try:
            xl = pd.ExcelFile(path, engine="xlrd")
        except Exception as exc:  # noqa: BLE001
            errors.append({"file": book, "error": f"open_failed: {exc}"})
            continue
        for sheet in xl.sheet_names:
            try:
                df = pd.read_excel(path, sheet_name=sheet, engine="xlrd")
            except Exception as exc:  # noqa: BLE001
                errors.append({"file": book, "sheet": sheet, "error": f"read_failed: {exc}"})
                continue
            # 1-based data row index matching Excel-like numbering after header row
            df = df.copy()
            df.insert(0, "src_file", book)
            df.insert(1, "src_sheet", sheet)
            df.insert(2, "src_row", range(2, len(df) + 2))
            safe_sheet = sheet.replace(" ", "_").replace("/", "_")
            out_name = f"{path.stem}__{safe_sheet}.csv"
            out_path = OUT_DIR / out_name
            df.to_csv(out_path, index=False, encoding="utf-8-sig")
            registry.append(
                {
                    "file": book,
                    "sheet": sheet,
                    "n_rows": int(len(df)),
                    "n_cols": int(df.shape[1] - 3),
                    "out_csv": str(out_path.relative_to(ROOT)).replace("\\", "/"),
                    "provenance": "src_file/src_sheet/src_row",
                }
            )

    summary = {
        "ts": datetime.now().isoformat(timespec="seconds"),
        "expected_books": len(EXPECTED_BOOKS),
        "loaded_books": len({r["file"] for r in registry}),
        "loaded_sheets": len(registry),
        "missing_files": missing_files,
        "errors": errors,
        "sheets": registry,
    }
    (OUT_DIR / "registry.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    md_lines = [
        "# I2-K-01 — Загрузчик книг и реестр происхождения строк",
        "",
        f"Сформировано: {summary['ts']}",
        "",
        f"- Ожидалось книг: **{summary['expected_books']}**",
        f"- Загружено книг: **{summary['loaded_books']}**",
        f"- Загружено листов: **{summary['loaded_sheets']}** (цель 36)",
        f"- Отсутствующие файлы: {missing_files or 'нет'}",
        f"- Ошибки чтения: {len(errors)}",
        "",
        "Каждая строка CSV содержит `src_file`, `src_sheet`, `src_row`.",
        "",
        "| Файл | Лист | Строк | CSV |",
        "|------|------|-------|-----|",
    ]
    for r in registry:
        md_lines.append(
            f"| {r['file']} | {r['sheet']} | {r['n_rows']} | `{r['out_csv']}` |"
        )
    md_lines.extend(
        [
            "",
            "## Как проверить",
            "",
            "```bash",
            "python scripts/i2_k01_loader.py",
            "python -c \"import json; s=json.load(open('data/processed/loader/registry.json',encoding='utf-8')); print(s['loaded_books'], s['loaded_sheets'], s['missing_files'], s['errors'])\"",
            "```",
            "",
            "Ожидание: 12 книг, 36 листов, пустые missing/errors.",
            "",
        ]
    )
    report = ROOT / "docs" / "iteration2" / "I2-K-01_loader.md"
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text("\n".join(md_lines), encoding="utf-8")
    print(json.dumps({k: summary[k] for k in ("loaded_books", "loaded_sheets", "missing_files", "errors")}, ensure_ascii=False))
    print(f"wrote {report}")
    return 0 if not missing_files and not errors and summary["loaded_sheets"] == 36 else 1


if __name__ == "__main__":
    raise SystemExit(main())
