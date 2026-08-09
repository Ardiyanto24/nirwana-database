"""
Milestone 3.6 -- proves a Data Analyst can query mart_cleaned AND
mart_aggregated in BigQuery programmatically using ONLY the analyst-readonly
credential. Stands in for a real BI tool connection (Docker wasn't running in
this session to spin up Metabase -- see decisions.md Keputusan #1 and
report.md Known Gaps: KK1 is Partially Met, this script is the strongest
proof available without a live BI tool session, not a substitute for one).

This script never reads DATA_SCIENTIST_READER_CREDENTIALS, DBT_TRANSFORM
credentials, GOOGLE_APPLICATION_CREDENTIALS, or any other admin key -- only
ANALYST_READONLY_CREDENTIALS.

Usage: python scripts/analyst_bi_access/example_query.py
"""
import os

from google.cloud import bigquery

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PROJECT_ID = "nirwana-database-elt"


def _load_env(path):
    env = {}
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    return env


def get_client():
    env = _load_env(os.path.join(REPO_ROOT, ".env"))
    keyfile_env = env["ANALYST_READONLY_CREDENTIALS"]
    keyfile = keyfile_env if os.path.isabs(keyfile_env) else os.path.join(REPO_ROOT, keyfile_env)
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = keyfile
    return bigquery.Client(project=PROJECT_ID)


def main():
    client = get_client()

    print("=== mart_cleaned: properties (row-level, semua baris) ===")
    df_properties = client.query(
        "SELECT property_id, property_name, city, star_rating FROM `mart_cleaned.mart_cleaned__properties`"
    ).to_dataframe()
    print(df_properties)

    print("\n=== mart_cleaned: bookings (sample 5 baris, investigasi ad-hoc) ===")
    df_bookings = client.query(
        """
        SELECT booking_id, property_id, check_in_date, check_out_date, total_amount
        FROM `mart_cleaned.mart_cleaned__bookings`
        ORDER BY booking_id
        LIMIT 5
        """
    ).to_dataframe()
    print(df_bookings)

    print("\n=== mart_aggregated: revenue per tipe kamar (agregat, query eksploratif lintas dataset) ===")
    df_agg = client.query(
        """
        SELECT property_id, room_type_id, AVG(occupancy_rate) AS avg_occupancy, AVG(revpar) AS avg_revpar
        FROM `mart_aggregated.fact_revenue_room_type_daily`
        WHERE period_date BETWEEN '2024-07-01' AND '2024-07-31'
        GROUP BY property_id, room_type_id
        ORDER BY property_id, room_type_id
        """
    ).to_dataframe()
    print(df_agg)

    print(
        "\nOK -- seluruh query di atas (mart_cleaned DAN mart_aggregated) dijalankan "
        "dengan kredensial analyst-readonly saja (lihat GOOGLE_APPLICATION_CREDENTIALS "
        "yang di-set get_client() dari ANALYST_READONLY_CREDENTIALS)."
    )


if __name__ == "__main__":
    main()
