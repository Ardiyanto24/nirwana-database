"""
Milestone 3.4 -- Multi-Endpoint API for Data Analyst.

Internal tool (NOT portfolio-facing like api/, M1.6) -- no auth, no rate
limiting, no CORS. Sits over analyst_views (M3.2, aggregate) and mart_cleaned
(row-level/ad-hoc) in the serving PostgreSQL project, both already indexed
(M3.3). Per-role credential isolation is Milestone 3.5's job, not this one's.

Route design: domain is a fixed path literal (e.g. /api/revenue/...), NOT a
generic /api/{any_domain}/... -- this keeps "endpoint terpisah per domain"
(KK1) true structurally, and lets M3.5's future access gate lock down by URL
prefix per role. Within a domain, the specific view/table is a whitelisted
path parameter (mirrors api/app/queries.py's SAMPLE_TABLE_WHITELIST pattern)
-- never a hardcoded function per view (48 views + 9 tables would mean 114
near-identical route functions), and never raw user-supplied table/column
names concatenated into SQL (injection risk). Filter values are always passed
as psycopg2 parameters, never string-interpolated.

Each domain's whitelist_<domain>.py module is added (and registered here via
register_domain_routes) in its own milestone checkpoint -- see decisions.md.
"""
from fastapi import FastAPI, HTTPException
from starlette.requests import Request

from connections import query

app = FastAPI(title="Nirwana Data Analyst API", version="1.0.0")

DEFAULT_LIMIT = 100
MAX_LIMIT = 1000


@app.get("/health")
def health():
    return {"status": "ok"}


def _run_whitelisted_query(entry, query_params, limit, offset):
    """entry = {"source": "<schema>.<view_or_table>", "filters": [{"param","column","op"}, ...]}.
    Only filters declared in the whitelist entry are ever applied; column
    names/operators come from the entry (never user input), values are always
    passed as %s parameters."""
    where_clauses = []
    values = []
    for f in entry["filters"]:
        val = query_params.get(f["param"])
        if val is not None and val != "":
            where_clauses.append(f'{f["column"]} {f["op"]} %s')
            values.append(val)

    sql = f'SELECT * FROM {entry["source"]}'
    if where_clauses:
        sql += " WHERE " + " AND ".join(where_clauses)

    limit = min(max(1, limit), MAX_LIMIT)
    offset = max(0, offset)
    sql += " ORDER BY 1 LIMIT %s OFFSET %s"
    values += [limit, offset]

    return query(sql, values)


def register_domain_routes(domain, aggregate_whitelist, rowlevel_whitelist):
    """Registers GET /api/{domain}/aggregate/{name} and /api/{domain}/rowlevel/{name}
    for one domain, backed by that domain's whitelist dicts."""

    def aggregate_handler(request: Request, name: str, limit: int = DEFAULT_LIMIT, offset: int = 0):
        entry = aggregate_whitelist.get(name)
        if entry is None:
            raise HTTPException(status_code=404, detail=f"'{name}' is not in the {domain} aggregate whitelist")
        return _run_whitelisted_query(entry, request.query_params, limit, offset)

    def rowlevel_handler(request: Request, name: str, limit: int = DEFAULT_LIMIT, offset: int = 0):
        entry = rowlevel_whitelist.get(name)
        if entry is None:
            raise HTTPException(status_code=404, detail=f"'{name}' is not in the {domain} row-level whitelist")
        return _run_whitelisted_query(entry, request.query_params, limit, offset)

    app.add_api_route(f"/api/{domain}/aggregate/{{name}}", aggregate_handler, methods=["GET"])
    app.add_api_route(f"/api/{domain}/rowlevel/{{name}}", rowlevel_handler, methods=["GET"])


# Domain routes registered below, one block added per M3.4 checkpoint.

from whitelist_revenue import AGGREGATE_WHITELIST as REVENUE_AGGREGATE, ROWLEVEL_WHITELIST as REVENUE_ROWLEVEL
from whitelist_fnb import AGGREGATE_WHITELIST as FNB_AGGREGATE, ROWLEVEL_WHITELIST as FNB_ROWLEVEL
from whitelist_facility import AGGREGATE_WHITELIST as FACILITY_AGGREGATE, ROWLEVEL_WHITELIST as FACILITY_ROWLEVEL
from whitelist_spa_event import AGGREGATE_WHITELIST as SPA_EVENT_AGGREGATE, ROWLEVEL_WHITELIST as SPA_EVENT_ROWLEVEL

register_domain_routes("revenue", REVENUE_AGGREGATE, REVENUE_ROWLEVEL)
register_domain_routes("fnb", FNB_AGGREGATE, FNB_ROWLEVEL)
register_domain_routes("facility", FACILITY_AGGREGATE, FACILITY_ROWLEVEL)
register_domain_routes("spa-event", SPA_EVENT_AGGREGATE, SPA_EVENT_ROWLEVEL)
