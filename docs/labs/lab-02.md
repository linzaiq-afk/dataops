# Лабораторная №2 — жизненный цикл данных и PostgreSQL

## Цель

Спроектировать источники, слои данных и контуры pipeline для интернет-магазина,
а также поднять PostgreSQL и загрузить sample-данные Olist.

## Что сделано

### Задание A. Три источника

Описаны в [docs/sources.md](../sources.md):

1. **PostgreSQL** — операционная БД `shop`, таблицы `ops.customers` и `ops.orders`.
2. **DummyJSON API** — товары, цены, остатки.
3. **Returns CSV** — ежедневные файлы возвратов.

Для каждого источника зафиксированы частота загрузки и технические поля:
`ingestion_timestamp`, `source_system`, `batch_id`.

### Задание B. Схема слоёв

В [docs/architecture.md](../architecture.md) описана цепочка:

```text
Sources → Ingestion → RAW → STAGING → CORE → MART → BI
```

Спроектированы таблицы:

- RAW: `raw_orders`, `raw_customers`, `raw_returns`, `raw_inventory`;
- STAGING: `stg_orders`, `stg_customers`, `stg_returns`;
- CORE: `fact_orders`, `dim_customers`, `dim_products`, `fact_returns`;
- MART: `mart_sales_daily`, `mart_product_performance`, `mart_customer_metrics`.

### Задание C. Три контура pipeline

- **Production** — ежедневный запуск: загрузка → RAW → STAGING → CORE → MART → BI,
  с retry и логированием.
- **Development** — ветка → коммиты → Pull Request → проверка → merge.
- **Environment** — DEV на sample-данных, CI на проверках, PROD на полных данных.

### Задание D. Docker + PostgreSQL

- `docker-compose.yml` поднимает PostgreSQL 16.
- `sql/init_ops.sql` создаёт схему `ops` и таблицы `customers`, `orders`.
- Sample-данные: `data/samples/customers_sample.csv` и
  `data/samples/orders_sample.csv` — по 200 строк.
- Загрузка выполнена через `COPY`, проверена JOIN-запросом.

## Как воспроизвести

```powershell
Copy-Item .env.example .env
# задать POSTGRES_PASSWORD в .env
docker compose up -d

Get-Content -Raw sql/init_ops.sql | docker compose exec -T postgres psql -v ON_ERROR_STOP=1 -U dataops -d shop

docker compose cp data/samples/customers_sample.csv postgres:/tmp/customers_sample.csv
docker compose cp data/samples/orders_sample.csv postgres:/tmp/orders_sample.csv
docker compose exec postgres psql -U dataops -d shop -c "COPY ops.customers FROM '/tmp/customers_sample.csv' WITH (FORMAT csv, HEADER true);"
docker compose exec postgres psql -U dataops -d shop -c "COPY ops.orders FROM '/tmp/orders_sample.csv' WITH (FORMAT csv, HEADER true);"

docker compose exec postgres psql -U dataops -d shop -c "SELECT COUNT(*) FROM ops.customers;"
docker compose exec postgres psql -U dataops -d shop -c "SELECT COUNT(*) FROM ops.orders;"
docker compose exec postgres psql -U dataops -d shop -c "SELECT COUNT(*) FROM ops.orders o JOIN ops.customers c ON o.customer_id = c.customer_id;"
```

Ожидаемый результат: 200, 200 и 200.

## Результат

- Pull Request: [#1 Lab 2: Data Lifecycle and PostgreSQL setup](https://github.com/linzaiq-afk/dataops/pull/1)
- Ветка: `lab-02`
- PostgreSQL запускается через Docker Compose, sample-данные загружены,
  связи между заказами и покупателями проверены.

## Вопросы на защите

**Почему три источника?**
По ТЗ нужны разные типы: РСУБД, REST API и файлы. Они проверяют разные сценарии
загрузки: снимок таблиц, HTTP-запрос и обработку появляющихся файлов.

**Зачем слои RAW / STAGING / CORE / MART?**
RAW хранит данные как пришли (плюс техполя) — можно перезапустить преобразования.
STAGING очищает и приводит типы. CORE содержит бизнес-сущности (факты и измерения).
MART — готовые витрины для BI.

**Почему sample, а не весь Olist?**
Полный датасет большой и не должен попадать в Git. В репозитории лежит sample
по 200 строк, полный набор каждый загружает локально по инструкции.

**Что если запустить загрузку дважды?**
На этом этапе sample загружается вручную через `COPY`; идемпотентность
реализована в лабе 3 для `raw_returns` (delete + insert по `batch_id`).

**Где хранятся секреты?**
Пароль в `.env`, файл в `.gitignore`. В репозитории только `.env.example`
с заглушкой `change_me`.
