-- Passthrough -- tidak ada isu data kotor terdaftar (pemetaan-kebutuhan-konsumen-data-mart.md).
select *
from {{ source('raw_production', 'fnb_operations__fnb_waste_log') }}
