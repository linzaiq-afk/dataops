# Подготовка к защите лаб 2–4

Шпаргалка: что рассказывать, что показывать и что отвечать на вопросы.
Все команды выполняются из корня репозитория.

---

## 1. Как рассказать за 2–3 минуты

### Лаба 2

> Мы спроектировали три источника: PostgreSQL с Olist, DummyJSON API и CSV с
> возвратами. Построили слои RAW → STAGING → CORE → MART → BI. Подняли
> PostgreSQL 16 в Docker Compose, создали схему `ops`, загрузили по 200 строк
> customers и orders через `COPY` и проверили связь JOIN — 200 совпадений.
> Секреты вынесены в `.env`, в Git лежит только `.env.example`.

### Лаба 3

> Сделали идемпотентную загрузку возвратов: скрипт читает дневной CSV, удаляет
> прошлый батч по `batch_id` и вставляет новый, поэтому повторный запуск не
> плодит дубликаты. Добавили загрузчики ops и DummyJSON. Собрали оркестратор:
> шаги идут по зависимостям, у каждой задачи есть retry и timeout, при ошибке
> pipeline останавливается. Проверили сценарий сбоя: несуществующая дата →
> ошибка → pipeline падает → после исправления успешный повтор без дублей.

### Лаба 4

> Перевели трансформации в dbt: описали source на RAW, сделали модель
> `stg_orders` с приведением типов и переименованиями, добавили описания колонок
> и тесты `not_null`/`unique`. Отработали schema change: в модели было старое имя
> колонки, dbt run упал, ошибку локализовали и исправили, прогнали run и test.
> Работали через issue #3 и ветку, предыдущие лабы — через PR #1 и #2.
> Пароли в Git не хранятся: `.env` и `profiles.yml` в `.gitignore`.

---

## 2. Что показать на экране

### Структура репозитория

```powershell
git log --oneline --graph --decorate -15
git branch -a
```

Обратить внимание: `main` содержит все лабы, есть ветки `lab-02`, `lab-03`,
`lab-04`, merge-коммиты PR.

### Лаба 2

```powershell
docker compose ps
docker compose exec postgres psql -U dataops -d shop -c "SELECT COUNT(*) FROM ops.customers;"
docker compose exec postgres psql -U dataops -d shop -c "SELECT COUNT(*) FROM ops.orders;"
docker compose exec postgres psql -U dataops -d shop -c "SELECT COUNT(*) FROM ops.orders o JOIN ops.customers c ON o.customer_id = c.customer_id;"
```

Ожидаемо: 200 / 200 / 200.

### Лаба 3

```powershell
python ingestion/load_returns.py --date 2017-04-02
python ingestion/load_returns.py --date 2017-04-02
docker compose exec postgres psql -U dataops -d shop -c "SELECT batch_id, COUNT(*) FROM raw.raw_returns GROUP BY batch_id ORDER BY batch_id;"
```

Ключевая фраза: «запустили дважды — количество не удвоилось, потому что
delete + insert по batch_id».

Сбой:

```powershell
python ingestion/load_returns.py --date 2099-01-01
```

Показать ненулевой код возврата и сообщение «файл не найден».

Оркестратор:

```powershell
python dag_orchestrator.py --date 2017-04-02
```

Показать шаги, retry, timeout и остановку при ошибке.

### Лаба 4

```powershell
dbt debug --project-dir dbt --profiles-dir dbt
dbt run --project-dir dbt --profiles-dir dbt --select stg_orders
dbt test --project-dir dbt --profiles-dir dbt --select stg_orders
```

Показать `dbt/models/staging/stg_orders.sql`: `source('raw', 'raw_orders')`,
`CAST`, переименования. Показать `schema.yml`: описания и тесты.

---

## 3. Вопросы и короткие ответы

### Общие вопросы по DataOps

**Что такое DataOps?**
Набор практик, который делает работу с данными воспроизводимой и управляемой:
версионирование кода, автоматизация pipeline, тесты качества, мониторинг,
документация и быстрая реакция на сбои.

**Чем DataOps отличается от обычного ETL?**
ETL — это процесс перемещения данных. DataOps добавляет инженерный контур:
Git, CI/CD, тесты, observability, lineage, управление изменениями.

**Почему ELT, а не ETL?**
Сначала грузим сырые данные в RAW (EL), затем преобразуем внутри БД через dbt (T).
Так проще перезапускать преобразования и хранить историю сырых данных.

**Что такое слой RAW?**
Снимок данных источника почти без изменений плюс технические поля
`ingestion_timestamp`, `source_system`, `batch_id`. Нужен, чтобы можно было
пересобрать STAGING/CORE/MART без повторной загрузки источника.

**Что такое идемпотентность?**
Повторный запуск операции не меняет результат и не создаёт дубликаты.
В лабе 3: удаляем батч по `batch_id` и вставляем заново.

**Что такое freshness?**
Насколько данные актуальны: когда последний раз успешно загружался источник.
Проверяется по `ingestion_timestamp`; в следующих лабах — через dbt source freshness.

### Лаба 2

**Почему PostgreSQL — операционная БД, а не хранилище?**
По ТЗ Olist загружается в PostgreSQL и рассматривается как система интернет-магазина.
Дальше из неё данные попадают в RAW и преобразуются.

**Почему sample 200 строк?**
Полный Olist слишком большой для Git. Sample достаточен, чтобы проверить схему,
загрузку и JOIN. Полный датасет каждый загружает локально.

