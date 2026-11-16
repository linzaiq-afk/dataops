# Источники данных

Проект использует три типа источников, как требует ТЗ.

| Источник | Тип | URL / путь | Что забираем | Частота | Техполя при загрузке |
|---|---|---|---|---|---|
| Olist → PostgreSQL | РСУБД | `ops.customers`, `ops.orders` в контейнере `postgres` | customers, orders | daily | `ingestion_timestamp`, `source_system`, `batch_id` |
| DummyJSON | REST API | https://dummyjson.com/products?limit=100 | products, price, stock, rating, availability | daily | `ingestion_timestamp`, `source_system`, `batch_id` |
| Returns CSV | File | `data/returns/incoming/returns_YYYY-MM-DD.csv` | return_id, order_id, return_date, return_reason, refund_amount | daily | `ingestion_timestamp`, `source_system`, `batch_id` |

## Детали

### 1. PostgreSQL (ops)

Полный датасет Olist скачивается с Kaggle и **не коммитится** в Git.
В репозитории лежат только sample-файлы по 200 строк:

- `data/samples/customers_sample.csv`
- `data/samples/orders_sample.csv`

Таблицы создаются скриптом `sql/init_ops.sql`, sample-данные загружаются через `COPY`.

### 2. DummyJSON API

Загрузчик: `ingestion/load_inventory.py`.
Пишет в `raw.raw_inventory`, batch_id по умолчанию `inventory_YYYY-MM-DD`.

### 3. Returns CSV

Файлы генерируются скриптом `scripts/generate_returns.py` на основе `orders_sample.csv`.
Загрузчик: `ingestion/load_returns.py`, пишет в `raw.raw_returns`.
Повторный запуск за ту же дату удаляет строки этого batch_id и вставляет их заново — дубликатов нет.
