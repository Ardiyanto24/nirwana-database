"""
Milestone 2.5 Task 3 -- proves a Data Scientist can pull mart_cleaned data
programmatically using ONLY the data-scientist-reader credential (Kriteria
Keberhasilan #1: "berhasil mengambil data ... tanpa memerlukan akses langsung
ke kredensial admin/service account inti"). This script never reads
DBT_TRANSFORM_CREDENTIALS, GOOGLE_APPLICATION_CREDENTIALS, or any other admin
key -- only DATA_SCIENTIST_READER_CREDENTIALS.

Usage: python scripts/data_scientist_access/example_query.py
"""
import os

import pandas as pd
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
    keyfile_env = env["DATA_SCIENTIST_READER_CREDENTIALS"]
    keyfile = keyfile_env if os.path.isabs(keyfile_env) else os.path.join(REPO_ROOT, keyfile_env)
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = keyfile
    return bigquery.Client(project=PROJECT_ID)


def main():
    client = get_client()

    print("=== properties (semua baris) ===")
    df_properties = client.query(
        "SELECT property_id, property_name, city, star_rating FROM `mart_cleaned.mart_cleaned__properties`"
    ).to_dataframe()
    print(df_properties)

    print("\n=== bookings (sample 5 baris, urut booking_id) ===")
    df_bookings = client.query(
        """
        SELECT booking_id, property_id, check_in_date, check_out_date, total_amount
        FROM `mart_cleaned.mart_cleaned__bookings`
        ORDER BY booking_id
        LIMIT 5
        """
    ).to_dataframe()
    print(df_bookings)

    print("\n=== agregasi contoh: rata-rata total_amount per property (butuh scan, bukti akses row-level penuh) ===")
    df_agg = client.query(
        """
        SELECT property_id, COUNT(*) AS n_bookings, ROUND(AVG(total_amount), 2) AS avg_amount
        FROM `mart_cleaned.mart_cleaned__bookings`
        GROUP BY property_id
        ORDER BY property_id
        """
    ).to_dataframe()
    print(df_agg)

    print(f"\nOK -- seluruh query di atas dijalankan dengan kredensial "
          f"data-scientist-reader saja (lihat GOOGLE_APPLICATION_CREDENTIALS "
          f"yang di-set get_client() dari DATA_SCIENTIST_READER_CREDENTIALS).")


if __name__ == "__main__":
    main()
