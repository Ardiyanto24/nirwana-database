# Report — Milestone 3.1: Pemetaan Pola Akses per Peran Analyst

Milestone ini berjenis **berbasis dokumen**. Hasilnya adalah pemetaan akses teknis bagi tujuh peran analyst.

## Bagian 1 — Ringkasan Hasil

**Status akhir:** Selesai sesuai rencana.

M3.1 menerjemahkan enam pola kebutuhan analyst dan Property/GM sebagai union menjadi pemetaan tabel, filter wajib, kebutuhan row-level, business rule, serta gap data yang konkret. Dokumen utama memakai skema final `DataSchema-mart-aggregated.md`, bukan draft lama, sehingga menjadi acuan langsung untuk view dan kontrol akses berikutnya.

## Bagian 2 — Kriteria Keberhasilan vs Bukti Nyata

| Kriteria (dari dokumen sumber) | Bukti Aktual | Terpenuhi? |
|---|---|---|
| Enam pola peran dan Property/GM memiliki pemetaan jelas yang dapat dipakai M3.2 tanpa membuka kebutuhan dari nol. | `pemetaan-pola-akses-analyst.md` memiliki tujuh baris lengkap dengan tabel mart, row-level, filter, rule kritis, dan gap; seluruh nama tabel dicek terhadap skema pasca-koreksi. | Ya |

## Bagian 3 — Cara Kerja dan Arsitektur

Milestone ini menghasilkan dokumen dan kesepakatan, tidak ada sistem yang berjalan untuk didiagramkan — lihat Bagian 1 untuk ringkasan hasil.

## Bagian 4 — Perubahan dari Plan

Tidak ada penyimpangan. Lokasi, skema kolom, metode pembacaan langsung, sumber kebenaran skema, dan penamaan mart_cleaned seluruhnya diikuti.

## Bagian 5 — Keterbatasan dan Item Provisional

- Status `fact_revenue_pace_booking_snapshot` perlu diverifikasi sebelum dipakai consumer.
- Threshold early-warning HR di luar `in_watchlist` belum ditetapkan.
- Kontrol granular untuk performa individu Facility baru menjadi lingkup API/kredensial.
- Forecast occupancy ML belum tersedia pada serving PostgreSQL.

## Bagian 6 — Follow-up

- M3.2 menanamkan 12 business rule hasil pemetaan ke view.
- M3.3 memakai kolom filter wajib sebagai kandidat index.
- M3.5 menerjemahkan larangan payroll dan data grup menjadi grant kredensial.
