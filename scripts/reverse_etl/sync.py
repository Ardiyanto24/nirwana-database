"""
Milestone 2.4 Task 5 -- reverse ETL BigQuery mart_cleaned -> serving PostgreSQL.

Per table: read BigQuery `mart_cleaned.mart_cleaned__<table>` paginated, bulk
load into a Postgres staging table (`mart_cleaned.<table>__staging`) via
psycopg2.copy_expert (text-format COPY, not row-by-row INSERT -- decisions.md
Decision 4), gate on row-count parity (BigQuery COUNT(*) vs staging COUNT(*))
BEFORE swap (decisions.md Decision 5 -- stricter than literal "pasca-sync"
wording in the source doc), then RENAME-swap into the live table
(`mart_cleaned.<table>`), matching the pattern in
docs/01-architecture/rancangan-arsitektur-data-platform-elt.md Bagian 7.2.

If the row count doesn't match, the staging table is dropped and the live
table is NOT touched at all -- whatever's already live stays authoritative.

Usage:
  python scripts/reverse_etl/sync.py --table properties
  python scripts/reverse_etl/sync.py --all
"""
import argparse
import io
import os
import sys
import time

import psycopg2
from google.cloud import bigquery

from connections import _load_env, get_serving_writer_connection, get_production_connection
from serving_tables import SERVING_TABLES

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BQ_PROJECT = "nirwana-database-elt"
BQ_DATASET = "mart_cleaned"
PG_SCHEMA = "mart_cleaned"
COPY_BATCH_SIZE = 50_000

# BigQuery field_type -> Postgres column type. mart_cleaned models are flat
# passthroughs (Milestone 2.2/2.3 -- no feature engineering, no nested
# STRUCT/RECORD columns), so this covers every type actually present.
BQ_TO_PG_TYPE = {
    "STRING": "text",
    "INTEGER": "bigint",
    "INT64": "bigint",
    "FLOAT": "double precision",
    "FLOAT64": "double precision",
    "BOOLEAN": "boolean",
    "BOOL": "boolean",
    "DATE": "date",
    "DATETIME": "timestamp",
    "TIMESTAMP": "timestamptz",
    "TIME": "time",
    "NUMERIC": "numeric",
    "BIGNUMERIC": "numeric",
    "BYTES": "bytea",
}


def get_reverse_etl_reader_client():
    env = _load_env(os.path.join(REPO_ROOT, ".env"))
    keyfile_env = env.get("REVERSE_ETL_READER_CREDENTIALS", "scripts/extract/gcp-reverse-etl-reader-key.json")
    keyfile = keyfile_env if os.path.isabs(keyfile_env) else os.path.join(REPO_ROOT, keyfile_env)
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = keyfile
    return bigquery.Client(project=BQ_PROJECT)


def _pg_column_ddl(bq_schema):
    cols = []
    for field in bq_schema:
        pg_type = BQ_TO_PG_TYPE.get(field.field_type)
        if pg_type is None:
            raise ValueError(f"No BQ->PG type mapping for {field.name} ({field.field_type})")
        cols.append(f'"{field.name}" {pg_type}')
    return ", ".join(cols)


def _escape_copy_field(value):
    """Postgres COPY text-format escaping. None -> \\N (the NULL marker),
    otherwise escape backslash/tab/newline/CR so the literal characters
    can't be mistaken for column/row delimiters."""
    if value is None:
        return "\\N"
    s = str(value)
    return s.replace("\\", "\\\\").replace("\t", "\\t").replace("\n", "\\n").replace("\r", "\\r")


