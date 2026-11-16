"""Идемпотентная загрузка CSV с возвратами в слой RAW.

Повторный запуск за ту же дату не создаёт дубликаты: строки батча
удаляются по batch_id и вставляются заново.

Параметры подключения берутся из переменных окружения или из .env
в корне репозитория. Пароль в коде не хранится.
"""

import argparse
import sys
from pathlib import Path

import pandas as pd
import psycopg2

try:  # запуск как модуль: python -m ingestion.load_returns
    from .db import ROOT, db_config, load_env
except ImportError:  # запуск как скрипт: python ingestion/load_returns.py
    from db import ROOT, db_config, load_env

REQUIRED_COLUMNS = {
    "return_id",
    "order_id",
    "return_date",
    "return_reason",
    "refund_amount",
}


def load_returns(date_str: str, file_path: Path | None = None) -> int:
    file_path = file_path or ROOT / "data" / "returns" / "incoming" / f"returns_{date_str}.csv"
    batch_id = f"returns_{date_str}"

    if not file_path.exists():
        print(f"ОШИБКА: файл {file_path} не найден!", file=sys.stderr)
        return 1

    print(f"--> Читаем файл {file_path}")
    df = pd.read_csv(file_path)

    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        print(f"ОШИБКА: в файле нет колонок: {', '.join(sorted(missing))}", file=sys.stderr)
        return 1

    rows = [
        (
            row.return_id,
            row.order_id,
            row.return_date,
            row.return_reason,
            None if pd.isna(row.refund_amount) else row.refund_amount,
            "returns_csv",
            batch_id,
        )
        for row in df.itertuples(index=False)
    ]

    conn = psycopg2.connect(**db_config())
    try:
        with conn, conn.cursor() as cursor:
            # Идемпотентность: сначала убираем прошлую версию этого батча.
            cursor.execute("DELETE FROM raw.raw_returns WHERE batch_id = %s", (batch_id,))
            cursor.executemany(
                """
                INSERT INTO raw.raw_returns
                    (return_id, order_id, return_date, return_reason,
                     refund_amount, source_system, batch_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                rows,
            )
            cursor.execute(
                "SELECT COUNT(*) FROM raw.raw_returns WHERE batch_id = %s",
                (batch_id,),
            )
            count = cursor.fetchone()[0]
    except psycopg2.Error as exc:
        print(f"ОШИБКА при вставке: {exc}", file=sys.stderr)
        print("Подсказка: примените sql/init_raw.sql, чтобы создать схему raw.", file=sys.stderr)
        return 1
    finally:
        conn.close()

    print(f"Успех! Загружено {len(rows)} строк. В raw.raw_returns за батч {batch_id}: {count}.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Загрузка возвратов в слой RAW")
    parser.add_argument("--date", required=True, help="Дата файла в формате YYYY-MM-DD")
    args = parser.parse_args()
    load_env()
    return load_returns(args.date)


if __name__ == "__main__":
    sys.exit(main())
