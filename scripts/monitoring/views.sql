-- Milestone 1.2 - Task 8: satu view untuk menjawab Kriteria Keberhasilan #1
-- ("berapa baris masuk hari ini dibanding biasanya" + "kapan data terakhir update")
-- tanpa query manual/analisis terpisah.

CREATE OR REPLACE VIEW monitoring.current_status AS
WITH latest_volume AS (
    SELECT DISTINCT ON (schema_name, table_name)
        schema_name, table_name, snapshot_date, row_count, day_of_week
    FROM monitoring.volume_daily_snapshot
    ORDER BY schema_name, table_name, snapshot_date DESC
),
baseline AS (
    SELECT
        lv.schema_name, lv.table_name,
        AVG(h.row_count)::NUMERIC(14,1) AS baseline_mean,
        STDDEV_POP(h.row_count)::NUMERIC(14,1) AS baseline_stdev,
        COUNT(h.row_count) AS baseline_points
    FROM latest_volume lv
    LEFT JOIN monitoring.volume_daily_snapshot h
        ON h.schema_name = lv.schema_name
       AND h.table_name = lv.table_name
       AND h.day_of_week = lv.day_of_week
       AND h.snapshot_date < lv.snapshot_date
    GROUP BY lv.schema_name, lv.table_name
),
latest_freshness AS (
    SELECT DISTINCT ON (schema_name, table_name)
        schema_name, table_name, freshness_column, latest_value, lag_hours
    FROM monitoring.freshness_snapshot
    ORDER BY schema_name, table_name, snapshot_date DESC
)
SELECT
    lv.schema_name,
    lv.table_name,
    lv.snapshot_date AS as_of_date,
    lv.row_count AS rows_today,
    b.baseline_mean,
    b.baseline_stdev,
    b.baseline_points,
    CASE WHEN b.baseline_points >= 3 AND b.baseline_mean > 0
         THEN ROUND(((lv.row_count - b.baseline_mean) / b.baseline_mean * 100)::NUMERIC, 1)
         ELSE NULL END AS pct_diff_from_baseline,
    CASE WHEN b.baseline_points < 3 THEN 'histori belum cukup (<3 titik)' ELSE 'cukup' END AS baseline_status,
    lf.freshness_column,
    lf.latest_value AS last_data_event_at,
    lf.lag_hours AS freshness_lag_hours
FROM latest_volume lv
LEFT JOIN baseline b ON b.schema_name = lv.schema_name AND b.table_name = lv.table_name
LEFT JOIN latest_freshness lf ON lf.schema_name = lv.schema_name AND lf.table_name = lv.table_name
ORDER BY lv.schema_name, lv.table_name;
