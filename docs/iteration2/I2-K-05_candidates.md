# I2-K-05 — Допустимые рецептуры и соответствия сырья

Сформировано: 2026-11-05T19:34:12

- Позиций заказов: **694** (контроль 694 строк zakazy)
- Позиций с ровно 1 кандидатом: **0**
- Позиций с ≥1 кандидатом: **694**
- Неподтверждённые расширения кандидатов не добавлялись.
- Соответствия порошков с неполным пересечением `nMaterialId` помечены как неизвестные (см. notes).

Файлы: `data/processed/candidates/`.

## Как проверить

```bash
python scripts/i2_k05_candidates.py
python -c "import json; print(json.load(open('data/processed/candidates/summary.json',encoding='utf-8')))"
```
