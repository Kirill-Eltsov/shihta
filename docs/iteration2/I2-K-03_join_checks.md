# I2-K-03 — Проверки объединений, пропусков и справочников

Сформировано: 2026-11-05T19:33:39

- Учтено листов загрузчика: **36 / 36**
- Заказы (март, events): 222
- Шихта component rows (март): 6656
- Уникальных ключей рецепта (марка+шихта): 686
- Заказов с маркой, у которой есть рецепт: 222
- Линии events: 4054
- Прессовка events: 730

Справочник рецептов не разворачивался в новые события спроса.
Журнал: `data/processed/normalized/join_journal.json`.

## Как проверить

```bash
python scripts/i2_k03_join_checks.py
python -c "import json; j=json.load(open('data/processed/normalized/join_journal.json',encoding='utf-8')); print(j['sheets_accounted'], j['march'])"
```
