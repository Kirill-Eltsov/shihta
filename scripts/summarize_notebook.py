import json
from pathlib import Path

nb = json.loads(Path("docs/MILP_Solvers.ipynb").read_text(encoding="utf-8"))
for i, c in enumerate(nb["cells"]):
    src = "".join(c.get("source", []))
    head = src.strip().splitlines()[:12]
    print(f"--- cell {i} ({c.get('cell_type')}) ---")
    for ln in head:
        print(ln[:140])
    print()
