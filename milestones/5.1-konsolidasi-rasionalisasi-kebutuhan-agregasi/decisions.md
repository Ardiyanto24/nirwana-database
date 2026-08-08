# Milestone 5.1: Konsolidasi dan Rasionalisasi Kebutuhan Agregasi — Decisions

**Source:** `docs/03-implementation-plans/03-mart-aggregated-owner.md`, baris 44-60.
**Status:** Planned
**Date started:** 2026-08-08

## Contract (from source doc)

- **Lingkup:** Menggabungkan seluruh kebutuhan metrik dari 6 pola domain Data Analyst (`docs/02-requirements/pemetaan-kebutuhan-data-analyst.md`) dan 20 persona AI Chatbot (`pemetaan-kebutuhan-chatbot-layer-staff.md`, `-manager.md`, `-korporat.md`) menjadi satu daftar agregasi konsolidasi — mengidentifikasi tumpang tindih, mana yang spesifik satu jenis konsumen, dan prioritas lintas peran.
- **Output:**
  1. Daftar konsolidasi metrik/agregasi, dikelompokkan per domain, dengan penanda konsumen mana saja yang butuh tiap metrik.
  2. Daftar terpisah untuk kebutuhan yang butuh perlakuan khusus (mis. snapshot harian pace booking).
  3. Daftar eksplisit kebutuhan yang **tidak** akan dibangun karena keterbatasan data sumber.
- **Kriteria Keberhasilan:**
  1. Setiap metrik siap pakai di dokumen kebutuhan Data Analyst dan ketiga dokumen layer chatbot sudah dipetakan statusnya: masuk cakupan awal / masuk cakupan dengan perlakuan khusus / ditandai di luar cakupan dengan alasan.
  2. Dokumen konsolidasi ini bisa dipakai langsung sebagai acuan Milestone 5.2 tanpa perlu menerka ulang kebutuhan dari dokumen sumber.

## Temuan Eksplorasi (sebelum breakdown)

- `pemetaan-kebutuhan-data-analyst.md` (576 baris): 6 domain, tiap domain punya section "Kebutuhan Final" (§1.3 Revenue, §2.3 F&B, §3.3 Facility/Ops, §4.3 Spa & Event, §5.3 HR, §6.3 Corporate/Financial) — ini sumber metrik-level per domain. Section "Ringkasan Lintas Domain" di akhir dokumen (baris 561-572) sifatnya kualitatif, bukan tabel metrik individual, jadi tidak bisa langsung dipakai sebagai output M5.1.
- 3 dokumen chatbot (staff 322 baris/7 persona, manager 323 baris/8 persona, korporat 230 baris/5 persona = total 20 persona) berlabel per **domain data** eksplisit di tiap persona (mis. "Kebutuhan Data (domain `reservation`+`properties_ref`+`guests_pii`, own_property)") — bisa dipetakan langsung ke 6 domain `mart_aggregated`.
- Manager & Korporat memakai **prinsip superset**: section "Kebutuhan Data Tambahan" saja (bukan re-derive penuh dari staff/manager di bawahnya) — mengurangi kerja pembacaan ulang.
- Total volume sumber ~1583 baris — cukup ditangani pembacaan langsung tanpa delegasi sub-agent per domain.

## Keputusan (via AskUserQuestion, dikonfirmasi user)

### 1. Lokasi dokumen output: `docs/07-mart-aggregated/konsolidasi-agregasi-mart-aggregated.md`

**Keputusan:** Folder baru bernomor urut `docs/07-mart-aggregated/`, isinya file konsolidasi metrik ini (dan berpotensi dokumen desain skema M5.2 nanti).

**Kenapa:** Deliverable inti M5.1 adalah dokumen substantif (bukan sekadar catatan planning) — menurut konvensi project, folder `milestones/<id>-*/` hanya boleh berisi `decisions.md`/`logs.md`/`report.md`. Preseden persis: M2.6 menaruh `kebijakan-akses-kredensial-scoped.md` di `docs/06-akses-kredensial/`, bukan di folder milestone-nya. User secara eksplisit minta folder bernomor baru (bukan menumpuk ke `docs/02-requirements/`) untuk konsistensi dengan pola `01-architecture`...`06-akses-kredensial`.

**Ditolak:** Taruh sebagai section baru di `docs/03-implementation-plans/03-mart-aggregated-owner.md` (dokumen itu berstatus "rancangan implementasi kerja" coarse-grained, bukan tempat data konsolidasi detail); taruh sebagai file ke-4 di folder milestone (menyimpang dari konvensi "exactly 3 files").

## Keputusan Teknis Lain (dikunci tanpa AskUserQuestion — mengikuti presenden project)

