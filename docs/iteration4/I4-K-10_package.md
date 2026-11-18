# I4-K — Комплект результатов итерации 4 (Кирилл)

## Точка входа

```bash
python scripts/iteration4/run_i4.py
```

Запускает подряд: bridge (I4-K-03) → controls (I4-K-04) → benchmark (I4-K-07/08)  
и пишет сводку `data/processed/i4/i4_run_summary.json`.

## Сводка по задачам

| Код | Результат |
|-----|-----------|
| I4-K-01 | Проект resource MILP + greedy по G2 |
| I4-K-02 | Модуль `resource_milp.py` |
| I4-K-03 | Bridge + журнал явного q, без warm-start |
| I4-K-04 | base 2.50 / deficit infeasible / changed_q 2.35 |
| I4-K-05 | `method_config.json` |
| I4-K-06 | Комплект метода готов |
| I4-K-07 | `run_benchmark.py` |
| I4-K-08 | `benchmark_control.json`, all_passed |

## Граница контура

Это **полноценный контур итерации 4 на учебных сценариях Алексея** (G2).  
Это **не** полный промышленный пайплайн от сырых XLS завода и не ML-ветка.

## Документы задач

`docs/iteration4/I4-K-01_design.md` … `I4-K-08_benchmark_collect.md`
