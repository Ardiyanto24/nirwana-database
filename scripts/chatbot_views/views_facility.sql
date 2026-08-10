-- Milestone 4.2: AI Chatbot views -- domain `facility`.
-- Source (aggregate): mart_aggregated.fact_facility_*/fact_housekeeping_*/
-- fact_maintenance_* (see docs/09-serving-ai-chatbot/pemetaan-akses-teknis-chatbot.md §2.3).
-- SLA threshold logic reused verbatim from M3.2 (Metadata.md baris 706-715).

CREATE OR REPLACE VIEW chatbot_views.v_facility_room_status_daily AS
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

CREATE OR REPLACE VIEW chatbot_views.v_housekeeping_room_type_daily AS
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

CREATE OR REPLACE VIEW chatbot_views.v_housekeeping_property_daily AS
SELECT
    f.property_id,
    p.property_name,
    f.period_date,
    f.delayed_rate,
    f.occupancy_rate
FROM mart_aggregated.fact_housekeeping_property_daily f
LEFT JOIN mart_aggregated.dim_property p ON p.property_id = f.property_id;

-- Performa individu -- sensitivitas lebih tinggi dari label domain RBAC "Rendah".
-- Filtering staff_id=diri-sendiri (untuk role Staff) adalah tanggung jawab
-- Milestone 4.4 (API), bukan view ini (M4.1 §2.3 Filter properti; pola sama
-- v_housekeeping_staff_daily M3.2).
-- KOREKSI (M4.4): property_id awalnya tidak ikut di-SELECT meski sudah
-- tersedia lewat join dim_employee -- ditemukan saat Milestone 4.4 mendesain
-- filter own_property, tanpa kolom ini API tidak bisa membatasi baris ke
-- properti karyawan yang meminta. Ditambahkan di akhir SELECT (bukan
-- disisipkan -- CREATE OR REPLACE VIEW tidak mengizinkan itu, pola sama M4.2).
CREATE OR REPLACE VIEW chatbot_views.v_housekeeping_staff_daily AS
SELECT
    f.staff_id,
    e.full_name AS staff_name,
    f.period_date,
    f.avg_cleaning_duration_minutes,
    f.team_avg_duration_minutes,
    e.property_id
FROM mart_aggregated.fact_housekeeping_staff_daily f
LEFT JOIN mart_aggregated.dim_employee e ON e.employee_id = f.staff_id;

CREATE OR REPLACE VIEW chatbot_views.v_maintenance_ticket_daily AS
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

CREATE OR REPLACE VIEW chatbot_views.v_maintenance_cost_daily AS
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

CREATE OR REPLACE VIEW chatbot_views.v_maintenance_room_recurrence_yearly AS
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

CREATE OR REPLACE VIEW chatbot_views.v_maintenance_property_benchmark_yearly AS
SELECT
    f.property_id,
    p.property_name,
    f.year,
    f.tickets_per_room,
    f.building_age_years,
    f.tickets_per_room_normalized
FROM mart_aggregated.fact_maintenance_property_benchmark_yearly f
LEFT JOIN mart_aggregated.dim_property p ON p.property_id = f.property_id;

-- KOREKSI (M4.4): sama seperti v_housekeeping_staff_daily di atas --
-- property_id ditambahkan di akhir SELECT untuk filter own_property M4.4.
CREATE OR REPLACE VIEW chatbot_views.v_maintenance_technician_daily AS
SELECT
    f.assigned_staff_id,
    e.full_name AS technician_name,
    f.period_date,
    f.ticket_count,
    f.labor_hours,
    e.property_id
FROM mart_aggregated.fact_maintenance_technician_daily f
LEFT JOIN mart_aggregated.dim_employee e ON e.employee_id = f.assigned_staff_id;

-- Row-level lookup views (Keputusan #2). Tidak join ke guests atau employees
-- penuh -- assigned_staff_id/staff_id diteruskan sebagai FK mentah saja
-- (resolusi nama, kalau perlu, lewat domain employees_directory terpisah).

-- Untuk kebutuhan Housekeeping Staff: status kamar tertentu saat ini.
CREATE OR REPLACE VIEW chatbot_views.v_lookup_rooms AS
SELECT
    r.room_id,
    r.property_id,
    r.room_number,
    r.room_type,
    r.floor,
    r.status
FROM mart_cleaned.rooms r;

-- Untuk kebutuhan Housekeeping Staff/Manager: durasi pembersihan, status delayed.
-- property_id di-join dari rooms (housekeeping_log sendiri tidak punya kolom
-- ini) -- wajib ada untuk filter own_property di API (M4.1 Keputusan #5).
-- Kolom ditaruh di AKHIR daftar SELECT (pola sama M3.2/v_lookup_fnb_inventory).
CREATE OR REPLACE VIEW chatbot_views.v_lookup_housekeeping_log AS
SELECT
    h.log_id,
    h.room_id,
    h.date,
    h.cleaning_start_time,
    h.cleaning_end_time,
    h.staff_id,
    h.status,
    r.property_id
FROM mart_cleaned.housekeeping_log h
LEFT JOIN mart_cleaned.rooms r ON r.room_id = h.room_id;

-- Untuk kebutuhan Maintenance Staff/Manager: detail 1 tiket, riwayat per room_id.
CREATE OR REPLACE VIEW chatbot_views.v_lookup_maintenance_tickets AS
SELECT
    m.ticket_id,
    m.property_id,
    m.room_id,
    m.facility_area,
    m.issue_type,
    m.reported_date,
    m.resolved_date,
    m.status,
    m.priority,
    m.assigned_staff_id,
    m.labor_hours,
    m.parts_replaced,
    m.cost
FROM mart_cleaned.maintenance_tickets m;
