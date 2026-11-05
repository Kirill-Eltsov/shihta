# shikhta-ml — выбор рецептуры шихты

Проект подготовки данных и (далее) ML/оптимизации для огнеупорного производства.

## Структура

```
shikhta-ml/
  data/raw/           # исходные Excel (копия из mathsKR/Данные/Данные)
  data/processed/     # готовые CSV
  scripts/00_data_prep.py
  docs/keys.md        # коды связей
```

## Пять разобранных файлов (март–май 2022)

| Файл | Роль |
|------|------|
| Заказы.xls | спрос |
| Шихта.xls | рецепты |
| Линии дозирования.xls | факт расхода + мост Распоряжение→Марка |
| Прессовка.xls | история качества (годное/брак) |
| Подача порошков.xls | поступления порошков (`nMaterialId`) |

## Как собрать CSV

```bash
pip install pandas numpy xlrd
python scripts/00_data_prep.py
```

Результат в `data/processed/`:

- `заказы.csv` / `zakazy.csv`
- `рецепты.csv` / `recepty.csv`
- `качество.csv` / `kachestvo.csv`
- `march_plan_checksum.json` — контрольные суммы мартовского плана
- `keys.md` — описание кодов

## Правило качества

Если у шихты **нет истории прессовки**, поля `press_yield` и `q2_press_yield` остаются **пустыми** (`has_press_history=0`).

Для воспроизведения мартовского MILP-плана (как в `MILP_Solvers.ipynb`) используется `q1_rank` внутри скрипта валидации — это заглушка ранга, не запись в `качество.csv`.

## Коды связей

См. `docs/keys.md`:

`order_id` → `mass_code` → (`mass_code`, `shikhta_num`) → `powder_code`  
Прессовка: `Распоряжение, код` + `№ шихты` → через Линии → `mass_code`  
Порошок: `nMaterialId` ≈ `powder_code`
