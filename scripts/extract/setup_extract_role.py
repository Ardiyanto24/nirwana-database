"""
Milestone 2.1 -- one-time (re-runnable) setup for the extraction pipeline's
Postgres role.

Creates/rotates `extract_reader` (LOGIN, random password, no superuser/
createdb/createrole), applies scripts/extract/grants.sql (SELECT-only on the
23-table whitelist across 6 schemas), verifies isolation (cannot write,
cannot read outside the whitelist -- checked against monitoring.alerts, a
schema this role has no grant on at all), then writes the resulting
connection string to the repo-root .env as EXTRACT_DB_URL -- never printed
in full to stdout.

Manual-only, like scripts/api_reader/setup_reader_role.py -- not part of the
scheduled GitHub Actions workflow.
"""
import os
import secrets
import sys

import psycopg2

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "monitoring"))
from db import _load_env  # noqa: E402

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ROLE = "extract_reader"

# Kept in sync with grants.sql -- used only to verify grant count, not to grant anything itself.
EXPECTED_TABLE_COUNT = 23


def main():
    env = _load_env(os.path.join(REPO_ROOT, ".env"))
    admin_conn = psycopg2.connect(env["SUPABASE_DB_URL"])
    admin_conn.autocommit = True
    password = secrets.token_urlsafe(24)

    with admin_conn.cursor() as cur:
        cur.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (ROLE,))
        exists = cur.fetchone() is not None
        if exists:
            cur.execute(f"ALTER ROLE {ROLE} WITH LOGIN PASSWORD %s", (password,))
            print(f"Role {ROLE} already existed -- password rotated.")
        else:
            cur.execute(
                f"CREATE ROLE {ROLE} WITH LOGIN PASSWORD %s NOSUPERUSER NOCREATEDB NOCREATEROLE",
                (password,),
            )
            print(f"Role {ROLE} created.")

    grants_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "grants.sql")
    with open(grants_path, "r", encoding="utf-8") as f:
        grants_sql = f.read()
    with admin_conn.cursor() as cur:
        cur.execute(grants_sql)

    with admin_conn.cursor() as cur:
        cur.execute(
            """
            SELECT COUNT(*) FROM information_schema.role_table_grants
            WHERE grantee = %s AND privilege_type = 'SELECT'
            """,
            (ROLE,),
        )
        granted_count = cur.fetchone()[0]
    admin_conn.close()
    print(f"Grants applied. SELECT grants on {granted_count} tables (expected {EXPECTED_TABLE_COUNT}).")

    from urllib.parse import urlparse

    parsed = urlparse(env["SUPABASE_DB_URL"])
    # Supabase's pooler (Supavisor) is multi-tenant: the login username must carry
    # the project ref as a suffix (<role>.<project_ref>), same pattern as
    # SUPABASE_DB_URL / M1.6's monitoring_api_reader.
    project_ref = parsed.username.split(".", 1)[1]
    pooler_user = f"{ROLE}.{project_ref}"
    reader_url = (
        f"postgresql://{pooler_user}:{password}@{parsed.hostname}:{parsed.port or 5432}"
        f"{parsed.path}"
    )

    # --- Verification: can read whitelist, cannot write, cannot read outside whitelist ---
    reader_conn = psycopg2.connect(reader_url)
    reader_conn.autocommit = True
    checks = []
    with reader_conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM corporate_master.properties")
        checks.append(("SELECT corporate_master.properties (whitelisted)", True, cur.fetchone()[0] == 6))

        cur.execute("SELECT COUNT(*) FROM hr_finance.payroll")
        checks.append(("SELECT hr_finance.payroll (whitelisted)", True, cur.fetchone()[0] > 0))

        try:
            cur.execute("SELECT COUNT(*) FROM monitoring.alerts")
            checks.append(("SELECT monitoring.alerts (NOT whitelisted)", False, False))
        except psycopg2.errors.InsufficientPrivilege:
            reader_conn.rollback()
            checks.append(("SELECT monitoring.alerts (NOT whitelisted)", False, True))

        try:
            cur.execute("INSERT INTO corporate_master.properties DEFAULT VALUES")
            checks.append(("INSERT corporate_master.properties", False, False))
        except psycopg2.errors.InsufficientPrivilege:
            reader_conn.rollback()
            checks.append(("INSERT corporate_master.properties", False, True))
    reader_conn.close()

    print("\nVerification:")
    all_ok = True
    for label, should_succeed, ok in checks:
        status = "OK" if ok else "FAIL"
        if not ok:
            all_ok = False
        expect = "should succeed" if should_succeed else "should be denied"
        print(f"  [{status}] {label} ({expect})")

    if not all_ok or granted_count != EXPECTED_TABLE_COUNT:
        print("\nOne or more checks failed -- inspect grants.sql before using this role for extraction.")
        sys.exit(1)

    env_path = os.path.join(REPO_ROOT, ".env")
    lines = []
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            lines = [l for l in f.read().splitlines() if not l.startswith("EXTRACT_DB_URL=")]
    lines.append(f"EXTRACT_DB_URL={reader_url}")
    with open(env_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print(f"\nAll checks passed. EXTRACT_DB_URL written to {env_path} (not printed here).")


if __name__ == "__main__":
    main()
