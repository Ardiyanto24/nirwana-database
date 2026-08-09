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

from connections import build_role_connection_string, get_serving_connection, write_env_var
from verify_role_isolation import verify_role_isolation

ROLE_CONFIGS = []
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
    schemas_granted = set()
    with admin_conn.cursor() as cur:
        for target in grant_targets:
            schema, obj = _grant_target_to_schema_object(target)
            if schema not in schemas_granted:
                cur.execute(f"GRANT USAGE ON SCHEMA {schema} TO {role}")
                schemas_granted.add(schema)
            cur.execute(f"GRANT SELECT ON {schema}.{obj} TO {role}")
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
