# Rancangan Pengujian — Ketahanan RBAC Lintas Persona AI Chatbot

**Nirwana Hospitality Group — Data Platform ELT**

| | |
|---|---|
| **Dihasilkan oleh** | Milestone 4.6 (`milestones/4.6-uji-ketahanan-rbac-lintas-persona/`) |
| **Ditulis** | SEBELUM eksekusi (dokumen rancangan, bukan hasil) — hasil aktual ada di `milestones/4.6-.../{logs.md,report.md}` |
| **Kode terkait** | `scripts/chatbot_rbac_test/` |
| **Ground truth** | `mart_cleaned.role_permissions` (77 baris, ditarik langsung via query, bukan disalin dari dokumen RBAC) |

---

## Kenapa Dokumen Ini Ada

Milestone 4.1-4.5 memverifikasi RBAC Lapis 2 chatbot dengan **sampel** beberapa persona per tingkat (Staff/Manager/Korporat) di setiap milestone-nya. Dokumen sumber (`docs/03-implementation-plans/05-serving-ai-chatbot.md`, Milestone 4.6) secara eksplisit menyebut sampel itu belum cukup untuk skala RBAC ini (20 persona × 10 domain): *"verifikasi ini tidak bisa dianggap 'otomatis benar' hanya karena Milestone 4.1–4.5 sudah selesai dikerjakan dengan hati-hati — butuh siklus pengujian eksplisit tersendiri"*.

Dokumen ini adalah rancangan siklus itu — ditulis dan disetujui **sebelum** satu pun kode pengujian dijalankan, supaya cakupannya bisa ditinjau utuh dulu (bukan baru terlihat sepotong-sepotong lewat commit log).

## Dua Kriteria Keberhasilan Sumber

1. Seluruh 20 persona, saat diuji lewat API, menghasilkan cakupan akses yang **persis cocok** dengan `role_permissions` — tidak lebih (kebocoran), tidak kurang (akses yang seharusnya ada tapi hilang).
2. Prinsip *superset* (Director superset Manager, Manager superset Staff, CEO superset semua) terverifikasi ulang di level implementasi, bukan hanya dipercaya dari hasil audit dokumen.

## Struktur Pengujian: 3 Layer

| Layer | Menjawab | Cakupan | KK Terkait |
|---|---|---|---|
| **A — Matriks Akses** | Untuk role X, domain Y: diizinkan atau ditolak? | **Exhaustive** — seluruh 200 sel (20×10) | KK1 |
| **B — Mekanisme `own_property`** | Apakah pembatasan properti benar-benar ditegakkan (bukan cuma keputusan ya/tidak)? | Sampel representatif (~15) | KK1 (kedalaman) |
| **C — Superset** | Apakah role yang lebih tinggi benar-benar mencakup seluruh akses role di bawahnya? | Analisis atas hasil Layer A, tanpa panggilan HTTP baru | KK2 |

Layer A wajib *exhaustive* karena KK1 secara harfiah minta "tidak lebih, tidak kurang" — pernyataan itu cuma bisa dibuktikan salah/benar kalau seluruh 200 kombinasi diperiksa, bukan cuma 77 yang granted (kalau cuma menguji yang granted, kebocoran di 123 sel yang seharusnya DENY tidak akan pernah ketahuan). Layer B dan C sengaja **tidak** exhaustive lagi — keduanya menguji *mekanisme* yang sudah domain-agnostic dan terbukti berulang di M4.4/M4.5, bukan *keputusan* yang berbeda-beda per role×domain seperti Layer A.

---

## Layer A: Matriks Ekspektasi Akses — 20 Role × 10 Domain

Ground truth ditarik langsung dari `mart_cleaned.role_permissions` (77 baris) lewat query nyata saat rancangan ini disusun — bukan disalin dari `role_permissions_chatbot_v2.csv` atau dokumen RBAC manapun, supaya kalau ada drift antara dokumen dan database sungguhan, itu sendiri sudah otomatis ketahuan di titik ini.

**Legenda:** `AP` = ALLOW dengan `access_scope=all_properties`. `OP` = ALLOW dengan `access_scope=own_property`. `—` = DENY (403 diharapkan).

**Urutan kolom domain** (dipakai konsisten di seluruh dokumen ini dan tooling): `reservation`, `fnb`, `facility`, `spa_event`, `hr`, `financial`, `properties_ref`, `employees_directory`, `guests_pii`, `guests_profile`.

