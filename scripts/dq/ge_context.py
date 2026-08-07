"""Shared Great Expectations Data Context + Postgres datasource for Milestone 1.3."""
import os
import sys
import great_expectations as gx

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "monitoring"))
from db import _load_env  # noqa: E402  (reuse the same .env loader as scripts/monitoring)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
GX_PROJECT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gx_project")
DATASOURCE_NAME = "nirwana_supabase"


def get_context():
    """
    PENTING (keamanan): `great_expectations.yml` didesain GE untuk di-commit ke repo
    (lihat komentar di file itu sendiri). Connection string TIDAK boleh ditulis
    mentah di sana -- itu bocor password ke git history. Simpan nilai asli via
    `save_config_variable` (masuk ke gx/uncommitted/config_variables.yml, sudah
    di-gitignore otomatis oleh GE) dan referensikan lewat substitusi ${VAR} di
    datasource config.
    """
    ctx = gx.get_context(mode="file", project_root_dir=GX_PROJECT_DIR)
    env = _load_env(os.path.join(REPO_ROOT, ".env"))
    ctx.save_config_variable("SUPABASE_DB_URL", env["SUPABASE_DB_URL"])

    try:
        datasource = ctx.data_sources.add_postgres(
            name=DATASOURCE_NAME, connection_string="${SUPABASE_DB_URL}"
        )
    except Exception:
        datasource = ctx.data_sources.get(DATASOURCE_NAME)
    return ctx, datasource


if __name__ == "__main__":
    ctx, ds = get_context()
    print(f"Context ready at {GX_PROJECT_DIR}")
    print(f"Datasource: {ds.name}")
