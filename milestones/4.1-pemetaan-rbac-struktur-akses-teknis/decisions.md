# Milestone 4.1: Pemetaan RBAC ke Struktur Akses Teknis — Decisions

**Sumber:** `docs/03-implementation-plans/05-serving-ai-chatbot.md`, Milestone 4.1 (baris 49-65).
**Prasyarat:** `mart_aggregated` (M5.1-5.7, selesai), `mart_cleaned` (M2.1-2.4, selesai), RBAC final `corporate_master.role_permissions` di production (77 baris, 20 role, 10 domain — diverifikasi Task 0 di bawah).
**Status:** In Progress
**Date started:** 2026-08-10

## Lingkup Sumber / Contract

- **Lingkup:** Menerjemahkan 77 baris `corporate_master.role_permissions` dan detail kebutuhan 20 persona (`pemetaan-kebutuhan-chatbot-layer-staff/manager/korporat.md`) menjadi struktur akses teknis konkret: domain data mana perlu view/kelompok kolom apa, bagaimana `own_property` vs `all_properties` diterapkan sebagai filter, bagaimana pemecahan `guests_pii`/`guests_profile` diwujudkan sebagai dua view berbeda di atas tabel `guests` yang sama.
- **Output:**
  1. Tabel pemetaan: 10 `data_domain` → view/kelompok kolom teknis yang mewakilinya.
  2. Definisi eksplisit mekanisme `own_property` vs `all_properties`.
  3. Konfirmasi eksplisit bahwa `role_permissions` tidak termasuk struktur akses apa pun yang bisa dijangkau chatbot.
- **Kriteria Keberhasilan:**
  1. Setiap 10 `data_domain` punya pemetaan teknis yang jelas ke struktur `mart_aggregated`/`mart_cleaned`, termasuk kasus khusus `guests_pii`/`guests_profile`.
  2. Pemetaan ini bisa dipakai langsung sebagai acuan Milestone 4.2 tanpa perlu menerka ulang dari `role_permissions`.

## Temuan Eksplorasi (sebelum breakdown)

- **Sumber RBAC sudah sinkron ke production** — query langsung `corporate_master.role_permissions`: 77 baris, 20 `role_title`, 10 `data_domain` (`employees_directory` 13, `facility` 7, `financial` 6, `fnb` 5, `guests_pii` 8, `guests_profile` 4, `hr` 5, `properties_ref` 14, `reservation` 10, `spa_event` 5) — persis cocok Bagian 2 `rancangan-rbac-ai-chatbot.md`. Dipakai sebagai sumber kebenaran definitif, bukan menyalin ulang tabel markdown.
- **Gap #1 (awalnya ditemukan):** Audit PII M5.2 (`DataSchema-mart-aggregated.md` baris 456-468) mengonfirmasi eksplisit **0 kolom** `email`/`phone`/`guest_id` individual di seluruh 46 fact + 27 dimension table `mart_aggregated` — sementara 8 dari 20 persona butuh `guests_pii`/`guests_profile` row-level.
- **Gap #2 (ditemukan saat audit ulang seluruh 3 dokumen persona, lebih besar dari Gap #1):** Mayoritas kebutuhan layer Staff (7 dari 20 persona) adalah lookup row-level (mis. "detail satu booking spesifik", "status kamar tertentu saat ini", "detail satu tiket maintenance") — `mart_aggregated` dirancang sebagai star schema teragregasi by design (M5.1-5.2), tidak pernah memuat grain per-booking/per-tiket/per-transaksi. Data itu hanya ada di `mart_cleaned`, yang menurut `05-serving-ai-chatbot.md` (sebelum revisi) sepenuhnya di luar jangkauan Lapis 2.
- Gap #2 mencakup dan menyelesaikan Gap #1 sekaligus — begitu boundary Lapis 2 diperluas ke `mart_cleaned` row-level, `guests_pii`/`guests_profile` otomatis terpenuhi dari `mart_cleaned.guests` tanpa perlu skema baru di `mart_aggregated`.

## Keputusan (via AskUserQuestion, dikonfirmasi user)

### 1. Perluasan boundary Lapis 2 ke tabel `mart_cleaned` terpilih

**Keputusan:** Kredensial chatbot (Milestone 4.3) menjangkau `mart_aggregated` (agregat/tren) **dan** sejumlah tabel `mart_cleaned` yang dipetakan eksplisit di milestone ini (bukan seluruh `mart_cleaned`) — tetap read-only, tetap tidak pernah menyentuh `raw_production` atau production asli.

