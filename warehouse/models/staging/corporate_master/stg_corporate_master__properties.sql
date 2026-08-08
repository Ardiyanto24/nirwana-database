-- Passthrough -- tidak ada isu data kotor terdaftar (pemetaan-kebutuhan-konsumen-data-mart.md baris 44).
select *
from {{ source('raw_production', 'corporate_master__properties') }}
