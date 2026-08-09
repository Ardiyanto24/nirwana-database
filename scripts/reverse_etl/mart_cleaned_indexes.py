"""
Milestone 3.3 -- index design for mart_cleaned (serving PostgreSQL), consumed by
reindex_analyze.py. Populated per-domain across M3.3's checkpoints (Revenue, F&B,
Facility/Ops, Spa & Event, HR, Corporate/Financial) -- see
docs/08-serving-data-analyst/index-baseline-analyst.md for the full rationale and
EXPLAIN ANALYZE evidence per entry.

Columns chosen from the "Filter Wajib" per role in
docs/08-serving-data-analyst/pemetaan-pola-akses-analyst.md (M3.1) -- entity/property
filter column(s) first, then date range, matching the composite-index convention in
rancangan-arsitektur-data-platform-elt.md Bagian 9.3.2.

Only tables/columns empirically confirmed to be used by the query planner (EXPLAIN
ANALYZE showing Index/Bitmap Index Scan, not Seq Scan) are kept here -- Milestone 3.3
Keputusan #2 (decisions.md): no blanket indexing of small tables.
"""

MART_CLEANED_INDEXES = []
