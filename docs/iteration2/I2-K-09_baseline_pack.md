# I2-K-09 — Воспроизводимый комплект baseline (учебный)

Исполнитель: Кирилл Ельцов

## Состав комплекта

| Элемент | Путь |
|---------|------|
| Входы CSV | `data/processed/zakazy.csv`, `recepty.csv`, `kachestvo.csv` |
| Загрузчик / registry | `scripts/i2_k01_loader.py`, `data/processed/loader/` |
| Нормализация | `data/processed/normalized/` |
| Кандидаты | `data/processed/candidates/` |
| MILP solve | `data/processed/milp/edu_solve.json`, `edu_assign.csv` |
| Журнал решателя | `data/processed/milp/solver_journal.json` |
| Toy validation | `data/processed/milp/validate_toy.json` |

## Повторяемость

Другой участник:

```bash
python scripts/i2_k01_loader.py
python scripts/i2_k04_reproduce_load.py
python scripts/i2_k06_milp.py
python scripts/i2_k07_solver_journal.py
python scripts/i2_k08_validate.py
```

## Явные ограничения

1. Комплект помечен как **educational**, не как подтверждённый промышленный baseline notebook Данила.
2. Промышленные коэффициенты/запасы из Colab-сценария **не смешаны** с этим комплектом.
3. Отсутствие полного локального прогона notebook зафиксировано (I1-K-03 / I2-K-07).

## Критерии

- [x] Входы, настройки, журналы и результаты контрольной модели сохранены.
- [x] Недостаток промышленного baseline обозначен явно.
