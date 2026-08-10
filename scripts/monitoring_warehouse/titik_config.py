"""
Konfigurasi mapping 9 titik pengamatan (dari 10, titik 10 dikecualikan -- lihat bawah)
ke sumber sinyal GitHub Actions untuk Milestone 6.2.

Sumber: docs/10-monitoring-warehouse-serving/pemetaan-titik-pengamatan-pipeline.md (Milestone 6.1)
        + milestones/6.2-monitoring-log-proses-pipeline/decisions.md

workflow_name harus PERSIS cocok field `name:` di file .github/workflows/*.yml terkait
(itu yang dikirim GitHub lewat github.event.workflow_run.name saat runtime, bukan nama file):
  Extract Production to Raw Warehouse              -> extract-production.yml
  Transform Staging and Mart Cleaned                -> transform-mart-cleaned.yml
  Reverse ETL Mart Cleaned to Serving PostgreSQL    -> reverse-etl-mart-cleaned.yml
  Scoring Occupancy Forecast (Mock)                 -> scoring-occupancy-forecast.yml
  Transform Mart Aggregated                         -> transform-mart-aggregated.yml
  Reverse ETL Mart Aggregated to Serving PostgreSQL -> reverse-etl-mart-aggregated.yml

step_name_substring:
  None  -> granularitas run-level, ambil status/timing dari github.event.workflow_run langsung
           (tidak perlu panggil GET .../runs/{id}/jobs sama sekali)
  str   -> granularitas step-level, cari step di GET .../runs/{id}/jobs yang `name`-nya
           mengandung substring ini (persis 1 match diharapkan per run)

granularity:
  'detailed' -> step/run ini representasi ASLI titik tersebut
  'coarse'   -> sinyal "dipinjam" dari step titik lain (titik 3 dari step titik 2,
                titik 7 dari step titik 6) -- lihat Keputusan #2 decisions.md. Cuma
                menjawab pass/fail, TIDAK bisa membedakan tahap mana yang gagal di
                dalamnya (itu tetap scope Milestone 6.3, docs/keputusan-tertunda.md).

Titik 10 (post-sync row-count parity) SENGAJA TIDAK ADA di list ini -- sinyalnya sudah
lebih granular dari GitHub Actions manapun (monitoring.reverse_etl_sync_log, per-tabel,
ditulis sync.py langsung), tidak diproses listener script M6.2.
"""

TITIK = [
    # titik_id, titik_label, workflow_name, step_name_substring, granularity
    (1, "Extract production -> raw_production",
        "Extract Production to Raw Warehouse", None, "detailed"),

    (2, "Transform staging -> mart_cleaned",
        "Transform Staging and Mart Cleaned",
        "build->test->swap gate ke mart_cleaned", "detailed"),

    (3, "DQ test mart_cleaned (coarse, dari gate promote.py)",
        "Transform Staging and Mart Cleaned",
        "build->test->swap gate ke mart_cleaned", "coarse"),

    (4, "Trigger scoring eksternal (mock)",
        "Scoring Occupancy Forecast (Mock)", None, "detailed"),

    (5, "Sensor ml_output",
        "Transform Mart Aggregated",
        "sensor, tunggu ml_output.predictions", "detailed"),

    (6, "Transform mart_aggregated (+join ml_output)",
        "Transform Mart Aggregated",
        "build->test->swap gate, 76 tabel existing", "detailed"),

    (7, "DQ test mart_aggregated (coarse, dari gate promote.py)",
        "Transform Mart Aggregated",
        "build->test->swap gate, 76 tabel existing", "coarse"),

    (8, "Reverse ETL mart_aggregated -> Postgres",
        "Reverse ETL Mart Aggregated to Serving PostgreSQL", None, "detailed"),

    (9, "Reverse ETL mart_cleaned -> Postgres",
        "Reverse ETL Mart Cleaned to Serving PostgreSQL", None, "detailed"),
]


def titik_for_workflow(workflow_name):
    """Kembalikan seluruh baris TITIK yang match workflow_name -- bisa >1 (titik 2&3, titik 6&7)."""
    return [t for t in TITIK if t[2] == workflow_name]
