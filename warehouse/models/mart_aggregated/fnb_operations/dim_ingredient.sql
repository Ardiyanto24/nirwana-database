-- Koreksi M5.3: desain M5.2 mengasumsikan kolom ingredient_name terpisah -- ternyata
-- mart_cleaned__ingredient_price_history cuma punya ingredient_id (STRING, berperan
-- ganda sebagai nama, mis. "Rice"/"Chicken"), tidak ada kolom nama terpisah.
select distinct
    ingredient_id
from {{ ref('mart_cleaned__ingredient_price_history') }}
where ingredient_id is not null
