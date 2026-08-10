"""
Milestone 4.4 -- API Query Interface for AI Chatbot.

Internal tool (NOT portfolio-facing like api/, M1.6) -- no auth/CORS/rate-
limiting at the transport level, same classification as scripts/data_analyst_api/
(M3.4). But unlike M3.4 -- which used one shared admin connection because
isolation was M3.5's job, exercised by humans OUTSIDE that API -- this API IS
the trust boundary: it is the only thing standing between an untrusted Lapis 1
(chatbot application layer, "tidak boleh diasumsikan selalu benar" per the
source doc) and the 10 scoped domain credentials from Milestone 4.3.

Route design: GET /chatbot/{domain}/{view_name} -- one pattern per domain
(no separate aggregate/rowlevel namespaces like M3.4, because every
chatbot_views view -- aggregate or lookup -- already lives in one uniform
schema). view_name is whitelisted per domain (whitelist_<domain>.py, mirrors
M3.4's SAMPLE_TABLE_WHITELIST idiom) -- never a raw user-supplied name.

Every request is authorized (authz.authorize) against role_permissions
BEFORE any data query runs, and the data query itself executes through the
domain-scoped M4.3 credential (connections.query_as_domain) -- never admin.
own_property access_scope always resolves property_id server-side from
employee_id (connections.resolve_property_id); a client-claimed property_id
is only ever used as an optional narrowing filter under all_properties.
"""
from fastapi import FastAPI, HTTPException
from starlette.requests import Request

from authz import authorize
from connections import query_as_domain, resolve_property_id

app = FastAPI(title="Nirwana AI Chatbot Query API", version="1.0.0")

DEFAULT_LIMIT = 100
MAX_LIMIT = 1000


@app.get("/health")
def health():
    return {"status": "ok"}


def _run_whitelisted_query(domain, entry, query_params, employee_id, access_scope, limit, offset):
    """entry = {"source": "chatbot_views.<view>", "filters": [{"param","column","op"}, ...],
    "own_property_column": "<column>" (optional, default "property_id")}.
    own_property_column exists because not every view names its property
    column "property_id" -- guests_contact_view/guests_profile_view (M4.2)
    expose "last_active_property_id" instead (guests aren't natively
    property-scoped, see docs/09-serving-ai-chatbot/pemetaan-akses-teknis-chatbot.md
    Section 3). Only filters declared in the whitelist entry are ever
    applied; column names/operators come from the entry (never user input),
    values are always passed as %s parameters (mirrors M3.4's
    _run_whitelisted_query)."""
    own_property_column = entry.get("own_property_column", "property_id")
    where_clauses = []
    values = []

    for f in entry["filters"]:
        if f["column"] == own_property_column and access_scope == "own_property":
            continue  # handled below via resolve_property_id -- client value never trusted
        val = query_params.get(f["param"])
        if val is not None and val != "":
            where_clauses.append(f'{f["column"]} {f["op"]} %s')
            values.append(val)

    if access_scope == "own_property":
        if not employee_id:
            raise HTTPException(status_code=400, detail="employee_id is required for own_property access")
        resolved_property_id = resolve_property_id(employee_id)
        if resolved_property_id is None:
            raise HTTPException(status_code=400, detail=f"employee_id '{employee_id}' not found")
        if own_property_column in {f["column"] for f in entry["filters"]}:
            where_clauses.append(f"{own_property_column} = %s")
            values.append(resolved_property_id)

    sql = f'SELECT * FROM {entry["source"]}'
    if where_clauses:
        sql += " WHERE " + " AND ".join(where_clauses)

    limit = min(max(1, limit), MAX_LIMIT)
    offset = max(0, offset)
    sql += " ORDER BY 1 LIMIT %s OFFSET %s"
    values += [limit, offset]

    return query_as_domain(domain, sql, values)


def register_domain_routes(domain, whitelist):
    """Registers GET /chatbot/{domain}/{view_name} for one domain, backed by
    that domain's whitelist dict. role_title is authorized against
    role_permissions BEFORE the whitelist lookup even happens for the data
    query -- an unknown/unauthorized role never reaches the database at all
    (KK2 M4.4)."""

    def handler(
        request: Request,
        view_name: str,
        role_title: str,
        employee_id: str = None,
        limit: int = DEFAULT_LIMIT,
        offset: int = 0,
    ):
        access_scope = authorize(role_title, domain)

        entry = whitelist.get(view_name)
        if entry is None:
            raise HTTPException(status_code=404, detail=f"'{view_name}' is not in the {domain} whitelist")

        return _run_whitelisted_query(domain, entry, request.query_params, employee_id, access_scope, limit, offset)

    app.add_api_route(f"/chatbot/{domain}/{{view_name}}", handler, methods=["GET"])


# Domain routes registered below, one block added per M4.4 checkpoint.

from whitelist_reservation import WHITELIST as RESERVATION_WHITELIST
from whitelist_fnb import WHITELIST as FNB_WHITELIST

register_domain_routes("reservation", RESERVATION_WHITELIST)
register_domain_routes("fnb", FNB_WHITELIST)

from whitelist_facility import WHITELIST as FACILITY_WHITELIST
from whitelist_spa_event import WHITELIST as SPA_EVENT_WHITELIST

register_domain_routes("facility", FACILITY_WHITELIST)
register_domain_routes("spa_event", SPA_EVENT_WHITELIST)

from whitelist_hr import WHITELIST as HR_WHITELIST
from whitelist_financial import WHITELIST as FINANCIAL_WHITELIST

register_domain_routes("hr", HR_WHITELIST)
register_domain_routes("financial", FINANCIAL_WHITELIST)

from whitelist_properties_ref import WHITELIST as PROPERTIES_REF_WHITELIST
from whitelist_employees_directory import WHITELIST as EMPLOYEES_DIRECTORY_WHITELIST
from whitelist_guests_pii import WHITELIST as GUESTS_PII_WHITELIST
from whitelist_guests_profile import WHITELIST as GUESTS_PROFILE_WHITELIST

register_domain_routes("properties_ref", PROPERTIES_REF_WHITELIST)
register_domain_routes("employees_directory", EMPLOYEES_DIRECTORY_WHITELIST)
register_domain_routes("guests_pii", GUESTS_PII_WHITELIST)
register_domain_routes("guests_profile", GUESTS_PROFILE_WHITELIST)
