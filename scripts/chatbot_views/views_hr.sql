-- Milestone 4.2: AI Chatbot views -- domain `hr`.
-- Source (aggregate): mart_aggregated.fact_hr_*
-- (see docs/09-serving-ai-chatbot/pemetaan-akses-teknis-chatbot.md §2.5).
-- Business rule kritis M3.1 #2 (berlaku sama untuk chatbot): payroll TIDAK
-- termasuk di sini dalam bentuk apa pun -- eksklusif domain `financial`.
-- dim_employee.property_id sudah live (M5.7) -- kolom property_id/property_name
-- langsung tersedia, tidak perlu pola "append di akhir" seperti M3.2.

CREATE OR REPLACE VIEW chatbot_views.v_hr_attendance_daily AS
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

CREATE OR REPLACE VIEW chatbot_views.v_hr_employee_monthly AS
SELECT
    f.employee_id,
    e.full_name,
    d.department_name,
    e.property_id,
    p.property_name,
    f.period_date,
    f.overtime_hours,
    f.overtime_vs_dept_avg,
    f.late_rate,
    f.late_vs_dept_avg
FROM mart_aggregated.fact_hr_employee_monthly f
LEFT JOIN mart_aggregated.dim_employee e ON e.employee_id = f.employee_id
LEFT JOIN mart_aggregated.dim_property p ON p.property_id = e.property_id
LEFT JOIN mart_aggregated.dim_department d ON d.department_id = e.department_id;

CREATE OR REPLACE VIEW chatbot_views.v_hr_employee_performance_semester AS
SELECT
    f.employee_id,
    e.full_name,
    d.department_name,
    e.property_id,
    p.property_name,
    f.review_period,
    f.score,
    f.notes
FROM mart_aggregated.fact_hr_employee_performance_semester f
LEFT JOIN mart_aggregated.dim_employee e ON e.employee_id = f.employee_id
LEFT JOIN mart_aggregated.dim_property p ON p.property_id = e.property_id
LEFT JOIN mart_aggregated.dim_department d ON d.department_id = e.department_id;

CREATE OR REPLACE VIEW chatbot_views.v_hr_turnover_snapshot AS
SELECT
    f.property_id,
    p.property_name,
    d.department_name,
    f.period_date,
    f.turnover_rate
FROM mart_aggregated.fact_hr_turnover_snapshot f
LEFT JOIN mart_aggregated.dim_property p ON p.property_id = f.property_id
LEFT JOIN mart_aggregated.dim_department d ON d.department_id = f.department_id;

CREATE OR REPLACE VIEW chatbot_views.v_hr_headcount_status_daily AS
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

CREATE OR REPLACE VIEW chatbot_views.v_hr_performance_department_semester AS
SELECT
    f.property_id,
    p.property_name,
    d.department_name,
    f.review_period,
    f.avg_performance_score
FROM mart_aggregated.fact_hr_performance_department_semester f
LEFT JOIN mart_aggregated.dim_property p ON p.property_id = f.property_id
LEFT JOIN mart_aggregated.dim_department d ON d.department_id = f.department_id;

CREATE OR REPLACE VIEW chatbot_views.v_hr_performance_by_status_semester AS
SELECT
    f.property_id,
    p.property_name,
    s.status_name,
    f.review_period,
    f.avg_performance_score
FROM mart_aggregated.fact_hr_performance_by_status_semester f
LEFT JOIN mart_aggregated.dim_property p ON p.property_id = f.property_id
LEFT JOIN mart_aggregated.dim_employee_status s ON s.status_id = f.status_id;

CREATE OR REPLACE VIEW chatbot_views.v_hr_watchlist_monthly AS
SELECT
    f.employee_id,
    e.full_name,
    d.department_name,
    e.property_id,
    p.property_name,
    f.period_date,
    f.current_absence_rate,
    f.baseline_absence_rate,
    f.current_late_rate,
    f.baseline_late_rate,
    f.absence_deviation_ratio,
    f.late_deviation_ratio,
    f.in_watchlist
FROM mart_aggregated.fact_hr_watchlist_monthly f
LEFT JOIN mart_aggregated.dim_employee e ON e.employee_id = f.employee_id
LEFT JOIN mart_aggregated.dim_property p ON p.property_id = e.property_id
LEFT JOIN mart_aggregated.dim_department d ON d.department_id = e.department_id;

-- Row-level lookup views (Keputusan #2). Tidak join ke payroll -- larangan
-- domain hr menyentuh payroll berlaku sama persis di level row-level.

-- Untuk kebutuhan HR Staff: status kehadiran karyawan hari ini.
-- property_id di-join dari employees (staff_shifts sendiri tidak punya kolom
-- ini) -- wajib ada supaya API (M4.4) bisa menerapkan filter own_property
-- (M4.1 Keputusan #5); hanya property_id yang ditarik dari employees, bukan
-- kolom lain, supaya tidak diam-diam bocor ke domain employees_directory.
CREATE OR REPLACE VIEW chatbot_views.v_lookup_staff_shifts AS
SELECT
    s.shift_id,
    s.employee_id,
    e.property_id,
    s.date,
    s.shift_type,
    s.clock_in,
    s.clock_out,
    s.status
FROM mart_cleaned.staff_shifts s
LEFT JOIN mart_cleaned.employees e ON e.employee_id = s.employee_id;

-- Untuk kebutuhan HR Staff: skor & catatan performa terakhir 1 karyawan.
-- Sama seperti di atas, property_id di-join dari employees.
CREATE OR REPLACE VIEW chatbot_views.v_lookup_employee_performance AS
SELECT
    r.review_id,
    r.employee_id,
    e.property_id,
    r.review_period,
    r.score,
    r.notes
FROM mart_cleaned.employee_performance r
LEFT JOIN mart_cleaned.employees e ON e.employee_id = r.employee_id;