### 2. Skema kolom tabel konsolidasi

`Domain | Metrik/Agregasi | Grain | Konsumen Analyst (pola mana) | Konsumen Chatbot (persona mana) | Status | Catatan`

Status berisi salah satu dari: `Cakupan Awal` / `Cakupan Khusus` (butuh perlakuan desain khusus, mis. snapshot) / `Luar Cakupan` (dengan alasan di kolom Catatan). Skema ini dipilih langsung (bukan ditanyakan) karena secara literal mengikuti 3 poin Output di dokumen sumber (baris 52-55) — tidak ada alternatif desain yang bersaing di titik ini.

### 3. Metode pengerjaan: pembacaan langsung per domain, tanpa delegasi ke Explore/sub-agent

Volume sumber (~1583 baris, 6 domain analyst + 20 persona chatbot) masih dalam jangkauan pembacaan langsung dalam sesi ini, dipecah per domain sesuai task breakdown di bawah — delegasi sub-agent tidak memberi manfaat berarti untuk pekerjaan yang butuh judgment konsolidasi lintas dokumen (bukan pencarian pola sederhana), dan berisiko kehilangan konteks silang antar-domain jika dipecah ke sesi terpisah.

### 4. Task fondasi lintas-domain (pemetaan persona → domain) dikerjakan lebih dulu sebagai task tersendiri

Sebelum masuk konsolidasi per domain, dibangun dulu 1 tabel rujukan cepat: 20 persona chatbot → domain data yang disentuh (dari label eksplisit "Kebutuhan Data (domain ...)" tiap persona). Ini dipakai berulang di tiap task domain berikutnya, mencegah re-derivasi manual 6x untuk pertanyaan yang sama ("persona mana saja yang menyentuh domain X").

## Task Breakdown

9 task, 5 fase, 5 checkpoint (commit + log tiap checkpoint — semua task murni analitis/dokumentasi, tidak ada kode, tapi pola commit-per-checkpoint tetap dipakai konsisten dengan milestone kode sebelumnya, terutama karena volume kerja besar dan butuh titik rollback yang aman).

### Fase 0 — Fondasi Lintas-Domain
1. Ekstrak tabel pemetaan 20 persona chatbot (7 Staff + 8 Manager + 5 Korporat) → domain data yang disentuh + jenis konsumsi (agregat/row-level/keduanya) — Acceptance: 20/20 persona terpetakan ke minimal 1 domain — Verify: hitung ulang total persona per domain cocok dengan jumlah section di 3 dokumen sumber — S

**✅ Checkpoint 1** — commit + log, buat draft `docs/07-mart-aggregated/konsolidasi-agregasi-mart-aggregated.md` berisi tabel pemetaan persona.

### Fase 1 — Domain Revenue + F&B
2. Konsolidasi metrik Revenue (silang §1.3 + persona chatbot terkait dari Task 1) — Acceptance: setiap metrik di §1.3 + kebutuhan chatbot terkait domain Revenue punya 1 baris dengan status — Verify: cross-check jumlah metrik vs §1.3 — S
3. Konsolidasi metrik F&B (§2.3 + persona terkait) — Acceptance/Verify sama pola Task 2 — S

**✅ Checkpoint 2** — commit + log.

### Fase 2 — Domain Facility/Ops + Spa & Event
4. Konsolidasi Facility/Ops (§3.3 + persona terkait) — S
5. Konsolidasi Spa & Event (§4.3 + persona terkait) — S

**✅ Checkpoint 3** — commit + log.

### Fase 3 — Domain HR + Corporate/Financial
6. Konsolidasi HR (§5.3 + persona terkait) — S
7. Konsolidasi Corporate/Financial (§6.3 + persona terkait) — S

**✅ Checkpoint 4** — commit + log.

### Fase 4 — Finalisasi
8. Daftar kebutuhan khusus (pace booking, dll yang sudah ditandai butuh perlakuan khusus di seluruh domain) + daftar eksplisit luar cakupan (net revenue setelah komisi OTA, target/budget vs actual, exit interview, dll) — Acceptance: kedua daftar terpisah dan lengkap, dirujuk silang ke domain asal — Verify: baca ulang seluruh domain, pastikan tidak ada yang tercecer — S
9. Verifikasi 2 Kriteria Keberhasilan sumber + tulis `report.md` — Acceptance: kedua KK dicek eksplisit satu per satu — Verify: `report.md` — S

**✅ Checkpoint 5 (final)** — commit + push, tutup milestone di `logs.md`.

## Open Questions Resolved with User

- Q: Dokumen konsolidasi ditaruh di mana? → A: Folder baru `docs/07-mart-aggregated/`, konsisten pola penomoran folder `docs/` yang sudah ada.
