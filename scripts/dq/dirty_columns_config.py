"""
Kolom dirty-by-design yang dipantau proporsinya (Milestone 1.3, Task 4).

Sumber: docs/04-monitoring/baseline-inventaris-produksi.md (kolom kotor/nullable yang sah,
terverifikasi live di Milestone 1.1). `bootstrap_expected_pct` adalah proporsi yang
terverifikasi live saat itu -- dipakai sebagai titik referensi tunggal SEBELUM histori
rolling (monitoring.dirty_proportion_snapshot) terkumpul minimal 3 titik. Begitu histori
cukup, baseline mean/stddev dari histori riil yang dipakai, bukan angka bootstrap ini lagi.
"""

DIRTY_COLUMNS = [
    # (schema, table, column, dirty_predicate_sql, bootstrap_expected_pct, description)
    ("corporate_master", "guests", "email",
     "email IS NULL OR email = ''", 4.0,
     "walk-in tidak isi form lengkap"),
    ("corporate_master", "guests", "phone",
     "phone IS NULL OR phone = ''", 3.0,
     "walk-in tidak isi form lengkap"),
    ("corporate_master", "employees", "role_title",
     "role_title IS NULL OR role_title = ''", 2.0,
     "belum diisi HR admin"),
    ("corporate_master", "employees", "department",
     "department NOT IN ('Housekeeping','F&B','Revenue','Spa&Event','Facility','HR','Finance','Corporate')",
     2.65,  # 20/755 baris non-kanonik, terverifikasi live saat Milestone 1.1 (19 variasi penulisan)
     "19 variasi penulisan untuk 8 departemen sebenarnya"),
    ("fnb_operations", "fnb_transactions", "guest_id",
     "guest_id IS NULL OR guest_id = ''", 31.0,
     "walk-in anonim (bermakna, bukan data hilang)"),
    ("spa_event", "spa_bookings", "guest_id",
     "guest_id IS NULL OR guest_id = ''", 21.0,
     "walk-in anonim (bermakna, bukan data hilang)"),
    ("facility_maintenance", "maintenance_tickets", "room_id",
     "room_id IS NULL OR room_id = ''", 28.0,
     "kerusakan di fasilitas umum, bukan kamar"),
    ("facility_maintenance", "maintenance_tickets", "parts_replaced",
     "parts_replaced IS NULL OR parts_replaced = ''", 52.0,
     "tidak ganti part saat perbaikan"),
]
