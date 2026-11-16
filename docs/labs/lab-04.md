# Лабораторная №4 — Analytics as Code, dbt и Git

## Цель

Перевести трансформации в dbt, хранить их в Git и провести schema change drill
через ветку и Pull Request.

## Что сделано

### Задание A. dbt-проект

Структура:

```text
dbt/
├── dbt_project.yml
├── profiles.yml.example
└── models/
    ├── sources.yml
    └── staging/
        ├── stg_orders.sql
        └── schema.yml
```

- `dbt_project.yml` — имя проекта `shop_dbt`, профиль `shop_dbt`.
- `sources.yml` — источники `raw.raw_orders`, `raw.raw_customers`,
  `raw.raw_returns`, `raw.raw_inventory`.
- `stg_orders.sql` — читает `source('raw', 'raw_orders')`, приводит timestamp-поля
  к `TIMESTAMP`, переименовывает `order_purchase_timestamp` → `purchased_at` и т.д.
- `schema.yml` — описание модели и колонок, тесты `not_null` и `unique` для
  `order_id`.

### Задание B. Git-flow

- Issue: [#3 Add stg_orders](https://github.com/linzaiq-afk/dataops/issues/3)
- Ветка: `lab-04`
- Коммит: `854ae52 feat: add dbt project, staging model, and complete schema change drill`

В репозитории также есть история предыдущих лаб через PR:

- PR [#1](https://github.com/linzaiq-afk/dataops/pull/1) — лаба 2;
- PR [#2](https://github.com/linzaiq-afk/dataops/pull/2) — лаба 3.

### Задание C. Schema change drill

Смоделировано переименование поля в источнике. В модели было указано
`order_state` вместо реального `order_status`, поэтому `dbt run` падал с ошибкой
вида `column "order_state" does not exist`.

Порядок действий:

1. **Обнаружение:** запуск `dbt run --select stg_orders` завершился ошибкой.
2. **Локализация:** ошибка в `dbt/models/staging/stg_orders.sql`, строка с
   `order_state AS order_status`.
3. **Исправление:** в ветке заменено на `order_status`, типы приведены через `CAST`.
4. **Проверка:** `dbt run` и `dbt test` проходят, модель создаётся.
5. **Git:** исправление закоммичено, ветка слита в `main`.

### Задание D. Секреты

- `.env` в `.gitignore`;
- `dbt/profiles.yml` в `.gitignore`, в репозитории только
  `dbt/profiles.yml.example` с `env_var('POSTGRES_PASSWORD')`;
- в `ingestion/load_returns.py` убран жёстко прописанный пароль: параметры
  подключения берутся из переменных окружения / `.env`.

## Как воспроизвести

```powershell
Copy-Item dbt/profiles.yml.example dbt/profiles.yml
$env:POSTGRES_PASSWORD = (Get-Content .env | Where-Object { $_ -match '^POSTGRES_PASSWORD=' }) -replace '^POSTGRES_PASSWORD=', ''

dbt debug --project-dir dbt --profiles-dir dbt
dbt run --project-dir dbt --profiles-dir dbt --select stg_orders
dbt test --project-dir dbt --profiles-dir dbt --select stg_orders
```

Перед `dbt run` таблица `raw.raw_orders` должна быть заполнена:

```powershell
python ingestion/load_ops_snapshot.py
# или весь pipeline:
python dag_orchestrator.py --date 2017-04-02
```

## Результат

- dbt-проект создан, `stg_orders` собирается из RAW;
- модель и колонки описаны;
- тесты `not_null` / `unique` для `order_id` проходят;
- исправление schema change закоммичено;
- секреты не хранятся в Git.

## Вопросы на защите

**Что такое Analytics as Code?**
Логика трансформаций хранится в виде кода (SQL-моделей dbt) в Git, а не
настраивается вручную в БД. Изменения проходят через коммит, ветку, PR и review,
поэтому их можно воспроизвести и откатить.

**Чем `source()` отличается от `ref()`?**
`source()` ссылается на исходную таблицу, которой dbt не управляет (например,
`raw.raw_orders`). `ref()` ссылается на другую dbt-модель и строит граф
зависимостей; dbt сам определяет порядок запуска.

**Что произойдёт, если переименовать колонку в источнике?**
Модель, которая обращается к старому имени, упадёт на этапе компиляции/выполнения
с ошибкой «column does not exist». Это и есть schema change. Исправление:
найти модель, обновить имя, прогнать `dbt run` и `dbt test`, провести через PR.

**Почему `profiles.yml` не в Git?**
В нём параметры подключения и пароль. В репозитории лежит шаблон
`profiles.yml.example`, а реальный файл каждый создаёт локально.

**Где пароль в Python-скриптах?**
В коде пароля нет. `ingestion/db.py` читает `.env` и переменные окружения,
поэтому один и тот же код работает локально и в CI.

**Как проверялась модель?**
`dbt run` создаёт `staging.stg_orders`, `dbt test` проверяет `order_id` на
`not_null` и `unique`. Плюс `raw_quality_check.py` проверяет RAW до запуска dbt.
