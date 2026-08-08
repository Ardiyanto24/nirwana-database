-- Koreksi grain (M5.3): payroll.period grain aslinya bulanan (sama seperti
-- financial_summary), bukan harian -- occupancy_rate di-roll-up bulanan juga
-- (bukan dijoin per hari) supaya grain kedua sisi cocok.
with service_charge as (
    select
        e.property_id,
        parse_date('%Y-%m', p.period) as period_date,
        sum(p.service_charge) as service_charge_pool
    from {{ ref('mart_cleaned__payroll') }} as p
    left join {{ ref('mart_cleaned__employees') }} as e
        on p.employee_id = e.employee_id
    group by 1, 2
),

occupancy_monthly as (
    select
        property_id,
        date_trunc(date, month) as period_date,
        safe_divide(sum(rooms_sold), nullif(sum(total_rooms_available), 0)) as occupancy_rate
    from {{ ref('mart_cleaned__daily_occupancy') }}
    group by 1, 2
)

select
    s.property_id,
    s.period_date,
    s.service_charge_pool,
    o.occupancy_rate
from service_charge as s
left join occupancy_monthly as o
    on s.property_id = o.property_id and s.period_date = o.period_date
