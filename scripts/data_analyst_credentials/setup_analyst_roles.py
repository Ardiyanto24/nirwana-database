"""
Milestone 3.5 -- creates/rotates the Data Analyst read-only Postgres roles in
the serving project and verifies isolation before writing connection strings
to .env. Manual-only (like scripts/api_reader/setup_reader_role.py), not part
of any scheduled workflow.

Each role config (imported from role_config_<domain>.py, added one per
checkpoint) declares: role name, target env var, GRANT targets (derived from
Milestone 3.4's whitelist_<domain>.py via grant_utils.derive_grant_targets),
and allow/deny checks for verify_role_isolation.

Usage:
  python setup_analyst_roles.py --role revenue_analyst_reader
  python setup_analyst_roles.py --all
"""
import argparse
import secrets
import sys

from connections import (
    build_role_connection_string,
    get_mart_cleaned_owner_connection,
    get_serving_connection,
    write_env_var,
)
from verify_role_isolation import verify_role_isolation

from role_config_revenue import ROLE_CONFIG as REVENUE_CONFIG
from role_config_fnb import ROLE_CONFIG as FNB_CONFIG
from role_config_facility import ROLE_CONFIG as FACILITY_CONFIG
from role_config_spa_event import ROLE_CONFIG as SPA_EVENT_CONFIG
from role_config_hr import ROLE_CONFIG as HR_CONFIG

ROLE_CONFIGS = [
    REVENUE_CONFIG,
    FNB_CONFIG,
    FACILITY_CONFIG,
    SPA_EVENT_CONFIG,
    HR_CONFIG,
]
# Populated by importing role_config_<domain> modules as they're added,
# one per M3.5 checkpoint -- see decisions.md task breakdown.


def _grant_target_to_schema_object(target):
    schema, obj = target.split(".", 1)
    return schema, obj


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
    """Routes each GRANT to the connection that actually owns the target.

    Found empirically in M3.5 Checkpoint 2: schema-level ownership and
    table-level ownership are separate in this project. Every schema here
    (analyst_views, mart_cleaned) was CREATEd via the admin connection, so
    `GRANT USAGE ON SCHEMA` always goes through admin_conn regardless of who
    owns the objects inside it. But the mart_cleaned *tables* are owned by
    reverse_etl_writer (created via that role's connection in sync.py's
    swap), so `GRANT SELECT` on those specific tables must go through
    connections.get_mart_cleaned_owner_connection() -- admin_conn silently
    no-ops (no error, no effect) on objects it doesn't own. analyst_views
    *views* ARE owned by admin_conn's role (created via
    scripts/data_analyst_views/apply_views.py, M3.2), so those object-level
    grants go through admin_conn too.

    mart_aggregated is deliberately NOT routable here -- Keputusan #8: analyst
    roles never get grants on that schema at all (views run with owner
    privilege, so GRANT SELECT on the view is always sufficient)."""
    object_owner_connections = {"analyst_views": admin_conn}
    schemas_granted = set()
    mart_cleaned_conn = None

    for target in grant_targets:
        schema, obj = _grant_target_to_schema_object(target)
        if schema == "mart_cleaned" and mart_cleaned_conn is None:
            mart_cleaned_conn = get_mart_cleaned_owner_connection()
            mart_cleaned_conn.autocommit = True
            object_owner_connections["mart_cleaned"] = mart_cleaned_conn
        if schema not in object_owner_connections:
            raise ValueError(
                f"No owner connection configured for schema '{schema}' -- "
                f"Keputusan #8 forbids analyst roles from being granted access to "
                f"mart_aggregated directly, and no other schema is expected here."
            )

        if schema not in schemas_granted:
            with admin_conn.cursor() as cur:
                cur.execute(f"GRANT USAGE ON SCHEMA {schema} TO {role}")
            schemas_granted.add(schema)

        with object_owner_connections[schema].cursor() as cur:
            cur.execute(f"GRANT SELECT ON {schema}.{obj} TO {role}")

    if mart_cleaned_conn:
        mart_cleaned_conn.close()

    print(f"  {len(grant_targets)} object(s) granted across schema(s): {sorted(schemas_granted)}")


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
