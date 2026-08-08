# Milestone 5.6: Mekanisme Pengajuan Perubahan Cakupan — Logs

## 2026-08-08 -- Checkpoint 1: decisions.md (Fase 0)

`decisions.md` ditulis (7 keputusan: 3 via AskUserQuestion, 4 teknis dikunci). Trial cycle KK2 dipilih: threshold watchlist HR (bisa ditutup penuh dengan tindak lanjut nyata), bukan `undistributed_expense` (berakhir ditolak) atau skema tabel ML (belum ada skema konkret, berakhir ditunda).

Dikonfirmasi langsung dari `warehouse/models/mart_aggregated/hr_finance/hr/fact_hr_watchlist_monthly.sql`: gap threshold masih terbuka persis seperti tercatat di M5.1/M5.2/M5.3 -- komentar file sendiri menyatakan "threshold belum ditentukan (Keputusan #7 decisions.md)" merujuk ke `milestones/5.2-.../decisions.md`.

## 2026-08-08 -- Checkpoint 2: dokumen proses (Fase 1)

`docs/07-mart-aggregated/mekanisme-pengajuan-perubahan-cakupan.md` ditulis -- alur kerja 5 langkah (submit -> evaluasi -> keputusan -> tindak lanjut -> tutup), template pengajuan (5 field), 3 kriteria evaluasi (ketersediaan data, dampak ke konsumen lain, prioritas relatif -- persis contoh dokumen sumber M5.6), 1 aturan keputusan sederhana ("tidak tersedia" -> ditolak langsung; dampak tinggi selalu butuh diskusi eksplisit, tidak bisa auto-disetujui). Peran pengaju vs pemilik `mart_aggregated` dipisah eksplisit. Catatan simulasi (Keputusan #2) ditulis sebagai section tersendiri, bukan disembunyikan di catatan kaki.

## 2026-08-08 -- Checkpoint 3-4: backlog + pengajuan trial + evaluasi + keputusan (Fase 2+3, digabung)

`docs/07-mart-aggregated/pengajuan-perubahan-cakupan.md` ditulis, pola persis `docs/keputusan-tertunda.md` (blockquote intro + entri dipisah `---`). **2 entri** ditulis sekaligus (bukan cuma 1) supaya backlog langsung punya contoh 2 jenis hasil berbeda:

1. **Threshold watchlist HR** (persona HR Manager, ditandai simulasi eksplisit) -- submission, evaluasi 3 kriteria, dan keputusan ditulis dalam 1 entri sekaligus (bukan dipisah jadi 2 checkpoint terpisah seperti draf rencana awal -- dokumentasi lebih koheren dibaca sekaligus daripada dipecah "Diajukan" lalu "diupdate" 2 file-write terpisah untuk pekerjaan yang sama-sama dilakukan hari yang sama). Evaluasi: ketersediaan data TERSEDIA (kolom mentah sudah ada M5.3), dampak RENDAH (kolom baru, tidak ubah existing), prioritas SEDANG (3 milestone berturut-turut menandai gap sama). Keputusan: **DISETUJUI**, threshold 1.5x baseline (Keputusan #5 decisions.md).
2. **Perubahan skema tabel ML** -- entri kedua, dicatat proaktif (bukan pengajuan masuk sungguhan) untuk mendemonstrasikan bagaimana backlog menampung pengajuan yang TIDAK bisa dievaluasi tuntas (belum ada skema konkret dari tim ML Engineer) -- status **DITUNDA**, bukan ditolak. Referensi ke `milestones/5.4-.../report.md` dan `milestones/5.5-.../report.md` yang sama-sama sudah menyebut M5.6 sebagai kanal yang dituju untuk ini.
