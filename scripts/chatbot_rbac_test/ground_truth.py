"""
Milestone 4.6 -- ground truth loader for RBAC matrix testing.

Queries mart_cleaned.role_permissions directly (77 rows) rather than
hardcoding the expectation table from
docs/09-serving-ai-chatbot/rancangan-pengujian-rbac-chatbot.md -- if the
database and the design doc ever drift, this catches it against the
database (the actual thing being tested), not a copy of the doc.
"""
from connections import get_serving_connection

# Fixed column/row order, matches the design doc exactly.
DOMAINS = [
    "reservation",
    "fnb",
    "facility",
    "spa_event",
    "hr",
    "financial",
    "properties_ref",
    "employees_directory",
    "guests_pii",
    "guests_profile",
]

ROLES = [
    "CEO",
    "Corporate Finance Director",
    "Corporate HR Director",
    "Corporate Operations Director",
    "Corporate Revenue Director",
    "General Manager",
    "Revenue Manager",
    "F&B Manager",
    "Finance Manager",
    "Housekeeping Manager",
    "HR Manager",
    "Maintenance Manager",
    "Spa & Event Manager",
    "Front Office Staff",
    "F&B Staff",
    "Finance Staff",
    "Housekeeping Staff",
    "HR Staff",
    "Maintenance Staff",
    "Spa & Event Staff",
]


def load_role_permissions():
    """Returns {(role_title, data_domain): access_scope} -- 77 entries."""
    conn = get_serving_connection(readonly=True)
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT role_title, data_domain, access_scope FROM mart_cleaned.role_permissions")
            return {(role, domain): scope for role, domain, scope in cur.fetchall()}
    finally:
        conn.close()


def pick_test_employee_ids():
    """Returns (employee_id_p01, employee_id_p02) -- any 2 active employees at
    P01/P02, independent of role_title (decisions.md M4.6 Keputusan #3:
    role_title and employee_id are independent claims to this API)."""
    conn = get_serving_connection(readonly=True)
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT property_id, min(employee_id) FROM mart_cleaned.employees "
                "WHERE status = 'active' AND property_id IN ('P01', 'P02') "
                "GROUP BY property_id"
            )
            by_property = dict(cur.fetchall())
            return by_property["P01"], by_property["P02"]
    finally:
        conn.close()
