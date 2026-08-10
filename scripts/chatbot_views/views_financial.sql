-- Milestone 4.2: AI Chatbot views -- domain `financial`.
-- Source (aggregate): mart_aggregated.fact_financial_*/fact_payroll_*
-- (see docs/09-serving-ai-chatbot/pemetaan-akses-teknis-chatbot.md §2.6).
--
-- Business rule kritis M3.1 #1 (paling berisiko, berlaku sama untuk chatbot):
-- v_financial_departmental_margin WAJIB exclude 'Overall'/'Corporate Overhead'
-- secara permanen -- risiko double counting. Filter ditanam di WHERE clause.

CREATE OR REPLACE VIEW chatbot_views.v_financial_departmental_margin AS
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

-- GOP/overhead ratio: dari fact_financial_overall_monthly (baris setara
-- Overall per properti) -- BUKAN dari fact_financial_business_line_monthly.
CREATE OR REPLACE VIEW chatbot_views.v_financial_gop_overhead AS
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

CREATE OR REPLACE VIEW chatbot_views.v_financial_revenue_runrate_daily AS
SELECT
    f.property_id,
    p.property_name,
    f.period_date,
    f.revenue_runrate
FROM mart_aggregated.fact_financial_revenue_runrate_daily f
LEFT JOIN mart_aggregated.dim_property p ON p.property_id = f.property_id;

CREATE OR REPLACE VIEW chatbot_views.v_payroll_department_monthly AS
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

CREATE OR REPLACE VIEW chatbot_views.v_financial_service_charge_monthly AS
SELECT
    f.property_id,
    p.property_name,
    f.period_date,
    f.service_charge_pool,
    f.occupancy_rate
FROM mart_aggregated.fact_financial_service_charge_monthly f
LEFT JOIN mart_aggregated.dim_property p ON p.property_id = f.property_id;

CREATE OR REPLACE VIEW chatbot_views.v_financial_labor_cost_monthly AS
SELECT
    f.property_id,
    p.property_name,
    f.period_date,
    f.labor_cost_pct_revenue
FROM mart_aggregated.fact_financial_labor_cost_monthly f
LEFT JOIN mart_aggregated.dim_property p ON p.property_id = f.property_id;

CREATE OR REPLACE VIEW chatbot_views.v_payroll_access_level_monthly AS
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

-- Group-level (lintas 5 properti, tanpa property_id). Konsisten M4.1 §2.6:
-- domain financial (all_properties) boleh akses; Property/GM-equivalent kalau
-- ada di masa depan wajib dilarang lewat GRANT M4.3.
CREATE OR REPLACE VIEW chatbot_views.v_financial_business_line_group_monthly AS
SELECT
    bl.line_name AS business_line_name,
    f.period_date,
    f.group_revenue,
    f.revenue_share_pct
FROM mart_aggregated.fact_financial_business_line_group_monthly f
LEFT JOIN mart_aggregated.dim_business_line bl ON bl.business_line_id = f.business_line_id;

CREATE OR REPLACE VIEW chatbot_views.v_financial_property_benchmark_monthly AS
SELECT
    f.property_id,
    p.property_name,
    f.period_date,
    f.gop_margin_rank
FROM mart_aggregated.fact_financial_property_benchmark_monthly f
LEFT JOIN mart_aggregated.dim_property p ON p.property_id = f.property_id;

-- Row-level lookup views (Keputusan #2).

-- Untuk kebutuhan Finance Staff/Manager: revenue/expense/profit per
-- departemen, wajib filter department='Overall' untuk GOP/undistributed_expense.
CREATE OR REPLACE VIEW chatbot_views.v_lookup_financial_summary AS
SELECT
    fs.property_id,
    fs.period,
    fs.department,
    fs.departmental_revenue,
    fs.departmental_expense,
    fs.departmental_profit,
    fs.undistributed_expense,
    fs.gop
FROM mart_cleaned.financial_summary fs;

-- Untuk kebutuhan Finance Manager: komponen payroll individual. property_id
-- di-join dari employees (payroll sendiri tidak punya kolom ini).
CREATE OR REPLACE VIEW chatbot_views.v_lookup_payroll AS
SELECT
    py.payroll_id,
    py.employee_id,
    py.period,
    py.base_salary,
    py.service_charge,
    py.overtime_pay,
    py.thr,
    py.deduction,
    py.net_salary,
    e.property_id
FROM mart_cleaned.payroll py
LEFT JOIN mart_cleaned.employees e ON e.employee_id = py.employee_id;
