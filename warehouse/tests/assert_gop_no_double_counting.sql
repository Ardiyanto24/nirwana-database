-- Business rule KK#2 M5.3: fact_financial_overall_monthly.gop_margin_pct harus
-- PERSIS sama dengan gop/departmental_revenue mentah pada baris Overall/Corporate
-- Overhead di financial_summary -- kalau model salah agregasi (mis. SUM lintas
-- SEMUA baris department termasuk Room/F&B/Spa&Event), denominator
-- departmental_revenue akan terinflasi (Overall sudah = total, ikut dijumlah lagi
-- dengan revenue per-departemen) sehingga gop_margin_pct keliru meski gop sendiri
-- kebetulan tidak berubah (gop cuma terisi non-zero di baris Overall/Corporate
-- Overhead -- dikonfirmasi lewat query agregat langsung ke BigQuery). Ini skenario
-- double-counting eksplisit yang diminta KK#2 M5.3.
-- dbt singular test: FAIL kalau query mengembalikan baris (selisih > toleransi).
select
    f.property_id,
    f.period_date,
    f.gop_margin_pct as fact_gop_margin_pct,
    src.gop_margin_pct as source_gop_margin_pct,
    abs(f.gop_margin_pct - src.gop_margin_pct) as diff
from {{ ref('fact_financial_overall_monthly') }} as f
join (
    select
        property_id,
        parse_date('%Y-%m', period) as period_date,
        safe_divide(gop, nullif(departmental_revenue, 0)) as gop_margin_pct
    from {{ ref('mart_cleaned__financial_summary') }}
    where department in ('Overall', 'Corporate Overhead')
) as src
    on f.property_id = src.property_id and f.period_date = src.period_date
where abs(f.gop_margin_pct - src.gop_margin_pct) > 0.001
