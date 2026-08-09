"""
Milestone 3.5 -- reusable Postgres role isolation verifier, built because
this milestone creates 7 roles (6 domain + Property/GM) and the existing
per-script inline verification pattern (setup_reader_role.py,
setup_extract_role.py, both setup_writer_role.py) would mean copy-pasting the
same connect/allow/deny/write-check logic 7 times. Generalizes that pattern
the same way scripts/bigquery_common/verify_dataset_isolation.py generalized
BigQuery isolation checks in Milestone 2.5 -- same motivation, no Postgres
equivalent existed before this file.

No RLS/row-level checks here -- Milestone 3.5's isolation is table/schema
level only (see decisions.md Keputusan #1); property-level filtering is
Milestone 3.4's API/query-layer responsibility.
"""
import time

import psycopg2

from connections import build_role_connection_string

# Found empirically in M3.5 Checkpoint 2: Supabase's Supavisor pooler caches
# role credentials/grants and does not pick up a just-issued CREATE ROLE /
# ALTER ROLE PASSWORD / GRANT immediately -- connecting as the new role right
# after setup can fail with "password authentication failed" (stale cached
# password) or connect successfully but see "permission denied for schema"
# on a query that WAS correctly granted (stale cached privilege snapshot,
# confirmed via pg_class.relacl/pg_namespace.nspacl showing the grant present
# in the catalog while the pooled session still denies it). No existing
# setup_*_role.py script hit this before -- possibly because they have more
# I/O between role creation and verification, giving the pooler cache time to
# refresh incidentally. Retrying the connect+warm-up query below is the fix.
_WARMUP_MAX_ATTEMPTS = 6
_WARMUP_DELAY_SECONDS = 5


def _connect_with_warmup(conn_str, warmup_sql):
    last_error = None
    for attempt in range(1, _WARMUP_MAX_ATTEMPTS + 1):
        try:
            conn = psycopg2.connect(conn_str)
            conn.autocommit = True
            cur = conn.cursor()
            cur.execute(warmup_sql)
            cur.fetchall()
            return conn, cur
        except (psycopg2.OperationalError, psycopg2.errors.InsufficientPrivilege) as e:
            last_error = e
            if attempt < _WARMUP_MAX_ATTEMPTS:
                print(f"  (pooler cache not warm yet, attempt {attempt}/{_WARMUP_MAX_ATTEMPTS}, retrying in {_WARMUP_DELAY_SECONDS}s: {e})")
                time.sleep(_WARMUP_DELAY_SECONDS)
    raise last_error


def verify_role_isolation(role, password, allow_checks, deny_checks, write_check_sql=None):
    """
    allow_checks: list of (label, sql) expected to succeed.
    deny_checks: list of (label, sql) expected to fail with InsufficientPrivilege
        (used both for cross-domain reads and for base-table `mart_aggregated`
        bypass checks -- Keputusan #8).
    write_check_sql: optional single SQL statement (e.g. INSERT) expected to
        fail with InsufficientPrivilege, proving the role is read-only.

    Returns True if every check behaved as expected; prints an [OK]/[FAIL]
    table (never prints the password). Exits nonzero via caller if False.
    """
    conn_str = build_role_connection_string(role, password)
    # Warm up with the first allow-check itself (a real, already-granted
    # query) rather than a throwaway SELECT 1 -- proves the pooler cache is
    # actually serving the fresh grants, not just that auth succeeded.
    warmup_sql = allow_checks[0][1] if allow_checks else "SELECT 1"
    conn, cur = _connect_with_warmup(conn_str, warmup_sql)

    results = []

    for label, sql in allow_checks:
        try:
            cur.execute(sql)
            cur.fetchall()
            results.append((f"ALLOW: {label}", True))
        except Exception as e:
            conn.rollback()
            results.append((f"ALLOW: {label} -- unexpected error: {e}", False))

    for label, sql in deny_checks:
        try:
            cur.execute(sql)
            cur.fetchall()
            results.append((f"DENY: {label} -- unexpectedly SUCCEEDED", False))
        except psycopg2.errors.InsufficientPrivilege:
            conn.rollback()
            results.append((f"DENY: {label}", True))
        except Exception as e:
            conn.rollback()
            results.append((f"DENY: {label} -- wrong error type: {e}", False))

    if write_check_sql:
        try:
            cur.execute(write_check_sql)
            conn.rollback()
            results.append(("WRITE (read-only proof) -- unexpectedly SUCCEEDED", False))
        except psycopg2.errors.InsufficientPrivilege:
            conn.rollback()
            results.append(("WRITE (read-only proof)", True))
        except Exception as e:
            conn.rollback()
            results.append((f"WRITE (read-only proof) -- wrong error type: {e}", False))

    cur.close()
    conn.close()

    all_ok = True
    for label, ok in results:
        print(f"  [{'OK' if ok else 'FAIL'}] {label}")
        if not ok:
            all_ok = False

    return all_ok
