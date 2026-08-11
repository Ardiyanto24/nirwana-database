"""
Milestone 6.7 - Checkpoint 3: dashboard Fase 2 (warehouse + serving + chatbot),
terpisah dari dashboard Fase 1 (scripts/grafana/build_dashboard.py, M1.5) --
"dua tampilan terpisah... saling dirujuk" (dokumen sumber). Datasource Postgres
SAMA dengan Fase 1 (SUPABASE_DB_URL admin sudah otomatis bisa baca seluruh
monitoring.* Fase 2, lihat decisions.md Temuan #5) -- tidak ada datasource
baru. Panel murni tabel SQL langsung ke monitoring.* -- tidak menghitung
ulang logic anomali/korelasi apa pun (view monitoring.alerts_with_root_cause,
Checkpoint 2, adalah satu-satunya tempat logic pengelompokan akar masalah).
"""
from grafana_client import api_request

DASHBOARD_TITLE = "Nirwana - Warehouse & Serving Monitoring (Fase 2)"


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


def _text_panel(panel_id, title, markdown, x, y, w=24, h=3):
    return {
        "id": panel_id,
        "type": "text",
        "title": title,
        "gridPos": {"x": x, "y": y, "w": w, "h": h},
        "options": {"mode": "markdown", "content": markdown},
    }


