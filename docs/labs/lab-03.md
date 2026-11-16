# Лабораторная №3 — Data Pipelines и оркестрация

## Цель

Сделать идемпотентную загрузку данных, генератор CSV и оркестрацию pipeline
с зависимостями, retry и timeout.

## Что сделано

### Задание A. Идемпотентная загрузка

Файл: `ingestion/load_returns.py`.

- читает `data/returns/incoming/returns_YYYY-MM-DD.csv`;
- проверяет наличие обязательных колонок;
- пишет в `raw.raw_returns`;
- добавляет `source_system='returns_csv'`, `batch_id='returns_YYYY-MM-DD'`,
  `ingestion_timestamp` (default `NOW()`);
- **идемпотентность:** перед вставкой выполняет
  `DELETE FROM raw.raw_returns WHERE batch_id = %s`, затем вставляет батч заново.

Дополнительно реализованы загрузчики:

- `ingestion/load_ops_snapshot.py` — снимок `ops.customers` и `ops.orders` в
  `raw.raw_customers` / `raw.raw_orders`;
- `ingestion/load_inventory.py` — товары и остатки из DummyJSON в
  `raw.raw_inventory`.

Все три загрузчика используют один batch_id на запуск и не создают дубликаты
при повторном запуске.

### Задание B. Генератор возвратов

Файл: `scripts/generate_returns.py`.

- берёт 5% строк из `data/samples/orders_sample.csv`;
- генерирует `return_id`, `return_reason`, `refund_amount`;
- `return_date = order_date + 1..10 дней`, то есть `return_date >= order_date`;
- раскладывает результат по файлам `returns_YYYY-MM-DD.csv`.

### Задание C. DAG

Файл: `dag_orchestrator.py` — учебная замена Airflow (практика 3 допускает
Makefile/bash/свой оркестратор с описанием перехода на Airflow).

```text
load_ops_snapshot
    → load_api_inventory
    → load_returns
    → raw_quality_check
    → dbt_run
    → dbt_test
```

Реализовано:

- последовательные зависимости (следующий шаг только после успеха предыдущего);
- `--retries 2` — до трёх попыток на задачу;
- `--timeout 180` — timeout на каждую попытку;
- остановка pipeline с кодом 1 после исчерпания повторов;
- логирование каждого шага и кода возврата.

Проверка RAW: `scripts/raw_quality_check.py` проверяет наличие данных,
неотрицательный `refund_amount`, заполненный `order_id`, отсутствие дублей.

### Задание D. Сбой и retry

Демонстрация:

```powershell
python ingestion/load_returns.py --date 2099-01-01
```

Скрипт завершается с ошибкой «файл не найден». В оркестраторе задача
`load_returns` сделает повторы и остановит pipeline. После указания
существующей даты pipeline проходит, а повторный запуск не создаёт дубликатов.

## Как воспроизвести

```powershell
python -m pip install -r requirements.txt
# PostgreSQL из лабы 2 должен быть запущен, sample-данные загружены

python scripts/generate_returns.py
python ingestion/load_returns.py --date 2017-04-02
python ingestion/load_returns.py --date 2017-04-02   # повторно

docker compose exec postgres psql -U dataops -d shop -c "SELECT batch_id, COUNT(*) FROM raw.raw_returns GROUP BY batch_id ORDER BY batch_id;"

python scripts/raw_quality_check.py
python dag_orchestrator.py --date 2017-04-02
```

Ожидаемо: после двух запусков `load_returns` количество строк за
`returns_2017-04-02` не удваивается, а остаётся равным числу строк в CSV.

## Результат

- Pull Request: [#2 Lab 3: Data Pipelines and Orchestration](https://github.com/linzaiq-afk/dataops/pull/2)
- Ветка: `lab-03`
- Коммит: `458e032 feat: add idempotent ingestion, returns generator, and dag orchestrator for lab 3`

## Вопросы на защите

**Что такое идемпотентность?**
Свойство операции: повторный запуск даёт тот же результат, что и первый.
Здесь повторная загрузка файла за дату не увеличивает количество строк,
потому что старый батч удаляется по `batch_id` и вставляется заново.

**Почему delete + insert, а не append?**
Append при повторном запуске создаёт дубликаты. Delete + insert прост и
предсказуем для небольшого дневного файла. Для больших данных лучше MERGE/upsert.

**Чем batch_id отличается от ingestion_timestamp?**
`batch_id` — логический идентификатор запуска/файла, по нему удобно удалять и
перезагружать батч. `ingestion_timestamp` — точное время фактической вставки.

**Где retry и timeout?**
В `dag_orchestrator.py`: `--retries` (по умолчанию 2) и `--timeout` на попытку.
При ошибке команда повторяется, после исчерпания попыток pipeline падает.

**Почему не Airflow?**
По условию практики 3 на этом этапе допустима замена. Оркестратор повторяет
граф зависимостей на Python. Переход на Airflow: те же шаги оформляются как
`PythonOperator`/`BashOperator`, retry и timeout задаются параметрами DAG.

**Как проверяется качество RAW?**
`raw_quality_check.py` запускается до dbt и возвращает код 1, если данные
отсутствуют, есть отрицательный возврат, пустой `order_id` или дубли.
