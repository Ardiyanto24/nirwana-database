-- Milestone 3.2: Corporate/Financial Analyst views.
-- Source: mart_aggregated.fact_financial_*/fact_payroll_*
-- (see docs/08-serving-data-analyst/pemetaan-pola-akses-analyst.md #6).
--
-- Business rule kritis #1 M3.1 (paling berisiko di seluruh milestone):
-- v_financial_departmental_margin WAJIB exclude 'Overall'/'Corporate Overhead' secara
-- permanen -- risiko double counting kalau baris itu ikut dijumlahkan/dirata-rata
-- bersama Room/F&B/Spa&Event. Filter ditanam di WHERE clause, bukan diserahkan ke
-- pemakai (KK2 M3.2).
CREATE OR REPLACE VIEW analyst_views.v_financial_departmental_margin AS
SELECT
    f.property_id,
    p.property_name,
    bl.line_name AS business_line_name,
    f.period_date,
    f.revenue,
    f.expense,
    f.profit,
    f.margin_pct
FROM mart_aggregated.fact_financial_business_line_monthly f
LEFT JOIN mart_aggregated.dim_property p ON p.property_id = f.property_id
LEFT JOIN mart_aggregated.dim_business_line bl ON bl.business_line_id = f.business_line_id
WHERE bl.line_name NOT IN ('Overall', 'Corporate Overhead');

-- GOP / overhead ratio: sourced from fact_financial_overall_monthly (already the
-- Overall-equivalent row per property, correctly handling P06's "Corporate Overhead"
-- P&L-row nuance per warehouse/README.md) -- NOT from fact_financial_business_line_monthly.
CREATE OR REPLACE VIEW analyst_views.v_financial_gop_overhead AS
SELECT
    f.property_id,
    p.property_name,
    f.period_date,
    f.gop,
    f.gop_margin_pct,
    f.mom_gop_growth,
    f.yoy_gop_growth,
    f.undistributed_expense_total,
    f.overhead_ratio
FROM mart_aggregated.fact_financial_overall_monthly f
LEFT JOIN mart_aggregated.dim_property p ON p.property_id = f.property_id;

CREATE OR REPLACE VIEW analyst_views.v_financial_revenue_runrate_daily AS
SELECT
    f.property_id,
    p.property_name,
    f.period_date,
    f.revenue_runrate
FROM mart_aggregated.fact_financial_revenue_runrate_daily f
LEFT JOIN mart_aggregated.dim_property p ON p.property_id = f.property_id;

CREATE OR REPLACE VIEW analyst_views.v_payroll_department_monthly AS
SELECT
    f.property_id,
    p.property_name,
    d.department_name,
    f.period_date,
    f.base_salary_total,
    f.service_charge_total,
    f.overtime_pay_total,
    f.thr_total,
    f.deduction_total,
    f.net_salary_total,
    f.mom_growth
FROM mart_aggregated.fact_payroll_department_monthly f
LEFT JOIN mart_aggregated.dim_property p ON p.property_id = f.property_id
LEFT JOIN mart_aggregated.dim_department d ON d.department_id = f.department_id;

CREATE OR REPLACE VIEW analyst_views.v_financial_service_charge_monthly AS
SELECT
    f.property_id,
    p.property_name,
    f.period_date,
    f.service_charge_pool,
    f.occupancy_rate
FROM mart_aggregated.fact_financial_service_charge_monthly f
LEFT JOIN mart_aggregated.dim_property p ON p.property_id = f.property_id;

CREATE OR REPLACE VIEW analyst_views.v_financial_labor_cost_monthly AS
SELECT
    f.property_id,
    p.property_name,
    f.period_date,
    f.labor_cost_pct_revenue
FROM mart_aggregated.fact_financial_labor_cost_monthly f
LEFT JOIN mart_aggregated.dim_property p ON p.property_id = f.property_id;

CREATE OR REPLACE VIEW analyst_views.v_payroll_access_level_monthly AS
SELECT
    f.property_id,
    p.property_name,
    al.access_level_name,
    f.period_date,
    f.service_charge_total,
    f.base_salary_total,
    f.service_charge_to_base_ratio
FROM mart_aggregated.fact_payroll_access_level_monthly f
LEFT JOIN mart_aggregated.dim_property p ON p.property_id = f.property_id
LEFT JOIN mart_aggregated.dim_access_level al ON al.access_level_id = f.access_level_id;

-- Group-level (lintas 5 properti, tanpa property_id) -- business rule kritis #3 M3.1:
-- Property/GM Analyst DILARANG akses view ini (larangan diberlakukan lewat GRANT di
-- Milestone 3.5, dicatat di sini sebagai dokumentasi teknis view-nya).
CREATE OR REPLACE VIEW analyst_views.v_financial_business_line_group_monthly AS
SELECT
    bl.line_name AS business_line_name,
    f.period_date,
    f.group_revenue,
    f.revenue_share_pct
FROM mart_aggregated.fact_financial_business_line_group_monthly f
LEFT JOIN mart_aggregated.dim_business_line bl ON bl.business_line_id = f.business_line_id;

CREATE OR REPLACE VIEW analyst_views.v_financial_property_benchmark_monthly AS
SELECT
    f.property_id,
    p.property_name,
    f.period_date,
    f.gop_margin_rank
FROM mart_aggregated.fact_financial_property_benchmark_monthly f
LEFT JOIN mart_aggregated.dim_property p ON p.property_id = f.property_id;
