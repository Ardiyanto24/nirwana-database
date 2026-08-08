-- Koreksi (M5.3): mart_cleaned__rooms tidak punya kolom tanggal -- status di sana
-- adalah state TERKINI (current-state), bukan histori harian. Sama seperti
-- fact_fnb_inventory_status, pakai current_date() sebagai penanda snapshot.
-- Kolom out_of_order_hours (durasi) di draf M5.2 DIHAPUS -- tidak ada sumber histori
-- durasi status per kamar (rooms cuma simpan status saat ini, bukan log perubahan
-- status berwaktu) -- dicatat sebagai koreksi, bukan diam-diam dihilangkan.
select
    room_id,
    current_date() as period_date,
    status,
    status = 'out-of-order' as is_out_of_order
from {{ ref('mart_cleaned__rooms') }}
