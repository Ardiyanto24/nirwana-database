# Milestone 5.6: Mekanisme Pengajuan Perubahan Cakupan — Logs

## 2026-08-08 -- Checkpoint 1: decisions.md (Fase 0)

`decisions.md` ditulis (7 keputusan: 3 via AskUserQuestion, 4 teknis dikunci). Trial cycle KK2 dipilih: threshold watchlist HR (bisa ditutup penuh dengan tindak lanjut nyata), bukan `undistributed_expense` (berakhir ditolak) atau skema tabel ML (belum ada skema konkret, berakhir ditunda).

Dikonfirmasi langsung dari `warehouse/models/mart_aggregated/hr_finance/hr/fact_hr_watchlist_monthly.sql`: gap threshold masih terbuka persis seperti tercatat di M5.1/M5.2/M5.3 -- komentar file sendiri menyatakan "threshold belum ditentukan (Keputusan #7 decisions.md)" merujuk ke `milestones/5.2-.../decisions.md`.

## 2026-08-08 -- Checkpoint 2: dokumen proses (Fase 1)

`docs/07-mart-aggregated/mekanisme-pengajuan-perubahan-cakupan.md` ditulis -- alur kerja 5 langkah (submit -> evaluasi -> keputusan -> tindak lanjut -> tutup), template pengajuan (5 field), 3 kriteria evaluasi (ketersediaan data, dampak ke konsumen lain, prioritas relatif -- persis contoh dokumen sumber M5.6), 1 aturan keputusan sederhana ("tidak tersedia" -> ditolak langsung; dampak tinggi selalu butuh diskusi eksplisit, tidak bisa auto-disetujui). Peran pengaju vs pemilik `mart_aggregated` dipisah eksplisit. Catatan simulasi (Keputusan #2) ditulis sebagai section tersendiri, bukan disembunyikan di catatan kaki.