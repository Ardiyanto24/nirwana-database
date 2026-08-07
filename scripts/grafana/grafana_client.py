"""Shared Grafana Cloud API client for Milestone 1.5 provisioning scripts."""
import json
import os
import sys
import urllib.request
import urllib.error

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "monitoring"))
from db import _load_env  # noqa: E402

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def get_config():
    env = _load_env(os.path.join(REPO_ROOT, ".env"))
    return {
        "base_url": env["GRAFANA_URL"].rstrip("/"),
        "token": env["GRAFANA_SERVICE_ACCOUNT_TOKEN"],
        "supabase_db_url": env["SUPABASE_DB_URL"],
    }


def api_request(method, path, body=None):
    cfg = get_config()
    url = cfg["base_url"] + path
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {cfg['token']}")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req) as resp:
            raw = resp.read()
            return resp.status, (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            parsed = raw.decode("utf-8", errors="replace")
        return e.code, parsed


def parse_supabase_url(db_url):
    """postgresql://user:password@host:port/dbname -> dict komponen."""
    from urllib.parse import urlparse, unquote

    parsed = urlparse(db_url)
    return {
        "user": unquote(parsed.username),
        "password": unquote(parsed.password),
        "host": parsed.hostname,
        "port": parsed.port or 5432,
        "database": parsed.path.lstrip("/"),
    }
