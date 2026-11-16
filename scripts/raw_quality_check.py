"""Базовые проверки качества слоя RAW перед запуском dbt.

Скрипт возвращает код 1, если хотя бы одна проверка не прошла.
"""

import sys
from pathlib import Path

import psycopg2

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ingestion.db import db_config, load_env  # noqa: E402


CHECKS = [
    (
        "raw_returns: есть данные",
        "SELECT COUNT(*) FROM raw.raw_returns",
        lambda value: value > 0,
    ),
    (
        "raw_inventory: есть данные",
        "SELECT COUNT(*) FROM raw.raw_inventory",
        lambda value: value > 0,
    ),
    (
        "raw_returns: refund_amount >= 0",
        "SELECT COUNT(*) FROM raw.raw_returns WHERE refund_amount < 0",
        lambda value: value == 0,
    ),
    (
        "raw_returns: order_id заполнен",
        "SELECT COUNT(*) FROM raw.raw_returns WHERE order_id IS NULL",
        lambda value: value == 0,
    ),
    (
        "raw_returns: нет дублей return_id в батче",
        """
        SELECT COUNT(*) FROM (
            SELECT return_id, batch_id
            FROM raw.raw_returns
            GROUP BY return_id, batch_id
            HAVING COUNT(*) > 1
        ) AS duplicates
        """,
        lambda value: value == 0,
    ),
]


def main() -> int:
    load_env()
    conn = psycopg2.connect(**db_config())
    failed = 0
    try:
        with conn.cursor() as cursor:
            for name, query, predicate in CHECKS:
                cursor.execute(query)
                value = cursor.fetchone()[0]
                ok = predicate(value)
                print(f"{'OK  ' if ok else 'FAIL'} {name}: {value}")
                if not ok:
                    failed += 1
    except psycopg2.Error as exc:
        print(f"FAIL не удалось выполнить проверки: {exc}", file=sys.stderr)
        return 1
    finally:
        conn.close()

    if failed:
        print(f"Проверки не пройдены: {failed}. Pipeline должен остановиться.", file=sys.stderr)
        return 1
    print("Все проверки RAW пройдены.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
