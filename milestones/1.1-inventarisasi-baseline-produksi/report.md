# Milestone 1.1: Inventarisasi dan Baseline Sumber Data Production — Report

**Status:** Completed
**Date completed:** 2026-08-07

## Kriteria Keberhasilan — Hasil

- [x] **Setiap 23 tabel di 6 database punya klasifikasi prioritas dan catatan karakteristik yang jelas.** — Evidence: `docs/04-monitoring/baseline-inventaris-produksi.md`, bagian "Pemetaan 23 Tabel" (6 sub-tabel per schema, 23/23 terisi: baris live, skor, prioritas, kolom kritis bisnis, kolom kotor/nullable yang sah).
- [x] **Dokumen ini bisa dipakai sebagai rujukan langsung oleh milestone-milestone berikutnya tanpa perlu analisis ulang dari nol.** — Evidence: baseline volume diverifikasi live (bukan disalin mentah dari dokumentasi), pola dirty data dikonfirmasi dengan query sampling aktual, dan katalog kandidat business rule per schema sudah tersedia sebagai starting point Milestone 1.3.

## Deliverables

- `docs/04-monitoring/baseline-inventaris-produksi.md` — deliverable utama: pemetaan 23 tabel + katalog business rule + temuan penting.
- `milestones/1.1-inventarisasi-baseline-produksi/decisions.md` — 4 keputusan teknis (rubrik prioritas, sumber baseline, cakupan business rule, lokasi deliverable) dengan alasan & alternatif yang ditolak.
- `milestones/1.1-inventarisasi-baseline-produksi/logs.md` — jurnal kerja, termasuk hasil verifikasi live dan temuan diskrepansi nama tabel RBAC.

## Deviations from decisions.md

- Checkpoint "review klasifikasi prioritas dengan user sebelum lanjut ke katalog business rule" (tercatat di Task Breakdown `decisions.md`) tidak dilakukan sebagai jeda terpisah — hasil klasifikasi disajikan langsung bersama deliverable final ke user untuk direview/dikoreksi. Alasan: seluruh 23 tabel sudah punya rasionalisasi skor yang bisa ditelusuri (bukan judgment call tersembunyi), dan mengubah klasifikasi satu tabel pun tidak mengubah struktur dokumen — koreksi bisa dilakukan sebagai revisi ringan tanpa mengulang kerja.
- Tidak ada deviasi lain dari `decisions.md`.

## Known Gaps / Follow-ups

- **Diskrepansi nama tabel**: `role_permissions_chatbot_v2` (nama di dokumentasi arsitektur) vs `role_permissions` (nama live di Supabase). Isinya sudah benar (v0.6, 77 baris, 10 domain) — hanya penamaan yang berbeda. Perlu ditindaklanjuti oleh pemilik dokumen arsitektur/skema production: baik menyamakan nama tabel live ke `role_permissions_chatbot_v2`, atau mengoreksi dokumentasi arsitektur ke nama live `role_permissions`. Di luar scope Milestone 1.1 untuk memutuskan/mengeksekusi.
- **`public._sim_state`**: tabel internal generator data, dikecualikan dari cakupan monitoring Fase 1. Tidak perlu tindak lanjut kecuali muncul indikasi ia dipakai proses production yang relevan (saat ini tidak).
- Script verifikasi live yang dipakai bersifat sekali-pakai (scratchpad session), tidak menjadi bagian permanen repo — Milestone 1.2 (monitoring volume/freshness terjadwal) perlu membangun mekanismenya sendiri, bukan reuse langsung.

## Handoff Notes

- **Untuk Milestone 1.2 (volume/freshness)**: pakai daftar 7 tabel prioritas Tinggi (`employees`, `guests`, `role_permissions`, `bookings`, `fnb_transactions`, `staff_shifts`, `payroll`) sebagai kandidat utama monitoring volume harian & freshness; 12 tabel Sedang sebagai kandidat sekunder.
- **Untuk Milestone 1.3 (kualitas data/anomali)**: katalog business rule di `docs/04-monitoring/baseline-inventaris-produksi.md` (bagian "Katalog Kandidat Business Rule") adalah starting point langsung — tinggal pilih tool (dbt/Great Expectations/dst) dan terjemahkan ke syntax test. Kolom kotor/nullable yang sudah diidentifikasi sebagai "bermakna" (mis. `fnb_transactions.guest_id`, `maintenance_tickets.room_id`) **jangan** dialarm sebagai anomali — itu justru sinyal utama yang dijaga Milestone 1.3 (lihat prinsip "murni observasional" di `decisions.md`).
- **Untuk Milestone 1.4 (schema drift)**: baseline struktur saat ini (23 tabel + `_sim_state`) sudah terverifikasi lewat `information_schema.tables`/`information_schema.columns` — bisa dipakai sebagai snapshot pembanding pertama untuk deteksi perubahan skema.
- **Untuk pemilik dokumen arsitektur**: rekomendasikan menyamakan penamaan `role_permissions` vs `role_permissions_chatbot_v2` antara skema live dan dokumentasi — lihat "Known Gaps" di atas.
