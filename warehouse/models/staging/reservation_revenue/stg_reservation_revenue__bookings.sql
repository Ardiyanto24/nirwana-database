-- Passthrough -- tidak ada isu data kotor terdaftar (pemetaan-kebutuhan-konsumen-data-mart.md).
select *
from {{ source('raw_production', 'reservation_revenue__bookings') }}
