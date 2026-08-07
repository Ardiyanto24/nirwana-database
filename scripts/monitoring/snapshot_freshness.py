"""
Milestone 1.2 - Task 5: freshness check per tabel.

Untuk tabel yang punya freshness_column (lihat tables_config.py), hitung
MAX(kolom sinyal) dan lag_hours terhadap waktu snapshot diambil, simpan ke
monitoring.freshness_snapshot. Tabel tanpa sinyal freshness tetap dicatat
(freshness_column/latest_value/lag_hours = NULL) supaya jelas "diukur,
tapi memang tidak berlaku" -- bukan diam-diam terlewat.
"""
import datetime
from db import get_connection
from tables_config import TABLES


def _parse_ddmmyyyy_mixed(cur, schema, table, column):
    """~2% baris DD/MM/YYYY, sisanya YYYY-MM-DD (dirty data, lihat decisions.md)."""
    cur.execute(f'SELECT "{column}" FROM "{schema}"."{table}" WHERE "{column}" IS NOT NULL AND "{column}" != \'\';')
    max_date = None
    for (raw,) in cur.fetchall():
        parsed = None
        for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
            try:
                parsed = datetime.datetime.strptime(raw.strip(), fmt).date()
                break
            except ValueError:
                continue
        if parsed and (max_date is None or parsed > max_date):
            max_date = parsed
    return max_date


def _parse_period_month(value):
    """'YYYY-MM' -> tanggal akhir bulan tersebut."""
    year, month = int(value[:4]), int(value[5:7])
    if month == 12:
        next_month_first = datetime.date(year + 1, 1, 1)
    else:
        next_month_first = datetime.date(year, month + 1, 1)
    return next_month_first - datetime.timedelta(days=1)


def _parse_period_semester(value):
    """'YYYY-S1' -> 30 Juni, 'YYYY-S2' -> 31 Desember."""
    year, sem = int(value[:4]), value[5:]
    return datetime.date(year, 6, 30) if sem == "S1" else datetime.date(year, 12, 31)


def snapshot_freshness(conn, snapshot_date=None, reference_now=None):
    snapshot_date = snapshot_date or datetime.date.today()
    reference_now = reference_now or datetime.datetime.now(datetime.timezone.utc)
    cur = conn.cursor()
    results = []

    for schema, table, priority, freshness_col, col_type, cadence in TABLES:
        latest_value = None

        if col_type == "date":
            cur.execute(f'SELECT MAX("{freshness_col}") FROM "{schema}"."{table}";')
            row = cur.fetchone()[0]
            if row is not None:
                latest_value = row if isinstance(row, datetime.datetime) else datetime.datetime.combine(row, datetime.time.min)

        elif col_type == "text_ddmmyyyy_mixed":
            max_date = _parse_ddmmyyyy_mixed(cur, schema, table, freshness_col)
            if max_date:
                latest_value = datetime.datetime.combine(max_date, datetime.time.min)

        elif col_type == "text_period_month":
            cur.execute(f'SELECT MAX("{freshness_col}") FROM "{schema}"."{table}" WHERE "{freshness_col}" IS NOT NULL;')
            row = cur.fetchone()[0]
            if row:
                latest_value = datetime.datetime.combine(_parse_period_month(row), datetime.time.min)

        elif col_type == "text_period_semester":
            cur.execute(f'SELECT MAX("{freshness_col}") FROM "{schema}"."{table}" WHERE "{freshness_col}" IS NOT NULL;')
            row = cur.fetchone()[0]
            if row:
                latest_value = datetime.datetime.combine(_parse_period_semester(row), datetime.time.min)

        # col_type is None -> volume-only table, latest_value stays None

        lag_hours = None
        if latest_value is not None:
            latest_value_utc = latest_value.replace(tzinfo=datetime.timezone.utc)
            lag_hours = round((reference_now - latest_value_utc).total_seconds() / 3600, 1)

        cur.execute(
            """
            INSERT INTO monitoring.freshness_snapshot
                (schema_name, table_name, snapshot_date, freshness_column, latest_value, lag_hours)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (schema_name, table_name, snapshot_date)
            DO UPDATE SET freshness_column = EXCLUDED.freshness_column,
                          latest_value = EXCLUDED.latest_value,
                          lag_hours = EXCLUDED.lag_hours,
                          created_at = now();
            """,
            (schema, table, snapshot_date, freshness_col, latest_value, lag_hours),
        )
        results.append((schema, table, freshness_col, latest_value, lag_hours))

    conn.commit()
    cur.close()
    return results


if __name__ == "__main__":
    conn = get_connection(readonly=False)
    try:
        rows = snapshot_freshness(conn)
        print(f"Snapshot freshness untuk {len(rows)} tabel tersimpan.")
        for schema, table, col, latest, lag in rows:
            if col is None:
                print(f"  {schema}.{table}: volume-only (tanpa sinyal freshness)")
            else:
                print(f"  {schema}.{table} ({col}): latest={latest}  lag={lag}h")
    finally:
        conn.close()
