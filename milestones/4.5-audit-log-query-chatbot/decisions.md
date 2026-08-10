# Milestone 4.5: Audit Log Query Chatbot — Decisions

**Sumber:** `docs/03-implementation-plans/05-serving-ai-chatbot.md`, Milestone 4.5 (baris 128-144).
**Prasyarat:** Milestone 4.4 (API Query Interface, Completed).
**Status:** In Progress
**Date started:** 2026-08-10

## Lingkup Sumber / Contract

- **Lingkup:** Membangun mekanisme pencatatan setiap query yang dieksekusi lewat API M4.4 — identitas/role pengguna yang meminta, domain/parameter yang diminta, waktu eksekusi, dan hasil (berhasil/ditolak). Menjadi dasar bagi Milestone 6.5 (`06-monitoring-warehouse-serving-fase2.md`, monitoring performa query chatbot).
- **Output:**
  1. Mekanisme pencatatan log query: identitas pengguna, role, domain diminta, waktu, status (berhasil/ditolak), jumlah baris hasil.
  2. Log tersimpan di lokasi yang bisa diakses pekerjaan monitoring Fase 2 tanpa perlu integrasi tambahan yang rumit.
- **Kriteria Keberhasilan:**
  1. Setiap panggilan API (baik berhasil maupun ditolak) tercatat di log dengan detail yang cukup untuk ditelusuri.
  2. Log bisa diquery/diakses secara terpisah dari sistem chatbot itu sendiri (tidak terkubur di dalam log aplikasi chatbot yang tidak bisa diakses tim data).

## Temuan Eksplorasi (sebelum breakdown)

