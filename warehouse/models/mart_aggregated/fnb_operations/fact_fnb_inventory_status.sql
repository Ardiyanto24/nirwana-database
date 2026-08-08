-- fnb_inventory tidak punya kolom tanggal -- ini tabel current-state (di-sync ulang
-- tiap ekstraksi, bukan histori). "snapshot terkini" sesuai catatan M5.1: pakai
-- current_date() sebagai penanda kapan snapshot ini diambil, bukan histori berjenjang.
select
    outlet_id,
    current_date() as period_date,
    countif(stock_current < stock_min_threshold) as low_stock_item_count
from {{ ref('mart_cleaned__fnb_inventory') }}
group by 1, 2
