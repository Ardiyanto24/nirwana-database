"""
Milestone 4.4 -- role config for chatbot_authz_reader. Not a data_domain
credential (beda dari 10 role M4.3) -- SELECT-only ke mart_cleaned.role_permissions
SAJA, dipakai murni internal oleh scripts/chatbot_api/ untuk keputusan
otorisasi per request (decisions.md M4.4 Keputusan #6). Hasil query tabel ini
tidak pernah diteruskan sebagai response endpoint API manapun.

GRANT_TARGETS di sini SENGAJA mart_cleaned (bukan chatbot_views) -- satu-satunya
pengecualian dari Keputusan #3 M4.3 ("GRANT hanya ke chatbot_views"), karena
role_permissions tidak punya (dan tidak seharusnya punya) view turunan di
chatbot_views sama sekali -- M4.1 Keputusan #7 menegaskan tabel ini tidak
pernah jadi bagian struktur akses chatbot yang bisa dijangkau.
"""

GRANT_TARGETS = [
    "mart_cleaned.role_permissions",
]

ROLE_CONFIG = {
    "role": "chatbot_authz_reader",
    "env_var": "CHATBOT_AUTHZ_READER_DB_URL",
    "grant_targets": GRANT_TARGETS,
    "allow_checks": [
        ("role_permissions (internal authz only)", "SELECT count(*) FROM mart_cleaned.role_permissions"),
    ],
    "deny_checks": [
        ("base table bypass (mart_aggregated direct)", "SELECT count(*) FROM mart_aggregated.dim_property"),
        ("chatbot_views (no data access at all)", "SELECT count(*) FROM chatbot_views.v_properties_ref"),
        ("cross-table: guests", "SELECT count(*) FROM mart_cleaned.guests"),
        ("cross-table: employees", "SELECT count(*) FROM mart_cleaned.employees"),
    ],
    "write_check_sql": "INSERT INTO mart_cleaned.role_permissions (role_title) VALUES ('should-fail')",
}
