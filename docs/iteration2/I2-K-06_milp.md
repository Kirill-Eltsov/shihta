# I2-K-06 — Исполняемая MILP по подготовленным входам

Сформировано: 2026-11-05T19:35:58

- Период: 2022-03, заказов в срезе: 25, переменных: 3610
- Статус: **Optimal**, objective=3336.085
- Solver: scipy.optimize.milp (HiGHS)
- Учебные/processed CSV отделены от Colab-путей notebook Данила.
- Полный промышленный model_spec от A ещё ожидается (`awaiting_A_model_spec=true`).

## Как проверить

```bash
python scripts/i2_k06_milp.py
python -c "import json; print(json.load(open('data/processed/milp/edu_solve.json',encoding='utf-8')))"
```
