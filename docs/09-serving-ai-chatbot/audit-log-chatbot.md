# Audit Log Query — AI Chatbot

**Nirwana Hospitality Group — Data Platform ELT**

| | |
|---|---|
| **Dihasilkan oleh** | Milestone 4.5 (`milestones/4.5-audit-log-query-chatbot/`) |
| **Kode** | `scripts/chatbot_audit/` (kredensial + skema), `scripts/chatbot_api/audit.py` (penulisan) |
| **Input utama** | `docs/09-serving-ai-chatbot/api-chatbot.md` (M4.4) |
| **Status** | Selesai |

---

## Batas Lapis 1/Lapis 2

Log ini **hanya mencatat request yang sudah lolos Lapis 1** (application layer sistem AI Chatbot — validasi intent/prompt sebelum query dieksekusi, sepenuhnya di luar cakupan repo ini). Request yang ditolak Lapis 1 sebelum pernah sampai ke API M4.4 secara struktural tidak pernah tercatat di `monitoring.chatbot_query_log` — dan memang bukan tanggung jawab M4.5 untuk mencatatnya (konsisten "Tidak termasuk" di `05-serving-ai-chatbot.md`).

Kolom `role_title` dan `employee_id` di tabel ini adalah **klaim yang dikirim Lapis 1 ke Lapis 2** (API M4.4 memvalidasinya terhadap `role_permissions`, "tidak dipercaya buta" — lihat `api-chatbot.md`), **bukan identitas pengguna chatbot asli yang sudah diverifikasi independen**. Kalau Lapis 1 pernah salah kirim klaim (bug, upaya prompt injection, dsb), log ini akan merekam klaim yang salah itu **beserta keputusan Lapis 2 terhadapnya** (403/404/400) — inilah nilai *defense in depth* log ini: bukti bahwa Lapis 2 tetap menahan meskipun Lapis 1 gagal, bukan catatan "siapa sebenarnya yang memakai chatbot". Pembaca log ini (Milestone 4.6, Milestone 6.5) perlu memperlakukan `role_title`/`employee_id` sebagai jejak keputusan Lapis 2, bukan ground truth identitas.

## Lokasi dan Alasan

`monitoring.chatbot_query_log` di **production Supabase** — bukan di serving project tempat API M4.4 dan seluruh 11 kredensial chatbot lain (M4.3/M4.4) berada. Ini mengikuti konvensi project yang sudah dikunci sejak M2.4 (`monitoring.reverse_etl_sync_log`): monitoring tetap terpusat di satu tempat, terlepas dari di mana sistem yang diamati secara fisik berada — sehingga Milestone 6.5 (`06-monitoring-warehouse-serving-fase2.md`, konsumen log ini berikutnya) otomatis tahu untuk melihat `monitoring.*` seperti tabel monitoring lain, tanpa integrasi tambahan.

Konsekuensinya: API chatbot (yang sebelum M4.5 tidak pernah terhubung ke production Supabase sama sekali) sekarang punya satu kredensial baru ke instance itu. Untuk menjaga prinsip isolasi yang sudah dibangun M4.1-4.4, kredensial ini (`chatbot_audit_writer`) dibuat **lebih ketat dari precedent monitoring manapun di project ini** — lihat bagian Kredensial di bawah.

## Skema Tabel

```sql
CREATE TABLE monitoring.chatbot_query_log (
    id                    bigserial PRIMARY KEY,
    role_title            text,             -- klaim Lapis 1, lihat "Batas Lapis 1/Lapis 2"
    domain                text NOT NULL,
    view_name             text,
    employee_id           text,             -- klaim Lapis 1, hanya diisi utk request own_property
    access_scope          text,             -- 'own_property' / 'all_properties', NULL kalau ditolak sebelum authorize() lolos
    resolved_property_id  text,             -- property_id yang BENAR-BENAR ditegakkan (bukan klaim caller), NULL utk all_properties
    status                text NOT NULL CHECK (status IN ('success', 'denied')),
    denial_reason         text,             -- detail HTTPException, NULL kalau status='success'
    row_count             integer,          -- NULL kalau status='denied' (query data tidak pernah jalan)
    requested_at          timestamptz NOT NULL DEFAULT now()
);
```

## Kredensial: `chatbot_audit_writer`

- **INSERT-only** ke `monitoring.chatbot_query_log` **saja** — tidak ada `SELECT` (bahkan ke tabelnya sendiri), tidak ada `UPDATE`/`DELETE`, tidak ada tabel `monitoring.*` lain, tidak ada tabel production lain.
- Di production Supabase, dibuat/dirotasi via `scripts/chatbot_audit/setup_audit_writer.py`. Isolasi diverifikasi lewat 7 uji coba nyata (`scripts/chatbot_audit/verify_role_isolation.py`): INSERT sukses; SELECT ke tabel sendiri, `monitoring.alerts`, `monitoring.reverse_etl_sync_log`, `corporate_master.role_permissions` semua ditolak; UPDATE/DELETE ke tabel sendiri ditolak.
- Env var: `CHATBOT_AUDIT_WRITER_DB_URL` (ditulis otomatis, jangan diisi manual).

