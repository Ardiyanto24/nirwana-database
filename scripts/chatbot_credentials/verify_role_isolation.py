"""
Milestone 4.3 -- reusable Postgres role isolation verifier, copied (not
imported) from scripts/data_analyst_credentials/verify_role_isolation.py
(M3.5) -- project convention since M2.1.

No RLS/row-level checks here -- Milestone 4.3's isolation is table/schema
level only (see decisions.md Keputusan #1); property-level filtering is
Milestone 4.4's API/query-layer responsibility.
"""
import time

import psycopg2

from connections import build_role_connection_string

# Same Supavisor pooler cache staleness finding as M3.5 Checkpoint 2: a
# just-issued CREATE ROLE / ALTER ROLE PASSWORD / GRANT is not picked up by
# the pooler immediately -- connecting right after setup can fail with stale
# auth or a stale privilege snapshot. Retrying the connect+warm-up query is
# the fix (same constants/behavior as M3.5's copy).
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
        (used for cross-domain reads AND for base-table mart_aggregated/
        mart_cleaned bypass checks -- Keputusan #3/#8, stricter than M3.5:
        every role here is denied ALL base-table access, not just some).
    write_check_sql: optional single SQL statement (e.g. INSERT) expected to
        fail with InsufficientPrivilege, proving the role is read-only.

    Returns True if every check behaved as expected; prints an [OK]/[FAIL]
    table (never prints the password).
    """
    conn_str = build_role_connection_string(role, password)
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
