"""
Milestone 6.2 -- baca status/durasi 1 run GitHub Actions, tulis ke monitoring.pipeline_run_log
untuk tiap titik (dari titik_config.py) yang match nama workflow run itu.

Dipanggil oleh .github/workflows/monitoring-warehouse-pipeline-log.yml (run_id dari
github.event.workflow_run.id), atau manual untuk uji coba:
    python snapshot_pipeline_run.py <run_id>

Autentikasi GitHub API (lihat decisions.md Keputusan #5):
    1. Env var GITHUB_TOKEN (otomatis tersedia di dalam run GitHub Actions)
    2. .env GITHUB_API_TOKEN (PAT manual, kalau didaftarkan)
    3. `gh auth token` (fallback lokal -- tidak perlu simpan token baru di .env
       kalau `gh` CLI di komputer ini sudah authenticated, seperti dipakai
       script/preseden lain di project ini yang memanggil `gh workflow run`/`gh repo create`)
"""
import argparse
import os
import subprocess
import sys
from datetime import datetime

import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from db import _load_env, get_connection
from titik_config import titik_for_workflow

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEFAULT_REPO = "Ardiyanto24/nirwana-database"


def _github_token():
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        return token
    env = _load_env(os.path.join(REPO_ROOT, ".env"))
    token = env.get("GITHUB_API_TOKEN")
    if token:
        return token
    result = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True, check=True)
    return result.stdout.strip()


def _github_repo():
    return os.environ.get("GITHUB_REPOSITORY", DEFAULT_REPO)


def _api_get(url, token):
    resp = requests.get(
        url,
        headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def _parse_ts(ts):
    return datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ")


def _duration_seconds(started_at, completed_at):
    return int((_parse_ts(completed_at) - _parse_ts(started_at)).total_seconds())


def _normalize_conclusion(conclusion):
    known = {"success", "failure", "cancelled", "skipped", "timed_out"}
    if conclusion in known:
        return conclusion
    # neutral/action_required/stale/None (step never reached) tidak masuk 5 status wajib
    # schema (monitoring.pipeline_run_log CHECK) -- perlakukan sebagai 'cancelled', dicatat
    # supaya tidak crash insert, bukan diam-diam dibuang.
    return "cancelled"


def fetch_run(repo, run_id, token):
    return _api_get(f"https://api.github.com/repos/{repo}/actions/runs/{run_id}", token)


def fetch_steps(repo, run_id, token):
    data = _api_get(f"https://api.github.com/repos/{repo}/actions/runs/{run_id}/jobs", token)
    steps = []
    for job in data.get("jobs", []):
        steps.extend(job.get("steps", []))
    return steps


def find_step(steps, substring):
    matches = [s for s in steps if substring in s["name"]]
    if len(matches) != 1:
        raise ValueError(
            f"Expected exactly 1 step matching {substring!r}, found {len(matches)}: "
            f"{[s['name'] for s in matches]}"
        )
    return matches[0]


def insert_row(conn, titik_id, titik_label, workflow_name, run_id, step_name,
                granularity, status, started_at, completed_at, trigger_event):
    duration = _duration_seconds(started_at, completed_at)
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO monitoring.pipeline_run_log
            (titik_id, titik_label, workflow_name, run_id, step_name, granularity,
             status, started_at, completed_at, duration_seconds, trigger_event)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (titik_id, run_id, (COALESCE(step_name, ''))) DO NOTHING
        """,
        (titik_id, titik_label, workflow_name, run_id, step_name, granularity,
         status, started_at, completed_at, duration, trigger_event),
    )
    conn.commit()
    cur.close()


def main(run_id):
    repo = _github_repo()
    token = _github_token()

    run = fetch_run(repo, run_id, token)
    workflow_name = run["name"]
    trigger_event = run["event"]
    conclusion = _normalize_conclusion(run["conclusion"])
    run_started_at = run["run_started_at"]
    run_completed_at = run["updated_at"]

    rows = titik_for_workflow(workflow_name)
    if not rows:
        print(f"No titik configured for workflow {workflow_name!r}, skip.")
        return

    # Job-level 'skipped' (mis. transform-mart-aggregated.yml men-skip diri sendiri
    # lewat if:-guard sendiri karena upstream gagal, pola M5.4 KK3 isolasi kegagalan)
    # berarti TIDAK ADA satu pun step yang benar-benar jalan -- fetch_steps akan
    # kembalikan list kosong. Titik step-level untuk workflow ini dicatat 'skipped'
    # langsung dari data run (step_name=NULL, timing dari run bukan step) TANPA
    # memanggil find_step() sama sekali -- ditemukan sebagai bug nyata (run
    # 31436870678, M6.3 Checkpoint 2): find_step() crash "found 0" pada kondisi ini,
    # membuat SELURUH titik untuk run itu gagal tercatat (bukan cuma yang crash),
    # dan step GitHub Actions-nya sendiri ikut FAILED padahal cuma observasional.
    run_was_skipped = run["conclusion"] == "skipped"

    steps = None
    conn = get_connection()
    try:
        for titik_id, titik_label, _wf_name, step_sub, granularity in rows:
            if step_sub is None or run_was_skipped:
                step_name = None if step_sub is None else f"{step_sub} (run skipped, no steps executed)"
                insert_row(conn, titik_id, titik_label, workflow_name, run_id, step_name,
                           granularity, conclusion, run_started_at, run_completed_at, trigger_event)
                level = "run-level" if step_sub is None else "step-level (run skipped, inferred)"
                print(f"Logged titik {titik_id} ({titik_label}) {level}: {conclusion}")
            else:
                if steps is None:
                    steps = fetch_steps(repo, run_id, token)
                step = find_step(steps, step_sub)
                step_conclusion = _normalize_conclusion(step["conclusion"])
                insert_row(conn, titik_id, titik_label, workflow_name, run_id, step["name"],
                           granularity, step_conclusion, step["started_at"], step["completed_at"],
                           trigger_event)
                print(f"Logged titik {titik_id} ({titik_label}) step-level: {step_conclusion}")
    finally:
        conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_id", type=int, help="GitHub Actions run id")
    args = parser.parse_args()
    main(args.run_id)
