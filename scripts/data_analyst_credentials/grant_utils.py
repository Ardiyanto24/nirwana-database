"""
Milestone 3.5 -- derives GRANT targets from Milestone 3.4's whitelist dicts,
so role_config_<domain>.py never re-types view/table names by hand (Keputusan
#4, decisions.md): the API's whitelist and the credential's GRANT scope stay
provably in sync, sourced from the same dict.
"""


def derive_grant_targets(*whitelists):
    """Each whitelist is an AGGREGATE_WHITELIST or ROWLEVEL_WHITELIST dict
    from scripts/data_analyst_api/whitelist_<domain>.py. Returns a sorted list
    of unique "<schema>.<object>" strings pulled from each entry's "source"."""
    targets = set()
    for whitelist in whitelists:
        for entry in whitelist.values():
            targets.add(entry["source"])
    return sorted(targets)
