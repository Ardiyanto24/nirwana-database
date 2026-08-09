-- Milestone 3.2: HR Analyst views.
-- Source: mart_aggregated.fact_hr_* (see docs/08-serving-data-analyst/pemetaan-pola-akses-analyst.md #5).
-- Business rule kritis M3.1 #2: payroll is NOT included here in any form -- exclusive
-- to Corporate/Financial Analyst (views_corporate_financial.sql).
--
-- RESOLVED GAP (2026-08-09): dim_employee originally shipped without property_id, which
-- blocked property-level filtering on the 3 employee-grain fact tables below. Fixed
-- upstream by the mart_aggregated owner via Milestone 5.7 (see
-- docs/07-mart-aggregated/pengajuan-perubahan-cakupan.md, submitted through the M5.6
-- change-request mechanism) -- dim_employee.property_id is now live in both BigQuery and
-- serving PostgreSQL (755/755 rows populated, verified). The 3 views below are updated
-- here accordingly as the M3.2/M3.4 follow-up flagged in M5.7's report.md.

CREATE OR REPLACE VIEW analyst_views.v_hr_attendance_daily AS
SELECT
    f.property_id,
    p.property_name,
    d.department_name,
    f.period_date,
    f.present_count,
    f.late_count,
    f.leave_count,
    f.absent_count,
    f.overtime_hours_total
FROM mart_aggregated.fact_hr_attendance_daily f
LEFT JOIN mart_aggregated.dim_property p ON p.property_id = f.property_id
LEFT JOIN mart_aggregated.dim_department d ON d.department_id = f.department_id;

-- property_id/property_name appended at the end (not inserted mid-list) -- Postgres
-- CREATE OR REPLACE VIEW cannot reorder/insert existing view columns, only append.
CREATE OR REPLACE VIEW analyst_views.v_hr_employee_monthly AS
SELECT
    f.employee_id,
    e.full_name,
    d.department_name,
    f.period_date,
    f.overtime_hours,
    f.overtime_vs_dept_avg,
    f.late_rate,
    f.late_vs_dept_avg,
    e.property_id,
    p.property_name
FROM mart_aggregated.fact_hr_employee_monthly f
LEFT JOIN mart_aggregated.dim_employee e ON e.employee_id = f.employee_id
LEFT JOIN mart_aggregated.dim_property p ON p.property_id = e.property_id
LEFT JOIN mart_aggregated.dim_department d ON d.department_id = e.department_id;

CREATE OR REPLACE VIEW analyst_views.v_hr_employee_performance_semester AS
SELECT
    f.employee_id,
    e.full_name,
    d.department_name,
    f.review_period,
    f.score,
    f.notes,
    e.property_id,
    p.property_name
FROM mart_aggregated.fact_hr_employee_performance_semester f
LEFT JOIN mart_aggregated.dim_employee e ON e.employee_id = f.employee_id
LEFT JOIN mart_aggregated.dim_property p ON p.property_id = e.property_id
LEFT JOIN mart_aggregated.dim_department d ON d.department_id = e.department_id;

CREATE OR REPLACE VIEW analyst_views.v_hr_turnover_snapshot AS
SELECT
    f.property_id,
    p.property_name,
    d.department_name,
    f.period_date,
    f.turnover_rate
FROM mart_aggregated.fact_hr_turnover_snapshot f
LEFT JOIN mart_aggregated.dim_property p ON p.property_id = f.property_id
LEFT JOIN mart_aggregated.dim_department d ON d.department_id = f.department_id;

CREATE OR REPLACE VIEW analyst_views.v_hr_headcount_status_daily AS
SELECT
    f.property_id,
    p.property_name,
    d.department_name,
    s.status_name,
    f.period_date,
    f.employee_count
FROM mart_aggregated.fact_hr_headcount_status_daily f
LEFT JOIN mart_aggregated.dim_property p ON p.property_id = f.property_id
LEFT JOIN mart_aggregated.dim_department d ON d.department_id = f.department_id
LEFT JOIN mart_aggregated.dim_employee_status s ON s.status_id = f.status_id;

CREATE OR REPLACE VIEW analyst_views.v_hr_performance_department_semester AS
SELECT
    f.property_id,
    p.property_name,
    d.department_name,
    f.review_period,
    f.avg_performance_score
FROM mart_aggregated.fact_hr_performance_department_semester f
LEFT JOIN mart_aggregated.dim_property p ON p.property_id = f.property_id
LEFT JOIN mart_aggregated.dim_department d ON d.department_id = f.department_id;

CREATE OR REPLACE VIEW analyst_views.v_hr_performance_by_status_semester AS
SELECT
    f.property_id,
    p.property_name,
    s.status_name,
    f.review_period,
    f.avg_performance_score
FROM mart_aggregated.fact_hr_performance_by_status_semester f
LEFT JOIN mart_aggregated.dim_property p ON p.property_id = f.property_id
LEFT JOIN mart_aggregated.dim_employee_status s ON s.status_id = f.status_id;

CREATE OR REPLACE VIEW analyst_views.v_hr_watchlist_monthly AS
SELECT
    f.employee_id,
    e.full_name,
    d.department_name,
    f.period_date,
    f.current_absence_rate,
    f.baseline_absence_rate,
    f.current_late_rate,
    f.baseline_late_rate,
    f.absence_deviation_ratio,
    f.late_deviation_ratio,
    f.in_watchlist,
    e.property_id,
    p.property_name
FROM mart_aggregated.fact_hr_watchlist_monthly f
LEFT JOIN mart_aggregated.dim_employee e ON e.employee_id = f.employee_id
LEFT JOIN mart_aggregated.dim_property p ON p.property_id = e.property_id
LEFT JOIN mart_aggregated.dim_department d ON d.department_id = e.department_id;
