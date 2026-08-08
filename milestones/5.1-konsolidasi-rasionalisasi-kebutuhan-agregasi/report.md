# Milestone 5.1: Konsolidasi dan Rasionalisasi Kebutuhan Agregasi — Report

**Status:** Completed
**Date completed:** 2026-08-08

## Kriteria Keberhasilan — Hasil

- [x] **Setiap metrik siap pakai di dokumen kebutuhan Data Analyst dan ketiga dokumen layer chatbot sudah dipetakan statusnya: masuk cakupan awal / masuk cakupan dengan perlakuan khusus / ditandai di luar cakupan dengan alasan.** — Terpenuhi. Seluruh 6 domain (`pemetaan-kebutuhan-data-analyst.md` §1.3–§6.3, termasuk audit §1.2–§6.2) diturunkan jadi 94 baris metrik/kebutuhan di `docs/07-mart-aggregated/konsolidasi-agregasi-mart-aggregated.md`: 77 Cakupan Awal, 1 Cakupan Khusus eksplisit (pace booking, ditambah 2 pola khusus lain yang tetap Cakupan Awal tapi didokumentasikan butuh perlakuan desain — window function *within-entity over time* untuk watchlist HR, dan 2 parameter/threshold yang belum diputuskan untuk SLA breach & early-warning HR), 16 Luar Cakupan (masing-masing dengan alasan eksplisit di kolom Catatan, dipisah kategori Gap Data Sumber vs Batasan Disengaja). Ketiga dokumen chatbot (20 persona) juga sudah dipetakan penuh ke 6 domain di bagian "Pemetaan Persona → Domain" (Checkpoint 1) dan disilangkan sebagai kolom "Konsumen Chatbot" di tiap baris metrik — tidak ada persona yang tidak terpetakan ke domain manapun.
- [x] **Dokumen konsolidasi ini bisa dipakai langsung sebagai acuan Milestone 5.2 tanpa perlu menerka ulang kebutuhan dari dokumen sumber.** — Terpenuhi. Tiap baris metrik sudah memuat grain (property_id/dept/dst × granularitas waktu), tabel sumber per domain, dan catatan cross-domain eksplisit (mis. capture rate F&B butuh join `daily_occupancy`; dampak pricing→GOP butuh join `financial_summary`) — cukup untuk langsung diturunkan jadi skema tabel di Milestone 5.2 tanpa membuka ulang 5 dokumen sumber. Bagian "Kebutuhan Khusus" mengisolasi 3 kasus yang butuh keputusan desain eksplisit (snapshot pace booking, pola within-entity HR, 2 threshold pending) persis seperti yang diminta Output #2 dokumen sumber M5.1. Bagian "Eksplisit Luar Cakupan" mengisolasi 16 kebutuhan yang tidak akan dibangun, dengan alasan per item, memenuhi Output #3.

## Deliverables

- `docs/07-mart-aggregated/konsolidasi-agregasi-mart-aggregated.md` — dokumen konsolidasi utama: pemetaan 20 persona → domain, 6 tabel metrik domain (Revenue 15 baris, F&B 17, Facility/Ops 17, Spa & Event 16 [7 Spa + 9 Event/MICE], HR 13, Corporate/Financial 16), bagian Kebutuhan Khusus (3 kasus, 3 kategori perlakuan), bagian Eksplisit Luar Cakupan (16 item, 2 kategori alasan).
- `milestones/5.1-konsolidasi-rasionalisasi-kebutuhan-agregasi/{decisions,logs}.md`.

## Deviations from decisions.md

Tidak ada deviasi pada keputusan inti (lokasi output, skema kolom, metode pengerjaan langsung tanpa sub-agent, urutan fondasi-persona-dulu). Satu penyempurnaan kecil ditambahkan saat eksekusi Checkpoint 2 (tidak mengubah keputusan, hanya memperjelas penerapannya): bagian "Cara Membaca Dokumen Ini" diberi catatan eksplisit bahwa status "Luar Cakupan" direservasi murni untuk gap data sumber, sedangkan kebutuhan row-level (yang dilayani `mart_cleaned`) dicatat sebagai catatan singkat per domain, bukan baris "Luar Cakupan" tersendiri — supaya kedua konsep (tidak tersedia vs tersedia-tapi-beda-tabel) tidak tercampur di kolom Status yang sama.

## Known Gaps / Follow-ups

- 3 kebutuhan di kategori "Kebutuhan Khusus" (pace booking, watchlist HR, 2 threshold pending) belum punya keputusan desain final — sengaja didokumentasikan sebagai isolasi kebutuhan untuk Milestone 5.2, bukan diselesaikan di sini (di luar scope M5.1 sesuai kontrak sumber).
- 10 item "Gap Data Sumber" (komisi OTA, target/budget, dll) berpotensi jadi rekomendasi penambahan kolom/tabel ke sistem produksi jika suatu saat dianggap penting — tidak ditindaklanjuti di sini, murni dicatat sebagai referensi supaya tidak ditanyakan ulang.
- Beberapa pemetaan "Konsumen Chatbot" bersifat pendekatan terbaik (best-effort matching) ketika dokumen chatbot tidak menyebut metrik persis sama kata dengan dokumen Data Analyst (mis. "revenue per kunjungan inhouse/walk-in" F&B dicocokkan ke "walk-in ratio dan tren" F&B Manager) — dicatat eksplisit di kolom Catatan tiap kali terjadi, bukan disembunyikan sebagai kecocokan pasti. Pemilik Milestone 5.2 sebaiknya tetap merujuk ke dokumen chatbot asli untuk detail kata-per-kata bila ragu.

## Handoff Notes

- `docs/07-mart-aggregated/konsolidasi-agregasi-mart-aggregated.md` adalah **input utama Milestone 5.2** (desain skema tabel `mart_aggregated`) — 3 hal yang perlu ditindaklanjuti eksplisit di sana: (1) desain mekanisme snapshot untuk pace booking, (2) desain kolom/pola query untuk metrik within-entity-over-time HR, (3) audit PII pada domain yang menyentuh `guests_pii`/`guests_profile` (Revenue, Spa & Event — sudah tersirat dari kolom Konsumen Chatbot yang menyebutkan persona ber-RBAC `guests_pii`, tapi keputusan masking/anonymization eksplisit adalah scope M5.2, bukan diputuskan di sini).
- Folder `docs/07-mart-aggregated/` dibuat baru di milestone ini, mengikuti pola penomoran `docs/01-architecture` s.d. `docs/06-akses-kredensial` — pemilik Milestone 5.2 disarankan menaruh dokumen desain skema di folder yang sama untuk konsistensi, bukan folder baru lagi.
- 2 metrik cross-domain eksplisit butuh keputusan desain di M5.2 soal bagaimana join lintas domain direpresentasikan di skema akhir (tabel terpisah dengan FK, view gabungan, atau kolom pre-joined): capture rate F&B (butuh `daily_occupancy`) dan dampak pricing terhadap GOP (butuh `financial_summary`) — keduanya sudah ditandai "Cross-domain" di tabel metrik masing-masing.