- **Precedent M2.4** (`milestones/2.4-reverse-etl-postgresql/decisions.md` Keputusan #6, dikutip ulang di CLAUDE.md sebagai konvensi project): tabel log lintas-sistem (`reverse_etl_sync_log`) selalu ditulis ke `monitoring.*` di **production Supabase** — bukan di lokasi fisik sistem yang dipantau — "monitoring stays centralized in one place by design". Prinsip project-wide yang sudah dikunci sebelum M4.5, bukan keputusan baru.
- **Gap ditemukan**: tidak ada satupun writer `monitoring.*` existing yang pakai kredensial scoped — `scripts/monitoring/db.py` dan `scripts/reverse_etl/connections.py` semua pakai admin `SUPABASE_DB_URL` mentah. Untuk M4.5 ini lebih material dari sekadar kurang rapi: API chatbot (`scripts/chatbot_api/`) sampai M4.4 selesai **sama sekali tidak pernah** terhubung ke instance production Supabase — seluruh 11 kredensialnya (M4.3+M4.4) scoped ke serving Postgres saja, sesuai janji arsitektur M4.1 ("isolasi ke raw_production tetap mutlak"). Memberi API ini kredensial admin penuh ke production Supabase demi 1 INSERT akan jadi celah baru yang tidak proporsional.
- Pola sync existing menulis blocking/synchronous per baris di dalam loop job batch (maksimal 23 tabel) — aman untuk batch job, tapi API chatbot menerima banyak request kecil sering (karakteristik eksplisit disebut sumber M6.5). INSERT blocking lintas-project di jalur request langsung akan menambah latency ke **setiap** panggilan API.
- **report.md M4.4** menyebut titik integrasi paling wajar ada di dalam `authorize()` — ternyata tidak cukup begitu breakdown dimulai: `authorize()` cuma menangani kasus 403. Kasus 404 (`view_name` tidak whitelisted) dan 400 (`own_property` tanpa `employee_id`) terjadi setelah `authorize()` lolos.

## Keputusan Teknis

### 1. Lokasi log: `monitoring.chatbot_query_log` di production Supabase

Mengikuti konvensi M2.4 yang sudah dikunci project-wide ("monitoring stays centralized"), sekaligus memenuhi kalimat literal sumber ("lokasi yang bisa diakses monitoring Fase 2 tanpa integrasi tambahan yang rumit") — M6.x nanti otomatis tahu untuk melihat `monitoring.*` seperti tabel lain.

### 2. Kredensial baru `chatbot_audit_writer` — INSERT-only, tanpa SELECT sama sekali

Berbeda dari precedent (admin `SUPABASE_DB_URL` mentah) — karena penulisnya adalah API bertraffic langsung, bukan batch job internal, dibuat scoped sejak awal: `GRANT INSERT` (+ `GRANT USAGE` pada sequence backing `id bigserial` — lihat Temuan Implementasi) ke `monitoring.chatbot_query_log` saja. Dibuat di folder baru `scripts/chatbot_audit/`, bukan diselipkan ke `scripts/chatbot_credentials/` — target instance fisiknya beda (production Supabase vs serving Postgres), butuh koneksi admin berbeda (`SUPABASE_DB_URL`, bukan `SERVING_DB_URL`).

### 3. Penulisan log: `FastAPI BackgroundTasks`, best-effort

INSERT dijalankan lewat `background_tasks.add_task(...)` — request langsung dikembalikan ke caller, INSERT ke production Supabase terjadi setelahnya di proses yang sama. Dibungkus try/except: kalau tulis log gagal, dicetak ke stderr tapi **tidak pernah** menggagalkan response API. Konsekuensi diterima sebagai keterbatasan: proses mati tepat di antara response terkirim dan background task selesai berarti baris itu tidak tercatat — dapat diterima untuk skala project ini.

### 4. Titik pemasangan: bungkus handler di `main.py`, bukan hanya di dalam `authorize()`

Pembungkus log ditaruh di level `handler()` (`register_domain_routes`, `main.py`) — menangkap seluruh outcome (200/403/404/400) di satu tempat, memanggil `scripts/chatbot_api/audit.py::log_query(...)` (modul baru, paralel `authz.py`/`connections.py`, menjaga pemisahan "logic" vs "shape" M4.4).

### 5. Skema kolom `monitoring.chatbot_query_log`

```sql
CREATE TABLE IF NOT EXISTS monitoring.chatbot_query_log (
    id bigserial PRIMARY KEY,
    role_title text, domain text NOT NULL, view_name text, employee_id text,
    access_scope text, resolved_property_id text,
    status text NOT NULL CHECK (status IN ('success', 'denied')),
    denial_reason text, row_count integer,
    requested_at timestamptz NOT NULL DEFAULT now()
);
```

`role_title`/`view_name`/`employee_id` nullable (bisa kosong di request yang ditolak sedini mungkin). `row_count` NULL untuk `status='denied'`. `resolved_property_id` (bukan klaim caller) dicatat untuk `own_property` — jejak audit sesungguhnya, berguna sebagai input M4.6.

### 6. Verifikasi: HTTP nyata + query langsung ke `monitoring.chatbot_query_log`

`uvicorn` + `curl` untuk memicu 4 jenis outcome (200/403/404/400), lalu query tabel log via admin `SUPABASE_DB_URL` (karena `chatbot_audit_writer` sendiri tidak bisa `SELECT`).

### 7. Batas eksplisit terhadap Lapis 1 — log ini murni Lapis 2, klaim bukan identitas terverifikasi

Log `chatbot_query_log` **hanya mencatat request yang sudah lolos Lapis 1** (application layer sistem chatbot, di luar cakupan repo ini) — request yang ditolak Lapis 1 sebelum pernah sampai ke API ini secara struktural tidak pernah tercatat di sini (konsisten "Tidak termasuk" sumber). Kolom yang direkam murni hal yang dilihat/diputuskan API ini sendiri — tidak ada kolom prompt/intent.

`role_title`/`employee_id` yang tercatat adalah **klaim yang dikirim Lapis 1 ke Lapis 2** (konsisten prinsip M4.4, "tidak dipercaya buta"), bukan identitas pengguna chatbot asli yang sudah diverifikasi independen — kalau Lapis 1 salah kirim klaim, log ini merekam klaim yang salah itu **beserta keputusan Lapis 2 terhadapnya**. Inilah nilai defense-in-depth log ini. Didokumentasikan eksplisit di `docs/09-serving-ai-chatbot/audit-log-chatbot.md` supaya M4.6/M6.5 tidak salah membaca log sebagai ground truth identitas pengguna.

## Temuan Implementasi (Checkpoint 0)

- **`SUPABASE_DB_URL` ternyata Supavisor pooler URL**, bukan direct connection seperti komentar asli `.env.example` — ditemukan saat `build_role_connection_string` pertama kali gagal dengan asumsi direct-connection regex. Diperbaiki di kode (`_POOLER_URL_RE`, sama pola `chatbot_credentials/connections.py`) dan komentar `.env.example`. Konsekuensi: Supavisor pooler-cache-staleness (temuan M3.5) berlaku juga di sini, jadi `verify_role_isolation.py` tetap memakai warmup-retry (bukan dibuang seperti draft rencana awal yang keliru mengasumsikan "direct connection, no cache").
- **`GRANT INSERT` saja tidak cukup untuk kolom `bigserial`** — `nextval()` pada sequence backing (`chatbot_query_log_id_seq`) butuh `GRANT USAGE ON SEQUENCE` terpisah. Ditemukan lewat error `permission denied for sequence` (bukan error privilege biasa) saat verifikasi pertama. Ditambahkan ke `apply_grants()`.

## Task Breakdown

3 checkpoint.

### Checkpoint 0 — Fondasi: skema + kredensial
1. `scripts/chatbot_audit/{schema.sql,connections.py,apply_schema.py}`. — **Selesai**
2. `scripts/chatbot_audit/setup_audit_writer.py` + `verify_role_isolation.py` — create/rotate role, GRANT INSERT+USAGE sequence, verifikasi isolasi (7/7 check OK: INSERT sukses; SELECT ke tabel sendiri/`alerts`/`reverse_etl_sync_log`/`corporate_master.role_permissions` gagal; UPDATE/DELETE ke tabel sendiri gagal). — **Selesai**
3. `.env.example` tambah `CHATBOT_AUDIT_WRITER_DB_URL` (+ koreksi komentar `SUPABASE_DB_URL`). — **Selesai**

**✅ Checkpoint 0** — commit `71ed6fc`.

### Checkpoint 1 — Instrumentasi API
4. `scripts/chatbot_api/audit.py` — `log_query(...)`, koneksi `CHATBOT_AUDIT_WRITER_DB_URL` per panggilan, best-effort try/except.
5. `main.py`: `background_tasks: BackgroundTasks` di `handler()`, bungkus badan handler, panggil `log_query` di jalur sukses maupun tiap titik ditolak.
6. Tes HTTP nyata: 1 sukses + 3 ditolak (403/404/400) — verifikasi lewat query `monitoring.chatbot_query_log`.

### Checkpoint 2 (final) — Dokumentasi + Penutupan
7. `docs/09-serving-ai-chatbot/audit-log-chatbot.md` (termasuk bagian "Batas Lapis 1/Lapis 2").
8. Update `docs/06-akses-kredensial/kebijakan-akses-kredensial-scoped.md` (+1 baris `chatbot_audit_writer`).
9. Verifikasi ulang KK1-KK2, tulis `report.md`. Commit; tanya user sebelum push.
