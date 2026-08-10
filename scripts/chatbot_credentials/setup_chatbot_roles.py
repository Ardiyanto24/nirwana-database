"""Milestone 4.3 -- creates/rotates the AI Chatbot read-only Postgres roles in
the serving project and verifies isolation before writing connection strings
to .env. Manual-only (like scripts/data_analyst_credentials/setup_analyst_roles.py),
not part of any scheduled workflow.

Each role config (imported from role_config_<domain>.py, added one per
checkpoint) declares: role name, target env var, GRANT_TARGETS (chatbot_views
view names, hand-enumerated from scripts/chatbot_views/views_<domain>.sql --
Keputusan #4, no whitelist file to derive from since Milestone 4.4/API
doesn't exist yet), and allow/deny checks for verify_role_isolation.

All GRANT_TARGETS are chatbot_views.<view> only (Keputusan #3) -- no
owner-routing needed, unlike M3.5's apply_grants: every chatbot_views view is
owned by the same admin role (verified Fase 0), so a single admin_conn
handles both schema USAGE and object SELECT grants.

Usage:
  python setup_chatbot_roles.py --role reservation_chatbot_reader
  python setup_chatbot_roles.py --all
"""
import argparse
import secrets
import sys

from connections import (
    build_role_connection_string,
    get_serving_connection,
    write_env_var,
)
from verify_role_isolation import verify_role_isolation

ROLE_CONFIGS = []
# Populated by importing role_config_<domain> modules as they're added, one
# per M4.3 checkpoint -- see decisions.md task breakdown. Each checkpoint's
# role_config module is appended here once written (mirrors M3.5's pattern
# of a growing static import list, kept as a single append point instead so
# each checkpoint's diff only touches this list + the new config file).

try:
    from role_config_reservation import ROLE_CONFIG as RESERVATION_CONFIG
    ROLE_CONFIGS.append(RESERVATION_CONFIG)
except ImportError:
    pass
try:
    from role_config_fnb import ROLE_CONFIG as FNB_CONFIG
    ROLE_CONFIGS.append(FNB_CONFIG)
except ImportError:
    pass
try:
    from role_config_facility import ROLE_CONFIG as FACILITY_CONFIG
    ROLE_CONFIGS.append(FACILITY_CONFIG)
except ImportError:
    pass
try:
    from role_config_spa_event import ROLE_CONFIG as SPA_EVENT_CONFIG
    ROLE_CONFIGS.append(SPA_EVENT_CONFIG)
except ImportError:
    pass
try:
    from role_config_hr import ROLE_CONFIG as HR_CONFIG
    ROLE_CONFIGS.append(HR_CONFIG)
except ImportError:
    pass
try:
    from role_config_financial import ROLE_CONFIG as FINANCIAL_CONFIG
    ROLE_CONFIGS.append(FINANCIAL_CONFIG)
except ImportError:
    pass
try:
    from role_config_properties_ref import ROLE_CONFIG as PROPERTIES_REF_CONFIG
    ROLE_CONFIGS.append(PROPERTIES_REF_CONFIG)
except ImportError:
    pass
try:
    from role_config_employees_directory import ROLE_CONFIG as EMPLOYEES_DIRECTORY_CONFIG
    ROLE_CONFIGS.append(EMPLOYEES_DIRECTORY_CONFIG)
except ImportError:
    pass
try:
    from role_config_guests_pii import ROLE_CONFIG as GUESTS_PII_CONFIG
    ROLE_CONFIGS.append(GUESTS_PII_CONFIG)
except ImportError:
    pass
try:
    from role_config_guests_profile import ROLE_CONFIG as GUESTS_PROFILE_CONFIG
    ROLE_CONFIGS.append(GUESTS_PROFILE_CONFIG)
except ImportError:
    pass


def create_or_rotate_role(admin_conn, role, password):
    with admin_conn.cursor() as cur:
        cur.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (role,))
        exists = cur.fetchone() is not None
        if exists:
            cur.execute(f"ALTER ROLE {role} WITH LOGIN PASSWORD %s", (password,))
            print(f"  Role {role} already existed -- password rotated.")
        else:
            cur.execute(
                f"CREATE ROLE {role} WITH LOGIN PASSWORD %s NOSUPERUSER NOCREATEDB NOCREATEROLE",
                (password,),
            )
            print(f"  Role {role} created.")


def apply_grants(admin_conn, role, grant_targets):
    """All grant_targets are chatbot_views.<view> (Keputusan #3) -- single
    admin_conn for schema USAGE + object SELECT, no owner-routing needed
    (every chatbot_views view is owned by the admin role, verified Fase 0)."""
    with admin_conn.cursor() as cur:
        cur.execute(f"GRANT USAGE ON SCHEMA chatbot_views TO {role}")
        for target in grant_targets:
            schema, obj = target.split(".", 1)
            if schema != "chatbot_views":
                raise ValueError(
                    f"Unexpected grant target schema '{schema}' for {target} -- "
                    f"Keputusan #3 forbids grants outside chatbot_views."
                )
            cur.execute(f"GRANT SELECT ON {schema}.{obj} TO {role}")
    print(f"  {len(grant_targets)} view(s) granted in schema chatbot_views")


def setup_role(admin_conn, config):
    role = config["role"]
    print(f"--- {role} ---")
    password = secrets.token_urlsafe(24)

    create_or_rotate_role(admin_conn, role, password)
    apply_grants(admin_conn, role, config["grant_targets"])

    ok = verify_role_isolation(
        role,
        password,
        config["allow_checks"],
        config["deny_checks"],
        write_check_sql=config.get("write_check_sql"),
    )

    if not ok:
        print(f"  Isolation verification FAILED for {role} -- .env NOT written.")
        return False

    write_env_var(config["env_var"], build_role_connection_string(role, password))
    print(f"  {config['env_var']} written to .env.")
    return True


def main():
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--role", help="Set up a single role by name")
    group.add_argument("--all", action="store_true", help="Set up all configured roles")
    args = parser.parse_args()

    if not ROLE_CONFIGS:
        print("No role configs registered yet -- import role_config_<domain> modules first.")
        sys.exit(1)

    configs = ROLE_CONFIGS if args.all else [c for c in ROLE_CONFIGS if c["role"] == args.role]
    if not configs:
        print(f"No config found for role '{args.role}'.")
        sys.exit(1)

    admin_conn = get_serving_connection(readonly=False)
    admin_conn.autocommit = True
    try:
        failures = [c["role"] for c in configs if not setup_role(admin_conn, c)]
    finally:
        admin_conn.close()

    if failures:
        print(f"\nFAILED: {failures}")
        sys.exit(1)
    print(f"\n{len(configs)} role(s) set up and verified successfully.")


if __name__ == "__main__":
    main()
