# Milestone 4.5: Audit Log Query Chatbot — Report

**Status:** Completed
**Date completed:** 2026-08-10

## Kriteria Keberhasilan — Hasil

- [x] **Setiap panggilan API (baik berhasil maupun ditolak) tercatat di log dengan detail yang cukup untuk ditelusuri.** — Diuji HTTP nyata lewat 4 skenario (sukses, 403 domain di luar cakupan, 404 view tidak whitelisted, 400 `own_property` tanpa `employee_id`) + 1 skenario tambahan (`all_properties`, tanpa `employee_id`) — seluruhnya tercatat di `monitoring.chatbot_query_log` dengan `role_title`, `domain`, `view_name`, `employee_id`, `access_scope`, `resolved_property_id`, `status`, `denial_reason`/`row_count` yang sesuai. Ditemukan dan diperbaiki di tengah jalan: FastAPI diam-diam membuang `BackgroundTasks` saat handler `raise` exception (hanya jalur sukses yang awalnya tercatat) — diperbaiki dengan `return JSONResponse(..., background=...)` di jalur ditolak, diverifikasi ulang 4/4 tercatat benar setelah fix.
- [x] **Log bisa diquery/diakses secara terpisah dari sistem chatbot itu sendiri.** — `monitoring.chatbot_query_log` adalah tabel PostgreSQL biasa di production Supabase, schema `monitoring` yang sudah jadi backbone monitoring bersama sejak M1.2 — dapat diquery langsung oleh pemilik infrastruktur data tanpa menyentuh proses API chatbot atau sistem chatbot sama sekali (dibuktikan lewat query verifikasi yang dijalankan terpisah dari `uvicorn`, pakai kredensial admin `SUPABASE_DB_URL`).

## Deliverables

- `scripts/chatbot_audit/{schema.sql,connections.py,apply_schema.py,setup_audit_writer.py,verify_role_isolation.py}` — kredensial `chatbot_audit_writer` (INSERT-only) + skema `monitoring.chatbot_query_log`.
- `scripts/chatbot_api/audit.py` + perubahan `scripts/chatbot_api/main.py` — instrumentasi log di setiap outcome (200/403/404/400) via `BackgroundTasks`.
- `docs/09-serving-ai-chatbot/audit-log-chatbot.md` — dokumentasi lengkap (termasuk bagian "Batas Lapis 1/Lapis 2" yang diminta eksplisit user sebelum plan disetujui).
- Update `docs/06-akses-kredensial/kebijakan-akses-kredensial-scoped.md` (+1 baris `chatbot_audit_writer`, +1 bullet "Siapa Boleh Memegang").
- Koreksi `.env.example` (`SUPABASE_DB_URL` ternyata Supavisor pooler, bukan direct connection seperti komentar asli).

## Deviations from decisions.md

Tidak ada deviasi dari 7 keputusan teknis — seluruhnya (lokasi log, kredensial scoped baru, `BackgroundTasks` best-effort, titik pemasangan di level `handler()`, skema kolom, verifikasi HTTP nyata, batas eksplisit Lapis 1/Lapis 2) dieksekusi persis seperti direncanakan. Dua temuan implementasi murni teknis muncul di tengah jalan (didokumentasikan di `decisions.md` "Temuan Implementasi", bukan deviasi keputusan):
1. `SUPABASE_DB_URL` ternyata Supavisor pooler URL, bukan direct connection — regex koneksi disesuaikan, warmup-retry (awalnya mau dibuang di draft plan) dikembalikan.
2. `GRANT INSERT` pada tabel `bigserial` tidak otomatis memberi privilege ke sequence backing-nya — perlu `GRANT USAGE ON SEQUENCE` terpisah.
3. FastAPI membuang `BackgroundTasks` saat handler `raise` — jalur ditolak diubah jadi `return JSONResponse(background=...)`.

## Known Gaps / Follow-ups

- **Best-effort, bukan guaranteed delivery** — kalau proses API mati tepat di antara response terkirim dan background task selesai menulis log, baris itu tidak tercatat. Diterima sadar sebagai keterbatasan skala project ini (dicatat eksplisit di `decisions.md` Keputusan #3 dan `audit-log-chatbot.md`), bukan disembunyikan.
- **Belum ada rotasi terjadwal** untuk `chatbot_audit_writer` — sama seperti gap project-wide yang sudah dicatat di `kebijakan-akses-kredensial-scoped.md` "Rotasi dan Pencabutan" untuk seluruh kredensial lain.
- **Belum ada dashboard/visualisasi** atas log ini — eksplisit cakupan Milestone 6.5 (`06-monitoring-warehouse-serving-fase2.md`), bukan gap M4.5. Contoh query dasar sudah disiapkan di `audit-log-chatbot.md` "Cara Query untuk M6.5".
- **Belum ada konsumen chatbot sungguhan** (sama seperti M4.4) — seluruh verifikasi lewat `curl`/HTTP manual mensimulasikan panggilan Lapis 1.

## Handoff Notes

- **Untuk Milestone 4.6 (Uji Ketahanan RBAC Lintas Persona):** `monitoring.chatbot_query_log` sekarang tersedia sebagai jejak audit tambahan saat menguji 20 persona × 10 domain — `resolved_property_id` khususnya berguna untuk membuktikan override `own_property` benar-benar konsisten di seluruh sampel uji, bukan cuma di beberapa kasus yang diperiksa manual.
- **Untuk Milestone 6.5 (Monitoring Performa Query AI Chatbot):** tabel dan lokasi sudah final (`monitoring.chatbot_query_log`, production Supabase) — 2 contoh query dasar (volume/tren gagal-ditolak per domain, view paling sering diakses) sudah disiapkan di `audit-log-chatbot.md`. Kredensial baca terpisah (`chatbot_audit_reader` atau setara) kemungkinan perlu dibuat M6.5 sendiri, karena `chatbot_audit_writer` sengaja tidak bisa `SELECT` sama sekali.
- **Kalau skema kolom `chatbot_query_log` perlu ditambah nanti** (mis. latency per request): ikuti pola append-only yang sama dengan `reverse_etl_sync_log` (M5.5 menambah `dataset_name` lewat `ALTER TABLE ... ADD COLUMN IF NOT EXISTS`, additive, backward-compatible) — jangan ubah kolom existing.
