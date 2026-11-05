"""I2-K-07: reproducible solver journal for educational MILP run."""
from __future__ import annotations

import hashlib
import json
import platform
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "processed" / "milp"


def sha(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def main() -> int:
    subprocess.check_call([sys.executable, str(ROOT / "scripts" / "i2_k06_milp.py")], cwd=ROOT)
    solve = json.loads((OUT / "edu_solve.json").read_text(encoding="utf-8"))
    journal = {
        "ts": datetime.now().isoformat(timespec="seconds"),
        "inputs": {
            "zakazy.csv": sha(ROOT / "data/processed/zakazy.csv"),
            "recepty.csv": sha(ROOT / "data/processed/recepty.csv"),
            "kachestvo.csv": sha(ROOT / "data/processed/kachestvo.csv"),
        },
        "config": {
            "period": "2022-03",
            "n_orders_slice": 40,
            "objective": "sum demand * q",
            "q_fallback": 0.5,
            "scenario_label": "educational",
        },
        "versions": {
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "numpy": __import__("numpy").__version__,
            "pandas": __import__("pandas").__version__,
            "scipy": __import__("scipy").__version__,
        },
        "solver_log": {
            "status": solve.get("status"),
            "objective": solve.get("objective"),
            "bound_gap": None,
            "time_note": "embedded in scipy milp runtime; wall clock not separately timed here",
            "solver": solve.get("solver"),
        },
        "march_scenario_label": "educational",
        "old_baseline_block": "Danila Colab notebook baseline not re-run locally (Colab/pulp path); educational model used instead",
    }
    (OUT / "solver_journal.json").write_text(json.dumps(journal, ensure_ascii=False, indent=2), encoding="utf-8")
    report = ROOT / "docs/iteration2/I2-K-07_journal.md"
    report.write_text(
        "\n".join(
            [
                "# I2-K-07 — Журнал решателя и воспроизводимый сценарий",
                "",
                f"Сформировано: {journal['ts']}",
                "",
                f"- Сценарий: **{journal['march_scenario_label']}** (не промышленный подтверждённый baseline)",
                f"- Status/objective: {journal['solver_log']['status']} / {journal['solver_log']['objective']}",
                f"- Версии: python {journal['versions']['python']}, scipy {journal['versions']['scipy']}",
                f"- Блокировка старого baseline: {journal['old_baseline_block']}",
                "",
                "Файл: `data/processed/milp/solver_journal.json`",
                "",
                "## Как проверить",
                "",
                "```bash",
                "python scripts/i2_k07_solver_journal.py",
                "```",
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(json.dumps({"status": journal["solver_log"]["status"], "label": journal["march_scenario_label"]}, ensure_ascii=False))
    return 0 if journal["solver_log"]["status"] == "Optimal" else 1


if __name__ == "__main__":
    raise SystemExit(main())