## Cara Kerja

```
1. Handler request (main.py, per domain) membungkus SELURUH badan pemrosesan
   dalam try/except HTTPException.
2. Sukses -> background_tasks.add_task(log_query, ..., status="success",
   row_count=len(rows)) -- dijadwalkan SETELAH hasil query siap dikembalikan,
   tidak pernah menambah latency response.
3. Ditolak (403 authorize / 404 whitelist / 400 own_property) -> exception
   ditangkap, background_tasks.add_task(log_query, ..., status="denied",
   denial_reason=str(exc.detail)) dijadwalkan, lalu response error yang SAMA
   PERSIS (status code + body) dikembalikan lewat JSONResponse(background=...)
   -- BUKAN `raise` (lihat catatan implementasi di bawah).
4. log_query() (scripts/chatbot_api/audit.py) membuka koneksi
   CHATBOT_AUDIT_WRITER_DB_URL, INSERT satu baris, tutup koneksi. Best-effort:
   kegagalan tulis log dicetak ke stderr, TIDAK PERNAH melempar exception ke
   pemanggil -- audit logging adalah pengamat, bukan bagian jalur kritis.
```

**Catatan implementasi penting**: FastAPI diam-diam **membuang** task yang ditambahkan ke `BackgroundTasks` kalau handler `raise` exception alih-alih `return` response secara normal — exception handler bawaan FastAPI untuk `HTTPException` membangun response error dari awal, tidak pernah membawa serta task yang sudah dijadwalkan di handler yang gagal. Ditemukan lewat tes HTTP nyata (3 dari 4 skenario awalnya tidak tercatat). Solusinya: jalur ditolak me-`return JSONResponse(status_code=..., content=..., background=background_tasks)`, bukan `raise` — status code/body ke caller tidak berubah sama sekali, cuma mekanisme pengiriman internalnya.

## Keterbatasan yang Diterima Sadar

- **Best-effort, bukan guaranteed delivery**: kalau proses API mati tepat di antara response terkirim dan background task selesai, baris log itu tidak tercatat. Diterima untuk skala project ini (internal tool, bukan sistem produksi nyata yang butuh audit trail tanpa celah).
- **Tidak melihat apa pun dari Lapis 1** — lihat bagian "Batas Lapis 1/Lapis 2" di atas.

## Bukti Verifikasi (KK1-KK2)

Seluruh bukti dari HTTP call nyata (`uvicorn` + `curl`) diikuti query langsung ke `monitoring.chatbot_query_log` via admin `SUPABASE_DB_URL` (karena `chatbot_audit_writer` sendiri tidak bisa `SELECT`):

- **KK1** (setiap panggilan tercatat dengan detail cukup): 4 skenario diuji — sukses (Front Office Staff, `reservation/room-type-daily`, `employee_id=E0071` → `access_scope=own_property`, `resolved_property_id=P01`, `row_count=3`), 403 (Front Office Staff → domain `fnb`, `denial_reason="role 'Front Office Staff' is not permitted for domain 'fnb'"`), 404 (`view_name` tidak ada di whitelist `reservation`), 400 (`own_property` tanpa `employee_id`, `denial_reason="employee_id is required for own_property access"`) — keempatnya tercatat lengkap. Uji tambahan: Corporate Revenue Director (`all_properties`) → `resolved_property_id=NULL` (benar, tidak pernah di-resolve untuk `all_properties`), `row_count=2`.
- **KK2** (log bisa diakses terpisah dari sistem chatbot): `monitoring.chatbot_query_log` adalah tabel PostgreSQL biasa di schema `monitoring` — dapat diquery langsung oleh siapa pun yang punya akses `monitoring.*` (pemilik infrastruktur data), tanpa perlu masuk ke proses API chatbot atau sistem chatbot itu sendiri sama sekali. Sudah menjadi bagian backbone monitoring bersama sejak M1.2 (lihat CLAUDE.md).

## Cara Query untuk M6.5

```sql
-- Volume + tren gagal/ditolak per domain per hari (dasar dashboard M6.5)
SELECT domain, status, date_trunc('day', requested_at) AS day, count(*)
FROM monitoring.chatbot_query_log
GROUP BY domain, status, day
ORDER BY day DESC;

-- Query paling lambat/paling sering per view_name (butuh join pg_stat_statements terpisah, M6.5)
SELECT domain, view_name, count(*) AS request_count
FROM monitoring.chatbot_query_log
WHERE status = 'success'
GROUP BY domain, view_name
ORDER BY request_count DESC;
```
