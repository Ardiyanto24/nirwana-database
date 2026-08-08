-- Passthrough -- tidak ada isu data kotor terdaftar (pemetaan-kebutuhan-konsumen-data-mart.md).
--
-- CATATAN KATEGORI C (data-profiling-findings.md Section 2.1 & 2.2, ditemukan lewat
-- profiling, tidak tercatat di Metadata.md/pemetaan doc):
-- 1. "gop/undistributed_expense hanya terisi di baris department='Overall'" TIDAK berarti
--    NULL untuk departemen lain -- diverifikasi: department IN ('F&B','Room','Spa&Event')
--    bernilai TEPAT 0 (bukan NULL). Filter "ambil P&L nyata" harus eksplisit
--    department IN ('Overall','Corporate Overhead'), BUKAN `WHERE gop IS NOT NULL`.
-- 2. department='Overall' HANYA muncul untuk 5 properti hotel (P01-P05). property_id='P06'
--    (kantor pusat, tidak punya F&B/Room/Spa&Event operasional) pakai nama departemen
--    berbeda: 'Corporate Overhead' -- juga berisi angka P&L nyata (36 baris, semua non-zero).
--    Kalau tidak disertakan, P&L kantor pusat akan selalu hilang dari agregasi manapun
--    yang cuma mencari 'Overall'.
select *
from {{ source('raw_production', 'hr_finance__financial_summary') }}
