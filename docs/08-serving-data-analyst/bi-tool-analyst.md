# Akses BigQuery Langsung via BI Tool — Data Analyst

**Nirwana Hospitality Group — Data Platform ELT**

| | |
|---|---|
| **Dihasilkan oleh** | Milestone 3.6 (`milestones/3.6-akses-bigquery-bi-tool/`) |
| **Kode** | `scripts/analyst_bi_access/` |
| **Kredensial** | `analyst-readonly@nirwana-database-elt.iam.gserviceaccount.com` |
| **Status** | Kredensial + isolasi + akses terprogram **selesai & terverifikasi**. Koneksi BI tool GUI sungguhan **belum dijalankan** — lihat Status di bawah. |

---

## Kenapa Jalur Ini Ada

Milestone 3.1-3.5 seluruhnya beroperasi di atas `mart_cleaned`/`mart_aggregated` versi **salinan** hasil reverse ETL di serving PostgreSQL. Jalur itu cepat untuk kebutuhan interaktif harian, tapi tetap salinan — ada kelas kebutuhan analitis lanjutan (eksplorasi skala besar, kombinasi tabel/agregasi yang belum tentu terwakili di struktur PostgreSQL) yang menurut arsitektur (`rancangan-arsitektur-data-platform-elt.md` §2.2/§8.1) memang tidak dimaksudkan dipenuhi lewat PostgreSQL — harus lewat BigQuery langsung. Milestone 3.6 membuka jalur itu.

## Kredensial `analyst-readonly`

- **Scope**: dataset ACL READER ke **`mart_cleaned`** dan **`mart_aggregated`** saja — TIDAK ke `raw_production` maupun `ml_output`.
- **Read-only**: `roles/bigquery.jobUser` project-level (untuk menjalankan query) + dataset ACL READER (bukan WRITER/EDITOR) — tidak ada privilege tulis di dataset manapun.
- **Env var**: `ANALYST_READONLY_CREDENTIALS` → `scripts/extract/gcp-analyst-readonly-key.json` (gitignored).

## Bukti Verifikasi (dijalankan sungguhan terhadap BigQuery `nirwana-database-elt`)

| Kriteria Keberhasilan | Status | Bukti |
|---|---|---|
| KK1 — Query eksploratif dari BI tool sungguhan | **Partially Met** | Lihat "Status Jujur" di bawah |
| KK2 — Tidak bisa akses `raw_production`/`ml_output` | **Met** | `verify_dataset_isolation.py --allow mart_cleaned.mart_cleaned__properties --allow mart_aggregated.dim_property --deny raw_production.properties --deny ml_output.predictions` → 4/4 OK |
| KK3 — Read-only, tidak bisa menulis | **Met** | Percobaan `CREATE TABLE mart_cleaned.__test_write_denied_analyst_readonly` → `403 Forbidden` |

## Status Jujur — KK1 Partially Met

Dokumen sumber KK1 secara eksplisit minta "Tim Data Analyst berhasil menjalankan query eksploratif langsung dari BI tool". Yang **sudah** dibuktikan:
- Kredensial bekerja penuh secara terprogram — `scripts/analyst_bi_access/example_query.py` menjalankan query row-level `mart_cleaned` DAN agregat `mart_aggregated` sekaligus, sukses, hanya memakai `analyst-readonly`.
- Panduan koneksi 2 kelas BI tool (upload-key seperti Metabase, OAuth+impersonation seperti Looker Studio) didokumentasikan teknis benar di `scripts/analyst_bi_access/README.md`.

Yang **belum** dibuktikan: koneksi BI tool GUI sungguhan (mis. Metabase via Docker) tidak benar-benar dijalankan — Docker Desktop tidak aktif di lingkungan pengerjaan milestone ini, dan alternatif OAuth (Looker Studio) tidak menguji kredensial `analyst-readonly` yang sama tanpa setup service account impersonation tambahan yang juga belum dikonfigurasi. Keputusan ini diambil sadar bersama user (`decisions.md` Keputusan #1) — bukan terlewat, dicatat eksplisit sebagai Known Gap di `report.md`.

## Cara Pakai

Lihat `scripts/analyst_bi_access/README.md` untuk panduan lengkap (kredensial, contoh query Python, pola koneksi BI tool, daftar tabel).

## Kebijakan Kredensial

Dicatat di `docs/06-akses-kredensial/kebijakan-akses-kredensial-scoped.md` (inventaris project-wide) — `analyst-readonly` adalah kredensial BigQuery kelima di project ini, dan kredensial ketiga yang benar-benar diserahkan ke konsumen akhir (setelah `data-scientist-reader` M2.5 dan 7 role `*_analyst_reader` PostgreSQL M3.5).
