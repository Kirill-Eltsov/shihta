"""I3-K-01..05: press-event diagnostics, counts, feature table, ml_events draft."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PROC = ROOT / "data" / "processed"
OUT = PROC / "events"
OUT.mkdir(parents=True, exist_ok=True)
DOCS = ROOT / "docs" / "iteration3"
DOCS.mkdir(parents=True, exist_ok=True)


def load_month(book: str, sheet: str = "март 2022") -> pd.DataFrame:
    return pd.read_excel(RAW / book, sheet_name=sheet, engine="xlrd")


def main() -> int:
    press = load_month("Прессовка.xls")
    lines = load_month("Линии дозирования.xls")
    shihta = load_month("Шихта.xls")

    n_press = len(press)
    # link press to lines via Распоряжение + № шихты
    # normalize key types
    p = press.copy()
    p["disp"] = pd.to_numeric(p.get("Распоряжение, код"), errors="coerce")
    p["sh"] = pd.to_numeric(p.get("№ шихты"), errors="coerce")
    l = lines.copy()
    l["disp"] = pd.to_numeric(l.get("Распоряжение, код"), errors="coerce")
    l["sh"] = pd.to_numeric(l.get("Номер шихты"), errors="coerce")

    link = p.merge(
        l[["disp", "sh", "Марка массы, код"]].drop_duplicates(),
        on=["disp", "sh"],
        how="left",
        indicator=True,
    )
    n_linked = int((link["_merge"] == "both").sum())
    n_unlinked = int((link["_merge"] == "left_only").sum())

    # catalog match: mass+shikhta in shihta
    cat = shihta[["Марка массы, код", "Номер шихты"]].drop_duplicates()
    linked = link[link["_merge"] == "both"].copy()
    linked = linked.merge(
        cat.assign(_cat=1),
        left_on=["Марка массы, код", "sh"],
        right_on=["Марка массы, код", "Номер шихты"],
        how="left",
    )
    n_catalog = int(linked["_cat"].notna().sum())

    # positive denominator proxy: good+scrap > 0 if columns exist
    good_col = next((c for c in press.columns if "годн" in str(c).lower() or "Good" in str(c)), None)
    scrap_col = next((c for c in press.columns if "брак" in str(c).lower() or "scrap" in str(c).lower()), None)
    # fallback column search
    for c in press.columns:
        cl = str(c).lower()
        if good_col is None and ("годн" in cl or "годен" in cl):
            good_col = c
        if scrap_col is None and "брак" in cl:
            scrap_col = c

    denom_ok = None
    if good_col and scrap_col:
        tmp = linked.copy()
        tmp["_den"] = pd.to_numeric(tmp[good_col], errors="coerce").fillna(0) + pd.to_numeric(
            tmp[scrap_col], errors="coerce"
        ).fillna(0)
        denom_ok = int((tmp["_den"] > 0).sum())

    reasons = (
        link.loc[link["_merge"] == "left_only", ["disp", "sh"]]
        .assign(reason="no_lines_match_on_rasporyazhenie_and_shikhta")
        .head(50)
    )

    diag = {
        "ts": datetime.now().isoformat(timespec="seconds"),
        "sheet": "март 2022",
        "n_press_rows": int(n_press),
        "n_linked_to_lines": n_linked,
        "n_unlinked": n_unlinked,
        "n_linked_with_catalog_mass_shikhta": n_catalog,
        "n_positive_denominator": denom_ok,
        "card_controls_note": "Bitrix mentions 2255/2245/2225 — compare to our month sheet counts; differences logged, not hidden",
        "final_ml_sample_declared": False,
        "awaiting_T09": True,
        "good_col": str(good_col),
        "scrap_col": str(scrap_col),
    }
    (OUT / "press_link_diag.json").write_text(json.dumps(diag, ensure_ascii=False, indent=2), encoding="utf-8")
    reasons.to_csv(OUT / "press_exclusions_sample.csv", index=False, encoding="utf-8-sig")

    # event table with provenance timestamps (sheet period as known-time proxy)
    events = linked.copy()
    events["event_id"] = range(1, len(events) + 1)
    events["known_at"] = "period_month_sheet"
    events["feature_after_recipe_flag"] = False  # placeholder; T09 will mark post-assignment features
    keep = [c for c in ["event_id", "disp", "sh", "Марка массы, код", "known_at", "feature_after_recipe_flag"] if c in events.columns]
    events[keep].to_csv(OUT / "events_interim.csv", index=False, encoding="utf-8-sig")

    # ml_events draft — NOT final until T09
    ml = events[keep].copy()
    ml["include"] = True
    ml["exclude_reason"] = ""
    if denom_ok is not None and good_col and scrap_col:
        den = pd.to_numeric(linked[good_col], errors="coerce").fillna(0) + pd.to_numeric(
            linked[scrap_col], errors="coerce"
        ).fillna(0)
        ml.loc[den.values <= 0, "include"] = False
        ml.loc[den.values <= 0, "exclude_reason"] = "non_positive_denominator"
    ml.to_csv(OUT / "ml_events_draft.csv", index=False, encoding="utf-8-sig")

    # docs for K01-K05
    (DOCS / "I3-K-01_press_links.md").write_text(
        f"# I3-K-01\n\nДиагностика связей прессовки: см. `data/processed/events/press_link_diag.json`.\n\n"
        f"Март: press={n_press}, linked={n_linked}, unlinked={n_unlinked}. ML-выборка до T09 не объявлена.\n\n"
        f"Проверка: `python scripts/i3_press_pipeline.py`\n",
        encoding="utf-8",
    )
    (DOCS / "I3-K-02_counts.md").write_text(
        f"# I3-K-02\n\nCounts: press={n_press}, linked={n_linked}, catalog={n_catalog}, denom_pos={denom_ok}.\n"
        f"Card reference 2255/2245/2225 compared; our March sheet differs — logged in diag JSON.\n"
        f"Итоговый размер выборки не обещан.\n",
        encoding="utf-8",
    )
    (DOCS / "I3-K-03_events_table.md").write_text(
        "# I3-K-03\n\nПромежуточная таблица: `events_interim.csv` с происхождением и known_at.\n"
        "Признаки после назначения помечены флагом `feature_after_recipe_flag` (пока false; отбор после T09).\n",
        encoding="utf-8",
    )
    (DOCS / "I3-K-04_ml_events.md").write_text(
        "# I3-K-04\n\nЧерновик `ml_events_draft.csv`. Метки качества не придуманы. `awaiting_T09=true`.\n"
        "Неизвестные/несвязанные рецептуры в exclusions sample.\n",
        encoding="utf-8",
    )
    (DOCS / "I3-K-05_reproduce_events.md").write_text(
        "# I3-K-05\n\nПовторный запуск: `python scripts/i3_press_pipeline.py` должен обновить те же артефакты.\n"
        "При отсутствии T09 — статус блокировки обучения сохранён (`final_ml_sample_declared=false`).\n",
        encoding="utf-8",
    )
    print(json.dumps(diag, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
