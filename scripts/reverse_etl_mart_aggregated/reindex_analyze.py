"""
Milestone 5.5 -- REINDEX/ANALYZE mechanism, run after every swap
(scripts/reverse_etl_mart_aggregated/sync.py).

Why this is needed (decisions.md Keputusan #3, correction found during
implementation): sync.py's staging table is CREATE TABLE'd fresh every run
with columns only, no indexes -- so RENAME-swapping it into the live table
name means the "new" live table has ZERO indexes, not just stale statistics.
Plain REINDEX (which only rebuilds indexes that already exist) can't recover
an index that was never created on the new table object. The correct
sequence, per table:
  1. CREATE INDEX IF NOT EXISTS for every index declared in example_indexes.py
     that targets this table -- recreates whatever the swap just dropped.
  2. REINDEX TABLE -- de-bloat/rebuild, safe no-op if the index above is
     already fresh (harmless either way, kept for general hygiene).
  3. ANALYZE -- refresh planner statistics.

Safe to run on any table, including ones with zero configured indexes (steps
1 and 2 are then no-ops, step 3 always has value).

The indexes in example_indexes.py are explicitly PROVISIONAL/example, not
Milestone 3.3's real index design -- see that file's docstring.

Usage:
  python scripts/reverse_etl_mart_aggregated/reindex_analyze.py --table fact_revenue_property_daily
  python scripts/reverse_etl_mart_aggregated/reindex_analyze.py --all
"""
import argparse

from connections import get_serving_writer_connection
from example_indexes import EXAMPLE_INDEXES
from mart_aggregated_tables import MART_AGGREGATED_TABLES

PG_SCHEMA = "mart_aggregated"


def reindex_analyze_table(pg_conn, table):
    indexes_for_table = [ix for ix in EXAMPLE_INDEXES if ix["table"] == table]

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
    group.add_argument("--all", action="store_true", help="Reindex/analyze all 76 mart_aggregated tables")
    args = parser.parse_args()

    tables = [t for _, t in MART_AGGREGATED_TABLES] if args.all else [args.table]

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
