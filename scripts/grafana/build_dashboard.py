"""
Milestone 1.5 - Task 4: bangun dashboard 4 pilar (volume/freshness M1.2, kualitas
data M1.3, schema drift M1.4) untuk 23 tabel, dikelompokkan per prioritas.

Panel dibangun sebagai tabel SQL langsung ke monitoring.* -- tidak menghitung ulang
logic anomali apa pun (lihat decisions.md), murni menampilkan hasil yang sudah ada.
"""
from grafana_client import api_request
from priority_case_sql import PRIORITY_CASE_SQL, PRIORITY_ORDER_SQL

DASHBOARD_TITLE = "Nirwana - Data Production Monitoring"


def _get_datasource_uid():
    status, ds = api_request("GET", "/api/datasources/name/Supabase%20Postgres%20(Nirwana)")
    if status != 200:
        raise RuntimeError(f"Datasource belum ada, jalankan create_datasource.py dulu: {ds}")
    return ds["uid"]


def _table_panel(panel_id, title, sql, x, y, w=24, h=8):
    return {
        "id": panel_id,
        "type": "table",
        "title": title,
        "gridPos": {"x": x, "y": y, "w": w, "h": h},
        "datasource": {"type": "grafana-postgresql-datasource", "uid": DS_UID},
        "targets": [{
            "rawSql": sql,
            "format": "table",
            "datasource": {"type": "grafana-postgresql-datasource", "uid": DS_UID},
            "refId": "A",
        }],
        "fieldConfig": {"defaults": {}, "overrides": []},
        "options": {"showHeader": True},
    }


def build_panels():
    panels = []
    y = 0

    panels.append(_table_panel(
        1, "Alert Aktif (M1.2 volume/freshness + M1.3 kualitas data)",
        """SELECT triggered_at, schema_name, table_name, alert_type, severity, detail
           FROM monitoring.alerts
           WHERE is_simulated = false
           ORDER BY triggered_at DESC LIMIT 50;""",
        0, y,
    ))
    y += 8

    panels.append(_table_panel(
        2, "Schema Drift - Menunggu Review (M1.4)",
        """SELECT detected_at, schema_name, table_name, column_name, drift_type, severity, detail
           FROM monitoring.schema_drift_events
           WHERE status = 'pending' AND schema_name != '_simulation'
           ORDER BY severity DESC, detected_at DESC;""",
        0, y,
    ))
    y += 8

    panels.append(_table_panel(
        3, "Volume & Freshness - Status Terkini (M1.2, 23 tabel)",
        f"""SELECT
                {PRIORITY_CASE_SQL} AS prioritas,
                schema_name, table_name, as_of_date, rows_today,
                baseline_mean, pct_diff_from_baseline, baseline_status,
                freshness_column, freshness_lag_hours
            FROM monitoring.current_status
            ORDER BY {PRIORITY_ORDER_SQL}, table_name;""",
        0, y, h=12,
    ))
    y += 12

    panels.append(_table_panel(
        4, "Kualitas Data - Ringkasan per Tabel (M1.3, run terakhir)",
        f"""WITH latest_date AS (
                SELECT MAX(run_date) AS run_date FROM monitoring.dq_test_results
                WHERE schema_name != '_simulation'
            )
            SELECT
                {PRIORITY_CASE_SQL} AS prioritas,
                r.schema_name, r.table_name,
                COUNT(*) FILTER (WHERE r.success) AS passed,
                COUNT(*) FILTER (WHERE NOT r.success) AS failed,
                COUNT(*) AS total_expectation
            FROM monitoring.dq_test_results r, latest_date d
            WHERE r.run_date = d.run_date AND r.schema_name != '_simulation'
            GROUP BY r.schema_name, r.table_name
            ORDER BY failed DESC, {PRIORITY_ORDER_SQL}, r.table_name;""",
        0, y, h=10,
    ))
    y += 10

    panels.append(_table_panel(
        5, "Kualitas Data - Detail Kegagalan (M1.3, run terakhir)",
        """WITH latest_date AS (
               SELECT MAX(run_date) AS run_date FROM monitoring.dq_test_results
               WHERE schema_name != '_simulation'
           )
           SELECT r.run_at, r.schema_name, r.table_name, r.expectation_type,
                  r.expectation_detail, r.unexpected_count
           FROM monitoring.dq_test_results r, latest_date d
           WHERE r.run_date = d.run_date AND r.success = false AND r.schema_name != '_simulation'
           ORDER BY r.run_at DESC;""",
        0, y, h=8,
    ))
    y += 8

    panels.append(_table_panel(
        6, "Proporsi Dirty Data Terkini (M1.3)",
        """WITH latest AS (
               SELECT schema_name, table_name, column_name, MAX(snapshot_date) AS snapshot_date
               FROM monitoring.dirty_proportion_snapshot WHERE schema_name != '_simulation'
               GROUP BY schema_name, table_name, column_name
           )
           SELECT s.schema_name, s.table_name, s.column_name, s.snapshot_date, s.dirty_pct
           FROM monitoring.dirty_proportion_snapshot s
           JOIN latest l ON l.schema_name=s.schema_name AND l.table_name=s.table_name
                         AND l.column_name=s.column_name AND l.snapshot_date=s.snapshot_date
           ORDER BY s.table_name, s.column_name;""",
        0, y, h=8,
    ))
    y += 8

    panels.append(_table_panel(
        7, "Anomali Nilai IQR Terkini (M1.3)",
        """WITH latest AS (
               SELECT schema_name, table_name, column_name, MAX(snapshot_date) AS snapshot_date
               FROM monitoring.value_anomaly_snapshot WHERE schema_name != '_simulation'
               GROUP BY schema_name, table_name, column_name
           )
           SELECT s.schema_name, s.table_name, s.column_name, s.snapshot_date, s.median,
                  s.outlier_count, s.row_count,
                  ROUND(s.outlier_count::numeric / NULLIF(s.row_count, 0) * 100, 2) AS outlier_pct
           FROM monitoring.value_anomaly_snapshot s
           JOIN latest l ON l.schema_name=s.schema_name AND l.table_name=s.table_name
                         AND l.column_name=s.column_name AND l.snapshot_date=s.snapshot_date
           ORDER BY outlier_pct DESC;""",
        0, y, h=8,
    ))
    y += 8

    return panels


def upsert_dashboard():
    global DS_UID
    DS_UID = _get_datasource_uid()
    panels = build_panels()

    dashboard = {
        "title": DASHBOARD_TITLE,
        "uid": "nirwana-data-monitoring",
        "panels": panels,
        "schemaVersion": 39,
        "refresh": "5m",
        "time": {"from": "now-24h", "to": "now"},
        "tags": ["nirwana", "milestone-1.5", "data-production-monitoring"],
    }

    status, result = api_request("POST", "/api/dashboards/db", {
        "dashboard": dashboard,
        "overwrite": True,
        "message": "Provisioned via scripts/grafana/build_dashboard.py",
    })
    return status, result


DS_UID = None

if __name__ == "__main__":
    status, result = upsert_dashboard()
    print(f"Status: {status}")
    print(result)
