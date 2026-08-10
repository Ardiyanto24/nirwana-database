"""
Milestone 6.4 -- Output 3 (KK3): canary check untuk data feature/prediction
drift. TIDAK ADA tabel/dataset drift apa pun di seluruh project saat ini
(decisions.md) -- mekanisme ini murni mendeteksi EKSISTENSI dataset yang
namanya cocok pola umum ("drift", "ml_monitoring"), NOL asumsi skema kolom.
Kalau ditemukan, dicatat 1 baris supaya tim tahu kapan mulai membangun
visualisasi tren sungguhan (KK3 baru bisa dipenuhi penuh setelah itu).

Murni informational -- TIDAK push ke monitoring.alerts (severity CHECK cuma
warning/critical, tidak ada level info -- lihat decisions.md).

Butuh IAM role project-level (roles/bigquery.metadataViewer) di
warehouse-monitor-reader, BEDA dari dataset-ACL per-dataset yang sudah
dipegang kredensial ini -- list_datasets() perlu enumerasi project-wide,
dataset ACL per-dataset saja tidak cukup (dikonfirmasi Checkpoint 4 logs.md).

Usage: python check_drift_data_availability.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bq import PROJECT_ID, get_client
from db import get_connection

# Case-insensitive substring match terhadap dataset_id -- nama persis dokumen
# arsitektur (ml_monitoring.feature_drift) cuma ilustratif, jadi dicek pola
# umum bukan nama exact.
NAME_PATTERNS = ("drift", "ml_monitoring")


def find_drift_dataset(client):
    for dataset in client.list_datasets():
        dataset_id_lower = dataset.dataset_id.lower()
        if any(pattern in dataset_id_lower for pattern in NAME_PATTERNS):
            return dataset.dataset_id
    return None


def record_check(conn, dataset_found, dataset_name):
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO monitoring.ml_drift_data_availability_check
            (dataset_found, dataset_name, project_id)
        VALUES (%s, %s, %s)
        """,
        (dataset_found, dataset_name, PROJECT_ID),
    )
    conn.commit()
    cur.close()


def main():
    client = get_client()
    dataset_name = find_drift_dataset(client)
    dataset_found = dataset_name is not None

    conn = get_connection(readonly=False)
    try:
        record_check(conn, dataset_found, dataset_name)
    finally:
        conn.close()

    if dataset_found:
        print(f"[FOUND] dataset drift terdeteksi: {dataset_name} -- saatnya membangun visualisasi tren sungguhan (KK3).")
    else:
        print("[ok] belum ada dataset drift -- KK3 masih menunggu tim Data Scientist mengekspos data.")


if __name__ == "__main__":
    main()
