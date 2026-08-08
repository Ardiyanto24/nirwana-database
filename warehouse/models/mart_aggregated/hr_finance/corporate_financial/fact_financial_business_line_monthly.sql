-- Wajib filter business_line_id ke Room/F&B/Spa&Event saat dipakai untuk "departmental
-- margin" -- jangan sertakan Overall/Corporate Overhead (risiko double counting,
-- ditegaskan sejak M5.1, lihat desain-skema-mart-aggregated.md).
select
    property_id,
    bl.business_line_id,
    parse_date('%Y-%m', f.period) as period_date,
    f.departmental_revenue as revenue,
    f.departmental_expense as expense,
    f.departmental_profit as profit,
    safe_divide(f.departmental_profit, nullif(f.departmental_revenue, 0)) as margin_pct
from {{ ref('mart_cleaned__financial_summary') }} as f
left join {{ ref('dim_business_line') }} as bl
    on f.department = bl.line_name
