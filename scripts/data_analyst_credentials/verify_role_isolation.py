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
import psycopg2

from connections import build_role_connection_string


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
    conn = psycopg2.connect(conn_str)
    conn.autocommit = True
    cur = conn.cursor()

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