def build_panels():
    panels = []
    y = 0

    panels.append(_table_panel(
        1, "Status 10 Titik Pengamatan Hari Ini (peta M6.1)",
        """WITH titik_meta AS (
                SELECT DISTINCT titik_id, titik_label, priority_class FROM monitoring.titik_dependency
            ),
            real_status AS (
                SELECT DISTINCT ON (titik_id)
                    titik_id, status, (started_at::date = CURRENT_DATE) AS ran_today,
                    started_at, completed_at, duration_seconds
                FROM monitoring.pipeline_run_log
                WHERE trigger_event != 'simulated'
                ORDER BY titik_id, completed_at DESC
            )
            SELECT tm.titik_id, tm.priority_class, tm.titik_label,
                   rs.status, rs.ran_today, rs.started_at, rs.completed_at, rs.duration_seconds
            FROM titik_meta tm
            LEFT JOIN real_status rs ON rs.titik_id = tm.titik_id
            ORDER BY tm.titik_id;""",
        0, y, h=10,
    ))
    y += 10

    panels.append(_table_panel(
        2, "Alert Aktif Hari Ini -- Dikelompokkan per Akar Masalah (KK2, M6.7)",
        """SELECT root_titik_id, is_root, titik_id, event_source, severity, detail, event_at
           FROM monitoring.alerts_with_root_cause
           WHERE is_simulated = false
           ORDER BY root_titik_id, is_root DESC, event_at DESC;""",
        0, y, h=8,
    ))
    y += 8

    panels.append(_table_panel(
        3, "DQ Gate mart_cleaned / mart_aggregated (run terakhir, M6.3)",
        """WITH latest_run AS (
                SELECT layer, MAX(github_run_id) AS github_run_id FROM monitoring.dbt_test_result GROUP BY layer
            )
            SELECT r.layer, r.github_run_id,
                   COUNT(*) FILTER (WHERE r.status = 'pass') AS passed,
                   COUNT(*) FILTER (WHERE r.status = 'fail') AS failed,
                   COUNT(*) AS total_test,
                   MAX(r.captured_at) AS captured_at
            FROM monitoring.dbt_test_result r
            JOIN latest_run l ON l.layer = r.layer AND l.github_run_id = r.github_run_id
            GROUP BY r.layer, r.github_run_id
            ORDER BY r.layer;""",
        0, y, h=6,
    ))
    y += 6

    panels.append(_table_panel(
        4, "Volume Anomaly Warehouse BigQuery -- Alert Terbaru (M6.3)",
        """SELECT triggered_at, schema_name AS dataset_name, table_name, severity, detail
           FROM monitoring.alerts
           WHERE alert_type = 'warehouse_volume_anomaly' AND is_simulated = false AND schema_name != '_simulation'
           ORDER BY triggered_at DESC LIMIT 20;""",
        0, y, h=8,
    ))
    y += 8

    panels.append(_table_panel(
        5, "Kesehatan ml_output -- Staleness / Completeness / Drift Canary (M6.4)",
        """SELECT 'Model Staleness' AS kategori,
                  (model_name || ' ' || model_version) AS item,
                  ('days_since_first_scored=' || days_since_first_scored ||
                   CASE WHEN is_most_recently_active THEN ' (paling aktif)' ELSE '' END) AS detail
           FROM monitoring.ml_model_staleness_status
           WHERE model_name != 'sim_model'
           UNION ALL
           SELECT 'Completeness', ('feature_snapshot_at=' || feature_snapshot_at),
                  ('expected=' || expected_entity_count || ' scored=' || scored_entity_count ||
                   ' missing=' || missing_entity_count)
           FROM monitoring.ml_output_completeness_snapshot
           WHERE snapshot_date = (SELECT MAX(snapshot_date) FROM monitoring.ml_output_completeness_snapshot)
           UNION ALL
           SELECT 'Drift Canary', ('checked_at=' || checked_at),
                  CASE WHEN dataset_found THEN 'dataset ditemukan: ' || dataset_name ELSE 'belum ada dataset drift' END
           FROM monitoring.ml_drift_data_availability_check
           WHERE checked_at = (SELECT MAX(checked_at) FROM monitoring.ml_drift_data_availability_check)
           ORDER BY 1;""",
        0, y, h=8,
    ))
    y += 8

    panels.append(_table_panel(
        6, "Kesehatan Swap Reverse ETL -- Run Terakhir per Tabel (M2.4/M5.5, instrumentasi M6.6)",
        """WITH latest AS (
                SELECT dataset_name, table_name, MAX(synced_at) AS synced_at
                FROM monitoring.reverse_etl_sync_log
                WHERE is_simulated = false AND dataset_name != '_simulation'
                GROUP BY dataset_name, table_name
            )
            SELECT r.dataset_name, r.table_name, r.status, r.swap_duration_ms, r.old_table_status, r.synced_at
            FROM monitoring.reverse_etl_sync_log r
            JOIN latest l ON l.dataset_name = r.dataset_name AND l.table_name = r.table_name AND l.synced_at = r.synced_at
            WHERE r.is_simulated = false AND r.dataset_name != '_simulation'
            ORDER BY r.swap_duration_ms DESC NULLS LAST
            LIMIT 30;""",
        0, y, h=10,
    ))
    y += 10

    panels.append(_table_panel(
        7, "Storage & Vacuum Serving Layer -- Ringkasan per Schema (M6.6)",
        """WITH latest_date AS (
                SELECT MAX(snapshot_date) AS snapshot_date FROM monitoring.serving_storage_snapshot
                WHERE schema_name != '_simulation'
           )
           SELECT s.schema_name,
                  COUNT(*) AS total_tabel,
                  COUNT(*) FILTER (WHERE s.is_orphan) AS orphan_tabel,
                  pg_size_pretty(SUM(s.total_size_bytes)) AS total_size,
                  pg_size_pretty(COALESCE(SUM(s.total_size_bytes) FILTER (WHERE s.is_orphan), 0)) AS orphan_size,
                  MAX(s.last_autovacuum) AS last_autovacuum_terbaru
           FROM monitoring.serving_storage_snapshot s, latest_date d
           WHERE s.snapshot_date = d.snapshot_date AND s.schema_name != '_simulation'
           GROUP BY s.schema_name;""",
        0, y, h=6,
    ))
    y += 6

    panels.append(_table_panel(
        8, "Performa Query AI Chatbot -- Latency Percentile + Denied (24 jam, M6.5)",
        """SELECT
               percentile_cont(0.5) WITHIN GROUP (ORDER BY duration_ms) AS p50_ms,
               percentile_cont(0.95) WITHIN GROUP (ORDER BY duration_ms) AS p95_ms,
               percentile_cont(0.99) WITHIN GROUP (ORDER BY duration_ms) AS p99_ms,
               COUNT(*) AS total_request,
               COUNT(*) FILTER (WHERE status = 'denied') AS denied,
               ROUND(COUNT(*) FILTER (WHERE status = 'denied')::numeric / NULLIF(COUNT(*), 0) * 100, 2) AS denied_pct
           FROM monitoring.chatbot_query_log
           WHERE requested_at > now() - interval '24 hours' AND duration_ms IS NOT NULL;""",
        0, y, h=6,
    ))
    y += 6

    panels.append(_text_panel(
        9, "Lihat Juga",
        "Dashboard ini mencakup **Fase 2** (warehouse BigQuery -> serving PostgreSQL, "
        "termasuk performa AI Chatbot). Untuk monitoring **Fase 1** (kualitas data "
        "production, sebelum masuk `raw_production`), lihat dashboard "
        "[**Nirwana - Data Production Monitoring**](/d/nirwana-data-monitoring).",
        0, y, h=3,
    ))

    return panels


def upsert_dashboard():
    global DS_UID
    DS_UID = _get_datasource_uid()
    panels = build_panels()

    dashboard = {
        "title": DASHBOARD_TITLE,
        "uid": "nirwana-warehouse-serving-monitoring",
        "panels": panels,
        "schemaVersion": 39,
        "refresh": "5m",
        "time": {"from": "now-24h", "to": "now"},
        "tags": ["nirwana", "milestone-6.7", "warehouse-serving-monitoring"],
    }

    status, result = api_request("POST", "/api/dashboards/db", {
        "dashboard": dashboard,
        "overwrite": True,
        "message": "Provisioned via scripts/grafana/build_dashboard_warehouse_serving.py",
    })
    return status, result


DS_UID = None

if __name__ == "__main__":
    status, result = upsert_dashboard()
    print(f"Status: {status}")
    print(result)
