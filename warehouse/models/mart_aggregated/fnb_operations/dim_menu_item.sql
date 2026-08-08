-- dim_menu_item: item_name teks sebagai natural key -- tidak ada ID terstruktur
-- di skema sumber (fnb_transactions.item_name, recipe_bom.item_name).
select distinct
    item_name
from {{ ref('mart_cleaned__fnb_transactions') }}
where item_name is not null
