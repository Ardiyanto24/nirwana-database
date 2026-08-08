-- Pengganti GOP mingguan yang tidak bisa dihitung akurat (financial_summary grain
-- bulanan). Agregasi lintas 4 sumber revenue: bookings, fnb_transactions,
-- spa_bookings, event_bookings.
with room_rev as (
    select property_id, check_in_date as period_date, sum(total_amount) as revenue
    from {{ ref('mart_cleaned__bookings') }}
    where status in ('completed', 'confirmed')
    group by 1, 2
),

fnb_rev as (
    select o.property_id, date(f.transaction_datetime) as period_date, sum(f.total_price) as revenue
    from {{ ref('mart_cleaned__fnb_transactions') }} as f
    left join {{ ref('mart_cleaned__fnb_outlets') }} as o
        on f.outlet_id = o.outlet_id
    group by 1, 2
),

spa_rev as (
    select property_id, service_date as period_date, sum(price) as revenue
    from {{ ref('mart_cleaned__spa_bookings') }}
    where status in ('completed', 'confirmed')
    group by 1, 2
),

event_rev as (
    select property_id, event_date as period_date, sum(total_revenue) as revenue
    from {{ ref('mart_cleaned__event_bookings') }}
    where status in ('completed', 'confirmed')
    group by 1, 2
),

unioned as (
    select * from room_rev
    union all select * from fnb_rev
    union all select * from spa_rev
    union all select * from event_rev
)

select
    property_id,
    period_date,
    sum(revenue) as revenue_runrate
from unioned
group by 1, 2
