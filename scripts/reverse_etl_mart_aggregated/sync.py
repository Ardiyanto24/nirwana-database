"""
Milestone 5.5 -- reverse ETL BigQuery mart_aggregated -> serving PostgreSQL.

Copy of scripts/reverse_etl/sync.py (M2.4), adapted for mart_aggregated --
not imported/parameterized, per decisions.md Keputusan #4 (preseden project:
"copied rather than imported across scripts/* subfolders").

Per table: read BigQuery `mart_aggregated.<table>` paginated (NO
`mart_cleaned__`-style prefix -- mart_aggregated table names in BigQuery are
already bare, see mart_aggregated_tables.py), bulk load into a Postgres
staging table (`mart_aggregated.<table>__staging`) via psycopg2.copy_expert
(text-format COPY), gate on row-count parity (BigQuery COUNT(*) vs staging
COUNT(*)) BEFORE swap (decisions.md Keputusan #7 -- same deviation as M2.4
Decision 5, stricter than literal "pasca-sync" wording), then RENAME-swap
into the live table (`mart_aggregated.<table>`).

If the row count doesn't match, the staging table is dropped and the live
table is NOT touched at all -- whatever's already live stays authoritative.

Only syncs the 76 tables in mart_aggregated_tables.py -- deliberately
EXCLUDES fact_ml_occupancy_forecast_property_room_type (M5.4, provisional,
schema not final -- decisions.md Keputusan #2).

Usage:
  python scripts/reverse_etl_mart_aggregated/sync.py --table dim_property
  python scripts/reverse_etl_mart_aggregated/sync.py --all
"""
import argparse
import io
import os
import sys

import psycopg2
from google.cloud import bigquery

from connections import _load_env, get_serving_writer_connection, get_production_connection
from mart_aggregated_tables import MART_AGGREGATED_TABLES

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BQ_PROJECT = "nirwana-database-elt"
BQ_DATASET = "mart_aggregated"
PG_SCHEMA = "mart_aggregated"
DATASET_LOG_NAME = "mart_aggregated"
COPY_BATCH_SIZE = 50_000

# BigQuery field_type -> Postgres column type. Same mapping as M2.4's
# sync.py -- mart_aggregated models are flat (no nested STRUCT/RECORD).
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
    keyfile_env = env.get(
        "REVERSE_ETL_MART_AGGREGATED_READER_CREDENTIALS",
        "scripts/extract/gcp-reverse-etl-mart-agg-reader-key.json",
    )
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
    bq_table_id = f"{BQ_PROJECT}.{BQ_DATASET}.{table}"
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

    # --- gate: row-count parity BEFORE swap (decisions.md Keputusan #7) ---
    bq_count = list(bq_client.query(f"SELECT COUNT(*) AS c FROM `{bq_table_id}`").result())[0]["c"]
    with pg_conn.cursor() as cur:
        cur.execute(f'SELECT COUNT(*) FROM {PG_SCHEMA}."{staging_table}"')
        pg_count = cur.fetchone()[0]

    if bq_count != pg_count:
        with pg_conn.cursor() as cur:
            cur.execute(f'DROP TABLE {PG_SCHEMA}."{staging_table}"')
        pg_conn.commit()
        return {"table": table, "bq_count": bq_count, "pg_count": pg_count, "status": "mismatch_aborted"}

    # --- swap (RENAME-based, matches arsitektur doc Bagian 7.2) ---
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

    if live_exists:
        with pg_conn.cursor() as cur:
            cur.execute(f'DROP TABLE {PG_SCHEMA}."{table}__old"')
        pg_conn.commit()

    return {"table": table, "bq_count": bq_count, "pg_count": pg_count, "status": "synced"}


def log_sync_result(prod_conn, result):
    """Write one row to monitoring.reverse_etl_sync_log on the PRODUCTION
    Supabase project -- same shared log table as M2.4 (decisions.md
    Keputusan #9), disambiguated via dataset_name='mart_aggregated'."""
    with prod_conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO monitoring.reverse_etl_sync_log
                (table_name, bq_row_count, pg_row_count, status, dataset_name)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (result["table"], result["bq_count"], result["pg_count"], result["status"], DATASET_LOG_NAME),
        )
    prod_conn.commit()


def main():
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--table", help="Sync a single table (bare name, e.g. 'dim_property')")
    group.add_argument("--domain", help="Sync all tables under one dbt domain folder (e.g. 'reservation_revenue')")
    group.add_argument("--all", action="store_true", help="Sync all 76 mart_aggregated tables")
    args = parser.parse_args()

    if args.all:
        tables = [t for _, t in MART_AGGREGATED_TABLES]
    elif args.domain:
        tables = [t for s, t in MART_AGGREGATED_TABLES if s == args.domain]
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
