# I2-K-01 — Загрузчик книг и реестр происхождения строк

Сформировано: 2026-11-05T19:32:19

- Ожидалось книг: **12**
- Загружено книг: **12**
- Загружено листов: **36** (цель 36)
- Отсутствующие файлы: нет
- Ошибки чтения: 0

Каждая строка CSV содержит `src_file`, `src_sheet`, `src_row`.

| Файл | Лист | Строк | CSV |
|------|------|-------|-----|
| Заказы.xls | март 2022 | 222 | `data/processed/loader/Заказы__март_2022.csv` |
| Заказы.xls | апрель 2022 | 180 | `data/processed/loader/Заказы__апрель_2022.csv` |
| Заказы.xls | май 2022 | 292 | `data/processed/loader/Заказы__май_2022.csv` |
| Шихта.xls | март 2022 | 6656 | `data/processed/loader/Шихта__март_2022.csv` |
| Шихта.xls | апрель 2022 | 5268 | `data/processed/loader/Шихта__апрель_2022.csv` |
| Шихта.xls | май 2022 | 5286 | `data/processed/loader/Шихта__май_2022.csv` |
| Линии дозирования.xls | март 2022 | 4054 | `data/processed/loader/Линии дозирования__март_2022.csv` |
| Линии дозирования.xls | аперль 2022 | 4075 | `data/processed/loader/Линии дозирования__аперль_2022.csv` |
| Линии дозирования.xls | май 2022 | 4440 | `data/processed/loader/Линии дозирования__май_2022.csv` |
| Прессовка.xls | март 2022 | 731 | `data/processed/loader/Прессовка__март_2022.csv` |
| Прессовка.xls | апрель 2022 | 691 | `data/processed/loader/Прессовка__апрель_2022.csv` |
| Прессовка.xls | май 2022 | 835 | `data/processed/loader/Прессовка__май_2022.csv` |
| Подача порошков.xls | март 2022 | 976 | `data/processed/loader/Подача порошков__март_2022.csv` |
| Подача порошков.xls | апрель 2022 | 991 | `data/processed/loader/Подача порошков__апрель_2022.csv` |
| Подача порошков.xls | май 2022 | 1061 | `data/processed/loader/Подача порошков__май_2022.csv` |
| Проценты.xls | март 2022 | 13 | `data/processed/loader/Проценты__март_2022.csv` |
| Проценты.xls | аперль 2022 | 13 | `data/processed/loader/Проценты__аперль_2022.csv` |
| Проценты.xls | май 2022 | 13 | `data/processed/loader/Проценты__май_2022.csv` |
| Сдача.xls | март 2022 | 657 | `data/processed/loader/Сдача__март_2022.csv` |
| Сдача.xls | апрель 2022 | 617 | `data/processed/loader/Сдача__апрель_2022.csv` |
| Сдача.xls | май 2022 | 1034 | `data/processed/loader/Сдача__май_2022.csv` |
| Садка.xls | март 2022 | 3305 | `data/processed/loader/Садка__март_2022.csv` |
| Садка.xls | апрель 2022 | 3460 | `data/processed/loader/Садка__апрель_2022.csv` |
| Садка.xls | май 2022 | 3593 | `data/processed/loader/Садка__май_2022.csv` |
| Печи.xls | март 2022 | 1808 | `data/processed/loader/Печи__март_2022.csv` |
| Печи.xls | апрель 2022 | 1680 | `data/processed/loader/Печи__апрель_2022.csv` |
| Печи.xls | май 2022 | 1900 | `data/processed/loader/Печи__май_2022.csv` |
| Простои.xls | март 2022 | 889 | `data/processed/loader/Простои__март_2022.csv` |
| Простои.xls | апрель 2022 | 940 | `data/processed/loader/Простои__апрель_2022.csv` |
| Простои.xls | май 2022 | 977 | `data/processed/loader/Простои__май_2022.csv` |
| Нормы прессовки.xls | март 2022 | 5873 | `data/processed/loader/Нормы прессовки__март_2022.csv` |
| Нормы прессовки.xls | апрель 2022 | 5873 | `data/processed/loader/Нормы прессовки__апрель_2022.csv` |
| Нормы прессовки.xls | май 2022 | 5874 | `data/processed/loader/Нормы прессовки__май_2022.csv` |
| Доп операции.xls | март 2022 | 1308 | `data/processed/loader/Доп операции__март_2022.csv` |
| Доп операции.xls | апрель 2022 | 1089 | `data/processed/loader/Доп операции__апрель_2022.csv` |
| Доп операции.xls | май 2022 | 1106 | `data/processed/loader/Доп операции__май_2022.csv` |

## Как проверить

```bash
python scripts/i2_k01_loader.py
python -c "import json; s=json.load(open('data/processed/loader/registry.json',encoding='utf-8')); print(s['loaded_books'], s['loaded_sheets'], s['missing_files'], s['errors'])"
```

Ожидание: 12 книг, 36 листов, пустые missing/errors.
