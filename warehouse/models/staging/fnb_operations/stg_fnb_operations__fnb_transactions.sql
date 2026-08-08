-- Passthrough -- tidak ada isu data kotor terdaftar (pemetaan-kebutuhan-konsumen-data-mart.md).
-- guest_id kosong (~31%, walk-in anonim) DIPERTAHANKAN sebagai missing value bermakna.
--
-- CATATAN KATEGORI C (data-profiling-findings.md Section 2.4, ditemukan lewat profiling,
-- tidak tercatat di Metadata.md/pemetaan doc): transaction_id BUKAN row-level unique key
-- (387.972 nilai distinct dari 902.574 baris, ~2.33 baris/transaction_id -- konsisten
-- satu transaksi berisi beberapa item, satu baris per item). Bukan data kotor yang perlu
-- diperbaiki -- tapi siapa pun yang butuh row-level unique key di layer berikutnya
-- (mart_cleaned/intermediate) perlu pakai kombinasi (transaction_id, item_name) atau
-- surrogate key baru, bukan mengasumsikan transaction_id sendiri unik.
select *
from {{ source('raw_production', 'fnb_operations__fnb_transactions') }}
