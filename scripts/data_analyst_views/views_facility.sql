-- Milestone 3.2: Facility/Ops Analyst views.
-- Source: mart_aggregated.fact_facility_*/fact_housekeeping_*/fact_maintenance_*
-- (see docs/08-serving-data-analyst/pemetaan-pola-akses-analyst.md #3).

CREATE OR REPLACE VIEW analyst_views.v_facility_room_status_daily AS
SELECT
    r.property_id,
    p.property_name,
    f.room_id,
    rt.room_type_name,
    f.period_date,
    f.status,
    f.is_out_of_order
FROM mart_aggregated.fact_facility_room_status_daily f
LEFT JOIN mart_aggregated.dim_room r ON r.room_id = f.room_id
LEFT JOIN mart_aggregated.dim_property p ON p.property_id = r.property_id
LEFT JOIN mart_aggregated.dim_room_type rt ON rt.room_type_id = r.room_type_id;

CREATE OR REPLACE VIEW analyst_views.v_housekeeping_room_type_daily AS
SELECT
    f.property_id,
    p.property_name,
    rt.room_type_name,
    f.period_date,
    f.avg_cleaning_duration_minutes,
    f.baseline_duration_minutes
FROM mart_aggregated.fact_housekeeping_room_type_daily f
LEFT JOIN mart_aggregated.dim_property p ON p.property_id = f.property_id
LEFT JOIN mart_aggregated.dim_room_type rt ON rt.room_type_id = f.room_type_id;

CREATE OR REPLACE VIEW analyst_views.v_housekeeping_property_daily AS
SELECT
    f.property_id,
    p.property_name,
    f.period_date,
    f.delayed_rate,
    f.occupancy_rate
FROM mart_aggregated.fact_housekeeping_property_daily f
LEFT JOIN mart_aggregated.dim_property p ON p.property_id = f.property_id;

CREATE OR REPLACE VIEW analyst_views.v_housekeeping_staff_daily AS
SELECT
    f.staff_id,
    e.full_name AS staff_name,
    f.period_date,
    f.avg_cleaning_duration_minutes,
    f.team_avg_duration_minutes
FROM mart_aggregated.fact_housekeeping_staff_daily f
LEFT JOIN mart_aggregated.dim_employee e ON e.employee_id = f.staff_id;

-- Business rule kritis M3.1 #5: pending_count (tiket open/in-progress) WAJIB terpisah
-- dari breach evaluation, tidak pernah digabung. sla_threshold_hours dan
-- avg_exceeds_sla_threshold dihitung dari threshold resmi per priority
-- (docs/01-architecture/Metadata.md baris 706-715: critical=8, high=24, medium=48, low=72),
-- diterapkan ke avg_sla_duration_hours (rata-rata tiket yang SUDAH resolved hari itu) --
-- bukan ke pending_count, yang statusnya memang belum final dan tidak bisa dievaluasi.
CREATE OR REPLACE VIEW analyst_views.v_maintenance_ticket_daily AS
SELECT
    f.property_id,
    p.property_name,
    fa.facility_area_name,
    it.issue_type_name,
    pr.priority_name,
    f.period_date,
    f.new_ticket_count,
    f.avg_sla_duration_hours,
    f.pending_count,
    CASE pr.priority_name
        WHEN 'critical' THEN 8
        WHEN 'high' THEN 24
        WHEN 'medium' THEN 48
        WHEN 'low' THEN 72
    END AS sla_threshold_hours,
    CASE
        WHEN f.avg_sla_duration_hours IS NULL THEN NULL
        ELSE f.avg_sla_duration_hours > CASE pr.priority_name
            WHEN 'critical' THEN 8
            WHEN 'high' THEN 24
            WHEN 'medium' THEN 48
            WHEN 'low' THEN 72
        END
    END AS avg_exceeds_sla_threshold
FROM mart_aggregated.fact_maintenance_ticket_daily f
LEFT JOIN mart_aggregated.dim_property p ON p.property_id = f.property_id
LEFT JOIN mart_aggregated.dim_facility_area fa ON fa.facility_area_id = f.facility_area_id
LEFT JOIN mart_aggregated.dim_issue_type it ON it.issue_type_id = f.issue_type_id
LEFT JOIN mart_aggregated.dim_priority pr ON pr.priority_id = f.priority_id;

CREATE OR REPLACE VIEW analyst_views.v_maintenance_cost_daily AS
SELECT
    f.property_id,
    p.property_name,
    it.issue_type_name,
    f.period_date,
    f.total_cost,
    f.cost_with_parts,
    f.cost_without_parts,
    f.mom_cost_growth,
    f.yoy_cost_growth
FROM mart_aggregated.fact_maintenance_cost_daily f
LEFT JOIN mart_aggregated.dim_property p ON p.property_id = f.property_id
LEFT JOIN mart_aggregated.dim_issue_type it ON it.issue_type_id = f.issue_type_id;

CREATE OR REPLACE VIEW analyst_views.v_maintenance_room_recurrence_yearly AS
SELECT
    r.property_id,
    p.property_name,
    f.room_id,
    rt.room_type_name,
    f.year,
    f.ticket_count,
    f.vs_median_ratio
FROM mart_aggregated.fact_maintenance_room_recurrence_yearly f
LEFT JOIN mart_aggregated.dim_room r ON r.room_id = f.room_id
LEFT JOIN mart_aggregated.dim_property p ON p.property_id = r.property_id
LEFT JOIN mart_aggregated.dim_room_type rt ON rt.room_type_id = r.room_type_id;

CREATE OR REPLACE VIEW analyst_views.v_maintenance_property_benchmark_yearly AS
SELECT
    f.property_id,
    p.property_name,
    f.year,
    f.tickets_per_room,
    f.building_age_years,
    f.tickets_per_room_normalized
FROM mart_aggregated.fact_maintenance_property_benchmark_yearly f
LEFT JOIN mart_aggregated.dim_property p ON p.property_id = f.property_id;

CREATE OR REPLACE VIEW analyst_views.v_maintenance_technician_daily AS
SELECT
    f.assigned_staff_id,
    e.full_name AS technician_name,
    f.period_date,
    f.ticket_count,
    f.labor_hours
FROM mart_aggregated.fact_maintenance_technician_daily f
LEFT JOIN mart_aggregated.dim_employee e ON e.employee_id = f.assigned_staff_id;
