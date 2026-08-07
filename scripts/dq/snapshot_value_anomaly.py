"""
Milestone 1.3 - Task 6: snapshot statistik IQR harian per kolom nilai bisnis kritis +
evaluasi drift (fence hari ini dibanding histori fence, bukan mean+-stddev seperti M1.2 --
lihat decisions.md kenapa IQR dipilih untuk kolom nilai yang skewed).
"""
import datetime
import statistics
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "monitoring"))
from db import get_connection  # noqa: E402

from value_anomaly_config import VALUE_COLUMNS, IQR_K

MIN_HISTORY_POINTS = 3
FENCE_DRIFT_WARNING_SIGMA = 2
FENCE_DRIFT_CRITICAL_SIGMA = 3


def snapshot_value_anomaly(conn, snapshot_date=None):
    snapshot_date = snapshot_date or datetime.date.today()
    cur = conn.cursor()
    results = []
    for schema, table, column, filter_sql in VALUE_COLUMNS:
        where_clause = f"WHERE {filter_sql}" if filter_sql else ""
        cur.execute(f"""
            SELECT
                COUNT(*),
                PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY "{column}"),
                PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY "{column}"),
                PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY "{column}")
            FROM "{schema}"."{table}" {where_clause};
        """)
        row_count, q1, median, q3 = cur.fetchone()
        iqr = float(q3 - q1)
        lower_fence = float(q1) - IQR_K * iqr
        upper_fence = float(q3) + IQR_K * iqr

        cur.execute(f"""
            SELECT COUNT(*) FROM "{schema}"."{table}" {where_clause}
            {"AND" if where_clause else "WHERE"} ("{column}" < %s OR "{column}" > %s);
        """, (lower_fence, upper_fence))
        outlier_count = cur.fetchone()[0]

        cur.execute(
            """
            INSERT INTO monitoring.value_anomaly_snapshot
                (schema_name, table_name, column_name, snapshot_date, q1, median, q3, iqr,
                 lower_fence, upper_fence, outlier_count, row_count)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (schema_name, table_name, column_name, snapshot_date)
            DO UPDATE SET q1=EXCLUDED.q1, median=EXCLUDED.median, q3=EXCLUDED.q3, iqr=EXCLUDED.iqr,
                          lower_fence=EXCLUDED.lower_fence, upper_fence=EXCLUDED.upper_fence,
                          outlier_count=EXCLUDED.outlier_count, row_count=EXCLUDED.row_count,
                          created_at=now();
            """,
            (schema, table, column, snapshot_date, q1, median, q3, iqr,
             lower_fence, upper_fence, outlier_count, row_count),
        )
        results.append((schema, table, column, float(median), lower_fence, upper_fence, outlier_count, row_count))
    conn.commit()
    cur.close()
    return results


def evaluate_outlier_drift(cur, schema, table, column, snapshot_date):
    """Bandingkan proporsi outlier hari ini vs histori proporsi outlier (rolling)."""
    cur.execute(
        """
        SELECT outlier_count, row_count FROM monitoring.value_anomaly_snapshot
        WHERE schema_name=%s AND table_name=%s AND column_name=%s AND snapshot_date=%s;
        """,
        (schema, table, column, snapshot_date),
    )
    row = cur.fetchone()
    if row is None or not row[1]:
        return None
    today_pct = row[0] / row[1] * 100

    cur.execute(
        """
        SELECT outlier_count, row_count FROM monitoring.value_anomaly_snapshot
        WHERE schema_name=%s AND table_name=%s AND column_name=%s AND snapshot_date < %s
        ORDER BY snapshot_date DESC LIMIT 12;
        """,
        (schema, table, column, snapshot_date),
    )
    history = [(r[0] / r[1] * 100) for r in cur.fetchall() if r[1]]

    if len(history) < MIN_HISTORY_POINTS:
        return {"status": "insufficient_history", "today_pct": round(today_pct, 3)}

    mean = statistics.mean(history)
    stdev = statistics.pstdev(history) or 1e-9
    z = (today_pct - mean) / stdev
    if abs(z) >= FENCE_DRIFT_CRITICAL_SIGMA:
        severity = "critical"
    elif abs(z) >= FENCE_DRIFT_WARNING_SIGMA:
        severity = "warning"
    else:
        severity = None
    return {"status": "evaluated", "today_pct": round(today_pct, 3), "baseline_mean_pct": round(mean, 3),
            "z_score": round(z, 2), "severity": severity}


if __name__ == "__main__":
    conn = get_connection(readonly=False)
    try:
        rows = snapshot_value_anomaly(conn)
        print(f"Snapshot IQR untuk {len(rows)} kolom tersimpan.\n")
        for schema, table, column, median, lo, hi, outliers, total in rows:
            pct = round(outliers / total * 100, 2) if total else 0
            print(f"  {schema}.{table}.{column}: median={median:,.0f} fence=[{lo:,.0f}, {hi:,.0f}] "
                  f"outlier={outliers}/{total} ({pct}%)")
    finally:
        conn.close()
