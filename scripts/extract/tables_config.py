"""
Konfigurasi 23 tabel production untuk Milestone 2.1 (ekstraksi ke raw_production).

cursor_strategy menentukan cara mendeteksi baris baru (lihat decisions.md
"Strategi incremental" untuk kenapa bukan CDC):

  "pk"            -> tabel punya primary key kolom tunggal berformat string
                      zero-padded (mis. BK0000001) -- urut leksikografis =
                      urut numerik, dipakai langsung sebagai cursor.
  "date"          -> tabel tidak punya PK kolom tunggal (composite key atau
                      tanpa PK sama sekali, dicek langsung ke
                      information_schema saat breakdown) tapi punya kolom
                      tanggal/periode yang bisa diurutkan -- dipakai sebagai
                      cursor. Catatan: baris dengan nilai cursor yang sama
                      persis (mis. banyak baris di tanggal yang sama) bisa
                      ter-proses ulang di run berikutnya (WHERE > bukan >=
                      pada boundary) -- diterima sebagai batasan, load ke
                      BigQuery pakai WRITE_TRUNCATE per keperluan re-sync,
                      bukan WRITE_APPEND, supaya duplikasi tidak terakumulasi.
  "full_refresh"  -> tabel referensi kecil atau snapshot yang secara desain
                      selalu representasi lengkap saat ini (bukan log
                      historis) -- disinkron ulang penuh tiap run, tidak ada
                      cursor sama sekali.

Sumber PK: dicek langsung ke information_schema.table_constraints saat
breakdown Milestone 2.1 (bukan diasumsikan dari docs/01-architecture/Metadata.md
-- 8 dari 23 tabel ternyata composite key atau tanpa PK sama sekali,
tidak sesuai asumsi awal "1 kolom PK per tabel").
"""

TABLES = [
    # schema, table, cursor_column, cursor_strategy
    ("corporate_master", "properties", None, "full_refresh"),  # 6 baris, referensi
    ("corporate_master", "employees", "employee_id", "pk"),
    ("corporate_master", "guests", "guest_id", "pk"),
    ("corporate_master", "role_permissions", None, "full_refresh"),  # composite PK, 77 baris, matriks RBAC selalu lengkap

    ("reservation_revenue", "bookings", "booking_id", "pk"),
    ("reservation_revenue", "daily_occupancy", "date", "date"),  # composite PK (property_id, room_type, date)
    ("reservation_revenue", "pricing_history", "date", "date"),  # composite PK (property_id, room_type, date)

    ("fnb_operations", "fnb_outlets", "outlet_id", "pk"),
    ("fnb_operations", "recipe_bom", None, "full_refresh"),  # composite PK, 120 baris, referensi resep
    ("fnb_operations", "ingredient_price_history", "date", "date"),  # composite PK (ingredient_id, date)
    ("fnb_operations", "fnb_transactions", "transaction_datetime", "date"),  # TIDAK ADA PK sama sekali di tabel ini
    ("fnb_operations", "fnb_waste_log", "waste_id", "pk"),
    ("fnb_operations", "fnb_inventory", None, "full_refresh"),  # composite PK, snapshot stok saat ini (Metadata.md: "snapshot selalu terisi")

    ("facility_maintenance", "rooms", "room_id", "pk"),
    ("facility_maintenance", "housekeeping_log", "log_id", "pk"),
    ("facility_maintenance", "maintenance_tickets", "ticket_id", "pk"),

    ("spa_event", "venues", "venue_id", "pk"),
    ("spa_event", "spa_bookings", "spa_booking_id", "pk"),
    ("spa_event", "event_bookings", "event_id", "pk"),

    ("hr_finance", "staff_shifts", "shift_id", "pk"),
    ("hr_finance", "employee_performance", "review_id", "pk"),
    ("hr_finance", "payroll", "payroll_id", "pk"),
    ("hr_finance", "financial_summary", "period", "date"),  # composite PK (property_id, period, department)
]

assert len(TABLES) == 23, f"expected 23 tables, got {len(TABLES)}"
