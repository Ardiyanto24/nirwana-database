"""
Milestone 4.5 -- role isolation verifier for chatbot_audit_writer.

Copy of scripts/chatbot_credentials/verify_role_isolation.py (itself copied
from M3.5's version, project convention since M2.1) -- including the
Supavisor-pooler warmup-retry logic, since SUPABASE_DB_URL turned out to ALSO
be a pooler URL in this repo's actual .env (not the direct connection
connections.py originally assumed -- see connections.py docstring), so the
same cache-staleness finding from M3.5 applies here too.

Shaped differently from the M4.3/M4.4 version's allow/deny/write_check_sql
split, though: those roles are read-only (deny_checks covers reads,
write_check_sql proves NO write ability at all). chatbot_audit_writer is the
opposite -- its one legitimate ability IS a write (INSERT), so INSERT is an
allow_check and SELECT/UPDATE/DELETE are all deny_checks -- no separate
write_check_sql param.
"""
import time

import psycopg2

from connections import build_role_connection_string

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
                pass  # INSERT has no result set to fetch
            return conn, cur
        except (psycopg2.OperationalError, psycopg2.errors.InsufficientPrivilege) as e:
            last_error = e
            if attempt < _WARMUP_MAX_ATTEMPTS:
                print(f"  (pooler cache not warm yet, attempt {attempt}/{_WARMUP_MAX_ATTEMPTS}, retrying in {_WARMUP_DELAY_SECONDS}s: {e})")
                time.sleep(_WARMUP_DELAY_SECONDS)
    raise last_error


def verify_role_isolation(role, password, allow_checks, deny_checks):
    """
    allow_checks: list of (label, sql) expected to succeed. The first
        allow_check also doubles as the pooler warmup probe.
    deny_checks: list of (label, sql) expected to fail with InsufficientPrivilege.

    Returns True if every check behaved as expected; prints an [OK]/[FAIL]
    table (never prints the password).
    """
    conn_str = build_role_connection_string(role, password)
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
