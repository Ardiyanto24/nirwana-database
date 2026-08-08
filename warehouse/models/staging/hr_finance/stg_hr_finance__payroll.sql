-- Passthrough -- tidak ada isu data kotor terdaftar (pemetaan-kebutuhan-konsumen-data-mart.md).
--
-- CATATAN KATEGORI C (data-profiling-findings.md Section 2.1, ditemukan lewat profiling,
-- tidak tercatat di Metadata.md/pemetaan doc): "thr hanya terisi 1x/tahun (Maret)" di
-- Metadata.md TIDAK berarti NULL di bulan lain -- diverifikasi lewat GROUP BY bulan:
-- seluruh baris non-Maret bernilai TEPAT 0 (bukan NULL). Nilai TIDAK diubah (0 valid
-- dari sumber) -- siapa pun yang query "thr aktual" harus filter eksplisit
-- RIGHT(period, 2) = '03', BUKAN pakai `WHERE thr IS NOT NULL` (tidak akan berfungsi).
select *
from {{ source('raw_production', 'hr_finance__payroll') }}
