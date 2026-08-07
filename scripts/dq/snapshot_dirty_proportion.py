"""
Milestone 1.3 - Task 4: snapshot proporsi dirty-by-design harian + evaluasi drift.

Untuk tiap kolom di DIRTY_COLUMNS, hitung proporsi "kotor" hari ini, simpan ke
monitoring.dirty_proportion_snapshot. Evaluasi drift memakai rolling baseline
(mean +- k*stddev dari histori) begitu >=3 titik terkumpul; sebelum itu, pakai
bootstrap_expected_pct (angka M1.1) sbg referensi tunggal dengan toleransi longgar.
"""
import datetime
import statistics
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "monitoring"))
from db import get_connection  # noqa: E402

from dirty_columns_config import DIRTY_COLUMNS

MIN_HISTORY_POINTS = 3
DRIFT_WARNING_SIGMA = 2
DRIFT_CRITICAL_SIGMA = 3
BOOTSTRAP_RELATIVE_TOLERANCE = 0.5  # +-50% dari angka M1.1 dianggap wajar sebelum ada histori riil


def snapshot_dirty_proportion(conn, snapshot_date=None):
    snapshot_date = snapshot_date or datetime.date.today()
    cur = conn.cursor()
    results = []
    for schema, table, column, predicate, bootstrap_pct, desc in DIRTY_COLUMNS:
        cur.execute(f'SELECT COUNT(*), COUNT(*) FILTER (WHERE {predicate}) FROM "{schema}"."{table}";')
        total, dirty = cur.fetchone()
        pct = round((dirty / total * 100) if total else 0, 2)
        cur.execute(
            """
            INSERT INTO monitoring.dirty_proportion_snapshot
                (schema_name, table_name, column_name, snapshot_date, total_rows, dirty_rows, dirty_pct)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (schema_name, table_name, column_name, snapshot_date)
            DO UPDATE SET total_rows = EXCLUDED.total_rows, dirty_rows = EXCLUDED.dirty_rows,
                          dirty_pct = EXCLUDED.dirty_pct, created_at = now();
            """,
            (schema, table, column, snapshot_date, total, dirty, pct),
        )
        results.append((schema, table, column, pct, desc))
    conn.commit()
    cur.close()
    return results


def evaluate_drift(cur, schema, table, column, snapshot_date, bootstrap_pct):
    cur.execute(
        """
        SELECT dirty_pct FROM monitoring.dirty_proportion_snapshot
        WHERE schema_name=%s AND table_name=%s AND column_name=%s AND snapshot_date=%s;
        """,
        (schema, table, column, snapshot_date),
    )
    row = cur.fetchone()
    if row is None:
        return None
    today_pct = float(row[0])

    cur.execute(
        """
        SELECT dirty_pct FROM monitoring.dirty_proportion_snapshot
        WHERE schema_name=%s AND table_name=%s AND column_name=%s AND snapshot_date < %s
        ORDER BY snapshot_date DESC LIMIT 12;
        """,
        (schema, table, column, snapshot_date),
    )
    history = [float(r[0]) for r in cur.fetchall()]

    if len(history) >= MIN_HISTORY_POINTS:
        mean = statistics.mean(history)
        stdev = statistics.pstdev(history) or 1e-9
        z = (today_pct - mean) / stdev
        if abs(z) >= DRIFT_CRITICAL_SIGMA:
            severity = "critical"
        elif abs(z) >= DRIFT_WARNING_SIGMA:
            severity = "warning"
        else:
            severity = None
        return {"mode": "rolling", "today_pct": today_pct, "baseline_mean": round(mean, 2),
                "baseline_stdev": round(stdev, 2), "z_score": round(z, 2), "severity": severity}

    # Bootstrap mode: bandingkan ke angka M1.1 dengan toleransi relatif longgar
    lower = bootstrap_pct * (1 - BOOTSTRAP_RELATIVE_TOLERANCE)
    upper = bootstrap_pct * (1 + BOOTSTRAP_RELATIVE_TOLERANCE)
    severity = None
    if today_pct < lower or today_pct > upper:
        severity = "warning"  # bootstrap mode tidak pernah critical -- histori riil belum ada
    return {"mode": "bootstrap", "today_pct": today_pct, "bootstrap_pct": bootstrap_pct,
            "tolerance_band": (round(lower, 2), round(upper, 2)), "severity": severity}


if __name__ == "__main__":
    conn = get_connection(readonly=False)
    try:
        rows = snapshot_dirty_proportion(conn)
        print(f"Snapshot proporsi dirty untuk {len(rows)} kolom tersimpan.\n")
        cur = conn.cursor()
        today = datetime.date.today()
        for schema, table, column, pct, desc in rows:
            bootstrap_pct = next(bp for s, t, c, _, bp, _ in DIRTY_COLUMNS
                                  if (s, t, c) == (schema, table, column))
            drift = evaluate_drift(cur, schema, table, column, today, bootstrap_pct)
            flag = f" -> {drift['severity'].upper()}" if drift and drift["severity"] else ""
            print(f"  {schema}.{table}.{column}: {pct}% ({desc}) [{drift['mode']}]{flag}")
        cur.close()
    finally:
        conn.close()
