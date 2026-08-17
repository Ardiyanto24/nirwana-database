# Report — Milestone 4.1: Pemetaan RBAC ke Struktur Akses Teknis

Milestone ini berjenis **berbasis dokumen**. Hasilnya adalah pemetaan teknis sepuluh `data_domain` chatbot.

## Bagian 1 — Ringkasan Hasil

**Status akhir:** Selesai dengan penyesuaian dari plan.

M4.1 menerjemahkan sepuluh domain pada `role_permissions` menjadi tabel, kolom, filter properti, dan kelompok kredensial serving yang nyata. Pemetaan ini memperluas boundary Lapis 2 dari mart agregat saja menjadi mart agregat plus tabel cleaned terpilih, karena mayoritas kebutuhan Staff tidak dapat dipenuhi oleh grain agregat. `guests_pii` dan `guests_profile` dipisahkan menjadi kontrak view berbeda di atas tabel guest yang sama.

## Bagian 2 — Kriteria Keberhasilan vs Bukti Nyata

| Kriteria (dari dokumen sumber) | Bukti Aktual | Terpenuhi? |
|---|---|---|
| Setiap 10 data domain memiliki pemetaan teknis, termasuk guests PII/profile. | Sepuluh nilai domain diverifikasi dari `role_permissions` dan dipetakan dalam `pemetaan-akses-teknis-chatbot.md`; PII dan profile memiliki kontrak kolom terpisah. | Ya |
| Pemetaan dapat dipakai M4.2 tanpa menafsir ulang role_permissions. | Setiap domain memuat tabel/kolom aktual, filter own/all property, rule kritis, dan input kelompok kredensial. | Ya |

## Bagian 3 — Cara Kerja dan Arsitektur

Milestone ini menghasilkan dokumen dan kesepakatan, tidak ada sistem yang berjalan untuk didiagramkan — lihat Bagian 1 untuk ringkasan hasil.

## Bagian 4 — Perubahan dari Plan

Boundary Lapis 2 diperluas dari rancangan awal agar kebutuhan row-level Staff dapat dipenuhi. Rencana ADR bernomor diganti catatan revisi inline karena project tidak memiliki konvensi ADR.

## Bagian 5 — Keterbatasan dan Item Provisional

- Threshold SLA Facility serta outlier HR belum diputuskan.
- Harga menu resmi tidak tersedia; masih bergantung proxy transaksi.
- Performa dua view guest dan kebutuhan kolom employees tambahan belum teruji.

## Bagian 6 — Follow-up

- M4.2 membangun view sesuai kontrak ini.
- M4.3 membuat sepuluh kredensial; M4.4 menegakkan own/all property.
