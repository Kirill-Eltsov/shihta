# -*- coding: utf-8 -*-
"""I4-K-10: primary comparative series per I4-A-09 / I4_reference_v1.

Produces configuration snapshot, full solver journals, and a results table.
Does not claim production-scale instances — uses the protocol instance set
(base, deficit, changed_q) with the K-09-compliant runner.
"""
from __future__ import annotations

import hashlib
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from run_benchmark import (  # noqa: E402
    EXPECTED_SHA,
    _demo_timeout,
    _force_single_thread_env,
    _load_cpu_diag,
    _sha_scenarios,
    run_method,
)

SCENARIOS = ROOT / "data" / "processed" / "i4" / "scenarios_v1.json"
CONFIG = ROOT / "data" / "processed" / "i4" / "method_config.json"
OUT_DIR = ROOT / "data" / "processed" / "i4" / "primary_series"
SERIES_ID = "I4_primary_series_v1_reference"


def _git_commit() -> str | None:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=str(ROOT), text=True, stderr=subprocess.DEVNULL
        ).strip()
    except Exception:
        return None


def _plan_str(plan: list[dict] | None) -> str:
    if not plan:
        return "—"
    return "/".join(f"{p['recipe_id']}" for p in sorted(plan, key=lambda x: x["order_id"]))


def _fmt_obj(v) -> str:
    if v is None:
        return "null"
    return f"{v:.2f}" if isinstance(v, (int, float)) else str(v)


