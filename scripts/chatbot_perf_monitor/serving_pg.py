"""
Milestone 6.5 -- scoped-credential read connections (distinct from db.py's
admin write connection to production monitoring.*).

get_perf_reader_connection(): serving project, via chatbot_perf_reader
(pg_monitor + chatbot_views SELECT) -- pg_stat_statements/pg_stat_activity/
chatbot_views reads.

get_audit_reader_connection(): production Supabase, via chatbot_audit_reader
(SELECT-only monitoring.chatbot_query_log).
"""
import os

import psycopg2

from db import _load_env

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def get_perf_reader_connection(readonly=True):
    env = _load_env(os.path.join(REPO_ROOT, ".env"))
    conn = psycopg2.connect(env["CHATBOT_PERF_READER_DB_URL"])
    if readonly:
        conn.set_session(readonly=True, autocommit=True)
    return conn


def get_audit_reader_connection(readonly=True):
    env = _load_env(os.path.join(REPO_ROOT, ".env"))
    conn = psycopg2.connect(env["CHATBOT_AUDIT_READER_DB_URL"])
    if readonly:
        conn.set_session(readonly=True, autocommit=True)
    return conn
