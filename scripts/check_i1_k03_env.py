"""I1-K-03: environment and source availability check."""
from __future__ import annotations

import importlib
import json
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
OUT = ROOT / "docs" / "iteration1" / "I1-K-03_env_log.txt"
MONTH = "март 2022"


def main() -> int:
    log: list[str] = []

    def rec(msg: str) -> None:
        print(msg)
        log.append(msg)

    rec(f"ts={datetime.now().isoformat(timespec='seconds')}")
    rec(f"python={sys.version.split()[0]}")
    rec(f"cwd={ROOT}")

    for mod_name in ("pandas", "numpy", "xlrd", "scipy"):
        mod = importlib.import_module(mod_name)
        rec(f"OK {mod_name} {getattr(mod, '__version__', '?')}")

    for mod_name in ("pulp", "ortools", "gurobipy"):
        try:
            importlib.import_module(mod_name)
            rec(f"OK {mod_name}")
        except Exception:
            rec(f"MISS {mod_name}")

    files = {
        "Шихта.xls": RAW / "Шихта.xls",
        "Заказы.xls": RAW / "Заказы.xls",
        "Линии дозирования.xls": RAW / "Линии дозирования.xls",
    }
    for name, path in files.items():
        if not path.exists():
            rec(f"FAIL missing {name}")
            continue
        df = pd.read_excel(path, sheet_name=MONTH, engine="xlrd")
        rec(f"LOAD_OK {name} shape={df.shape}")

    nb_path = ROOT / "docs" / "MILP_Solvers.ipynb"
    nb = json.loads(nb_path.read_text(encoding="utf-8"))
    rec(f"notebook_cells={len(nb.get('cells', []))}")
    rec("NOTE: notebook expects Google Colab uploads and names like Линии_дозирования.xls")
    rec("BLOCK: pulp not installed locally; full CBC path from notebook not reproduced here")
    rec("BLOCK: separate industrial solver source code absent (only notebook + prep script)")
    rec("RESULT: registry inputs readable; local end-to-end notebook solve not claimed")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(log) + "\n", encoding="utf-8")
    rec(f"wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
