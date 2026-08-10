"""
Milestone 4.4 -- authorization check, the API's own Lapis 2 gate (decisions.md
Keputusan #3). Every route handler calls authorize() BEFORE running any data
query. role_permissions is looked up via chatbot_authz_reader (connections.py)
-- its rows are used only to decide allow/deny here, never returned as an API
response body.
"""
from fastapi import HTTPException

from connections import query_authz


def get_access_scope(role_title, domain):
    """Returns 'own_property' / 'all_properties' if role_title is permitted
    for domain, else None. role_title not existing at all in role_permissions
    also returns None (same treatment -- caller can't distinguish "unknown
    role" from "known role, wrong domain" from the response, by design: doesn't
    leak which role_titles exist to a caller probing with a fake one)."""
    rows = query_authz(
        "SELECT access_scope FROM role_permissions WHERE role_title = %s AND data_domain = %s",
        (role_title, domain),
    )
    return rows[0]["access_scope"] if rows else None


def authorize(role_title, domain):
    """Raises HTTPException(403) if role_title has no permission for domain.
    Returns the access_scope ('own_property'/'all_properties') on success."""
    if not role_title:
        raise HTTPException(status_code=403, detail="role_title is required")
    scope = get_access_scope(role_title, domain)
    if scope is None:
        raise HTTPException(
            status_code=403,
            detail=f"role '{role_title}' is not permitted for domain '{domain}'",
        )
    return scope
