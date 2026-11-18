# I4-K-03 — Связь модуля с MILP

Исполнитель: Кирилл Ельцов  
Код: `scripts/iteration4/milp_bridge.py`  
Журнал: `data/processed/i4/milp_bridge_trace.json`

## Результат

Подтверждённый путь G2: в решатель передаются **только явные q**.  
Warm-start **не используется** (`warm_start_status=not_confirmed_not_used`).

Трассировка на 3 сценариях сохранена: входной q, число переменных назначения, stocks/orders, выход status/plan/objective/bound/timings.

## Критерии

- [x] Сохранена трассировка входов и выхода.
- [x] Заявленная передача (явный q) подтверждается журналом; warm-start не заявлен.

## Как проверить

```bash
python scripts/iteration4/milp_bridge.py
python -c "import json; t=json.load(open('data/processed/i4/milp_bridge_trace.json',encoding='utf-8')); print(t['warm_start'], len(t['traces']))"
```
