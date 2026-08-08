-- Grain: outlet_id x period_date. fnb_transactions BUKAN row-level unik per transaction_id
-- (~2.33 baris/transaksi, multi-item order -- lihat warehouse/README.md) -- transaction_count
-- dan walk_in_ratio dihitung dari transaction_id distinct, bukan jumlah baris.
with tx_level as (
    select distinct
        transaction_id,
        outlet_id,
        date(transaction_datetime) as period_date,
        customer_type
    from {{ ref('mart_cleaned__fnb_transactions') }}
),

outlet_revenue as (
    select
        outlet_id,
        date(transaction_datetime) as period_date,
        sum(total_price) as revenue
    from {{ ref('mart_cleaned__fnb_transactions') }}
    group by 1, 2
),

tx_counts as (
    select
        outlet_id,
        period_date,
        count(*) as transaction_count,
        countif(customer_type = 'walk-in') as walk_in_count
    from tx_level
    group by 1, 2
),

-- Cross-domain: capture rate tamu inhouse yang belanja F&B (Keputusan #6 decisions.md).
-- rooms_sold dari daily_occupancy dipakai sebagai proksi populasi tamu menginap per hari.
inhouse_tx as (
    select
        o.property_id,
        date(f.transaction_datetime) as period_date,
        count(distinct f.transaction_id) as inhouse_tx_count
    from {{ ref('mart_cleaned__fnb_transactions') }} as f
    left join {{ ref('mart_cleaned__fnb_outlets') }} as o
        on f.outlet_id = o.outlet_id
    where f.customer_type = 'inhouse'
    group by 1, 2
),

occupancy_guests as (
    select property_id, date as period_date, sum(rooms_sold) as rooms_sold
    from {{ ref('mart_cleaned__daily_occupancy') }}
    group by 1, 2
),

capture_rate_by_property as (
    select
        i.property_id,
        i.period_date,
        safe_divide(i.inhouse_tx_count, nullif(g.rooms_sold, 0)) as capture_rate
    from inhouse_tx as i
    left join occupancy_guests as g
        on i.property_id = g.property_id and i.period_date = g.period_date
),

joined as (
    select
        o.outlet_id,
        ot.outlet_type_id,
        dm.property_id,
        a.period_date,
        a.revenue,
        t.transaction_count,
        safe_divide(a.revenue, nullif(t.transaction_count, 0)) as avg_check,
        safe_divide(t.walk_in_count, nullif(t.transaction_count, 0)) as walk_in_ratio
    from outlet_revenue as a
    left join tx_counts as t
        on a.outlet_id = t.outlet_id and a.period_date = t.period_date
    left join {{ ref('dim_outlet') }} as o
        on a.outlet_id = o.outlet_id
    left join {{ ref('mart_cleaned__fnb_outlets') }} as dm
        on a.outlet_id = dm.outlet_id
    left join {{ ref('dim_outlet_type') }} as ot
        on o.outlet_type_id = ot.outlet_type_id
),

with_growth as (
    select
        cur.*,
        cur.revenue - mom.revenue as mom_revenue_growth,
        cur.revenue - yoy.revenue as yoy_revenue_growth,
        safe_divide(cur.revenue, avg(cur.revenue) over (partition by cur.outlet_type_id, cur.period_date)) as revenue_rank_vs_outlet_type_avg
    from joined as cur
    left join joined as mom
        on cur.outlet_id = mom.outlet_id and mom.period_date = date_sub(cur.period_date, interval 1 month)
    left join joined as yoy
        on cur.outlet_id = yoy.outlet_id and yoy.period_date = date_sub(cur.period_date, interval 1 year)
)

select
    w.outlet_id,
    w.period_date,
    w.revenue,
    w.transaction_count,
    w.avg_check,
    w.mom_revenue_growth,
    w.yoy_revenue_growth,
    c.capture_rate,
    w.walk_in_ratio,
    w.revenue_rank_vs_outlet_type_avg
from with_growth as w
left join capture_rate_by_property as c
    on w.property_id = c.property_id and w.period_date = c.period_date
