# Milestone 3.4: Multi-Endpoint API untuk Data Analyst — Logs

## 2026-08-09 — Mulai kerja

- Plan disetujui via Plan Mode. `decisions.md` ditulis, mengunci 10 keputusan teknis (topologi in-repo bukan portfolio-facing, pola kode FastAPI dari `api/`, desain route domain+whitelist, keamanan query, paginasi, dst).
- Folder dibuat: `milestones/3.4-multi-endpoint-api-analyst/`, `scripts/data_analyst_api/`.
- Mulai Task 1 (Fase 0 — FastAPI app skeleton).

## 2026-08-09 — Checkpoint 1

- `scripts/data_analyst_api/{connections.py,main.py}` dibuat. `connections.py` copy pola `get_serving_connection` dari `scripts/data_analyst_views/connections.py`, ditambah `query()` helper `RealDictCursor` persis pola `api/app/db.py` (M1.6). `main.py` berisi app FastAPI, `/health`, helper generik `_run_whitelisted_query` (filter kolom/operator dari whitelist entry, value selalu psycopg2 parameter) dan `register_domain_routes(domain, aggregate_whitelist, rowlevel_whitelist)` untuk dipanggil tiap checkpoint domain berikutnya.
- `requirements.txt` root ditambah blok baru `fastapi==0.115.6`, `uvicorn[standard]==0.34.0`.
- Verifikasi: `python -m uvicorn main:app --reload` dijalankan sungguhan di `127.0.0.1:8101`, `curl`/HTTP call langsung ke `/health` → `{"status":"ok"}` (200), `/docs` (Swagger auto-docs) → 200.
