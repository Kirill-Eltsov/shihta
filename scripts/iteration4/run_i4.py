# -*- coding: utf-8 -*-
"""I4-K single entry point: bridge + controls + benchmark → summary.

Usage (from repo root):
    python scripts/iteration4/run_i4.py
"""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
OUT_DIR = ROOT / "data" / "processed" / "i4"
SUMMARY = OUT_DIR / "i4_run_summary.json"


def _run(script: str) -> dict:
    proc = subprocess.run(
        [sys.executable, str(HERE / script)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return {
        "script": script,
        "returncode": proc.returncode,
        "stdout": (proc.stdout or "").strip(),
        "stderr": (proc.stderr or "").strip(),
        "ok": proc.returncode == 0,
    }


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    steps = [
        _run("milp_bridge.py"),
        _run("run_controls.py"),
        _run("run_benchmark.py"),
    ]
    all_ok = all(s["ok"] for s in steps)

    controls = None
    bench = None
    if (OUT_DIR / "k_control_results.json").exists():
        controls = json.loads((OUT_DIR / "k_control_results.json").read_text(encoding="utf-8"))
    if (OUT_DIR / "benchmark_control.json").exists():
        bench = json.loads((OUT_DIR / "benchmark_control.json").read_text(encoding="utf-8"))

    rows = []
    if bench:
        for r in bench.get("rows", []):
            milp = r["resource_milp"]["primary"]
            greedy = r["greedy_quality"]["primary"]
            rows.append(
                {
                    "scenario_id": r["scenario_id"],
                    "milp_status": milp.get("status"),
                    "milp_objective": milp.get("objective"),
                    "milp_plan": milp.get("plan"),
                    "greedy_status": greedy.get("status"),
                    "greedy_objective": greedy.get("objective"),
                    "passed": r.get("passed"),
                }
            )

    coverage = (bench or {}).get("coverage")
    timeout_demo = (bench or {}).get("timeout_demo")
    summary = {
        "scope": "I4-K control contour after K-09 runner fixes (Kirill)",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "entry_point": "scripts/iteration4/run_i4.py",
        "all_ok": all_ok and bool(controls and controls.get("all_passed")) and bool(bench and bench.get("all_passed")),
        "steps": steps,
        "artifacts": {
            "scenarios": "data/processed/i4/scenarios_v1.json",
            "config": "data/processed/i4/method_config.json",
            "bridge_trace": "data/processed/i4/milp_bridge_trace.json",
            "controls": "data/processed/i4/k_control_results.json",
            "benchmark": "data/processed/i4/benchmark_control.json",
            "timeout_demo": "data/processed/i4/timeout_demo.json",
            "docs": "docs/iteration4/",
        },
        "coverage": coverage,
        "timeout_demo": timeout_demo,
        "scenario_results": rows,
        "notes": [
            "Contour covers G2/G3 educational control scenarios from Alexey I4-A-01.",
            "I4-K-09: hard external timeout, full repetition journal, threads diagnostic.",
            "I4-K-10 primary series is NOT run here; blocked until Alexey series admission.",
            "Does not claim industrial Colab baseline or ML/warm-start.",
        ],
    }
    SUMMARY.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"all_ok": summary["all_ok"], "summary": str(SUMMARY), "scenarios": rows}, ensure_ascii=False, indent=2))
    return 0 if summary["all_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
