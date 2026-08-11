"""
Milestone 6.5 -- Output 3 (KK3): snapshot jumlah koneksi aktif chatbot di
pg_stat_activity (project serving, via chatbot_perf_reader). Filter ke role
`%chatbot%` (11 role: 10 *_chatbot_reader domain M4.3 + chatbot_authz_reader
M4.4 -- persis role yang dipakai scripts/chatbot_api/connections.py, bukan
supabase_admin/postgres/pgbouncer yang selalu ada dan tidak relevan).

chatbot_api tidak punya connection pooling sendiri (buka koneksi baru tiap
request, temuan M4.6) -- burst request = burst baris pg_stat_activity yang
nyata, bukan simulasi.

Usage: python snapshot_connection_pool.py
"""
import datetime
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from db import get_connection
from serving_pg import get_perf_reader_connection


def count_chatbot_connections(serving_conn):
    # exclude chatbot_perf_reader itself -- its role name matches '%chatbot%'
    # too, and its own connection (running THIS query) would otherwise
    # self-count as chatbot_api traffic every single snapshot (found while
    # building baseline history: count was never 0 even with zero API traffic).
    cur = serving_conn.cursor()
    cur.execute(
        "SELECT count(*) FROM pg_stat_activity WHERE usename ILIKE %s AND usename != 'chatbot_perf_reader'",
        ("%chatbot%",),
    )
    count = cur.fetchone()[0]
    cur.close()
    return count


def insert_snapshot(conn, snapshot_time, active_connection_count):
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO monitoring.chatbot_connection_snapshot (snapshot_time, active_connection_count)
        VALUES (%s, %s)
        """,
        (snapshot_time, active_connection_count),
    )
    conn.commit()
    cur.close()


def run():
    snapshot_time = datetime.datetime.now(datetime.timezone.utc)

    serving_conn = get_perf_reader_connection()
    try:
        count = count_chatbot_connections(serving_conn)
    finally:
        serving_conn.close()

    conn = get_connection(readonly=False)
    try:
        insert_snapshot(conn, snapshot_time, count)
    finally:
        conn.close()

    print(f"snapshot_time={snapshot_time} active_connection_count={count}")
    return count


if __name__ == "__main__":
    run()
