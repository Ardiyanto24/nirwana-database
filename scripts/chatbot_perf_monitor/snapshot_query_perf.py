"""
Milestone 6.5 -- Output 1/2 (KK1): snapshot top query chatbot_views.* dari
pg_stat_statements (project serving, via chatbot_perf_reader), tulis ke
monitoring.chatbot_query_perf_snapshot (production Supabase, via db.py admin).

queryid (hash normalized-query bawaan pg_stat_statements) dipakai sebagai
unique key per snapshot_date -- bukan hash query_text sendiri, dan bukan
percentile (pg_stat_statements tidak punya kolom itu sama sekali, lihat
decisions.md Keputusan A -- ini murni utk "query paling lambat/sering",
bagian KK1 yang memang didukung pg_stat_statements).

Usage: python snapshot_query_perf.py [--limit 50]
"""
import argparse
import datetime
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from db import get_connection
from serving_pg import get_perf_reader_connection


def fetch_chatbot_query_stats(serving_conn, limit):
    cur = serving_conn.cursor()
    # ILIKE pattern passed as a bound parameter, not inlined -- a literal '%'
    # in the SQL string confuses psycopg2's own %s-style parameter
    # substitution (it reads '%c...%' as an unrelated format conversion and
    # raises IndexError against the params tuple, discovered on first run).
    cur.execute(
        """
        SELECT queryid, query, calls, mean_exec_time, max_exec_time, rows
        FROM extensions.pg_stat_statements
        WHERE query ILIKE %s
        ORDER BY calls DESC
        LIMIT %s
        """,
        ("%chatbot_views%", limit),
    )
    rows = cur.fetchall()
    cur.close()
    return rows


def upsert_snapshot(conn, snapshot_date, rows):
    cur = conn.cursor()
    for queryid, query_text, calls, mean_exec_time, max_exec_time, rows_returned in rows:
        cur.execute(
            """
            INSERT INTO monitoring.chatbot_query_perf_snapshot
                (snapshot_date, queryid, query_text, calls, mean_exec_time_ms, max_exec_time_ms, rows_returned)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (snapshot_date, queryid)
            DO UPDATE SET calls = EXCLUDED.calls, mean_exec_time_ms = EXCLUDED.mean_exec_time_ms,
                           max_exec_time_ms = EXCLUDED.max_exec_time_ms, rows_returned = EXCLUDED.rows_returned,
                           captured_at = now()
            """,
            (snapshot_date, queryid, query_text, calls, mean_exec_time, max_exec_time, rows_returned),
        )
    conn.commit()
    cur.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=50, help="berapa banyak query teratas (by calls) yang disimpan")
    args = parser.parse_args()

    snapshot_date = datetime.datetime.now(datetime.timezone.utc).date()

    serving_conn = get_perf_reader_connection()
    try:
        rows = fetch_chatbot_query_stats(serving_conn, args.limit)
    finally:
        serving_conn.close()

    conn = get_connection(readonly=False)
    try:
        upsert_snapshot(conn, snapshot_date, rows)
    finally:
        conn.close()

    print(f"snapshot_date={snapshot_date}: {len(rows)} query chatbot_views tersimpan.")
    if rows:
        slowest = max(rows, key=lambda r: r[4])
        print(f"  paling lambat (max_exec_time): {slowest[4]:.2f}ms -- {slowest[1][:100]}")
        most_called = max(rows, key=lambda r: r[2])
        print(f"  paling sering (calls): {most_called[2]} -- {most_called[1][:100]}")


if __name__ == "__main__":
    main()