def sync_table(bq_client, pg_conn, table):
    bq_table_id = f"{BQ_PROJECT}.{BQ_DATASET}.mart_cleaned__{table}"
    staging_table = f"{table}__staging"

    bq_table = bq_client.get_table(bq_table_id)
    column_ddl = _pg_column_ddl(bq_table.schema)
    column_names = [f'"{f.name}"' for f in bq_table.schema]

    with pg_conn.cursor() as cur:
        cur.execute(f'DROP TABLE IF EXISTS {PG_SCHEMA}."{staging_table}"')
        cur.execute(f'CREATE TABLE {PG_SCHEMA}."{staging_table}" ({column_ddl})')
    pg_conn.commit()

    # --- bulk load via COPY (text format), batched ---
    copy_sql = f'COPY {PG_SCHEMA}."{staging_table}" ({", ".join(column_names)}) FROM STDIN'
    buffer = io.StringIO()
    buffered_rows = 0
    with pg_conn.cursor() as cur:
        for row in bq_client.list_rows(bq_table_id):
            line = "\t".join(_escape_copy_field(row[f.name]) for f in bq_table.schema)
            buffer.write(line + "\n")
            buffered_rows += 1
            if buffered_rows >= COPY_BATCH_SIZE:
                buffer.seek(0)
                cur.copy_expert(copy_sql, buffer)
                buffer = io.StringIO()
                buffered_rows = 0
        if buffered_rows > 0:
            buffer.seek(0)
            cur.copy_expert(copy_sql, buffer)
    pg_conn.commit()

    # --- gate: row-count parity BEFORE swap (decisions.md Decision 5) ---
    bq_count = list(bq_client.query(f"SELECT COUNT(*) AS c FROM `{bq_table_id}`").result())[0]["c"]
    with pg_conn.cursor() as cur:
        cur.execute(f'SELECT COUNT(*) FROM {PG_SCHEMA}."{staging_table}"')
        pg_count = cur.fetchone()[0]

    if bq_count != pg_count:
        with pg_conn.cursor() as cur:
            cur.execute(f'DROP TABLE {PG_SCHEMA}."{staging_table}"')
        pg_conn.commit()
        return {"table": table, "bq_count": bq_count, "pg_count": pg_count, "status": "mismatch_aborted",
                "old_table": None, "swap_duration_ms": None}

    # --- swap (RENAME-based, matches arsitektur doc Bagian 7.2) ---
    # Milestone 6.6 fix: timer wraps RENAME+DROP only (not the whole
    # sync_table() call, which is dominated by BigQuery fetch+COPY) -- this
    # is the literal "proses swap table" KK2 M6.6 asks about, and no
    # duration was ever captured anywhere for it before this.
    swap_start = time.monotonic()
    with pg_conn.cursor() as cur:
        cur.execute(
            "SELECT 1 FROM information_schema.tables WHERE table_schema = %s AND table_name = %s",
            (PG_SCHEMA, table),
        )
        live_exists = cur.fetchone() is not None

        if live_exists:
            cur.execute(f'ALTER TABLE {PG_SCHEMA}."{table}" RENAME TO "{table}__old"')
        cur.execute(f'ALTER TABLE {PG_SCHEMA}."{staging_table}" RENAME TO "{table}"')
    pg_conn.commit()

    # --- cleanup: drop the renamed-away old table, best-effort ---
    # Milestone 6.6 fix: ported from scripts/reverse_etl_mart_aggregated/sync.py
    # (M5.7 finding, proven there since) -- this sibling copy never had it,
    # so it crashed the whole --all run (not just warned) on the exact same
    # DependentObjectsStillExist error real production history already hit
    # once (milestones/6.2-.../logs.md: "employees__old already exists").
    # Postgres views bind to the underlying table by OID, not name -- once
    # analyst_views/chatbot_views exist on top of mart_cleaned tables, a
    # RENAME-based swap leaves them still pointing at "<table>__old" until
    # those views are explicitly reapplied. The live table under "<table>"
    # is already correct at this point -- dropping "__old" is pure cleanup,
    # not correctness-critical -- so a dependency conflict here is downgraded
    # to a warning instead of crashing the whole sync run.
    old_table_status = "n/a"
    if live_exists:
        try:
            with pg_conn.cursor() as cur:
                cur.execute(f'DROP TABLE {PG_SCHEMA}."{table}__old"')
            pg_conn.commit()
            old_table_status = "dropped"
        except psycopg2.errors.DependentObjectsStillExist:
            pg_conn.rollback()
            old_table_status = "kept (analyst_views/chatbot_views dependency -- reapply views, then rerun sync to clean up)"
            print(
                f"  WARNING: {table}__old kept -- a view still depends on it. "
                "Run scripts/data_analyst_views/apply_views.py --all and/or "
                "scripts/chatbot_views/apply_views.py --all, then rerun sync "
                "to drop the orphaned table."
            )
    swap_duration_ms = round((time.monotonic() - swap_start) * 1000, 2)

    return {"table": table, "bq_count": bq_count, "pg_count": pg_count, "status": "synced",
            "old_table": old_table_status, "swap_duration_ms": swap_duration_ms}


def log_sync_result(prod_conn, result):
    """Write one row to monitoring.reverse_etl_sync_log on the PRODUCTION
    Supabase project (decisions.md Decision 6 -- monitoring stays centralized
    there regardless of where the serving layer physically lives).

    Milestone 6.6 fix: old_table_status and swap_duration_ms are new columns
    (monitoring.reverse_etl_sync_log had neither before this)."""
    with prod_conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO monitoring.reverse_etl_sync_log
                (table_name, bq_row_count, pg_row_count, status, old_table_status, swap_duration_ms)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (result["table"], result["bq_count"], result["pg_count"], result["status"],
             result.get("old_table"), result.get("swap_duration_ms")),
        )
    prod_conn.commit()


def main():
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--table", help="Sync a single table (bare name, e.g. 'properties')")
    group.add_argument("--domain", help="Sync all tables under one production schema (e.g. 'corporate_master')")
    group.add_argument("--all", action="store_true", help="Sync all 23 mart_cleaned tables")
    args = parser.parse_args()

    if args.all:
        tables = [t for _, t in SERVING_TABLES]
    elif args.domain:
        tables = [t for s, t in SERVING_TABLES if s == args.domain]
        if not tables:
            parser.error(f"no tables found for domain '{args.domain}'")
    else:
        tables = [args.table]

    bq_client = get_reverse_etl_reader_client()
    pg_conn = get_serving_writer_connection()
    prod_conn = get_production_connection()

    results = []
    try:
        for table in tables:
            print(f"=== syncing {table} ===")
            result = sync_table(bq_client, pg_conn, table)
            results.append(result)
            log_sync_result(prod_conn, result)
            print(f"  {result['status']}: BigQuery={result['bq_count']} Postgres={result['pg_count']}")
    finally:
        pg_conn.close()
        prod_conn.close()

    mismatches = [r for r in results if r["status"] != "synced"]
    print(f"\n{len(results) - len(mismatches)}/{len(results)} table(s) synced.")
    if mismatches:
        print(f"{len(mismatches)} table(s) ABORTED (row count mismatch, live table untouched):")
        for r in mismatches:
            print(f"  {r['table']}: BigQuery={r['bq_count']} vs Postgres={r['pg_count']}")
        sys.exit(1)


if __name__ == "__main__":
    main()