| Role (tingkat) | reservation | fnb | facility | spa_event | hr | financial | properties_ref | employees_directory | guests_pii | guests_profile |
|---|---|---|---|---|---|---|---|---|---|---|
| CEO (Korporat) | AP | AP | AP | AP | AP | AP | AP | AP | AP | AP |
| Corporate Finance Director (Korporat) | AP | — | — | — | — | AP | AP | AP | — | — |
| Corporate HR Director (Korporat) | — | — | — | — | AP | — | AP | AP | — | — |
| Corporate Operations Director (Korporat) | AP | AP | AP | AP | — | — | AP | AP | AP | — |
| Corporate Revenue Director (Korporat) | AP | — | — | — | — | AP | AP | — | AP | AP |
| General Manager (Manager) | OP | OP | OP | OP | OP | OP | OP | OP | OP | OP |
| Revenue Manager (Manager) | OP | — | — | — | — | — | OP | — | OP | OP |
| F&B Manager (Manager) | OP | OP | — | — | — | — | OP | OP | — | — |
| Finance Manager (Manager) | OP | — | — | — | — | OP | OP | OP | — | — |
| Housekeeping Manager (Manager) | OP | — | OP | — | — | — | OP | OP | — | — |
| HR Manager (Manager) | — | — | — | — | OP | — | OP | OP | — | — |
| Maintenance Manager (Manager) | — | — | OP | — | — | — | OP | OP | — | — |
| Spa & Event Manager (Manager) | — | — | — | OP | — | — | OP | OP | OP | — |
| Front Office Staff (Staff) | OP | — | — | — | — | — | OP | — | OP | — |
| F&B Staff (Staff) | — | OP | — | — | — | — | — | — | — | — |
| Finance Staff (Staff) | — | — | — | — | — | OP | — | OP | — | — |
| Housekeeping Staff (Staff) | — | — | OP | — | — | — | — | — | — | — |
| HR Staff (Staff) | — | — | — | — | OP | — | — | OP | — | — |
| Maintenance Staff (Staff) | — | — | OP | — | — | — | — | — | — | — |
| Spa & Event Staff (Staff) | — | — | — | OP | — | — | — | — | OP | — |

**Sel ALLOW (AP+OP) = 77, sel DENY = 123, total = 200** — cocok persis dengan jumlah baris `role_permissions` (77) dan `20 role × 10 domain - 77 = 123` kombinasi yang harus ditolak.

### Pemetaan 1 View Representatif per Domain

`authorize(role_title, domain)` (`scripts/chatbot_api/authz.py`) adalah keputusan di level **domain**, bukan level **view** — `view_name` cuma dicek lewat whitelist SETELAH `authorize()` lolos. Jadi 1 view representatif per domain sudah cukup untuk membuktikan keputusan akses; menguji ulang seluruh 67 view M4.2 tidak menambah bukti apa pun untuk KK M4.6 (kolom/isi tiap view sendiri sudah dibuktikan M4.2, filter own_property per view sudah dibuktikan M4.4).

| Domain | `view_name` dipakai | Alasan pemilihan |
|---|---|---|
| `reservation` | `room-type-daily` | View pertama yang sudah teruji sejak M4.4 |
| `fnb` | `outlet-daily` | idem |
| `facility` | `room-status-daily` | Aggregate biasa, bukan salah satu dari 2 view yang butuh koreksi property_id M4.4 |
| `spa_event` | `spa-daily` | Aggregate biasa |
| `hr` | `attendance-daily` | Aggregate biasa, bukan `payroll` (sengaja hindari kolom paling sensitif untuk uji rutin) |
| `financial` | `departmental-margin` | Sudah punya business rule exclusion (`Overall`/`Corporate Overhead`) teruji M3.1/M4.4 — representatif |
| `properties_ref` | `properties` | Satu-satunya view domain ini |
| `employees_directory` | `employees` | Satu-satunya view domain ini |
| `guests_pii` | `guests-contact` | Satu-satunya view domain ini, `own_property_column=last_active_property_id` |
| `guests_profile` | `guests-profile` | Satu-satunya view domain ini, `own_property_column=last_active_property_id` |

### Data Uji `own_property`

