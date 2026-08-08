-- department IN ('Overall','Corporate Overhead') -- P06 kantor pusat pakai
-- 'Corporate Overhead' sebagai baris P&L-nya, P01-P05 pakai 'Overall'
-- (warehouse/README.md). Tiap property_id hanya punya salah satu, tidak keduanya.
-- undistributed_expense HANYA 1 kolom total di sumber -- tidak ada breakdown
-- per komponen (koreksi M5.3, lihat desain-skema-mart-aggregated.md).
with agg as (
    select
        property_id,
        parse_date('%Y-%m', period) as period_date,
        gop,
        safe_divide(gop, nullif(departmental_revenue, 0)) as gop_margin_pct,
        undistributed_expense as undistributed_expense_total,
        safe_divide(undistributed_expense, nullif(departmental_revenue, 0)) as overhead_ratio
    from {{ ref('mart_cleaned__financial_summary') }}
    where department in ('Overall', 'Corporate Overhead')
)

select
    cur.property_id,
    cur.period_date,
    cur.gop,
    cur.gop_margin_pct,
    cur.gop - mom.gop as mom_gop_growth,
    cur.gop - yoy.gop as yoy_gop_growth,
    cur.undistributed_expense_total,
    cur.overhead_ratio
from agg as cur
left join agg as mom
    on cur.property_id = mom.property_id and mom.period_date = date_sub(cur.period_date, interval 1 month)
left join agg as yoy
    on cur.property_id = yoy.property_id and yoy.period_date = date_sub(cur.period_date, interval 1 year)
