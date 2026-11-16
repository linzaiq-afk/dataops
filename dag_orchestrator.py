"""Учебный оркестратор pipeline ecommerce_daily.

Это облегчённая замена Airflow для лабораторной №3:
- явные зависимости между шагами (шаги выполняются последовательно);
- retries (по умолчанию 2 повтора на задачу);
- timeout на каждую попытку;
- остановка pipeline при ошибке;
- логирование каждого шага.

Граф:
load_ops_snapshot -> load_api_inventory -> load_returns
    -> raw_quality_check -> dbt_run -> dbt_test
"""

import argparse
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def run_task(task_name: str, command: list[str], retries: int, timeout: int) -> None:
    attempts = retries + 1
    for attempt in range(1, attempts + 1):
        print(f"\n[{task_name}] попытка {attempt}/{attempts}: {' '.join(command)}")
        try:
            result = subprocess.run(command, cwd=ROOT, timeout=timeout)
        except subprocess.TimeoutExpired:
            print(f"FAIL [{task_name}] timeout {timeout} секунд.")
            continue
        except FileNotFoundError as exc:
            print(f"FAIL [{task_name}] команда не найдена: {exc}")
            raise SystemExit(1)

        if result.returncode == 0:
            print(f"OK   [{task_name}] успешно выполнено.")
            return

        print(f"FAIL [{task_name}] код возврата {result.returncode}.")
        if attempt < attempts:
            print(f"     Повтор через 2 секунды...")
            time.sleep(2)

    print(f"КРИТИЧЕСКАЯ ОШИБКА: задача {task_name} не выполнена после {attempts} попыток.")
    raise SystemExit(1)


def main() -> int:
    parser = argparse.ArgumentParser(description="Оркестратор учебного Data Pipeline")
    parser.add_argument("--date", default="2017-04-02", help="Дата CSV с возвратами (YYYY-MM-DD)")
    parser.add_argument("--retries", type=int, default=2, help="Количество повторов на задачу")
    parser.add_argument("--timeout", type=int, default=180, help="Timeout одной попытки, секунды")
    args = parser.parse_args()

    python = sys.executable
    dbt = shutil.which("dbt")
    if not dbt:
        print("ОШИБКА: dbt не найден в PATH. Установите dbt-postgres.", file=sys.stderr)
        return 1

    tasks = [
        ("load_ops_snapshot", [python, "ingestion/load_ops_snapshot.py"]),
        ("load_api_inventory", [python, "ingestion/load_inventory.py"]),
        ("load_returns", [python, "ingestion/load_returns.py", "--date", args.date]),
        ("raw_quality_check", [python, "scripts/raw_quality_check.py"]),
        ("dbt_run", [dbt, "run", "--project-dir", "dbt", "--profiles-dir", "dbt"]),
        ("dbt_test", [dbt, "test", "--project-dir", "dbt", "--profiles-dir", "dbt"]),
    ]

    print("ЗАПУСК ПАЙПЛАЙНА (ecommerce_daily)")
    for task_name, command in tasks:
        run_task(task_name, command, args.retries, args.timeout)

    print("\nПАЙПЛАЙН УСПЕШНО ЗАВЕРШЕН!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
