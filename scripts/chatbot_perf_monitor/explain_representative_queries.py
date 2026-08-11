"""
Milestone 6.5 -- Output 2: EXPLAIN ANALYZE berkala terhadap query
representatif chatbot (Keputusan D). pg_stat_statements.query menyimpan teks
ternormalisasi berplaceholder ($1, $2) -- tidak bisa langsung dieksekusi
ulang, jadi 10 query (1 per domain chatbot) dikurasi manual di sini dengan
parameter sampel nyata, mengikuti bentuk query yang sama persis dipakai
scripts/chatbot_api/main.py::_run_whitelisted_query (SELECT * FROM <source>
[WHERE ...] ORDER BY 1 LIMIT %s OFFSET %s).

Usage: python explain_representative_queries.py
"""
import datetime
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from db import get_connection
from serving_pg import get_perf_reader_connection

SAMPLE_PROPERTY_ID = "P01"

# (domain, view_name, sql) -- 1 per domain chatbot (M4.3/M4.4), bentuk sama
# persis _run_whitelisted_query (SELECT * FROM source [WHERE ...] ORDER BY 1
# LIMIT/OFFSET). property_id sengaja dipakai di separuh -- mencerminkan pola
# own_property nyata, bukan cuma all_properties.
REPRESENTATIVE_QUERIES = [
    ("reservation", "v_reservation_property_daily",
     f"SELECT * FROM chatbot_views.v_reservation_property_daily WHERE property_id = '{SAMPLE_PROPERTY_ID}' ORDER BY 1 LIMIT 100 OFFSET 0"),
    ("fnb", "v_fnb_outlet_daily",
     f"SELECT * FROM chatbot_views.v_fnb_outlet_daily WHERE property_id = '{SAMPLE_PROPERTY_ID}' ORDER BY 1 LIMIT 100 OFFSET 0"),
    ("facility", "v_facility_room_status_daily",
     "SELECT * FROM chatbot_views.v_facility_room_status_daily ORDER BY 1 LIMIT 100 OFFSET 0"),
    ("spa_event", "v_spa_daily",
     "SELECT * FROM chatbot_views.v_spa_daily ORDER BY 1 LIMIT 100 OFFSET 0"),
    ("hr", "v_hr_attendance_daily",
     f"SELECT * FROM chatbot_views.v_hr_attendance_daily WHERE property_id = '{SAMPLE_PROPERTY_ID}' ORDER BY 1 LIMIT 100 OFFSET 0"),
    ("financial", "v_financial_revenue_runrate_daily",
     "SELECT * FROM chatbot_views.v_financial_revenue_runrate_daily ORDER BY 1 LIMIT 100 OFFSET 0"),
    ("properties_ref", "v_properties_ref",
     "SELECT * FROM chatbot_views.v_properties_ref ORDER BY 1 LIMIT 100 OFFSET 0"),
    ("employees_directory", "v_employees_directory",
     "SELECT * FROM chatbot_views.v_employees_directory WHERE property_id = '{}' ORDER BY 1 LIMIT 100 OFFSET 0".format(SAMPLE_PROPERTY_ID)),
    ("guests_pii", "guests_contact_view",
     "SELECT * FROM chatbot_views.guests_contact_view ORDER BY 1 LIMIT 100 OFFSET 0"),
    ("guests_profile", "guests_profile_view",
     "SELECT * FROM chatbot_views.guests_profile_view ORDER BY 1 LIMIT 100 OFFSET 0"),
]


def explain_analyze(serving_conn, sql):
    cur = serving_conn.cursor()
    cur.execute(f"EXPLAIN (ANALYZE, FORMAT TEXT) {sql}")
    plan_lines = [row[0] for row in cur.fetchall()]
    cur.close()
    plan_text = "\n".join(plan_lines)

    execution_time_ms = None
    for line in plan_lines:
        if line.strip().startswith("Execution Time:"):
            execution_time_ms = float(line.strip().split("Execution Time:")[1].replace("ms", "").strip())
    return plan_text, execution_time_ms


def insert_result(conn, domain, view_name, sql, execution_time_ms, plan_text, snapshot_date):
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO monitoring.chatbot_explain_analyze_log
            (domain, view_name, query_text, execution_time_ms, plan_summary, snapshot_date)
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (domain, view_name, sql, execution_time_ms, plan_text, snapshot_date),
    )
    conn.commit()
    cur.close()


def main():
    snapshot_date = datetime.datetime.now(datetime.timezone.utc).date()

    serving_conn = get_perf_reader_connection(readonly=True)
    conn = get_connection(readonly=False)
    try:
        for domain, view_name, sql in REPRESENTATIVE_QUERIES:
            plan_text, execution_time_ms = explain_analyze(serving_conn, sql)
            insert_result(conn, domain, view_name, sql, execution_time_ms, plan_text, snapshot_date)
            print(f"[{domain}/{view_name}] execution_time={execution_time_ms}ms")
    finally:
        serving_conn.close()
        conn.close()


if __name__ == "__main__":
    main()
