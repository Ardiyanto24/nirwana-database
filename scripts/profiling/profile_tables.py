"""
Milestone 2.2 -- independent data profiling across all 23 production tables,
run BEFORE any cleaning decision.dl.

Manual-only diagnostic tool (like scripts/schema_drift/baseline_columns.py),
not part of the scheduled workflow. Uses EXTRACT_DB_URL (extract_reader,
read-only, already whitelisted to exactly these 23 tables -- see
scripts/extract/grants.sql) rather than the admin connection, since
profiling is pure SELECT and this role is the least-privilege fit.

For every column of every table: type, null count/pct, distinct count.
For text columns: regex-based format-variant detection (not full sampling,
to keep output reviewable) plus leading/trailing whitespace detection.
For numeric columns: min/max/negative count.
For date/timestamp columns: min/max range.
Plus one full-row duplicate check per table.

Output: one JSON file per run to scripts/profiling/output/, timestamped --
raw material for the findings document, not the findings themselves.
"""
import datetime
import json
import os
import sys

import psycopg2

sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "extract"))
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "monitoring"))
from db import _load_env  # noqa: E402
from tables_config import TABLES  # noqa: E402

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def get_columns(cur, schema, table):
    cur.execute(
        """
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_schema = %s AND table_name = %s
        ORDER BY ordinal_position
        """,
        (schema, table),
    )
    return cur.fetchall()


def profile_column(cur, schema, table, col, dtype, row_count):
    q = f'"{col}"'
    result = {"column": col, "data_type": dtype}

    cur.execute(f"SELECT COUNT(*) FROM {schema}.{table} WHERE {q} IS NULL")
    null_count = cur.fetchone()[0]
    result["null_count"] = null_count
    result["null_pct"] = round(100.0 * null_count / row_count, 2) if row_count else 0.0

    cur.execute(f"SELECT COUNT(DISTINCT {q}) FROM {schema}.{table}")
    result["distinct_count"] = cur.fetchone()[0]

    if dtype in ("character varying", "text", "character"):
        # leading/trailing whitespace
        cur.execute(f"SELECT COUNT(*) FROM {schema}.{table} WHERE {q} <> TRIM({q})")
        result["whitespace_issue_count"] = cur.fetchone()[0]
        # mixed case variants of the same trimmed-lowercased value (e.g. "Jakarta" vs "JAKARTA")
        cur.execute(
            f"""
            SELECT COUNT(*) FROM (
                SELECT LOWER(TRIM({q})) AS norm, COUNT(DISTINCT {q}) AS variants
                FROM {schema}.{table}
                WHERE {q} IS NOT NULL
                GROUP BY LOWER(TRIM({q}))
                HAVING COUNT(DISTINCT {q}) > 1
            ) sub
            """
        )
        result["case_variant_groups"] = cur.fetchone()[0]
    elif dtype in ("integer", "bigint", "numeric", "double precision", "real", "smallint"):
        cur.execute(f"SELECT MIN({q}), MAX({q}) FROM {schema}.{table}")
        mn, mx = cur.fetchone()
        result["min"] = float(mn) if mn is not None else None
        result["max"] = float(mx) if mx is not None else None
        cur.execute(f"SELECT COUNT(*) FROM {schema}.{table} WHERE {q} < 0")
        result["negative_count"] = cur.fetchone()[0]
    elif dtype in ("date", "timestamp without time zone", "timestamp with time zone"):
        cur.execute(f"SELECT MIN({q}), MAX({q}) FROM {schema}.{table}")
        mn, mx = cur.fetchone()
        result["min"] = str(mn) if mn is not None else None
        result["max"] = str(mx) if mx is not None else None

    return result


def profile_table(conn, schema, table):
    with conn.cursor() as cur:
        cur.execute(f"SELECT COUNT(*) FROM {schema}.{table}")
        row_count = cur.fetchone()[0]

        columns = get_columns(cur, schema, table)
        col_profiles = [profile_column(cur, schema, table, c, t, row_count) for c, t in columns]

        colnames_quoted = ", ".join(f'"{c}"' for c, _ in columns)
        cur.execute(
            f"""
            SELECT COUNT(*) FROM (
                SELECT {colnames_quoted} FROM {schema}.{table}
                GROUP BY {colnames_quoted}
                HAVING COUNT(*) > 1
            ) dup
            """
        )
        duplicate_group_count = cur.fetchone()[0]

    return {
        "schema": schema,
        "table": table,
        "row_count": row_count,
        "duplicate_row_groups": duplicate_group_count,
        "columns": col_profiles,
    }


def main():
    env = _load_env(os.path.join(REPO_ROOT, ".env"))
    conn = psycopg2.connect(env["EXTRACT_DB_URL"])
    conn.set_session(readonly=True, autocommit=True)

    results = []
    for schema, table, _, _ in TABLES:
        print(f"Profiling {schema}.{table}...")
        results.append(profile_table(conn, schema, table))
    conn.close()

    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
    os.makedirs(out_dir, exist_ok=True)
    ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_path = os.path.join(out_dir, f"profile_{ts}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\nWritten to {out_path}")


if __name__ == "__main__":
    main()
