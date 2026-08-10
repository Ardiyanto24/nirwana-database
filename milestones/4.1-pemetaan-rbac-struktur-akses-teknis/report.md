# Milestone 4.1: Pemetaan RBAC ke Struktur Akses Teknis — Report

**Status:** Completed
**Date completed:** 2026-08-10

## Kriteria Keberhasilan — Hasil

- [x] **Setiap 10 `data_domain` punya pemetaan teknis yang jelas ke struktur `mart_aggregated`/`mart_cleaned`, termasuk kasus khusus `guests_pii`/`guests_profile`.** — Diverifikasi: query `SELECT DISTINCT data_domain FROM corporate_master.role_permissions` menghasilkan persis 10 domain (`employees_directory`, `facility`, `financial`, `fnb`, `guests_pii`, `guests_profile`, `hr`, `properties_ref`, `reservation`, `spa_event`), seluruhnya tertelusuri ke §2.1-2.10 `docs/09-serving-ai-chatbot/pemetaan-akses-teknis-chatbot.md`. `guests_pii`/`guests_profile` diwujudkan sebagai 2 view berbeda (`guests_contact_view`/`guests_profile_view`) di atas tabel fisik `mart_cleaned.guests` yang sama, sesuai §4 `rancangan-rbac-ai-chatbot.md`.
- [x] **Pemetaan ini bisa dipakai langsung sebagai acuan Milestone 4.2 tanpa perlu menerka ulang dari `role_permissions`.** — Setiap baris tabel domain di §2 mencantumkan tabel/kolom nyata yang sudah diverifikasi ke `DataSchema-mart-aggregated.md`, `Metadata.md`, dan 3 dokumen kebutuhan persona (bukan diasumsikan dari kesan umum) — pola verifikasi sama seperti dokumen kebutuhan chatbot asli. §3 memberi kontrak kolom eksak untuk 2 view PII, §4 memberi input langsung untuk kelompok kredensial M4.3.

## Deliverables

- `milestones/4.1-pemetaan-rbac-struktur-akses-teknis/decisions.md` — contract, temuan eksplorasi, 2 keputusan via `AskUserQuestion` + 5 keputusan teknis turunan, task breakdown 3 fase.
- `docs/09-serving-ai-chatbot/pemetaan-akses-teknis-chatbot.md` — pemetaan teknis 10 domain, mekanisme filter `own_property`/`all_properties`, kontrak 2 view PII, ringkasan 10 kelompok kredensial.
- Update `docs/01-architecture/rancangan-arsitektur-data-platform-elt.md` §8.1-8.2 dan `docs/03-implementation-plans/05-serving-ai-chatbot.md` (4 titik) — boundary Lapis 2 direvisi dari "`mart_aggregated` SAJA" menjadi "`mart_aggregated` + tabel `mart_cleaned` terpilih", dengan catatan inline yang merujuk balik ke milestone ini.

## Deviations from decisions.md

- **Perluasan boundary Lapis 2 (Keputusan #1) adalah deviasi dari dokumen sumber `05-serving-ai-chatbot.md` versi awal**, yang eksplisit menyatakan Lapis 2 hanya `mart_aggregated`. Deviasi ini disengaja dan disetujui user setelah ditemukan bahwa mayoritas kebutuhan layer Staff (7/20 persona) secara struktural tidak bisa dipenuhi grain agregat — dicatat lengkap di `decisions.md` Keputusan #1 beserta alternatif yang ditolak.
- **Rencana awal memakai ADR bernomor (`docs/decisions/0001-...`) dibatalkan** setelah dicek ulang bahwa project ini tidak punya konvensi tersebut — diganti pola "catatan revisi inline yang merujuk balik ke `decisions.md`", konsisten pola `DataSchema-mart-aggregated.md` "Koreksi M5.7". Tidak ada `docs/decisions/` dibuat.
- Rencana pengajuan change request M5.6 untuk gap `guests_pii`/`guests_profile` (sempat direkomendasikan di diskusi awal) **tidak jadi dieksekusi** — disupersede oleh Keputusan #1 (lihat `decisions.md` Keputusan #2).

## Known Gaps / Follow-ups

- **Threshold SLA per `priority`** (`facility`) dan **threshold "di luar kebiasaan"** selain `in_watchlist` (`hr`) — gap parameter, bukan gap data, carry-over dari dokumen kebutuhan asli, belum diputuskan di milestone manapun.
- **Harga jual menu resmi** (`fnb`) — tidak ada tabel harga resmi, proxy dari `unit_price` transaksi terakhir, carry-over dari `pemetaan-kebutuhan-chatbot-layer-staff.md`.
- **Performa `guests_contact_view`/`guests_profile_view`** (join `guests` ↔ union `bookings`/`spa_bookings`/`event_bookings` untuk `last_active_property_id`) belum diuji terhadap data nyata — kandidat index tambahan perlu dicek saat implementasi M4.2, pola sama M3.3.
- **Kolom penuh `mart_cleaned.employees` di luar `dim_employee`** (mis. `status`, `hire_date`) belum dipastikan dibutuhkan — didesain sebagai fallback opsional di §2.8, bukan wajib.

## Handoff Notes

- **Untuk Milestone 4.2 (view):** Pakai §2 dan §3 `pemetaan-akses-teknis-chatbot.md` langsung sebagai spesifikasi — termasuk business rule kritis yang di-carry-over dari M3.1 (filter `business_line_id` untuk `financial`, larangan `hr` menyentuh `payroll`, filter `staff_id` wajib untuk data performa individu `facility`).
- **Untuk Milestone 4.3 (kredensial):** §4 memberi struktur 10 kelompok akses (1 per `data_domain`). Implementasi kredensial murni tugas milestone ini sendiri (pola sama `data-scientist-reader` M2.5 dan 7 role Data Analyst M3.5) — tidak perlu koordinasi dengan pemilik `mart_cleaned`/`mart_aggregated`, karena struktur/isi kedua mart tidak berubah.
- **Untuk Milestone 4.4 (API):** Mekanisme filter `own_property`/`all_properties` (§1) adalah kontrak wajib — API bertanggung jawab penuh atas enforcement filter properti (database/view tidak melakukannya), termasuk `last_active_property_id` untuk domain `guests_pii`/`guests_profile`.
- **Dokumen arsitektur berubah** — pemilik/pembaca `rancangan-arsitektur-data-platform-elt.md` dan `05-serving-ai-chatbot.md` di masa depan perlu tahu boundary Lapis 2 sudah direvisi sejak Milestone 4.1, bukan lagi "`mart_aggregated` SAJA" seperti rancangan awal.
