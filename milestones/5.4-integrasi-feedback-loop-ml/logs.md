# Milestone 5.4: Integrasi Feedback Loop ML — Logs

## 2026-08-08 -- Checkpoint 1: decisions.md + kredensial ml-scoring-writer (Fase 0)

`decisions.md` ditulis (11 keputusan: 6 via AskUserQuestion 2 putaran, 5 teknis dikunci mengikuti preseden M5.3). Termasuk catatan status provisional di header dokumen (permintaan eksplisit user setelah plan pertama sempat ditolak untuk direvisi) -- seluruh desain `ml_output`/use-case occupancy forecast di milestone ini murni contoh/simulasi, menunggu definisi nyata dari tim ML Engineer.

Kredensial `ml-scoring-writer` dibuat mengikuti pola `extract-writer` (M2.1) persis -- service account + dataset ACL WRITER scoped, key file dibuat manual oleh user (bukan assistant), konsisten prinsip project ini soal penanganan kredensial mentah:

- `gcloud iam service-accounts create ml-scoring-writer --project=nirwana-database-elt` -- sukses, `ml-scoring-writer@nirwana-database-elt.iam.gserviceaccount.com`.
- `bq mk --dataset --location=US --default_table_expiration=5184000 --default_partition_expiration=5184000 nirwana-database-elt:ml_output` -- dataset baru dibuat, default expiration 60 hari (5184000000 ms) konsisten Sandbox mode, sama seperti dataset lain (`mart_cleaned` dicek sebagai referensi).
- `gcloud projects add-iam-policy-binding nirwana-database-elt --member=serviceAccount:ml-scoring-writer@... --role=roles/bigquery.jobUser` -- sukses.
- Dataset ACL `ml_output`: `bq show --format=prettyjson` -> tambah entry `{"role": "WRITER", "userByEmail": "ml-scoring-writer@..."}` via Python (round-trip JSON, path Windows-native dipakai karena `python.exe` di git-bash tidak resolve path style `/c/...`) -> `bq update --source=<file> nirwana-database-elt:ml_output` -- sukses, diverifikasi ulang lewat `bq show` (WRITER entry ada).

`docs/06-akses-kredensial/kebijakan-akses-kredensial-scoped.md`: baris baru ditambahkan ke tabel inventaris + daftar "Kredensial per-job". `.env.example`: `ML_SCORING_WRITER_CREDENTIALS=scripts/extract/gcp-ml-scoring-writer-key.json` ditambahkan (path sama seperti kredensial lain -- semua key file BigQuery memang disimpan di folder `scripts/extract/` walau beda milestone asal, sudah tercakup pattern `.gitignore` `scripts/extract/*.json` yang ada, tidak perlu entry baru).

**Belum selesai (butuh aksi user):** key file JSON untuk `ml-scoring-writer` belum dibuat -- assistant tidak membuat key file kredensial (prinsip project + batasan keamanan). User perlu jalankan sendiri sebelum Checkpoint 2 (`mock_score.py`) bisa benar-benar dites end-to-end terhadap BigQuery:

```bash
gcloud iam service-accounts keys create scripts/extract/gcp-ml-scoring-writer-key.json \
  --iam-account=ml-scoring-writer@nirwana-database-elt.iam.gserviceaccount.com
```

Setelah key file ada, isi `ML_SCORING_WRITER_CREDENTIALS` di `.env` (bukan `.env.example`) dengan path yang sama, lalu verifikasi isolasi:

```bash
python scripts/bigquery_common/verify_dataset_isolation.py \
  --keyfile scripts/extract/gcp-ml-scoring-writer-key.json \
  --project nirwana-database-elt \
  --allow "ml_output.predictions" \
  --deny "mart_cleaned.financial_summary"
```
