# ERD — `mart_aggregated`

**Nirwana Hospitality Group — Data Platform ELT**

Diagram relasi entitas (ERD) star schema `mart_aggregated`: 27 dimension table + 49 fact table, 1 diagram tunggal (Keputusan #9 `milestones/5.3-.../decisions.md` — dipilih eksplisit oleh user dibanding opsi split per domain untuk keterbacaan). Kolom yang ditampilkan per entitas dibatasi ke primary/foreign key + 1-2 kolom representatif — daftar kolom lengkap ada di `DataSchema-mart-aggregated.md` dan cara hitungnya di `Metadata-mart-aggregated.md`.

```mermaid
erDiagram
    %% ================= DIMENSION TABLES (lintas-domain) =================
    dim_property {
        string property_id PK
        string property_name
        string region
    }
    dim_employee {
        string employee_id PK
        int department_id FK
        int access_level_id FK
        string full_name
    }
    dim_department {
        int department_id PK
        string department_name
    }
    dim_customer_type {
        int customer_type_id PK
        string customer_type_name
    }

    %% ================= DIMENSION TABLES (Revenue) =================
    dim_room_type {
        int room_type_id PK
        string room_type_name
    }
    dim_room {
        string room_id PK
        string property_id FK
        int room_type_id FK
    }
    dim_channel {
        int channel_id PK
        string channel_name
    }
    dim_loyalty_tier {
        int loyalty_tier_id PK
        string loyalty_tier_name
    }
    dim_nationality_group {
        int nationality_group_id PK
        string group_name
    }
    dim_pricing_reason {
        int reason_id PK
        string reason_name
    }

    %% ================= DIMENSION TABLES (F&B) =================
    dim_outlet_type {
        int outlet_type_id PK
        string outlet_type_name
    }
    dim_outlet {
        string outlet_id PK
        string property_id FK
        int outlet_type_id FK
    }
    dim_fnb_category {
        int category_id PK
        string category_name
    }
    dim_menu_item {
        string item_name PK
    }
    dim_waste_reason {
        int reason_id PK
        string reason_name
    }
    dim_ingredient {
        string ingredient_id PK
    }

    %% ================= DIMENSION TABLES (Facility/Ops) =================
    dim_facility_area {
        int facility_area_id PK
        string facility_area_name
    }
    dim_issue_type {
        int issue_type_id PK
        string issue_type_name
    }
    dim_priority {
        int priority_id PK
        string priority_name
    }

    %% ================= DIMENSION TABLES (Spa & Event) =================
    dim_spa_service {
        int service_id PK
        string service_name
    }
    dim_venue_type {
        int venue_type_id PK
        string venue_type_name
    }
    dim_venue {
        string venue_id PK
        string property_id FK
        int venue_type_id FK
        int max_capacity
    }
    dim_event_type {
        int event_type_id PK
        string event_type_name
    }

    %% ================= DIMENSION TABLES (HR) =================
    dim_shift_type {
        int shift_type_id PK
        string shift_type_name
    }
    dim_employee_status {
        int status_id PK
        string status_name
    }

    %% ================= DIMENSION TABLES (Corporate/Financial) =================
    dim_business_line {
        int business_line_id PK
        string line_name
    }
    dim_access_level {
        int access_level_id PK
        string access_level_name
    }

    %% ================= FACT TABLES (Revenue) =================
    fact_revenue_room_type_daily {
        string property_id FK
        int room_type_id FK
        date period_date
        float occupancy_rate
        float revenue
    }
    fact_revenue_channel_daily {
        string property_id FK
        int channel_id FK
        date period_date
        float revenue
    }
    fact_revenue_los_daily {
        string property_id FK
        int room_type_id FK
        int channel_id FK
        date period_date
        float avg_los_nights
    }
    fact_revenue_property_daily {
        string property_id FK
        date period_date
        float repeat_guest_rate
    }
    fact_revenue_gop_impact_monthly {
        string property_id FK
        date period_date
        float gop_margin
    }
    fact_revenue_pricing_deviation {
        string property_id FK
        int reason_id FK
        date period_date
        float avg_deviation_pct
    }
    fact_revenue_loyalty_daily {
        string property_id FK
        int loyalty_tier_id FK
        date period_date
        float revenue
    }
    fact_revenue_nationality_daily {
        string property_id FK
        int nationality_group_id FK
        date period_date
        float revenue
    }
    fact_revenue_pace_booking_snapshot {
        string property_id FK
        int room_type_id FK
        date stay_date
        date snapshot_date
        int rooms_sold_asof
    }

    %% ================= FACT TABLES (F&B) =================
    fact_fnb_outlet_daily {
        string outlet_id FK
        date period_date
        float revenue
        float capture_rate
    }
    fact_fnb_category_daily {
        string outlet_id FK
        int category_id FK
        date period_date
        float revenue
    }
    fact_fnb_hourly {
        string outlet_id FK
        date period_date
        int hour_of_day
        int transaction_count
    }
    fact_fnb_customer_type_daily {
        string outlet_id FK
        int customer_type_id FK
        date period_date
        float revenue
    }
    fact_fnb_menu_item_daily {
        string outlet_id FK
        string item_name FK
        date period_date
        float food_cost_ratio_actual
    }
    fact_fnb_waste_daily {
        string outlet_id FK
        int reason_id FK
        date period_date
        float waste_ratio
    }
    fact_fnb_inventory_status {
        string outlet_id FK
        date period_date
        int low_stock_item_count
    }
    fact_fnb_ingredient_price_daily {
        string ingredient_id FK
        date period_date
        float avg_unit_cost
    }

    %% ================= FACT TABLES (Facility/Ops) =================
    fact_facility_room_status_daily {
        string room_id FK
        date period_date
        string status
    }
    fact_housekeeping_room_type_daily {
        string property_id FK
        int room_type_id FK
        date period_date
        float avg_cleaning_duration_minutes
    }
    fact_housekeeping_property_daily {
        string property_id FK
        date period_date
        float delayed_rate
    }
    fact_housekeeping_staff_daily {
        string staff_id FK
        date period_date
        float avg_cleaning_duration_minutes
    }
    fact_maintenance_ticket_daily {
        string property_id FK
        int facility_area_id FK
        int issue_type_id FK
        int priority_id FK
        date period_date
        float avg_sla_duration_hours
    }
    fact_maintenance_cost_daily {
        string property_id FK
        int issue_type_id FK
        date period_date
        float total_cost
    }
    fact_maintenance_room_recurrence_yearly {
        string room_id FK
        int year
        int ticket_count
    }
    fact_maintenance_property_benchmark_yearly {
        string property_id FK
        int year
        float tickets_per_room_normalized
    }
    fact_maintenance_technician_daily {
        string assigned_staff_id FK
        date period_date
        int ticket_count
    }

    %% ================= FACT TABLES (Spa & Event) =================
    fact_spa_daily {
        string property_id FK
        date period_date
        float revenue
    }
    fact_spa_customer_type_daily {
        string property_id FK
        int customer_type_id FK
        date period_date
        float revenue
    }
    fact_spa_service_daily {
        string property_id FK
        int service_id FK
        date period_date
        float revenue_share_pct
    }
    fact_event_venue_daily {
        string venue_id FK
        date period_date
        float utilization_rate
    }
    fact_event_property_daily {
        string property_id FK
        date period_date
        float cancellation_rate
    }
    fact_event_type_daily {
        string property_id FK
        int event_type_id FK
        date period_date
        float revenue
    }

    %% ================= FACT TABLES (HR) =================
    fact_hr_attendance_daily {
        string property_id FK
        int department_id FK
        date period_date
        int present_count
    }
    fact_hr_employee_monthly {
        string employee_id FK
        date period_date
        float overtime_hours
    }
    fact_hr_employee_performance_semester {
        string employee_id FK
        string review_period
        float score
    }
    fact_hr_turnover_snapshot {
        string property_id FK
        int department_id FK
        date period_date
        float turnover_rate
    }
    fact_hr_headcount_status_daily {
        string property_id FK
        int department_id FK
        int status_id FK
        date period_date
        int employee_count
    }
    fact_hr_performance_department_semester {
        string property_id FK
        int department_id FK
        string review_period
        float avg_performance_score
    }
    fact_hr_performance_by_status_semester {
        string property_id FK
        int status_id FK
        string review_period
        float avg_performance_score
    }
    fact_hr_watchlist_monthly {
        string employee_id FK
        date period_date
        float absence_deviation_ratio
    }

    %% ================= FACT TABLES (Corporate/Financial) =================
    fact_financial_business_line_monthly {
        string property_id FK
        int business_line_id FK
        date period_date
        float revenue
    }
    fact_financial_overall_monthly {
        string property_id FK
        date period_date
        float gop
    }
    fact_financial_revenue_runrate_daily {
        string property_id FK
        date period_date
        float revenue_runrate
    }
    fact_payroll_department_monthly {
        string property_id FK
        int department_id FK
        date period_date
        float net_salary_total
    }
    fact_financial_service_charge_monthly {
        string property_id FK
        date period_date
        float service_charge_pool
    }
    fact_financial_labor_cost_monthly {
        string property_id FK
        date period_date
        float labor_cost_pct_revenue
    }
    fact_payroll_access_level_monthly {
        string property_id FK
        int access_level_id FK
        date period_date
        float service_charge_to_base_ratio
    }
    fact_financial_business_line_group_monthly {
        int business_line_id FK
        date period_date
        float group_revenue
    }
    fact_financial_property_benchmark_monthly {
        string property_id FK
        date period_date
        int gop_margin_rank
    }

    %% ================= RELATIONSHIPS: dim_property =================
    dim_property ||--o{ fact_revenue_room_type_daily : property_id
    dim_property ||--o{ fact_revenue_channel_daily : property_id
    dim_property ||--o{ fact_revenue_los_daily : property_id
    dim_property ||--o{ fact_revenue_property_daily : property_id
    dim_property ||--o{ fact_revenue_gop_impact_monthly : property_id
    dim_property ||--o{ fact_revenue_pricing_deviation : property_id
    dim_property ||--o{ fact_revenue_loyalty_daily : property_id
    dim_property ||--o{ fact_revenue_nationality_daily : property_id
    dim_property ||--o{ fact_revenue_pace_booking_snapshot : property_id
    dim_property ||--o{ dim_room : property_id
    dim_property ||--o{ dim_outlet : property_id
    dim_property ||--o{ dim_venue : property_id
    dim_property ||--o{ fact_housekeeping_room_type_daily : property_id
    dim_property ||--o{ fact_housekeeping_property_daily : property_id
    dim_property ||--o{ fact_maintenance_ticket_daily : property_id
    dim_property ||--o{ fact_maintenance_cost_daily : property_id
    dim_property ||--o{ fact_maintenance_property_benchmark_yearly : property_id
    dim_property ||--o{ fact_spa_daily : property_id
    dim_property ||--o{ fact_spa_customer_type_daily : property_id
    dim_property ||--o{ fact_spa_service_daily : property_id
    dim_property ||--o{ fact_event_property_daily : property_id
    dim_property ||--o{ fact_event_type_daily : property_id
    dim_property ||--o{ fact_hr_attendance_daily : property_id
    dim_property ||--o{ fact_hr_turnover_snapshot : property_id
    dim_property ||--o{ fact_hr_headcount_status_daily : property_id
    dim_property ||--o{ fact_hr_performance_department_semester : property_id
    dim_property ||--o{ fact_hr_performance_by_status_semester : property_id
    dim_property ||--o{ fact_financial_business_line_monthly : property_id
    dim_property ||--o{ fact_financial_overall_monthly : property_id
    dim_property ||--o{ fact_financial_revenue_runrate_daily : property_id
    dim_property ||--o{ fact_payroll_department_monthly : property_id
    dim_property ||--o{ fact_financial_service_charge_monthly : property_id
    dim_property ||--o{ fact_financial_labor_cost_monthly : property_id
    dim_property ||--o{ fact_payroll_access_level_monthly : property_id
    dim_property ||--o{ fact_financial_property_benchmark_monthly : property_id

    %% ================= RELATIONSHIPS: dim_employee =================
    dim_department ||--o{ dim_employee : department_id
    dim_access_level ||--o{ dim_employee : access_level_id
    dim_employee ||--o{ fact_housekeeping_staff_daily : staff_id
    dim_employee ||--o{ fact_maintenance_technician_daily : assigned_staff_id
    dim_employee ||--o{ fact_hr_employee_monthly : employee_id
    dim_employee ||--o{ fact_hr_employee_performance_semester : employee_id
    dim_employee ||--o{ fact_hr_watchlist_monthly : employee_id

    %% ================= RELATIONSHIPS: dim_department =================
    dim_department ||--o{ fact_hr_attendance_daily : department_id
    dim_department ||--o{ fact_hr_turnover_snapshot : department_id
    dim_department ||--o{ fact_hr_headcount_status_daily : department_id
    dim_department ||--o{ fact_hr_performance_department_semester : department_id
    dim_department ||--o{ fact_payroll_department_monthly : department_id

    %% ================= RELATIONSHIPS: dim_customer_type =================
    dim_customer_type ||--o{ fact_fnb_customer_type_daily : customer_type_id
    dim_customer_type ||--o{ fact_spa_customer_type_daily : customer_type_id

    %% ================= RELATIONSHIPS: Revenue dims =================
    dim_room_type ||--o{ dim_room : room_type_id
    dim_room_type ||--o{ fact_revenue_room_type_daily : room_type_id
    dim_room_type ||--o{ fact_revenue_los_daily : room_type_id
    dim_room_type ||--o{ fact_revenue_pace_booking_snapshot : room_type_id
    dim_room_type ||--o{ fact_housekeeping_room_type_daily : room_type_id
    dim_room ||--o{ fact_facility_room_status_daily : room_id
    dim_room ||--o{ fact_maintenance_room_recurrence_yearly : room_id
    dim_channel ||--o{ fact_revenue_channel_daily : channel_id
    dim_channel ||--o{ fact_revenue_los_daily : channel_id
    dim_loyalty_tier ||--o{ fact_revenue_loyalty_daily : loyalty_tier_id
    dim_nationality_group ||--o{ fact_revenue_nationality_daily : nationality_group_id
    dim_pricing_reason ||--o{ fact_revenue_pricing_deviation : reason_id

    %% ================= RELATIONSHIPS: F&B dims =================
    dim_outlet_type ||--o{ dim_outlet : outlet_type_id
    dim_outlet ||--o{ fact_fnb_outlet_daily : outlet_id
    dim_outlet ||--o{ fact_fnb_category_daily : outlet_id
    dim_outlet ||--o{ fact_fnb_hourly : outlet_id
    dim_outlet ||--o{ fact_fnb_customer_type_daily : outlet_id
    dim_outlet ||--o{ fact_fnb_menu_item_daily : outlet_id
    dim_outlet ||--o{ fact_fnb_waste_daily : outlet_id
    dim_outlet ||--o{ fact_fnb_inventory_status : outlet_id
    dim_fnb_category ||--o{ fact_fnb_category_daily : category_id
    dim_menu_item ||--o{ fact_fnb_menu_item_daily : item_name
    dim_waste_reason ||--o{ fact_fnb_waste_daily : reason_id
    dim_ingredient ||--o{ fact_fnb_ingredient_price_daily : ingredient_id

    %% ================= RELATIONSHIPS: Facility/Ops dims =================
    dim_facility_area ||--o{ fact_maintenance_ticket_daily : facility_area_id
    dim_issue_type ||--o{ fact_maintenance_ticket_daily : issue_type_id
    dim_issue_type ||--o{ fact_maintenance_cost_daily : issue_type_id
    dim_priority ||--o{ fact_maintenance_ticket_daily : priority_id

    %% ================= RELATIONSHIPS: Spa & Event dims =================
    dim_spa_service ||--o{ fact_spa_service_daily : service_id
    dim_venue_type ||--o{ dim_venue : venue_type_id
    dim_venue ||--o{ fact_event_venue_daily : venue_id
    dim_event_type ||--o{ fact_event_type_daily : event_type_id

    %% ================= RELATIONSHIPS: HR dims =================
    dim_employee_status ||--o{ fact_hr_headcount_status_daily : status_id
    dim_employee_status ||--o{ fact_hr_performance_by_status_semester : status_id

    %% ================= RELATIONSHIPS: Corporate/Financial dims =================
    dim_business_line ||--o{ fact_financial_business_line_monthly : business_line_id
    dim_business_line ||--o{ fact_financial_business_line_group_monthly : business_line_id
    dim_access_level ||--o{ fact_payroll_access_level_monthly : access_level_id
```

## Cara Membaca Diagram

- **`||--o{`**: relasi satu-ke-banyak (1 baris dimension → 0 atau banyak baris fact). Baca dari kiri (dimension) ke kanan (fact/dimension turunan).
- **Kolom cross-domain**: beberapa fact table (mis. `fact_fnb_outlet_daily.capture_rate`, `fact_housekeeping_property_daily.occupancy_rate`) berisi nilai yang di-*precompute* dari domain lain saat transformasi (M5.3) — relasi FK-nya tetap ke dimension domain tabel itu sendiri, bukan panah lintas-domain terpisah di diagram ini (join sumbernya didokumentasikan di `Metadata-mart-aggregated.md`, bukan digambar sebagai relasi ERD).
- **`dim_property`, `dim_employee`, `dim_customer_type`, `dim_room`, `dim_outlet`, `dim_venue`** adalah *conformed dimensions* — dipakai berulang lintas banyak domain, terlihat dari banyaknya garis relasi yang keluar dari entitas-entitas ini.

## Catatan Ukuran Diagram

Diagram ini sengaja dibuat sebagai 1 file tunggal mencakup seluruh 76 entitas (27 dimension + 49 fact) dan ~90 relasi, sesuai preferensi eksplisit user (Keputusan #9) — bukan dipecah per domain. Konsekuensinya: diagram butuh scroll/zoom signifikan saat dirender. Untuk navigasi per domain tanpa scroll penuh, rujuk section per domain di `DataSchema-mart-aggregated.md`/`Metadata-mart-aggregated.md` yang sudah dipecah rapi.