**Temuan desain penting** (ditemukan saat menyusun rancangan ini, lihat juga `decisions.md`): `role_title` (dipakai `authorize()`) dan `employee_id` (dipakai `resolve_property_id()`) adalah **dua klaim yang sepenuhnya independen** di dalam API — `authorize()` tidak pernah membaca `employee_id`, dan `resolve_property_id()` tidak pernah membaca/memvalidasi `role_title`. Ini konsisten dengan pemisahan Lapis 1/Lapis 2 (`docs/09-serving-ai-chatbot/audit-log-chatbot.md`, M4.5 Keputusan #7) — pengikatan "pegawai X sungguhan menjabat role_title Y" adalah tanggung jawab Lapis 1 (sistem chatbot/session), bukan Lapis 2.

Konsekuensinya untuk rancangan ini: **satu `employee_id` tetap bisa dipakai untuk seluruh 48 sel `OP` di Layer A**, apa pun `role_title` yang diklaim bersamaan dengannya — bukan penyederhanaan yang mengorbankan validitas uji, karena `authorize()` memang tidak pernah melihatnya sama sekali.

- `employee_id` **A** → resolve ke property **P01** — dipakai default di seluruh sel `OP` Layer A.
- `employee_id` **B** → resolve ke property **P02** — dipakai di Layer B untuk membuktikan override benar-benar mengikuti `employee_id` yang berbeda (bukan konstanta P01 yang kebetulan selalu cocok).

ID pegawai konkret diambil dari `mart_cleaned.employees WHERE status='active'` saat eksekusi Checkpoint 1 (dicatat di `logs.md`, bukan di-hardcode di dokumen rancangan ini karena status aktif seorang pegawai bisa berubah antar-run).

---

## Layer B: Spot-Check Mekanisme `own_property`

Untuk tiap 15 role bertingkat Manager/Staff (General Manager + 7 Manager + 7 Staff, sesuai daftar KK sumber Milestone 4.1), pilih **1 domain `OP` miliknya** dari matriks Layer A, panggil API 2×:

1. `employee_id` **A** (resolve P01) + klaim `property_id=P02` di query string → harus tetap kembali **100% P01** (klaim caller diabaikan).
2. `employee_id` **B** (resolve P02), tanpa klaim apa pun → harus kembali **100% P02** (bukan konstanta hardcode P01 dari test #1).

Kedua hasil bersama membuktikan override benar-benar melakukan *resolve per-employee_id*, bukan kebetulan selalu menampilkan properti yang sama.

---

## Layer C: Definisi 4 Rantai Superset (KK2)

Dihitung sebagai **set-containment** murni atas domain yang benar-benar ALLOW per role dari hasil Layer A **nyata** (HTTP call sungguhan) — bukan dari tabel ekspektasi di atas, karena tabel ekspektasi itu justru premis yang mau dibuktikan konsisten dengan implementasi.

1. **Staff → Manager** (7 pasang per fungsi): F&B Staff⊆F&B Manager, Finance Staff⊆Finance Manager, Housekeeping Staff⊆Housekeeping Manager, HR Staff⊆HR Manager, Maintenance Staff⊆Maintenance Manager, Spa & Event Staff⊆Spa & Event Manager, **Front Office Staff⊆Revenue Manager** (satu-satunya pasangan lintas-nama — front office secara fungsi RBAC ada di bawah revenue management, bukan salah ketik: `{guests_pii,properties_ref,reservation} ⊆ {guests_pii,guests_profile,properties_ref,reservation}`).
2. **Manager → Corporate Director** (7 pasang): F&B/Housekeeping/Maintenance/Spa & Event Manager ⊆ Corporate Operations Director; Finance Manager ⊆ Corporate Finance Director; HR Manager ⊆ Corporate HR Director; Revenue Manager ⊆ Corporate Revenue Director.
3. **Manager → General Manager** (7 pasang, GM dikecualikan dari dirinya sendiri): setiap Manager fungsional ⊆ General Manager.
4. **Seluruh peran → CEO** (19 pasang, CEO dikecualikan dari dirinya sendiri): setiap role lain ⊆ CEO di level breadth-domain (CEO ALLOW di seluruh 10 domain — rantai ini murni soal cakupan domain, bukan perbandingan `access_scope` AP vs OP).

---

## Prosedur Eksekusi

1. `uvicorn main:app` (`scripts/chatbot_api/`) berjalan lokal.
2. `scripts/chatbot_rbac_test/run_access_matrix.py` — loop 200 kombinasi (Layer A), request via view representatif per domain (tabel di atas), `employee_id` A dipakai otomatis untuk setiap sel `OP` yang diharapkan. Bandingkan HTTP status aktual (200/403) terhadap tabel ekspektasi. Cetak + simpan hasil lengkap.
3. Kalau ada mismatch: investigasi akar penyebab (bug RBAC nyata vs kesalahan skrip uji itu sendiri), perbaiki, jalankan ulang sampai 200/200 cocok.
4. `scripts/chatbot_rbac_test/run_property_override_sample.py` — Layer B, 15×2 = 30 panggilan.
5. Analisis Layer C dari hasil Layer A tersimpan (tanpa panggilan baru) — assert 7+7+7+19 = 40 pasang set-containment.
6. Seluruh hasil dicatat di `milestones/4.6-uji-ketahanan-rbac-lintas-persona/logs.md`, diringkas di `report.md`.

## Kriteria Lulus

- Layer A: 200/200 sel cocok ekspektasi (0 kebocoran, 0 akses hilang) — atau seluruh mismatch yang ditemukan sudah diperbaiki dan diverifikasi ulang sebelum milestone ditutup.
- Layer B: 15/15 kombinasi menunjukkan override konsisten (P02 diabaikan saat `employee_id` A, P02 muncul benar saat `employee_id` B).
- Layer C: 40/40 pasang set-containment valid.
