"""
Milestone 2.1 -- generic extraction: production Postgres (via `extract_reader`,
EXTRACT_DB_URL) -> raw_production dataset in BigQuery.

Cursor tracking (see tables_config.py + decisions.md "Strategi incremental"):
strategy "pk"/"date" fetch only rows with cursor_column > last known cursor
(read/written in monitoring.extract_cursor, via the ADMIN connection --
extract_reader is intentionally read-only, it never touches monitoring.*).
strategy "full_refresh" re-syncs the whole table every run, no cursor.

BigQuery table naming: raw_production.<schema>__<table> (double underscore),
one BigQuery table per production table, kept 1:1 -- no cross-schema merging.
Schema is autodetected per load (Task 5 will pin this down more precisely
once all 23 tables are wired up; autodetect is sufficient to prove the
mechanism end-to-end here).
"""
import datetime
import decimal
import json
import os
import sys

import psycopg2
from google.cloud import bigquery

sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "monitoring"))
from db import _load_env  # noqa: E402
from bq import get_client  # noqa: E402
from tables_config import TABLES  # noqa: E402

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _pg_connect(url_key, env):
    return psycopg2.connect(env[url_key])


def _get_cursor(admin_conn, schema, table):
    with admin_conn.cursor() as cur:
        cur.execute(
            "SELECT last_cursor FROM monitoring.extract_cursor WHERE schema_name = %s AND table_name = %s",
            (schema, table),
        )
        row = cur.fetchone()
        return row[0] if row else None


def _set_cursor(admin_conn, schema, table, value):
    with admin_conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO monitoring.extract_cursor (schema_name, table_name, last_cursor, updated_at)
            VALUES (%s, %s, %s, now())
            ON CONFLICT (schema_name, table_name)
            DO UPDATE SET last_cursor = EXCLUDED.last_cursor, updated_at = now()
            """,
            (schema, table, str(value)),
        )
    admin_conn.commit()


def _json_safe(value):
    if isinstance(value, (datetime.date, datetime.datetime, datetime.time)):
        return value.isoformat()
    if isinstance(value, decimal.Decimal):
        return float(value)
    return value


def extract_table(schema, table, cursor_column, cursor_strategy, env, client, dataset, admin_conn=None):
    """Extract one table, return (row_count, write_disposition_used)."""
    pg_conn = _pg_connect("EXTRACT_DB_URL", env)
    last_cursor = None
    try:
        with pg_conn.cursor() as cur:
            if cursor_strategy == "full_refresh":
                cur.execute(f"SELECT * FROM {schema}.{table}")
            else:
                last_cursor = _get_cursor(admin_conn, schema, table)
                if last_cursor is None:
                    cur.execute(f"SELECT * FROM {schema}.{table} ORDER BY {cursor_column}")
                else:
                    cur.execute(
                        f"SELECT * FROM {schema}.{table} WHERE {cursor_column} > %s ORDER BY {cursor_column}",
                        (last_cursor,),
                    )
            colnames = [desc[0] for desc in cur.description]
            rows = cur.fetchall()
    finally:
        pg_conn.close()

    synced_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
    records = []
    max_cursor = last_cursor
    for row in rows:
        record = {col: _json_safe(val) for col, val in zip(colnames, row)}
        record["_synced_at"] = synced_at
        records.append(record)
        if cursor_strategy != "full_refresh":
            raw_cursor_val = row[colnames.index(cursor_column)]
            if max_cursor is None or str(raw_cursor_val) > str(max_cursor):
                max_cursor = raw_cursor_val

    bq_table_id = f"{client.project}.{dataset}.{schema}__{table}"
    write_disposition = (
        bigquery.WriteDisposition.WRITE_TRUNCATE
        if cursor_strategy == "full_refresh" or last_cursor is None
        else bigquery.WriteDisposition.WRITE_APPEND
    )
    job_config = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
        autodetect=True,
        write_disposition=write_disposition,
    )
    if records:
        payload = "\n".join(json.dumps(r) for r in records).encode("utf-8")
        job = client.load_table_from_file(
            __import__("io").BytesIO(payload), bq_table_id, job_config=job_config
        )
        job.result()

    if cursor_strategy != "full_refresh" and records and max_cursor is not None:
        _set_cursor(admin_conn, schema, table, max_cursor)

    return len(records), write_disposition


def main():
    env = _load_env(os.path.join(REPO_ROOT, ".env"))
    client, dataset = get_client()
    admin_conn = psycopg2.connect(env["SUPABASE_DB_URL"])
    admin_conn.autocommit = False

    target = sys.argv[1] if len(sys.argv) > 1 else None  # e.g. "corporate_master.properties"
    try:
        for schema, table, cursor_column, cursor_strategy in TABLES:
            if target and f"{schema}.{table}" != target:
                continue
            count, disposition = extract_table(
                schema, table, cursor_column, cursor_strategy, env, client, dataset, admin_conn
            )
            print(f"{schema}.{table}: {count} rows synced ({disposition})")
    finally:
        admin_conn.close()


if __name__ == "__main__":
    main()
