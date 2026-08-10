"""Apply one or more .sql files to the serving PostgreSQL project (Milestone 4.2).

Usage:
    python apply_views.py schema.sql
    python apply_views.py views_reservation.sql views_fnb.sql
    python apply_views.py --all
"""
import os
import sys

from connections import get_serving_connection

DOMAIN_FILES = [
    "views_reservation.sql",
    "views_fnb.sql",
    "views_facility.sql",
    "views_spa_event.sql",
    "views_hr.sql",
    "views_financial.sql",
    "views_properties_ref.sql",
    "views_employees_directory.sql",
    "views_guests.sql",
]


def apply_file(cur, path):
    with open(path, "r", encoding="utf-8") as f:
        ddl = f.read()
    cur.execute(ddl)
    print(f"Applied: {os.path.basename(path)}")


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        print("Usage: python apply_views.py <file1.sql> [file2.sql ...] | --all")
        sys.exit(1)

    if args == ["--all"]:
        filenames = DOMAIN_FILES
    else:
        filenames = args

    here = os.path.dirname(os.path.abspath(__file__))
    conn = get_serving_connection(readonly=False)
    conn.autocommit = False
    cur = conn.cursor()
    try:
        for filename in filenames:
            apply_file(cur, os.path.join(here, filename))
        conn.commit()
        print("All files applied successfully.")
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()
