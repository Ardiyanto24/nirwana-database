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

MART_AGGREGATED_INDEXES = [
    # --- Revenue (Checkpoint 2) ---
    {
        "table": "fact_revenue_room_type_daily",
        "index_name": "idx_fact_revenue_room_type_daily_property_period",
        "columns": ["property_id", "period_date"],
    },
    {
        "table": "fact_revenue_channel_daily",
        "index_name": "idx_fact_revenue_channel_daily_property_period",
        "columns": ["property_id", "period_date"],
    },
    {
        "table": "fact_revenue_los_daily",
        "index_name": "idx_fact_revenue_los_daily_property_period",
        "columns": ["property_id", "period_date"],
    },
    {
        "table": "fact_revenue_property_daily",
        "index_name": "idx_fact_revenue_property_daily_property_period",
        "columns": ["property_id", "period_date"],
    },
    {
        "table": "fact_revenue_pricing_deviation",
        "index_name": "idx_fact_revenue_pricing_deviation_property_period",
        "columns": ["property_id", "period_date"],
    },
    {
        "table": "fact_revenue_loyalty_daily",
        "index_name": "idx_fact_revenue_loyalty_daily_property_period",
        "columns": ["property_id", "period_date"],
    },
    {
        "table": "fact_revenue_nationality_daily",
        "index_name": "idx_fact_revenue_nationality_daily_property_period",
        "columns": ["property_id", "period_date"],
    },
    # fact_revenue_gop_impact_monthly (180 rows) deliberately excluded -- too small
    # for Postgres to ever prefer an index scan over seq scan (Keputusan #2).
]
