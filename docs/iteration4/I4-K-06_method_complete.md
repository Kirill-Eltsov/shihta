# I4-K-06 — Завершение реализации одного выбранного метода

Исполнитель: Кирилл Ельцов

## Результат

Линия T14 (K) закрыта по содержимому: один метод G2 готов к независимой проверке Алексеем.

| Артефакт | Путь |
|----------|------|
| Проект | `docs/iteration4/I4-K-01_design.md` |
| Модуль | `scripts/iteration4/resource_milp.py` |
| Bridge | `scripts/iteration4/milp_bridge.py` |
| Контроли | `data/processed/i4/k_control_results.json` |
| Конфиг | `data/processed/i4/method_config.json` |
| Точка входа | `scripts/iteration4/run_i4.py` |

Не заявлено: ML, warm-start, промышленный масштаб, ускорение.

## Критерии

- [x] Один основной метод реализован end-to-end на контрольном наборе.
- [x] Ограничения G2 соблюдены.

## Как проверить

```bash
python scripts/iteration4/run_i4.py
```
