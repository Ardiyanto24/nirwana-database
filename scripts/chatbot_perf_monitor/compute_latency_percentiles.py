"""
Milestone 6.5 -- KK1 (latency) + KK2 (denied trend): query
monitoring.chatbot_query_log via chatbot_audit_reader.

Percentile SUNGGUHAN (bukan aproksimasi pg_stat_statements) via
percentile_cont() atas duration_ms per-request nyata (Keputusan A, M6.5).
Baris lama pra-instrumentasi (M4.5/M4.6, duration_ms IS NULL) otomatis
dikecualikan oleh percentile_cont (mengabaikan NULL).

Usage: python compute_latency_percentiles.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from serving_pg import get_audit_reader_connection


def latency_percentiles(conn):
    cur = conn.cursor()
    cur.execute(
        """
        SELECT
            count(*) FILTER (WHERE duration_ms IS NOT NULL) AS n,
            percentile_cont(0.5) WITHIN GROUP (ORDER BY duration_ms) AS p50,
            percentile_cont(0.95) WITHIN GROUP (ORDER BY duration_ms) AS p95,
            percentile_cont(0.99) WITHIN GROUP (ORDER BY duration_ms) AS p99
        FROM monitoring.chatbot_query_log
        WHERE duration_ms IS NOT NULL
        """
    )
    row = cur.fetchone()
    cur.close()
    return {"n": row[0], "p50_ms": row[1], "p95_ms": row[2], "p99_ms": row[3]}


def slowest_queries(conn, limit=10):
    cur = conn.cursor()
    cur.execute(
        """
        SELECT domain, view_name, duration_ms, status, requested_at
        FROM monitoring.chatbot_query_log
        WHERE duration_ms IS NOT NULL
        ORDER BY duration_ms DESC
        LIMIT %s
        """,
        (limit,),
    )
    rows = cur.fetchall()
    cur.close()
    return rows


def volume_and_denied_trend(conn):
    cur = conn.cursor()
    cur.execute(
        """
        SELECT
            requested_at::date AS request_date,
            count(*) AS total,
            count(*) FILTER (WHERE status = 'denied') AS denied,
            round(100.0 * count(*) FILTER (WHERE status = 'denied') / count(*), 1) AS denied_pct
        FROM monitoring.chatbot_query_log
        GROUP BY 1
        ORDER BY 1
        """
    )
    rows = cur.fetchall()
    cur.close()
    return rows


def main():
    conn = get_audit_reader_connection()
    try:
        perc = latency_percentiles(conn)
        print(f"Latency (n={perc['n']}, duration_ms non-NULL saja): "
              f"p50={perc['p50_ms']} p95={perc['p95_ms']} p99={perc['p99_ms']}")

        print("\nTop 10 query paling lambat:")
        for domain, view_name, duration_ms, status, requested_at in slowest_queries(conn):
            print(f"  {duration_ms}ms  {domain}/{view_name}  status={status}  {requested_at}")

        print("\nVolume + tren gagal/ditolak per hari:")
        for request_date, total, denied, denied_pct in volume_and_denied_trend(conn):
            print(f"  {request_date}: total={total} denied={denied} ({denied_pct}%)")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
