"""Shared BigQuery client helper for Milestone 6.3 warehouse-monitor-reader scripts."""
import os

from google.cloud import bigquery

from db import _load_env

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PROJECT_ID = "nirwana-database-elt"


def get_client():
    env = _load_env(os.path.join(REPO_ROOT, ".env"))
    keyfile_env = env["WAREHOUSE_MONITOR_READER_CREDENTIALS"]
    keyfile = keyfile_env if os.path.isabs(keyfile_env) else os.path.join(REPO_ROOT, keyfile_env)
    return bigquery.Client.from_service_account_json(keyfile, project=PROJECT_ID)