**Kenapa:** Mayoritas kebutuhan layer Staff (Gap #2) struktural tidak bisa dipenuhi `mart_aggregated` saja — bukan kekurangan implementasi, tapi ketidakcocokan grain data yang mendasar (agregat vs row-level).

**Ditolak:**
- *Descope kebutuhan row-level Staff, catat sebagai gap tertunda* — mengorbankan mayoritas kebutuhan 7 dari 20 persona, terlalu besar untuk dianggap "gap kecil".
- *Ajukan tabel "current-state snapshot" tambahan ke `mart_aggregated` lewat mekanisme M5.6* — bertentangan langsung dengan prinsip desain M5.1 ("row-level bukan tanggung jawab `mart_aggregated`") dan memaksa `mart_aggregated` memuat data operasional yang bukan karakternya.

**Dampak dokumentasi:** `docs/01-architecture/rancangan-arsitektur-data-platform-elt.md` §8.1-8.2 dan `docs/03-implementation-plans/05-serving-ai-chatbot.md` (Lapis 2, Milestone 4.3, Milestone 4.4) sudah diperbarui dengan catatan revisi eksplisit yang merujuk balik ke keputusan ini (bukan diam-diam diubah tanpa jejak) — lihat Task 1 di bawah.

### 2. `guests_pii`/`guests_profile` disupersede oleh Keputusan #1

**Keputusan:** Tidak perlu lagi pengajuan change request M5.6 terpisah untuk Gap #1 (sempat direkomendasikan di diskusi awal) — cukup 2 view row-level di atas `mart_cleaned.guests` (lihat Task 4), karena Keputusan #1 sudah membuka jalur ke `mart_cleaned`.

**Kenapa:** Premis awal rekomendasi M5.6 (guest data cuma bisa lewat `mart_aggregated`) sudah tidak berlaku setelah Keputusan #1. Dicatat eksplisit di sini sebagai keputusan yang di-supersede, bukan dihapus diam-diam dari riwayat diskusi.

## Keputusan Teknis (dikunci tanpa AskUserQuestion — mengikuti preseden project)

### 3. Sumber RBAC = `corporate_master.role_permissions` production langsung

Tidak menyalin ulang tabel markdown `rancangan-rbac-ai-chatbot.md` Bagian 2 — production sudah diverifikasi sinkron (lihat Temuan Eksplorasi). Query production dipakai sebagai input Task 2.

### 4. Reuse mapping domain operasional dari M3.1

6 domain operasional (`reservation`, `fnb`, `facility`, `spa_event`, `hr`, `financial`) sisi agregat memakai ulang tabel referensi domain→fact/dim dari `docs/08-serving-data-analyst/pemetaan-pola-akses-analyst.md` (M3.1) — sudah diverifikasi terhadap skema aktual, tidak perlu didesain ulang dari nol. Ditambah pemetaan row-level `mart_cleaned` per domain khusus untuk lookup Staff (baru, hasil Task 2 milestone ini).

### 5. Mekanisme filter `own_property`/`all_properties`: enforced di layer API (M4.4), bukan di Postgres role

**Keputusan:** Filter `property_id` diterapkan sebagai parameter runtime yang divalidasi API (Milestone 4.4) terhadap identitas/properti user yang dikirim Lapis 1 — bukan lewat kredensial Postgres terpisah per properti.

**Kenapa:** Beda karakter dari pola M3.5 (Data Analyst): di M3.5, 1 kredensial statis dipakai 1 orang tetap (mis. `property_gm_analyst_reader` untuk 1 GM tertentu) sehingga scoping properti bisa dibakar ke role Postgres. Chatbot melayani banyak individu berbeda secara dinamis lewat kredensial yang sama per kelompok akses — scoping properti tidak bisa statis di level Postgres tanpa membuat 1 role per staff (tidak skalabel untuk ratusan karyawan).

### 6. Kelompok kredensial M4.3: 1 kelompok akses per `data_domain` (10 kelompok)

Mengikuti preseden M3.5 (Data Analyst: 1 role per domain, defense-in-depth). Detail per domain jadi bagian Task 2. Implementasi kredensial (M4.3) murni pekerjaan AI Chatbot Serving sendiri, pola sama seperti `data-scientist-reader` (M2.5) dan 7 role Data Analyst (M3.5) — tidak melibatkan pemilik `mart_cleaned`/`mart_aggregated`, karena struktur/isi kedua mart tidak berubah sama sekali, hanya bertambah pemegang akses baca baru.

### 7. Konfirmasi: `role_permissions` tidak pernah jadi target akses

Ditegaskan eksplisit di setiap tabel pemetaan Task 2: tidak ada baris yang mengarah ke `corporate_master.role_permissions` sebagai tabel yang bisa di-`SELECT` chatbot dalam skenario apa pun — konsisten `rancangan-rbac-ai-chatbot.md` Bagian 1 ("kunci keamanan sistem itu sendiri").

## Task Breakdown

**Kenapa 3 fase:** Fase 0 menyentuh dokumen arsitektur platform-wide (butuh checkpoint terpisah, di-review sebelum lanjut). Fase 1 adalah inti pemetaan teknis (3 task, saling terkait, satu unit kerja). Fase 2 murni verifikasi & penutupan.

### Fase 0 — Update dokumen arsitektur terdampak
1. Update `docs/03-implementation-plans/05-serving-ai-chatbot.md` (Lapis 2, Milestone 4.3, Milestone 4.4) dan `docs/01-architecture/rancangan-arsitektur-data-platform-elt.md` §8.1-8.2 — catatan inline "Revisi Milestone 4.1" yang merujuk balik ke `decisions.md` ini, pola sama seperti catatan "Koreksi M5.7" di `DataSchema-mart-aggregated.md`. — S — **Selesai**

**✅ Checkpoint 0** — commit + log.

### Fase 1 — Pemetaan struktur teknis
2. Tulis tabel "10 data_domain → struktur teknis" (kolom: domain, sensitivitas, tabel `mart_aggregated`, tabel `mart_cleaned` row-level, catatan filter properti) di `docs/08-serving-ai-chatbot/pemetaan-akses-teknis-chatbot.md`. — M
3. Definisikan mekanisme `own_property`/`all_properties` sebagai kontrak eksplisit untuk M4.2-4.4 (Keputusan #5, didokumentasikan lengkap dengan contoh). — S
4. Definisikan 2 view `guests_pii`/`guests_profile` (kolom eksak) di atas `mart_cleaned.guests` sebagai kontrak M4.2. — S

**✅ Checkpoint 1** — commit + log.

### Fase 2 — Verifikasi & tutup
5. Verifikasi akhir: tiap 10 domain di `role_permissions` production ditelusuri ke baris tabel Task 2 tanpa menerka ulang (Kriteria Keberhasilan sumber). Tulis `report.md`. — S

**✅ Checkpoint 2 (final)** — commit; tanya user sebelum push.
