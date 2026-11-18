# I4-K-08 — Автосбор результатов на контрольном запуске

Исполнитель: Кирилл Ельцов  
Результат: `data/processed/i4/benchmark_control.json`  
Сводка контура: `data/processed/i4/i4_run_summary.json`

## Результаты автосбора

| scenario | MILP | obj | greedy | passed |
|----------|------|-----|--------|--------|
| base | optimal | 2.50 | feasible 2.35 | yes |
| deficit | infeasible | null | no_solution / ошибка запаса | yes |
| changed_q | optimal | 2.35 | feasible | yes |

`all_passed=true`. Окружение и hash сценариев сохранены в журнале.

## Критерии

- [x] Контрольный автосбор выполнен.
- [x] Неудачи не подменяются нулевой целью.

## Как проверить

```bash
python scripts/iteration4/run_i4.py
python -c "import json; print(json.load(open('data/processed/i4/benchmark_control.json',encoding='utf-8'))['all_passed'])"
```
