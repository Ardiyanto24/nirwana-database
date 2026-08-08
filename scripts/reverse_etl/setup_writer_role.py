"""
Milestone 2.4 Task 2 -- one-time (re-runnable) setup for the reverse ETL
job's Postgres role on the NEW serving project.

Creates/rotates `reverse_etl_writer` (LOGIN, random password, no superuser/
createdb/createrole), scoped to USAGE+CREATE on schema `mart_cleaned` only
(no access to `public`, no ability to CREATE SCHEMA/DATABASE) -- this is the
role sync.py connects as to CREATE/DROP/RENAME tables during the swap.
Verifies isolation (can create/drop tables in mart_cleaned, cannot touch
public schema, cannot create new schemas), then writes the resulting
connection string to the repo-root .env as REVERSE_ETL_WRITER_DB_URL.

Manual-only, same pattern as scripts/extract/setup_extract_role.py -- run
once against SERVING_DB_URL (which must be an admin/owner connection at this
point, e.g. the postgres user from the Supabase dashboard).

Usage: python scripts/reverse_etl/setup_writer_role.py
"""
import os
import secrets
import sys
from urllib.parse import urlparse

import psycopg2

from connections import _load_env

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ROLE = "reverse_etl_writer"
SCHEMA = "mart_cleaned"


def main():
    env = _load_env(os.path.join(REPO_ROOT, ".env"))
    admin_conn = psycopg2.connect(env["SERVING_DB_URL"])
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

        # Explicit deny on public (default PUBLIC grants vary by PG version --
        # don't rely on absence, revoke explicitly) + explicit scoped grant.
        cur.execute(f"REVOKE ALL ON SCHEMA public FROM {ROLE}")
        cur.execute(f"GRANT USAGE, CREATE ON SCHEMA {SCHEMA} TO {ROLE}")
    admin_conn.close()

    parsed = urlparse(env["SERVING_DB_URL"])
    # Same Supavisor pooler convention as EXTRACT_DB_URL: username carries
    # the project ref as <role>.<project_ref>.
    admin_user = parsed.username
    if "." in admin_user:
        project_ref = admin_user.split(".", 1)[1]
        pooler_user = f"{ROLE}.{project_ref}"
    else:
        pooler_user = ROLE
    writer_url = (
        f"postgresql://{pooler_user}:{password}@{parsed.hostname}:{parsed.port or 5432}"
        f"{parsed.path}"
    )

    # --- Verification ---
    writer_conn = psycopg2.connect(writer_url)
    writer_conn.autocommit = True
    checks = []
    with writer_conn.cursor() as cur:
        try:
            cur.execute(f"CREATE TABLE {SCHEMA}.__verify_writer (id int)")
            cur.execute(f"INSERT INTO {SCHEMA}.__verify_writer VALUES (1)")
            cur.execute(f"ALTER TABLE {SCHEMA}.__verify_writer RENAME TO __verify_writer_renamed")
            cur.execute(f"DROP TABLE {SCHEMA}.__verify_writer_renamed")
            checks.append((f"CREATE/RENAME/DROP TABLE {SCHEMA}.*", True, True))
        except psycopg2.Error as e:
            writer_conn.rollback()
            checks.append((f"CREATE/RENAME/DROP TABLE {SCHEMA}.*", True, False))
            print(f"  (unexpected error: {e})")

        try:
            cur.execute("CREATE TABLE public.__verify_writer (id int)")
            checks.append(("CREATE TABLE public.* (should be denied)", False, False))
            cur.execute("DROP TABLE public.__verify_writer")
        except psycopg2.errors.InsufficientPrivilege:
            writer_conn.rollback()
            checks.append(("CREATE TABLE public.* (should be denied)", False, True))

        try:
            cur.execute("CREATE SCHEMA __verify_new_schema")
            checks.append(("CREATE SCHEMA (should be denied)", False, False))
            cur.execute("DROP SCHEMA __verify_new_schema")
        except psycopg2.errors.InsufficientPrivilege:
            writer_conn.rollback()
            checks.append(("CREATE SCHEMA (should be denied)", False, True))
    writer_conn.close()

    print("\nVerification:")
    all_ok = True
    for label, should_succeed, ok in checks:
        status = "OK" if ok else "FAIL"
        if not ok:
            all_ok = False
        expect = "should succeed" if should_succeed else "should be denied"
        print(f"  [{status}] {label} ({expect})")

    if not all_ok:
        print("\nOne or more checks failed -- inspect role grants before using this role.")
        sys.exit(1)

    env_path = os.path.join(REPO_ROOT, ".env")
    lines = []
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            lines = [l for l in f.read().splitlines() if not l.startswith("REVERSE_ETL_WRITER_DB_URL=")]
    lines.append(f"REVERSE_ETL_WRITER_DB_URL={writer_url}")
    with open(env_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print(f"\nAll checks passed. REVERSE_ETL_WRITER_DB_URL written to {env_path} (not printed here).")


if __name__ == "__main__":
    main()
