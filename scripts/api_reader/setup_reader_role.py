"""
Milestone 1.6 -- one-time (re-runnable) setup for the public API's Postgres role.

Creates/rotates `monitoring_api_reader` (LOGIN, random password, no superuser/
createdb/createrole), applies scripts/api_reader/grants.sql, verifies isolation
(cannot write, cannot read outside the whitelist), then writes the resulting
connection string to api/.env as API_DB_URL -- never printed in full to stdout.

Manual-only, like scripts/schema_drift/baseline_columns.py -- not part of the
scheduled GitHub Actions workflow.
"""
import os
import secrets
import sys

import psycopg2

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "monitoring"))
from db import _load_env  # noqa: E402

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ROLE = "monitoring_api_reader"


def main():
    env = _load_env(os.path.join(REPO_ROOT, ".env"))
    admin_conn = psycopg2.connect(env["SUPABASE_DB_URL"])
    admin_conn.autocommit = True
    password = secrets.token_urlsafe(24)

    with admin_conn.cursor() as cur:
        cur.execute(
            "SELECT 1 FROM pg_roles WHERE rolname = %s", (ROLE,)
        )
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
    admin_conn.close()
    print("Grants applied.")

    from urllib.parse import urlparse

    parsed = urlparse(env["SUPABASE_DB_URL"])
    # Supabase's pooler (Supavisor) is multi-tenant: the login username must carry
    # the project ref as a suffix (<role>.<project_ref>), same pattern as the
    # existing SUPABASE_DB_URL's "postgres.<project_ref>" username.
    project_ref = parsed.username.split(".", 1)[1]
    pooler_user = f"{ROLE}.{project_ref}"
    reader_url = (
        f"postgresql://{pooler_user}:{password}@{parsed.hostname}:{parsed.port or 5432}"
        f"{parsed.path}"
    )

    # --- Verification: reader can read whitelist, cannot write, cannot read outside whitelist ---
    reader_conn = psycopg2.connect(reader_url)
    reader_conn.autocommit = True
    checks = []
    with reader_conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM monitoring.current_status")
        checks.append(("SELECT monitoring.current_status", True, cur.fetchone()[0] >= 0))

        cur.execute("SELECT COUNT(*) FROM corporate_master.properties")
        checks.append(("SELECT corporate_master.properties (whitelisted)", True, cur.fetchone()[0] == 6))

        try:
            cur.execute("SELECT COUNT(*) FROM corporate_master.guests")
            checks.append(("SELECT corporate_master.guests (NOT whitelisted)", False, False))
        except psycopg2.errors.InsufficientPrivilege:
            reader_conn.rollback()
            checks.append(("SELECT corporate_master.guests (NOT whitelisted)", False, True))

        try:
            cur.execute("INSERT INTO monitoring.alerts DEFAULT VALUES")
            checks.append(("INSERT monitoring.alerts", False, False))
        except psycopg2.errors.InsufficientPrivilege:
            reader_conn.rollback()
            checks.append(("INSERT monitoring.alerts", False, True))
    reader_conn.close()

    print("\nVerification:")
    all_ok = True
    for label, should_succeed, ok in checks:
        status = "OK" if ok else "FAIL"
        if not ok:
            all_ok = False
        expect = "should succeed" if should_succeed else "should be denied"
        print(f"  [{status}] {label} ({expect})")

    if not all_ok:
        print("\nOne or more checks failed -- inspect grants.sql before using this role in the API.")
        sys.exit(1)

    api_dir = os.path.join(REPO_ROOT, "api")
    os.makedirs(api_dir, exist_ok=True)
    env_path = os.path.join(api_dir, ".env")
    lines = []
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            lines = [l for l in f.read().splitlines() if not l.startswith("API_DB_URL=")]
    lines.append(f"API_DB_URL={reader_url}")
    with open(env_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print(f"\nAll checks passed. API_DB_URL written to {env_path} (not printed here).")


if __name__ == "__main__":
    main()
