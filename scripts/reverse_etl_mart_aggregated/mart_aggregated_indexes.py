"""
Milestone 3.3 -- index design for mart_aggregated (serving PostgreSQL), consumed by
reindex_analyze.py. Replaces the M5.5 provisional example_indexes.py (which existed
only to prove the REINDEX/ANALYZE-after-swap mechanism worked, docstring explicitly
said "Jangan dianggap sebagai desain index M3.3"). Populated per-domain across M3.3's
checkpoints (Revenue, F&B, Facility/Ops, Spa & Event, HR, Corporate/Financial) -- see
docs/08-serving-data-analyst/index-baseline-analyst.md for the full rationale and
EXPLAIN ANALYZE evidence per entry.

Columns chosen from the "Filter Wajib" per role in
docs/08-serving-data-analyst/pemetaan-pola-akses-analyst.md (M3.1) and the join columns
in docs/08-serving-data-analyst/view-query-pattern-analyst.md (M3.2) -- entity/property
filter column(s) first, then date range, matching the composite-index convention in
rancangan-arsitektur-data-platform-elt.md Bagian 9.3.2.

Only tables/columns empirically confirmed to be used by the query planner (EXPLAIN
ANALYZE showing Index/Bitmap Index Scan, not Seq Scan) are kept here -- Milestone 3.3
Keputusan #2 (decisions.md): no blanket indexing of small tables. Several mart_aggregated
fact tables are small dimension-style aggregates (hundreds of rows) where Postgres will
sequential-scan regardless of indexing -- those are deliberately left out, documented in
index-baseline-analyst.md rather than indexed "for completeness."
"""

MART_AGGREGATED_INDEXES = []
