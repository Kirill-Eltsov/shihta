# I4-K-05 — Интеграция и воспроизводимая конфигурация

Исполнитель: Кирилл Ельцов  
Конфиг: `data/processed/i4/method_config.json`

## Результат

Зафиксирован `config_id=i4_resource_milp_v1`:

- scenarios hash = hash Алексея I4-A-01;
- time_budget_s=120, repetitions_deterministic=4, threads=1;
- `warm_start=false`, `ml=false`, `silent_q_fallback=false`;
- допуски ресурса/цели как в I4-A-03;
- пути модуля, bridge, controls и benchmark runner.

Повтор контрольного контура одной командой: `python scripts/iteration4/run_i4.py`.

## Критерии

- [x] Конфигурация сохранена и достаточна для повтора.
- [x] Интеграция воспроизводима без ручной подстройки параметров.

## Как проверить

```bash
python -c "import json; print(json.load(open('data/processed/i4/method_config.json',encoding='utf-8'))['config_id'])"
python scripts/iteration4/run_i4.py
```
