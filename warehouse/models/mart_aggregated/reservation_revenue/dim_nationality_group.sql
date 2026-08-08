-- dim_nationality_group: bucket Domestik/Mancanegara (Audit PII M5.2: domain guests_profile,
-- diteruskan apa adanya -- kategori agregat, bukan nationality individual mentah).
-- Tabel statis 2 baris, bukan diturunkan dari distinct source values -- aturan kategorisasi
-- (nationality='Indonesia' -> Domestik, selain itu -> Mancanegara, per M5.1 §1.3) diterapkan
-- di fact_revenue_nationality_daily saat join ke guests.nationality, bukan di sini.
select 1 as nationality_group_id, 'Domestik' as group_name
union all
select 2 as nationality_group_id, 'Mancanegara' as group_name
