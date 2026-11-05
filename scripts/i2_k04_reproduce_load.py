"""I2-K-04: re-run loader and confirm sheet/book counts + provenance columns."""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    before = json.loads((ROOT / "data/processed/loader/registry.json").read_text(encoding="utf-8"))
    before_sheets = {(s["file"], s["sheet"], s["n_rows"]) for s in before["sheets"]}

    subprocess.check_call([sys.executable, str(ROOT / "scripts" / "i2_k01_loader.py")], cwd=ROOT)
    after = json.loads((ROOT / "data/processed/loader/registry.json").read_text(encoding="utf-8"))
    after_sheets = {(s["file"], s["sheet"], s["n_rows"]) for s in after["sheets"]}

    # sample provenance columns
    sample = ROOT / "data/processed/loader/Заказы__март_2022.csv"
    import pandas as pd

    df = pd.read_csv(sample, nrows=5)
    prov_ok = set(["src_file", "src_sheet", "src_row"]).issubset(df.columns)

    result = {
        "ts": datetime.now().isoformat(timespec="seconds"),
        "books": after["loaded_books"],
        "sheets": after["loaded_sheets"],
        "sheet_counts_match_previous": before_sheets == after_sheets,
        "provenance_columns_ok": prov_ok,
        "registry_sha256": sha256(ROOT / "data/processed/loader/registry.json"),
        "sample_csv": str(sample.relative_to(ROOT)).replace("\\", "/"),
    }
    out_json = ROOT / "data/processed/loader/reproduce_load.json"
    out_json.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    report = ROOT / "docs/iteration2/I2-K-04_reproduce.md"
    report.write_text(
        "\n".join(
            [
                "# I2-K-04 — Воспроизведение загрузки данных",
                "",
                f"Сформировано: {result['ts']}",
                "",
                f"- Книг: {result['books']}",
                f"- Листов: {result['sheets']}",
                f"- Совпадение счётчиков с предыдущим прогоном: **{result['sheet_counts_match_previous']}**",
                f"- Колонки происхождения: **{result['provenance_columns_ok']}**",
                f"- SHA256 registry: `{result['registry_sha256']}`",
                "",
                "## Как проверить",
                "",
                "```bash",
                "python scripts/i2_k04_reproduce_load.py",
                "```",
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(json.dumps(result, ensure_ascii=False))
    ok = (
        result["books"] == 12
        and result["sheets"] == 36
        and result["sheet_counts_match_previous"]
        and result["provenance_columns_ok"]
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
