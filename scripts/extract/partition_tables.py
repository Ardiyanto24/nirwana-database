"""
Milestone 2.1, Task 6 -- add time partitioning to the raw tables that have a
genuinely clean DATE/TIMESTAMP column (verified via `bq show --schema`, not
assumed). Tables whose only date-like column is dirty text (`employees.hire_date`,
~2% DD/MM/YYYY -- see scripts/monitoring/tables_config.py) or a text period
(`payroll.period`, `financial_summary.period`, `employee_performance.review_period`)
are intentionally NOT partitioned here -- partitioning requires a native
DATE/TIMESTAMP column, and raw_production preserves dirty data as-is (no
cleaning at this layer, see docs/03-implementation-plans/02-serving-data-scientist.md
"Konteks dan Prinsip Kunci"). Reference/snapshot tables with no date column at
all (properties, role_permissions, fnb_outlets, recipe_bom, fnb_inventory,
rooms, venues, event_bookings) are also skipped -- nothing meaningful to
partition on.

Uses CREATE OR REPLACE TABLE ... PARTITION BY ... AS SELECT * FROM <table> --
this is DDL (allowed in BigQuery Sandbox mode), not DML (blocked, see
decisions.md "BigQuery Sandbox mode" finding).
"""
import os
import sys

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "monitoring"))
from bq import get_client  # noqa: E402

# (schema, table, date_column, is_timestamp)
PARTITION_TABLES = [
    ("corporate_master", "guests", "registered_date", False),
    ("reservation_revenue", "bookings", "booking_date", False),
    ("reservation_revenue", "daily_occupancy", "date", False),
    ("reservation_revenue", "pricing_history", "date", False),
    ("fnb_operations", "ingredient_price_history", "date", False),
    ("fnb_operations", "fnb_transactions", "transaction_datetime", True),
    ("fnb_operations", "fnb_waste_log", "date", False),
    ("facility_maintenance", "housekeeping_log", "date", False),
    ("facility_maintenance", "maintenance_tickets", "reported_date", False),
    ("spa_event", "spa_bookings", "booking_date", False),
    ("hr_finance", "staff_shifts", "date", False),
]


def main():
    client, dataset = get_client()
    project = client.project
    for schema, table, col, is_timestamp in PARTITION_TABLES:
        table_id = f"{schema}__{table}"
        tmp_id = f"{table_id}__partitioned_tmp"
        full = f"`{project}.{dataset}.{table_id}`"
        tmp = f"`{project}.{dataset}.{tmp_id}`"
        partition_expr = f"DATE({col})" if is_timestamp else col

        # BigQuery can't change an existing table's partitioning spec in place
        # (CREATE OR REPLACE with a new spec errors) -- build a partitioned
        # copy, drop the original, then rename the copy back.
        client.query(f"CREATE OR REPLACE TABLE {tmp} PARTITION BY {partition_expr} AS SELECT * FROM {full}").result()
        client.query(f"DROP TABLE {full}").result()
        client.query(f"ALTER TABLE {tmp} RENAME TO {table_id}").result()
        print(f"{schema}.{table}: partitioned by {partition_expr}")


if __name__ == "__main__":
    main()
