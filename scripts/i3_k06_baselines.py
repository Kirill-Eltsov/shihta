"""I3-K-06/09: control forecasts + one simple model on draft events (if usable)."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "processed" / "ml"
OUT.mkdir(parents=True, exist_ok=True)
DOCS = ROOT / "docs" / "iteration3"


def main() -> int:
    diag = json.loads((ROOT / "data/processed/events/press_link_diag.json").read_text(encoding="utf-8"))
    draft = pd.read_csv(ROOT / "data/processed/events/ml_events_draft.csv")
    # Use kachestvo as proxy supervised target when press yield exists
    kach = pd.read_csv(ROOT / "data/processed/kachestvo.csv")
    kach = kach[kach["period"] == "2022-03"].copy()
    y = kach["q2_press_yield"]
    mask = y.notna()
    blocked = not bool(mask.any()) or bool(diag.get("awaiting_T09", True))

    result = {
        "ts": datetime.now().isoformat(timespec="seconds"),
        "awaiting_T09": True,
        "training_allowed": False,
        "reason": "T09 label/protocol not confirmed by analytics; baselines computed on available q2 only as diagnostic, not claimed ML-ready",
        "n_draft_events": int(len(draft)),
        "n_q2_available": int(mask.sum()),
    }

    if mask.any():
        yv = y[mask].astype(float).values
        # split by index order as time proxy; May not used for tuning
        n = len(yv)
        cut = int(n * 0.7)
        y_train, y_test = yv[:cut], yv[cut:]
        preds = {
            "all_good_1": np.ones_like(y_test),
            "train_mean": np.full_like(y_test, y_train.mean()),
            "fallback_global_mean": np.full_like(y_test, yv.mean()),
        }
        # simple model: predict train mean (explicitly simple)
        preds["simple_mean_model"] = np.full_like(y_test, y_train.mean())
        errors = {k: float(np.mean(np.abs(y_test - p))) for k, p in preds.items()}
        result["mae"] = errors
        result["may_used_for_tuning"] = False
        (OUT / "baseline_errors.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    else:
        result["mae"] = None
        (OUT / "baseline_errors.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    (DOCS / "I3-K-06_baselines.md").write_text(
        "# I3-K-06\n\nКонтроли: всё годное / mean train / mean fallback + simple mean model.\n"
        "Обучение как продуктовый ML **не разрешено** до T09; май не использовался для подбора.\n"
        f"См. `data/processed/ml/baseline_errors.json`.\n",
        encoding="utf-8",
    )
    (DOCS / "I3-K-09_ml_test.md").write_text(
        "# I3-K-09\n\nДиагностическое сравнение контролей сохранено. Финальный ML-тест без подтверждённой метки не заявляется.\n"
        "Блокировка + диагностика вместо выдуманных меток.\n",
        encoding="utf-8",
    )
    print(json.dumps({k: result[k] for k in ("n_q2_available", "training_allowed", "mae")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
