-- Passthrough -- tidak ada isu data kotor (pemetaan-kebutuhan-konsumen-data-mart.md baris 47).
select *
from {{ source('raw_production', 'corporate_master__role_permissions') }}
