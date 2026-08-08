-- mart_cleaned: 1:1 passthrough dari staging (pemetaan-kebutuhan-konsumen-data-mart.md).
-- Cleaning sudah dilakukan penuh di layer staging (Milestone 2.2) -- mart_cleaned
-- secara teknis hanya meneruskan hasil staging tanpa transformasi bisnis tambahan.
select *
from {{ ref('stg_corporate_master__employees') }}