def _median(vals: list[float]) -> float:
    s = sorted(vals)
    n = len(s)
    if n == 0:
        return float("nan")
    if n % 2:
        return s[n // 2]
    return 0.5 * (s[n // 2 - 1] + s[n // 2])


def build_table_md(rows: list[dict], meta: dict) -> str:
    lines = [
        f"# Первичная серия {meta['series_id']}",
        "",
        f"- protocol: `{meta['protocol_ref']}`",
        f"- scenarios_sha256: `{meta['scenarios_sha256']}`",
        f"- config_id: `{meta['config_id']}`",
        f"- git_commit: `{meta['git_commit']}`",
        f"- generated_at: `{meta['generated_at']}`",
        f"- time_budget_s: `{meta['time_budget_s']}`",
        f"- repetitions: `{meta['reps']}`",
        "",
        "## Сводная таблица (primary repetition)",
        "",
        "| scenario | method | status | objective | plan | median_time_s | valid |",
        "|----------|--------|--------|-----------|------|---------------|-------|",
    ]
    for row in rows:
        for method in ("resource_milp", "greedy_quality"):
            block = row[method]
            p = block["primary"]
            valid = (p.get("validation") or {}).get("valid")
            lines.append(
                "| {sc} | {m} | {st} | {obj} | {plan} | {t:.6f} | {v} |".format(
                    sc=row["scenario_id"],
                    m=method,
                    st=p.get("status"),
                    obj=_fmt_obj(p.get("objective")),
                    plan=_plan_str(p.get("plan")),
                    t=float(block["time"]["median_s"]),
                    v=valid,
                )
            )
    lines.extend(
        [
            "",
            "## Доля допустимых планов по всем повторам",
            "",
            f"- planned_runs: {meta['coverage']['planned_runs']}",
            f"- recorded_runs: {meta['coverage']['recorded_runs']}",
            f"- valid_plans: {meta['coverage']['valid_plans_across_reps']}",
            f"- valid_plan_share: {meta['coverage']['valid_plan_share']}",
            "",
            "## Примечание",
            "",
            "Набор экземпляров — учебный `I4_reference_v1` (base/deficit/changed_q).",
            "Производственные экземпляры в серию не входят.",
            "Сравнение целей внутри сценария; `deficit` без плана исключается из сравнения целей,",
            "но учитывается в знаменателе доли допустимых.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    _force_single_thread_env()
    import numpy
    import scipy

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    raw, sha = _sha_scenarios(SCENARIOS)
    payload = json.loads(raw)

    reps = int(cfg.get("repetitions_deterministic", 4))
    budget = float(cfg.get("time_budget_s", 120))
    threads = int(cfg.get("threads", 1))
    thread_diag = _load_cpu_diag(threads)
    timeout_demo = _demo_timeout(0.2)

    series_config = {
        "series_id": SERIES_ID,
        "protocol_ref": "I4-A-09 (draft after G3) / I4_reference_v1",
        "bitrix_task": "I4-K-10 / №10535",
        "config_id": cfg.get("config_id"),
        "method_config": cfg,
        "scenarios_file": "data/processed/i4/scenarios_v1.json",
        "scenarios_sha256": sha,
        "methods": ["resource_milp", "greedy_quality"],
        "reps": reps,
        "time_budget_s": budget,
        "threads": thread_diag,
        "ml": False,
        "warm_start": False,
        "silent_q_fallback": False,
        "git_commit": _git_commit(),
        "python": platform.python_version(),
        "scipy": scipy.__version__,
        "numpy": numpy.__version__,
        "platform": platform.platform(),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "note": (
            "Primary series on protocol educational instances. "
            "Speed conclusions on three tiny cases are not scalability proof."
        ),
    }
    (OUT_DIR / "series_config.json").write_text(
        json.dumps(series_config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    rows = []
    total_reps = 0
    total_valid = 0
    for s in payload["scenarios"]:
        case, q = s["case"], s["q"]
        milp = run_method("resource_milp", case, q, reps, budget)
        greedy = run_method("greedy_quality", case, q, reps, budget)
        total_reps += milp["n_reps"] + greedy["n_reps"]
        total_valid += milp["n_feasible_or_optimal"] + greedy["n_feasible_or_optimal"]

        # expected checks for educational set (same as control)
        expected_status = s.get("expected_status")
        expected_obj = s.get("expected_objective")
        milp_status = milp["primary"]["status"]
        milp_obj = milp["primary"]["objective"]
        passed = True
        if expected_status == "infeasible":
            passed = milp_status == "infeasible"
        else:
            passed = milp_status in {"optimal", "feasible"}
            if expected_obj is not None:
                passed = passed and milp_obj is not None and abs(milp_obj - float(expected_obj)) <= 1e-8

        rows.append(
            {
                "scenario_id": s["scenario_id"],
                "q_version": s.get("q_version"),
                "expected_status": expected_status,
                "expected_objective": expected_obj,
                "resource_milp": milp,
                "greedy_quality": greedy,
                "passed_expected": passed,
                "exclude_objective_compare": expected_status == "infeasible",
            }
        )

    coverage = {
        "planned_runs": total_reps,
        "recorded_runs": total_reps,
        "valid_plans_across_reps": total_valid,
        "valid_plan_share": (total_valid / total_reps) if total_reps else None,
    }

    # status distribution
    status_counts: dict[str, int] = {}
    for row in rows:
        for method in ("resource_milp", "greedy_quality"):
            for rep in row[method]["repetitions"]:
                st = rep.get("status") or "unknown"
                status_counts[st] = status_counts.get(st, 0) + 1

    # timing summary for comparable scenarios only (with plans)
    timing_rows = []
    for row in rows:
        if row["exclude_objective_compare"]:
            continue
        for method in ("resource_milp", "greedy_quality"):
            times = [float(r.get("external_wall_s") or r.get("wall_s") or 0.0) for r in row[method]["repetitions"]]
            timing_rows.append(
                {
                    "scenario_id": row["scenario_id"],
                    "method": method,
                    "median_s": _median(times),
                    "min_s": min(times),
                    "max_s": max(times),
                    "primary_objective": row[method]["primary"].get("objective"),
                    "primary_status": row[method]["primary"].get("status"),
                }
            )

    journal = {
        "series_id": SERIES_ID,
        "scope": "I4-K-10 primary comparative series",
        "protocol_ref": series_config["protocol_ref"],
        "scenarios_sha256": sha,
        "git_commit": series_config["git_commit"],
        "config_id": cfg.get("config_id"),
        "generated_at": series_config["generated_at"],
        "timeout_demo": timeout_demo,
        "threads": thread_diag,
        "coverage": coverage,
        "status_counts": status_counts,
        "timing_comparable": timing_rows,
        "all_expected_passed": all(r["passed_expected"] for r in rows) and bool(timeout_demo.get("passed")),
        "rows": rows,
    }
    (OUT_DIR / "series_journal.json").write_text(
        json.dumps(journal, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    table_meta = {
        "series_id": SERIES_ID,
        "protocol_ref": series_config["protocol_ref"],
        "scenarios_sha256": sha,
        "config_id": cfg.get("config_id"),
        "git_commit": series_config["git_commit"],
        "generated_at": series_config["generated_at"],
        "time_budget_s": budget,
        "reps": reps,
        "coverage": coverage,
    }
    table_md = build_table_md(rows, table_meta)
    (OUT_DIR / "results_table.md").write_text(table_md, encoding="utf-8")
    (OUT_DIR / "results_table.json").write_text(
        json.dumps(
            {
                "series_id": SERIES_ID,
                "coverage": coverage,
                "status_counts": status_counts,
                "timing_comparable": timing_rows,
                "primary_rows": [
                    {
                        "scenario_id": r["scenario_id"],
                        "resource_milp": {
                            "status": r["resource_milp"]["primary"]["status"],
                            "objective": r["resource_milp"]["primary"]["objective"],
                            "plan": r["resource_milp"]["primary"]["plan"],
                            "median_time_s": r["resource_milp"]["time"]["median_s"],
                        },
                        "greedy_quality": {
                            "status": r["greedy_quality"]["primary"]["status"],
                            "objective": r["greedy_quality"]["primary"]["objective"],
                            "plan": r["greedy_quality"]["primary"]["plan"],
                            "median_time_s": r["greedy_quality"]["time"]["median_s"],
                        },
                        "passed_expected": r["passed_expected"],
                    }
                    for r in rows
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    print(
        json.dumps(
            {
                "all_expected_passed": journal["all_expected_passed"],
                "out_dir": str(OUT_DIR),
                "coverage": coverage,
                "status_counts": status_counts,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if journal["all_expected_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
