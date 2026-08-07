"""
Konfigurasi expectation per 23 tabel untuk Milestone 1.3.

Sumber: docs/04-monitoring/baseline-inventaris-produksi.md (katalog 27 business rule,
kolom kritis, kolom dirty-by-design) + docs/01-architecture/Metadata.md (nilai enum).

Kolom yang didokumentasikan dirty-by-design (nullable bermakna / format tidak konsisten)
SENGAJA tidak dimasukkan ke "not_null" di sini -- dipantau lewat jalur terpisah
(dirty_columns_config.py, rolling tolerance band) sesuai keputusan di decisions.md.

Format tiap entri tabel:
  not_null:        list kolom yang harus selalu terisi (bukan dirty-by-design)
  unique:           list kolom yang harus unik (biasanya PK)
  accepted_values:  {kolom: [nilai valid]} untuk enum
  custom:           list of (nama_rule, sql_predicate_pelanggaran) -- dieksekusi sebagai
                     "SELECT * FROM {batch} WHERE <predicate>", baris yang match = pelanggaran
"""

RULES = {
    ("corporate_master", "properties"): {
        "not_null": ["property_id", "property_name", "city", "region"],
        "unique": ["property_id"],
        "accepted_values": {"region": ["Bali", "Jawa", "Nusa Tenggara"]},
        "custom": [
            ("total_rooms_non_negative", "total_rooms < 0"),
        ],
    },
    ("corporate_master", "employees"): {
        "not_null": ["employee_id", "property_id", "access_level", "status"],
        "unique": ["employee_id"],
        "accepted_values": {
            "access_level": ["staff", "manager", "corporate"],
            "status": ["active", "resigned", "terminated"],
        },
        "custom": [
            ("role_title_exists_in_rbac_when_filled",
             "subselect.role_title IS NOT NULL AND subselect.role_title != '' AND subselect.role_title NOT IN "
             "(SELECT DISTINCT role_title FROM corporate_master.role_permissions)"),
        ],
    },
    ("corporate_master", "guests"): {
        "not_null": ["guest_id"],
        "unique": [],  # sengaja TIDAK unique -- ~367 baris duplikat memang disengaja (M1.1)
        "accepted_values": {"loyalty_tier": ["none", "Silver", "Gold", "Platinum"]},
        "custom": [
            ("email_format_when_filled",
             "email IS NOT NULL AND email != '' AND email !~ '^[^@\\s]+@[^@\\s]+\\.[^@\\s]+$'"),
        ],
    },
    ("corporate_master", "role_permissions"): {
        "not_null": ["role_title", "data_domain", "access_scope", "permission_type"],
        "unique": [],  # PK gabungan (role_title, data_domain) -- dicek via custom
        "accepted_values": {
            "access_scope": ["own_property", "all_properties"],
            "permission_type": ["read"],
            "data_domain": ["reservation", "fnb", "facility", "spa_event", "hr", "financial",
                             "properties_ref", "employees_directory", "guests_pii", "guests_profile"],
        },
        "custom": [
            ("role_domain_combo_unique",
             "(subselect.role_title, subselect.data_domain) IN (SELECT role_title, data_domain FROM corporate_master.role_permissions "
             "GROUP BY role_title, data_domain HAVING COUNT(*) > 1)"),
        ],
    },

    ("reservation_revenue", "bookings"): {
        "not_null": ["booking_id", "property_id", "guest_id", "status"],
        "unique": ["booking_id"],
        "accepted_values": {
            "room_type": ["Standard", "Deluxe", "Suite", "Villa"],
            "status": ["confirmed", "cancelled", "no-show", "completed"],
        },
        "custom": [
            ("total_amount_matches_rate_x_nights", "total_amount != room_rate * nights"),
            ("check_out_after_check_in", "check_out_date <= check_in_date"),
            ("booking_date_before_check_in", "booking_date > check_in_date"),
            ("room_rate_non_negative", "room_rate < 0 OR total_amount < 0"),
            ("villa_only_in_p01_p04_p05",
             "room_type = 'Villa' AND property_id NOT IN ('P01', 'P04', 'P05')"),
        ],
    },
    ("reservation_revenue", "daily_occupancy"): {
        "not_null": ["property_id", "room_type", "date", "occupancy_rate"],
        "unique": [],
        "accepted_values": {},
        "custom": [
            ("occupancy_rate_between_0_and_1", "occupancy_rate < 0 OR occupancy_rate > 1"),
            ("rooms_sold_not_exceed_available", "rooms_sold > total_rooms_available"),
        ],
    },
    ("reservation_revenue", "pricing_history"): {
        "not_null": ["property_id", "room_type", "date", "base_rate", "applied_rate"],
        "unique": [],
        "accepted_values": {"reason": ["manual", "promo", "dynamic-pricing-AI"]},
        "custom": [
            ("rates_non_negative", "base_rate < 0 OR applied_rate < 0"),
        ],
    },

    ("fnb_operations", "fnb_outlets"): {
        "not_null": ["outlet_id", "property_id", "outlet_name", "outlet_type"],
        "unique": ["outlet_id"],
        "accepted_values": {"outlet_type": ["Restaurant", "Bar", "Room Service"]},
        "custom": [],
    },
    ("fnb_operations", "recipe_bom"): {
        "not_null": ["item_name", "ingredient_id", "qty_per_portion"],
        "unique": [],
        "accepted_values": {},
        "custom": [("qty_per_portion_positive", "qty_per_portion <= 0")],
    },
    ("fnb_operations", "ingredient_price_history"): {
        "not_null": ["ingredient_id", "date", "unit_cost"],
        "unique": [],
        "accepted_values": {},
        "custom": [("unit_cost_positive", "unit_cost <= 0")],
    },
    ("fnb_operations", "fnb_transactions"): {
        "not_null": ["transaction_id", "outlet_id", "customer_type", "transaction_datetime", "item_name"],
        "unique": [],  # transaction_id sengaja berulang (banyak item per struk)
        "accepted_values": {
            "customer_type": ["inhouse", "walk-in"],
            "category": ["Food", "Beverage", "Dessert"],
        },
        "custom": [
            ("total_price_matches_unit_price_x_qty", "total_price != unit_price * quantity"),
            ("inhouse_must_have_guest_id", "customer_type = 'inhouse' AND (guest_id IS NULL OR guest_id = '')"),
            ("quantity_positive", "quantity <= 0"),
            ("unit_price_non_negative", "unit_price < 0"),
        ],
    },
    ("fnb_operations", "fnb_waste_log"): {
        "not_null": ["waste_id", "outlet_id", "date", "ingredient_id", "reason"],
        "unique": ["waste_id"],
        "accepted_values": {"reason": ["overproduction", "expired", "spillage"]},
        "custom": [("quantity_wasted_positive", "quantity_wasted <= 0")],
    },
    ("fnb_operations", "fnb_inventory"): {
        "not_null": ["ingredient_id", "outlet_id", "ingredient_name", "unit"],
        "unique": [],
        "accepted_values": {"unit": ["kg", "liter", "pcs"]},
        "custom": [("stock_current_non_negative", "stock_current < 0")],
    },

    ("facility_maintenance", "rooms"): {
        "not_null": ["room_id", "property_id", "room_type"],
        "unique": ["room_id"],
        "accepted_values": {
            "room_type": ["Standard", "Deluxe", "Suite", "Villa"],
            "status": ["available", "occupied", "cleaning", "maintenance", "out-of-order"],
        },
        "custom": [],
    },
    ("facility_maintenance", "housekeeping_log"): {
        "not_null": ["log_id", "room_id", "date", "staff_id", "status"],
        "unique": ["log_id"],
        "accepted_values": {"status": ["completed", "delayed"]},
        "custom": [
            ("cleaning_end_after_start", "cleaning_end_time <= cleaning_start_time"),
        ],
    },
    ("facility_maintenance", "maintenance_tickets"): {
        "not_null": ["ticket_id", "property_id", "facility_area", "issue_type", "reported_date", "status", "priority"],
        "unique": ["ticket_id"],
        "accepted_values": {
            "status": ["open", "in-progress", "resolved"],
            "priority": ["low", "medium", "high", "critical"],
        },
        "custom": [
            ("cost_non_negative", "cost < 0"),
            ("resolved_date_after_reported", "resolved_date IS NOT NULL AND resolved_date < reported_date"),
        ],
    },

    ("spa_event", "venues"): {
        "not_null": ["venue_id", "property_id", "venue_name", "venue_type", "max_capacity"],
        "unique": ["venue_id"],
        "accepted_values": {"venue_type": ["Ballroom", "Meeting Room", "Outdoor"]},
        "custom": [("max_capacity_positive", "max_capacity <= 0")],
    },
    ("spa_event", "spa_bookings"): {
        "not_null": ["spa_booking_id", "property_id", "customer_type", "service_name", "status"],
        "unique": ["spa_booking_id"],
        "accepted_values": {
            "customer_type": ["inhouse", "walk-in"],
            "status": ["confirmed", "cancelled", "completed"],
            "duration_minutes": [45, 60, 90, 120],
        },
        "custom": [
            ("service_date_not_before_booking_date", "service_date < booking_date"),
        ],
    },
    ("spa_event", "event_bookings"): {
        "not_null": ["event_id", "property_id", "venue_id", "event_type", "event_date", "status"],
        "unique": ["event_id"],
        "accepted_values": {
            "event_type": ["Wedding", "Corporate Meeting", "Conference", "Gala Dinner",
                            "Product Launch", "Training/Workshop"],
            "status": ["completed", "cancelled", "confirmed"],
        },
        "custom": [
            ("capacity_not_exceed_venue_max",
             "subselect.capacity_booked > (SELECT max_capacity FROM spa_event.venues v WHERE v.venue_id = subselect.venue_id)"),
            ("no_duplicate_venue_per_day",
             "(subselect.venue_id, subselect.event_date) IN (SELECT venue_id, event_date FROM spa_event.event_bookings "
             "GROUP BY venue_id, event_date HAVING COUNT(*) > 1)"),
        ],
    },

    ("hr_finance", "staff_shifts"): {
        "not_null": ["shift_id", "employee_id", "date", "shift_type", "status"],
        "unique": ["shift_id"],
        "accepted_values": {
            "shift_type": ["Morning", "Afternoon", "Night"],
            "status": ["present", "late", "absent", "leave"],
        },
        # Rule "clock_out > clock_in" DIHAPUS dari suite -- clock_in/clock_out bertipe
        # Postgres `time` (bukan timestamp), tanpa komponen tanggal. Shift Night (23:00-07:00)
        # DAN lembur di shift Afternoon yang berlanjut lewat tengah malam (ditemukan: 31.044
        # baris, clock_in ~15:00 & clock_out ~00:xx-02:xx) sama-sama membuat clock_out < clock_in
        # secara sah. Tanpa komponen tanggal, tidak ada cara membedakan "durasi negatif yang
        # salah" dari "shift yang sah melewati tengah malam" lewat SQL biasa -- rule ini
        # secara fundamental tidak bisa divalidasi dengan skema yang ada. Dicatat sebagai
        # keterbatasan nyata di report.md, bukan disembunyikan atau dipaksakan dengan heuristik
        # yang rapuh (percobaan pertama: exclude Night saja -> masih 31.044 false-positive dari
        # Afternoon; keduanya diverifikasi legitimate lewat sampling data, bukan data kotor).
        "custom": [],
    },
    ("hr_finance", "employee_performance"): {
        "not_null": ["review_id", "employee_id", "review_period", "score"],
        "unique": ["review_id"],
        "accepted_values": {},
        "custom": [("score_in_valid_range", "score < 1.0 OR score > 5.0")],
    },
    ("hr_finance", "payroll"): {
        "not_null": ["payroll_id", "employee_id", "period", "base_salary", "net_salary"],
        "unique": ["payroll_id"],
        "accepted_values": {},
        "custom": [
            ("base_salary_positive", "base_salary <= 0"),
            ("net_salary_matches_formula",
             "net_salary != base_salary + service_charge + overtime_pay + thr - deduction"),
        ],
    },
    ("hr_finance", "financial_summary"): {
        "not_null": ["property_id", "period", "department", "departmental_revenue", "departmental_expense"],
        "unique": [],
        "accepted_values": {"department": ["Room", "F&B", "Spa&Event", "Overall", "Corporate Overhead"]},
        "custom": [
            # Implementasi live mengisi gop/undistributed_expense dengan 0 (bukan NULL) di
            # baris non-Overall -- Metadata.md menyebut "hanya terisi di baris Overall" yang
            # sekilas tersirat NULL di baris lain, ternyata bukan. Rule pertama (cek IS NOT
            # NULL) -> 576 false-positive dari 756 baris.
            # Percobaan kedua (cek != 0, tanpa kecuali) -> 36 "gagal", ternyata SEMUA 36 baris
            # `Corporate Overhead` (P06, kantor pusat) -- department ini menurut Metadata.md
            # "hanya biaya, tanpa revenue", dan memang secara konsisten (36/36) punya `gop`
            # terisi (selalu negatif, cost-only). Bukan baris ringkasan seperti 'Overall', tapi
            # tetap sah punya P&L sendiri. Dikoreksi: kecualikan 'Corporate Overhead' juga.
            ("gop_zero_except_overall_and_corporate_overhead",
             "department NOT IN ('Overall', 'Corporate Overhead') AND (gop != 0 OR undistributed_expense != 0)"),
        ],
    },
}
