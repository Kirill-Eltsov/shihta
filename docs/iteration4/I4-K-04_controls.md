# I4-K-04 — Проверка на контрольных сценариях

Исполнитель: Кирилл Ельцов  
Запуск: `python scripts/iteration4/run_controls.py`  
Результат: `data/processed/i4/k_control_results.json`

## Результаты

| Сценарий | MILP status | objective | План |
|----------|-------------|-----------|------|
| base | optimal | **2.50** | H / L / L |
| deficit | **infeasible** | null | — |
| changed_q | optimal | **2.35** | (допустимый оптимум) |

Дополнительно:

- запрет H для заказа 1 на старом плане H/L/L → `invalid_plan`;
- пересчёт старого H/L/L при q(1,H)=0.1 → objective **1.65**;
- частичные планы не выдаются за успех; `all_passed=true`, checks_run=6.

## Критерии

- [x] Нет скрытых частичных планов.
- [x] Ошибки и отсутствие допустимого решения имеют отдельные статусы.

## Как проверить

```bash
python scripts/iteration4/run_controls.py
```
