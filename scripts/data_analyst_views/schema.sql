-- Milestone 3.2: schema for Data Analyst-facing views.
-- Kept separate from mart_aggregated/mart_cleaned so Milestone 3.5 can GRANT
-- per-view/per-role here without touching the reverse-ETL writer roles' schemas.
CREATE SCHEMA IF NOT EXISTS analyst_views;
