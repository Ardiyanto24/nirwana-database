-- Milestone 5.5 -- serving layer schema for mart_aggregated, on the SAME
-- serving Supabase project created in Milestone 2.4 (not a new project --
-- decisions.md Keputusan #5). mart_aggregated here holds 76 tables (27 dim +
-- 49 fact, M5.3) synced from BigQuery via full refresh + swap table
-- (scripts/reverse_etl_mart_aggregated/sync.py). The M5.4 provisional ML
-- table is deliberately excluded (decisions.md Keputusan #2).
CREATE SCHEMA IF NOT EXISTS mart_aggregated;
