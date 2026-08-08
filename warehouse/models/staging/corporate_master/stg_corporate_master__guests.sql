-- Cleaning per pemetaan-kebutuhan-konsumen-data-mart.md baris 46:
--   phone       : normalisasi 4 variasi format -> 1 format standar, KHUSUS nomor domestik
--                 (nomor asing pakai format negara asal sendiri, tidak disentuh --
--                 Metadata.md baris 188). Domestik dikenali via regex (awalan +62/62/0
--                 diikuti '8', hanya digit/spasi/strip -- nomor asing yang pakai titik,
--                 kurung, atau ekstensi "x123" tidak akan cocok, sengaja dibiarkan).
--   nationality : normalisasi case/whitespace saja (LOWER+TRIM lalu INITCAP) -- keputusan
--                 M2.2: tidak membangun mapping menyeluruh ke daftar negara baku, supaya
--                 tidak overlap dengan typo/variasi lain yang mungkin sengaja disuntikkan.
--
-- DIPERTAHANKAN apa adanya (Kategori B, data-profiling-findings.md):
--   full_name        : typo (~2%) TIDAK diperbaiki -- tidak bisa dinormalisasi via rule.
--   email/phone null : missing value bermakna (walk-in tidak isi form).
--   367 baris duplikat (guest_id G24501+, kunci full_name) : TIDAK di-dedup -- keputusan
--                 dedup diserahkan ke eksperimen Data Scientist sendiri.
with source as (
    select * from {{ source('raw_production', 'corporate_master__guests') }}
),

phone_cleaned as (
    select
        *,
        regexp_replace(phone, r'[\s\-]', '') as phone_digits_only
    from source
),

with_phone_normalized as (
    select
        * except (phone_digits_only),
        case
            when phone is null then null
            when not regexp_contains(phone_digits_only, r'^(\+?62|0)8[0-9]{8,11}$') then phone
            when starts_with(phone_digits_only, '+62') then concat('0', substr(phone_digits_only, 4))
            when starts_with(phone_digits_only, '62') then concat('0', substr(phone_digits_only, 3))
            else phone_digits_only
        end as phone_normalized
    from phone_cleaned
)

select
    guest_id,
    full_name,
    email,
    phone_normalized as phone,
    initcap(trim(nationality)) as nationality,
    loyalty_tier,
    registered_date,
    _synced_at
from with_phone_normalized
