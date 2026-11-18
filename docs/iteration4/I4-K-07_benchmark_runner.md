# I4-K-07 — Автоматический запуск benchmark

Исполнитель: Кирилл Ельцов  
Код: `scripts/iteration4/run_benchmark.py`

## Результат

Есть автоматический runner:

- читает `method_config.json` + `scenarios_v1.json`;
- гоняет `resource_milp` и `greedy_quality`;
- 4 повтора для времени (медиана/мин/макс);
- бюджет 120 с;
- пишет `data/processed/i4/benchmark_control.json`.

Текущий набор — контрольный (3 учебных сценария). Масштабная серия отдельно не запускалась и не заявляется.

## Критерии

- [x] Исполняемый автоматический запуск с конфигом и журналом.

## Как проверить

```bash
python scripts/iteration4/run_benchmark.py
```
