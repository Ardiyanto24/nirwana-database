"""
Milestone 3.3 -- REINDEX/ANALYZE mechanism for mart_cleaned, run after every swap
(scripts/reverse_etl/sync.py). Clone of scripts/reverse_etl_mart_aggregated's
reindex_analyze.py (M5.5) -- copied, not imported, per the project's established
copy-across-scripts/*-subfolders convention (connections.py's own docstring, M2.1
tables_config.py collision).

Why this is needed: sync.py's staging table is CREATE TABLE'd fresh every run with
columns only, no indexes -- so RENAME-swapping it into the live table name means the
"new" live table has ZERO indexes, not just stale statistics. Plain REINDEX (which only
rebuilds indexes that already exist) can't recover an index that was never created on
the new table object. The correct sequence, per table:
  1. CREATE INDEX IF NOT EXISTS for every index declared in mart_cleaned_indexes.py
     that targets this table -- recreates whatever the swap just dropped.
  2. REINDEX TABLE -- de-bloat/rebuild, safe no-op if the index above is already fresh.
  3. ANALYZE -- refresh planner statistics.

Safe to run on any table, including ones with zero configured indexes (steps 1 and 2
are then no-ops, step 3 always has value).

Usage:
  python scripts/reverse_etl/reindex_analyze.py --table bookings
  python scripts/reverse_etl/reindex_analyze.py --all
"""
import argparse

from connections import get_serving_writer_connection
from mart_cleaned_indexes import MART_CLEANED_INDEXES
from serving_tables import SERVING_TABLES

PG_SCHEMA = "mart_cleaned"


def reindex_analyze_table(pg_conn, table):
    indexes_for_table = [ix for ix in MART_CLEANED_INDEXES if ix["table"] == table]

    with pg_conn.cursor() as cur:
        for ix in indexes_for_table:
            cols = ", ".join(f'"{c}"' for c in ix["columns"])
            cur.execute(
                f'CREATE INDEX IF NOT EXISTS "{ix["index_name"]}" '
                f'ON {PG_SCHEMA}."{table}" ({cols})'
            )
        cur.execute(f'REINDEX TABLE {PG_SCHEMA}."{table}"')
        cur.execute(f'ANALYZE {PG_SCHEMA}."{table}"')
    pg_conn.commit()

    return {"table": table, "indexes_ensured": [ix["index_name"] for ix in indexes_for_table]}


def main():
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--table", help="Reindex/analyze a single table")
    group.add_argument("--all", action="store_true", help="Reindex/analyze all 23 mart_cleaned tables")
    args = parser.parse_args()

    tables = [t for _, t in SERVING_TABLES] if args.all else [args.table]

    pg_conn = get_serving_writer_connection()
    try:
        for table in tables:
            result = reindex_analyze_table(pg_conn, table)
            if result["indexes_ensured"]:
                print(f"  {table}: REINDEX+ANALYZE done, indexes ensured: {result['indexes_ensured']}")
            else:
                print(f"  {table}: REINDEX+ANALYZE done (no configured indexes -- no-op reindex)")
    finally:
        pg_conn.close()

    print(f"\n{len(tables)} table(s) reindexed/analyzed.")


if __name__ == "__main__":
    main()