**Почему JOIN даёт 200, а не больше?**
В sample по 200 уникальных customers и orders, каждый заказ ссылается на одного
покупателя, поэтому 200 совпадений.

**Что будет, если загрузить `orders` без `customers`?**
JOIN не найдёт связи, а проверка referential integrity в следующих лабах упадёт.
Поэтому sample загружаются вместе.

**Зачем технические поля?**
По ним видно, откуда пришли данные, когда и в каком запуске. Это основа
lineage, повторной загрузки и диагностики.

### Лаба 3

**Как устроен DAG?**
Шаги выполняются последовательно: снимок ops → API → returns → проверка RAW →
dbt run → dbt test. Следующий шаг запускается только после успеха предыдущего.

**Где retry и timeout?**
В `dag_orchestrator.py`: `--retries` (по умолчанию 2) и `--timeout` на попытку.
После исчерпания попыток pipeline завершается с кодом 1.

**Что будет, если API недоступен?**
`load_inventory.py` вернёт код 1, оркестратор сделает повторы и остановит
pipeline. Данные не пойдут в dbt, чтобы не публиковать неполные витрины.

**Почему delete + insert, а не upsert?**
Для дневного файла небольшого размера delete + insert проще и предсказуемее.
Для больших объёмов и конкурентной записи лучше MERGE/upsert или staging-таблица
с последующим merge.

**Как проверяли отсутствие дублей?**
Запустили загрузку дважды и сравнили `COUNT(*)` по batch_id: число не удвоилось.
Плюс `raw_quality_check.py` проверяет дубли по `(return_id, batch_id)`.

**Почему оркестратор, а не Airflow?**
По условию практики 3 на этом этапе допустима замена. Граф, retry и timeout
реализованы явно; переход на Airflow — это перенос тех же шагов в
`PythonOperator`/`BashOperator` с параметрами DAG.

**Что такое batch_id?**
Идентификатор одного запуска/файла. По нему удобно удалить и перезагрузить
именно этот батч, не затрагивая остальные.

### Лаба 4

**Что такое dbt?**
Инструмент Analytics as Code: SQL-модели, источники, тесты, документация и
граф зависимостей. dbt компилирует модели и выполняет их в БД.

**Чем `source()` отличается от `ref()`?**
`source()` — внешняя таблица, которой dbt не управляет. `ref()` — другая модель
dbt; по `ref()` dbt строит граф и запускает модели в правильном порядке.

**Что такое schema change drill?**
Учебная имитация переименования колонки в источнике. Старый код падает с
«column does not exist»; нужно найти модель, исправить, прогнать run/test и
провести изменение через Git.

**Почему `profiles.yml` не в Git?**
Там пароль и параметры подключения. В репозитории шаблон
`profiles.yml.example`, реальный файл создаётся локально.

**Где ещё могли остаться секреты?**
Проверяли `git grep` и историю: в старой версии `load_returns.py` был пароль,
сейчас он убран, параметры берутся из `.env`. В `.env.example` заглушка.

**Какие тесты есть в dbt?**
`not_null` и `unique` для `order_id`. Этого мало для полного ТЗ (нужно 10+
тестов разных измерений), это план следующих лаб.

**Что произойдёт при повторном `dbt run`?**
Модель материализуется как view и пересоздаётся; повторный запуск безопасен.

---

## 4. Слабые места и что честно сказать

Не пытайтесь выдать нереализованное за готовое. Лучше сказать «это следующий шаг»
и объяснить, как будете делать.

| Вопрос | Честный ответ |
|---|---|
| Где CORE и MART? | Пока реализованы RAW и STAGING, CORE/MART — следующие лабы. Схема и имена таблиц уже спроектированы. |
| Где Airflow? | Используется учебный оркестратор по условию практики 3; переход на Airflow описан. |
| Где CI/CD? | Появится в лабе 5; сейчас есть Git-история, ветки и PR. |
| Почему только 2 dbt-теста? | Это лаба 4; 10+ тестов по разным измерениям — лаба 6. |
| Где дашборд? | BI — следующий этап; витрины MART ещё не построены. |
| Почему нет PR для лабы 4? | Issue #3 и ветка есть; полный PR-цикл показан в лабах 2 и 3. Можно оформить PR задним числом. |

---

## 5. Быстрая проверка перед защитой

```powershell
# 1. Git чистый и всё запушено
git status
git log --oneline -5

# 2. PostgreSQL запущен
docker compose ps

# 3. Лаба 2: данные на месте
docker compose exec postgres psql -U dataops -d shop -c "SELECT COUNT(*) FROM ops.customers;"
docker compose exec postgres psql -U dataops -d shop -c "SELECT COUNT(*) FROM ops.orders;"

# 4. Лаба 3: идемпотентность
python ingestion/load_returns.py --date 2017-04-02
python ingestion/load_returns.py --date 2017-04-02
docker compose exec postgres psql -U dataops -d shop -c "SELECT COUNT(*) FROM raw.raw_returns WHERE batch_id = 'returns_2017-04-02';"

# 5. Лаба 4: dbt
dbt run --project-dir dbt --profiles-dir dbt --select stg_orders
dbt test --project-dir dbt --profiles-dir dbt --select stg_orders
```

Если Docker не запущен — запустите Docker Desktop и `docker compose up -d`.
Если dbt не видит пароль — проверьте, что переменная `POSTGRES_PASSWORD`
установлена в текущей сессии PowerShell.
