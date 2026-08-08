"""Shared BigQuery client helper for Milestone 2.1 extraction scripts."""
import os

from google.cloud import bigquery

import sys
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "monitoring"))
from db import _load_env  # noqa: E402

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def get_client():
    env = _load_env(os.path.join(REPO_ROOT, ".env"))
    creds_path = env["GOOGLE_APPLICATION_CREDENTIALS"]
    if not os.path.isabs(creds_path):
        creds_path = os.path.join(REPO_ROOT, creds_path)
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = creds_path
    return bigquery.Client(project=env["BIGQUERY_PROJECT_ID"]), env["BIGQUERY_DATASET"]
