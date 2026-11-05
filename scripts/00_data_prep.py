# -*- coding: utf-8 -*-
"""
Подготовка данных для проекта выбора рецептуры шихты.

Пять исходных файлов (март–май 2022):
  Заказы.xls, Шихта.xls, Линии дозирования.xls, Прессовка.xls, Подача порошков.xls

Выход (data/processed/):
  zakazy.csv    — заказы
  recepty.csv   — рецепты (марка × шихта × компонент/порошок)
  kachestvo.csv — качество по истории прессовки
                (пусто, если нет истории прессовки)

Критерий готовности: по CSV воспроизводится мартовский план
(orders / recipes / supply / quality_q1) как в MILP_Solvers.ipynb.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "processed"
OUT.mkdir(parents=True, exist_ok=True)

MONTHS = ["март 2022", "апрель 2022", "май 2022"]
LD_MONTHS = ["март 2022", "аперль 2022", "май 2022"]  # опечатка в исходнике
PERIOD_MAP = {
    "март 2022": "2022-03",
    "апрель 2022": "2022-04",
    "аперль 2022": "2022-04",
    "май 2022": "2022-05",
}

MIN_DEMAND = 0.0
SUPPLY_BUFFER = 1.30


def find_file(substr: str) -> Path:
    matches = [p for p in RAW.glob("*.xls") if substr in p.name]
    if not matches:
        raise FileNotFoundError(f"Не найден файл с '{substr}' в {RAW}")
    return matches[0]


def read_sheets(path: Path, sheets: list[str]) -> pd.DataFrame:
    frames = []
    available = pd.ExcelFile(path, engine="xlrd").sheet_names
    for sheet in sheets:
        if sheet not in available:
            continue
        df = pd.read_excel(path, sheet_name=sheet, engine="xlrd")
        df["period"] = PERIOD_MAP[sheet]
        df["sheet"] = sheet
        frames.append(df)
    if not frames:
        raise ValueError(f"Нет листов {sheets} в {path.name}")
    return pd.concat(frames, ignore_index=True)


def build_orders(df_z: pd.DataFrame, recipe_masses: set[int]) -> pd.DataFrame:
    rows = []
    for period, g in df_z.groupby("period"):
        oid = 0
        for _, row in g.iterrows():
            mc = int(row["Марка массы, код"])
            if mc not in recipe_masses:
                continue
            dem = float(row["Заказ, тн."])
            dop = float(row["Доп. заказ, тн."]) if pd.notna(row.get("Доп. заказ, тн.")) else 0.0
            demand = dem + dop
            if demand < MIN_DEMAND:
                continue
            rows.append(
                {
                    "period": period,
                    "order_id": oid,
                    "mass_code": mc,
                    "mass_name": str(row.get("Марка, наименование", "")),
                    "group_code": int(row["Группа сырца, код"])
                    if pd.notna(row.get("Группа сырца, код"))
                    else pd.NA,
                    "product_code": int(row["Марка изделия, код"])
                    if pd.notna(row.get("Марка изделия, код"))
                    else pd.NA,
                    "demand_t": round(demand, 6),
                    "order_t": round(dem, 6),
                    "extra_order_t": round(dop, 6),
                }
            )
            oid += 1
    return pd.DataFrame(rows)


def build_recipes(df_sh: pd.DataFrame) -> pd.DataFrame:
    df = df_sh.copy()
    df = df.dropna(subset=["Марка массы, код", "Номер шихты", "Компонент, код", "Норма, %"])
    out = pd.DataFrame(
        {
            "period": df["period"],
            "mass_code": df["Марка массы, код"].astype(int),
            "mass_name": df["Марка массы, наименование"].astype(str),
            "shikhta_num": df["Номер шихты"].astype(int),
            "order_code": df["Распоряжение, код"].astype(int),
            "powder_code": df["Компонент, код"].astype(int),
            "powder_name": df["Компонент, наименование"].astype(str),
            "norm_pct": df["Норма, %"].astype(float),
            "substitutes": df.get("Заменяющие компоненты, код", pd.Series([""] * len(df)))
            .fillna("")
            .astype(str),
        }
    )
    # одна норма на ключ (если дубли — среднее)
    out = (
        out.groupby(
            [
                "period",
                "mass_code",
                "mass_name",
                "shikhta_num",
                "order_code",
                "powder_code",
                "powder_name",
                "substitutes",
            ],
            as_index=False,
        )["norm_pct"]
        .mean()
    )
    return out


def build_quality(df_pr: pd.DataFrame, df_ld: pd.DataFrame, recipes: pd.DataFrame) -> pd.DataFrame:
    """Качество = press_yield. Без истории прессовки — пусто (NaN)."""
    bridge = (
        df_ld[["period", "Марка массы, код", "Распоряжение, код"]]
        .dropna()
        .drop_duplicates()
    )
    bridge["Марка массы, код"] = bridge["Марка массы, код"].astype(int)
    bridge["Распоряжение, код"] = bridge["Распоряжение, код"].astype(int)

    pr = df_pr.copy()
    pr = pr.dropna(subset=["Распоряжение, код", "№ шихты"])
    pr["Распоряжение, код"] = pr["Распоряжение, код"].astype(int)
    pr["№ шихты"] = pr["№ шихты"].astype(int)
    pr["Годное, тн."] = pd.to_numeric(pr["Годное, тн."], errors="coerce").fillna(0.0)
    pr["Брак, тн."] = pd.to_numeric(pr["Брак, тн."], errors="coerce").fillna(0.0)

    pr2 = pr.merge(
        bridge,
        on=["period", "Распоряжение, код"],
        how="left",
    )
    pr2 = pr2.dropna(subset=["Марка массы, код"])
    pr2["Марка массы, код"] = pr2["Марка массы, код"].astype(int)

    grp = (
        pr2.groupby(["period", "Марка массы, код", "№ шихты"], as_index=False)[
            ["Годное, тн.", "Брак, тн."]
        ]
        .sum()
    )
    total = grp["Годное, тн."] + grp["Брак, тн."]
    grp["press_yield"] = np.where(total > 0, grp["Годное, тн."] / total, np.nan)

    # Нормировка внутри марки и периода → q2 ∈ [0,1]
    def norm_in_group(s: pd.Series) -> pd.Series:
        mn, mx = s.min(), s.max()
        if pd.isna(mn) or pd.isna(mx) or mx <= mn:
            return pd.Series(1.0, index=s.index)
        return (s - mn) / (mx - mn)

    grp["q2_press_yield"] = grp.groupby(["period", "Марка массы, код"])["press_yield"].transform(
        norm_in_group
    )

    # Все известные рецепты (уникальные марка×шихта по периоду)
    keys = (
        recipes[["period", "mass_code", "shikhta_num"]]
        .drop_duplicates()
        .rename(columns={"mass_code": "Марка массы, код", "shikhta_num": "№ шихты"})
    )
    out = keys.merge(
        grp[
            [
                "period",
                "Марка массы, код",
                "№ шихты",
                "Годное, тн.",
                "Брак, тн.",
                "press_yield",
                "q2_press_yield",
            ]
        ],
        on=["period", "Марка массы, код", "№ шихты"],
        how="left",
    )
    out = out.rename(
        columns={
            "Марка массы, код": "mass_code",
            "№ шихты": "shikhta_num",
            "Годное, тн.": "good_t",
            "Брак, тн.": "scrap_t",
        }
    )
    # Без истории прессовки — пустые поля качества (как в задании)
    out["has_press_history"] = out["press_yield"].notna().astype(int)
    return out[
        [
            "period",
            "mass_code",
            "shikhta_num",
            "good_t",
            "scrap_t",
            "press_yield",
            "q2_press_yield",
            "has_press_history",
        ]
    ]


def build_keys_doc(
    orders: pd.DataFrame,
    recipes: pd.DataFrame,
    quality: pd.DataFrame,
    df_ld: pd.DataFrame,
    df_pow: pd.DataFrame,
) -> str:
    lines = [
        "# Коды связей (заказ → марка → шихта → порошок)",
        "",
        "| Код | Где | Роль |",
        "|-----|-----|------|",
        "| `order_id` | zakazy.csv | Локальный id заказа внутри period |",
        "| `mass_code` (Марка массы, код) | zakazy, recepty, kachestvo, Линии | Связывает заказ и рецепты |",
        "| `shikhta_num` (Номер шихты / № шихты) | recepty, kachestvo, Линии, Прессовка | Идентификатор рецепта внутри марки |",
        "| `powder_code` (Компонент, код) | recepty, Линии | Порошок/компонент шихты |",
        "| `order_code` (Распоряжение, код) | recepty, Линии, Прессовка | Мост прессовка ↔ марка массы |",
        "| `nMaterialId` | Подача порошков | Код материала порошка (сопоставляется с powder_code) |",
        "",
        "## Цепочки",
        "1. Заказ → `mass_code` → рецепты шихты",
        "2. Рецепт → (`mass_code`, `shikhta_num`) → компоненты `powder_code` + `norm_pct`",
        "3. Прессовка → `Распоряжение` + `№ шихты` → через Линии → `mass_code`",
        "4. Подача порошков → `nMaterialId` ≈ `powder_code`",
        "",
        f"## Статистика (все периоды)",
        f"- Заказов: {len(orders)}",
        f"- Строк рецептов: {len(recipes)}",
        f"- Уникальных шихт в качестве: {len(quality)}",
        f"- С историей прессовки: {int(quality['has_press_history'].sum())}",
        f"- Без истории (пустое качество): {int((quality['has_press_history'] == 0).sum())}",
    ]
    # Пересечение порошков
    powder_recipe = set(recipes["powder_code"].unique())
    powder_feed = set(
        pd.to_numeric(df_pow["nMaterialId"], errors="coerce").dropna().astype(int)
    )
    inter = powder_recipe & powder_feed
    lines += [
        "",
        "## Порошки",
        f"- Уникальных powder_code в рецептах: {len(powder_recipe)}",
        f"- Уникальных nMaterialId в подаче: {len(powder_feed)}",
        f"- Пересечение: {len(inter)}",
    ]
    return "\n".join(lines) + "\n"


def reproduce_march_plan(
    orders: pd.DataFrame,
    recipes: pd.DataFrame,
    df_ld_march: pd.DataFrame,
) -> dict:
    """Воспроизведение структур мартовского плана из MILP_Solvers (q1_rank)."""
    o = orders[orders["period"] == "2022-03"].copy()
    r = recipes[recipes["period"] == "2022-03"].copy()

    recipes_dict: dict[int, dict[int, dict[int, float]]] = {}
    for _, row in r.iterrows():
        mc, sn, cc = int(row["mass_code"]), int(row["shikhta_num"]), int(row["powder_code"])
        recipes_dict.setdefault(mc, {}).setdefault(sn, {})[cc] = float(row["norm_pct"])

    orders_list = [
        {
            "id": int(row["order_id"]),
            "mass_code": int(row["mass_code"]),
            "demand": float(row["demand_t"]),
        }
        for _, row in o.iterrows()
        if int(row["mass_code"]) in recipes_dict
    ]

    supply_raw = df_ld_march.groupby("Компонент, код")["Годное, тн."].sum()
    supply = {
        int(c): float(v) * SUPPLY_BUFFER for c, v in supply_raw.items() if float(v) > 0
    }

    quality = {}
    for mc, sh in recipes_dict.items():
        sn_s = sorted(sh.keys())
        n = len(sn_s)
        for k, sn in enumerate(sn_s):
            quality[(mc, sn)] = (k + 1) / n

    # Простой greedy-by-quality как в ноутбуке (для контрольной суммы)
    recipe_lists = {mc: sorted(sh.keys()) for mc, sh in recipes_dict.items()}
    rem = dict(supply)
    asgn = []
    for oi in sorted(
        range(len(orders_list)),
        key=lambda i: -max(quality.get((orders_list[i]["mass_code"], sn), 0) for sn in recipe_lists[orders_list[i]["mass_code"]]),
    ):
        o_i = orders_list[oi]
        mc, d = o_i["mass_code"], o_i["demand"]
        chosen = None
        for sn in sorted(recipe_lists[mc], key=lambda s: -quality.get((mc, s), 0)):
            ok = all(
                rem.get(c, 0) >= (nm / 100) * d
                for c, nm in recipes_dict[mc][sn].items()
                if c in rem
            )
            if ok:
                chosen = sn
                break
        if chosen is None:
            chosen = max(recipe_lists[mc], key=lambda s: quality.get((mc, s), 0))
        for c, nm in recipes_dict[mc][chosen].items():
            if c in rem:
                rem[c] -= (nm / 100) * d
        asgn.append((oi, chosen))

    asgn_map = {oi: sn for oi, sn in asgn}
    obj = sum(
        quality.get((orders_list[i]["mass_code"], asgn_map[i]), 0) * orders_list[i]["demand"]
        for i in range(len(orders_list))
    )

    return {
        "n_orders": len(orders_list),
        "n_masses": len(recipes_dict),
        "n_recipes": sum(len(v) for v in recipes_dict.values()),
        "total_demand_t": round(sum(x["demand"] for x in orders_list), 3),
        "n_supply_comps": len(supply),
        "greedy_quality_obj": round(obj, 3),
    }


def main() -> None:
    print("[1] Загрузка пяти файлов...")
    f_orders = find_file("Заказы")
    f_shikhta = find_file("Шихта")
    f_ld = find_file("Линии")
    f_press = find_file("Прессовка")
    f_pow = find_file("Подача")

    df_z = read_sheets(f_orders, MONTHS)
    df_sh = read_sheets(f_shikhta, MONTHS)
    df_ld = read_sheets(f_ld, LD_MONTHS)
    df_pr = read_sheets(f_press, MONTHS)
    df_pow = read_sheets(f_pow, MONTHS)

    print("[2] Сборка recepty / zakazy / kachestvo...")
    recipes = build_recipes(df_sh)
    recipe_masses = set(recipes["mass_code"].unique())
    orders = build_orders(df_z, recipe_masses)
    quality = build_quality(df_pr, df_ld, recipes)

    # Русские имена файлов как в задании + латинские алиасы
    paths = {
        "заказы.csv": orders,
        "рецепты.csv": recipes,
        "качество.csv": quality,
        "zakazy.csv": orders,
        "recepty.csv": recipes,
        "kachestvo.csv": quality,
    }
    for name, df in paths.items():
        p = OUT / name
        df.to_csv(p, index=False, encoding="utf-8-sig")
        print(f"  saved {p.name}: {len(df)} rows")

    keys_md = build_keys_doc(orders, recipes, quality, df_ld, df_pow)
    (OUT / "keys.md").write_text(keys_md, encoding="utf-8")
    (ROOT / "docs").mkdir(exist_ok=True)
    (ROOT / "docs" / "keys.md").write_text(keys_md, encoding="utf-8")

    print("[3] Воспроизведение мартовского плана...")
    df_ld_march = df_ld[df_ld["period"] == "2022-03"]
    march = reproduce_march_plan(orders, recipes, df_ld_march)
    (OUT / "march_plan_checksum.json").write_text(
        json.dumps(march, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(march, ensure_ascii=False, indent=2))

    # Контроль: пустые качества без прессовки
    empty_q = int((quality["has_press_history"] == 0).sum())
    filled_q = int((quality["has_press_history"] == 1).sum())
    print(f"[OK] качество: с историей={filled_q}, пустых={empty_q}")
    print("[DONE] data/processed готов")


if __name__ == "__main__":
    main()
