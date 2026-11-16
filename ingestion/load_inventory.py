"""Загрузка товаров/остатков из DummyJSON в raw.raw_inventory.

Источник: https://dummyjson.com/products?limit=100
Повторный запуск с тем же batch_id не создаёт дубликаты.
"""

import argparse
import json
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone

import psycopg2

try:
    from .db import db_config, load_env
except ImportError:
    from db import db_config, load_env

DEFAULT_URL = "https://dummyjson.com/products?limit=100"


def fetch_products(url: str) -> list[dict]:
    request = urllib.request.Request(url, headers={"User-Agent": "dataops-lab/1.0"})
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = json.loads(response.read().decode("utf-8"))
    return payload.get("products", [])


def load_inventory(url: str, batch_id: str) -> int:
    print(f"--> Загружаем {url}")
    try:
        products = fetch_products(url)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        print(f"ОШИБКА при запросе к API: {exc}", file=sys.stderr)
        return 1

    if not products:
        print("ОШИБКА: API вернул пустой список товаров.", file=sys.stderr)
        return 1

    rows = [
        (
            item.get("id"),
            item.get("title"),
            item.get("price"),
            item.get("stock"),
            item.get("rating"),
            item.get("availabilityStatus"),
            "dummyjson",
            batch_id,
        )
        for item in products
    ]

    conn = psycopg2.connect(**db_config())
    try:
        with conn, conn.cursor() as cursor:
            cursor.execute("DELETE FROM raw.raw_inventory WHERE batch_id = %s", (batch_id,))
            cursor.executemany(
                """
                INSERT INTO raw.raw_inventory
                    (product_id, title, price, stock, rating,
                     availability_status, source_system, batch_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                rows,
            )
            cursor.execute(
                "SELECT COUNT(*) FROM raw.raw_inventory WHERE batch_id = %s",
                (batch_id,),
            )
            count = cursor.fetchone()[0]
    except psycopg2.Error as exc:
        print(f"ОШИБКА при вставке: {exc}", file=sys.stderr)
        print("Подсказка: примените sql/init_raw.sql, чтобы создать схему raw.", file=sys.stderr)
        return 1
    finally:
        conn.close()

    print(f"Успех! Загружено {len(rows)} товаров. В raw.raw_inventory за батч {batch_id}: {count}.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Загрузка товаров DummyJSON в слой RAW")
    parser.add_argument("--url", default=DEFAULT_URL, help="URL API DummyJSON")
    parser.add_argument(
        "--batch-id",
        default=datetime.now(timezone.utc).strftime("inventory_%Y-%m-%d"),
        help="Идентификатор батча (по умолчанию — текущая дата)",
    )
    args = parser.parse_args()
    load_env()
    return load_inventory(args.url, args.batch_id)


if __name__ == "__main__":
    sys.exit(main())
