"""
Milestone 6.5 -- role isolation verifier, copy of scripts/chatbot_audit/
verify_role_isolation.py (itself copied from M3.5/M4.3, project convention
since M2.1), including the Supavisor-pooler warmup-retry logic.

Adapted for M6.5's dual-instance need: takes a pre-built connection string
(caller picks build_serving_role_connection_string or
build_production_role_connection_string from connections.py) instead of
hardcoding one instance like every prior single-instance chatbot_* folder.
"""
import time

import psycopg2

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
            try:
                cur.fetchall()
            except psycopg2.ProgrammingError:
                pass  # INSERT/no-result statements have nothing to fetch
            return conn, cur
        except (psycopg2.OperationalError, psycopg2.errors.InsufficientPrivilege) as e:
            last_error = e
            if attempt < _WARMUP_MAX_ATTEMPTS:
                print(f"  (pooler cache not warm yet, attempt {attempt}/{_WARMUP_MAX_ATTEMPTS}, retrying in {_WARMUP_DELAY_SECONDS}s: {e})")
                time.sleep(_WARMUP_DELAY_SECONDS)
    raise last_error


def verify_role_isolation(conn_str, allow_checks, deny_checks):
    """
    allow_checks: list of (label, sql) expected to succeed. The first
        allow_check also doubles as the pooler warmup probe.
    deny_checks: list of (label, sql) expected to fail with InsufficientPrivilege.

    Returns True if every check behaved as expected; prints an [OK]/[FAIL] table.
    """
    warmup_sql = allow_checks[0][1] if allow_checks else "SELECT 1"
    conn, cur = _connect_with_warmup(conn_str, warmup_sql)

    results = [(f"ALLOW: {allow_checks[0][0]}", True)] if allow_checks else []

    for label, sql in allow_checks[1:]:
        try:
            cur.execute(sql)
            try:
                cur.fetchall()
            except psycopg2.ProgrammingError:
                pass
            results.append((f"ALLOW: {label}", True))
        except Exception as e:
            conn.rollback()
            results.append((f"ALLOW: {label} -- unexpected error: {e}", False))

    for label, sql in deny_checks:
        try:
            cur.execute(sql)
            try:
                cur.fetchall()
            except psycopg2.ProgrammingError:
                pass
            results.append((f"DENY: {label} -- unexpectedly SUCCEEDED", False))
        except psycopg2.errors.InsufficientPrivilege:
            conn.rollback()
            results.append((f"DENY: {label}", True))
        except Exception as e:
            conn.rollback()
            results.append((f"DENY: {label} -- wrong error type: {e}", False))

    cur.close()
    conn.close()

    all_ok = True
    for label, ok in results:
        print(f"  [{'OK' if ok else 'FAIL'}] {label}")
        if not ok:
            all_ok = False

    return all_ok
