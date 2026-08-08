-- Passthrough -- tidak ada isu data kotor terdaftar (pemetaan-kebutuhan-konsumen-data-mart.md).
select *
from {{ source('raw_production', 'facility_maintenance__housekeeping_log') }}
