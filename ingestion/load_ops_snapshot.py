"""Снимок операционной PostgreSQL (ops) в слой RAW.

Копирует customers и orders, добавляет технические поля
source_system, batch_id и ingestion_timestamp.
Повторный запуск с тем же batch_id идемпотентен.
"""

import argparse
import sys
from datetime import datetime, timezone

import psycopg2

try:
    from .db import db_config, load_env
except ImportError:
    from db import db_config, load_env

TABLES = [
    (
        "customers",
        "raw_customers",
        [
            "customer_id",
            "customer_unique_id",
            "customer_zip_code_prefix",
            "customer_city",
            "customer_state",
        ],
    ),
    (
        "orders",
        "raw_orders",
        [
            "order_id",
            "customer_id",
            "order_status",
            "order_purchase_timestamp",
            "order_approved_at",
            "order_delivered_carrier_date",
            "order_delivered_customer_date",
            "order_estimated_delivery_date",
        ],
    ),
]


def load_ops_snapshot(batch_id: str) -> int:
    conn = psycopg2.connect(**db_config())
    total = 0
    try:
        with conn, conn.cursor() as cursor:
            for source_table, raw_table, columns in TABLES:
                column_list = ", ".join(columns)

                cursor.execute(f"DELETE FROM raw.{raw_table} WHERE batch_id = %s", (batch_id,))
                cursor.execute(
                    f"""
                    INSERT INTO raw.{raw_table} ({column_list}, source_system, batch_id)
                    SELECT {column_list}, 'ops_postgres', %s
                    FROM ops.{source_table}
                    """,
                    (batch_id,),
                )
                loaded = cursor.rowcount
                total += loaded
                print(f"OK   ops.{source_table} -> raw.{raw_table}: {loaded} строк")

        if total == 0:
            print("ОШИБКА: ops.customers/ops.orders пусты. Загрузите sample-данные из лабы 2.", file=sys.stderr)
            return 1
    except psycopg2.Error as exc:
        print(f"ОШИБКА при снимке ops: {exc}", file=sys.stderr)
        print("Подсказка: примените sql/init_ops.sql и sql/init_raw.sql.", file=sys.stderr)
        return 1
    finally:
        conn.close()

    print(f"Успех! Снимок ops загружен в RAW. Batch ID: {batch_id}, всего строк: {total}.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Снимок ops.customers/orders в RAW")
    parser.add_argument(
        "--batch-id",
        default=datetime.now(timezone.utc).strftime("ops_%Y-%m-%d"),
        help="Идентификатор батча (по умолчанию — текущая дата)",
    )
    args = parser.parse_args()
    load_env()
    return load_ops_snapshot(args.batch_id)


if __name__ == "__main__":
    sys.exit(main())
