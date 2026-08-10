-- Milestone 4.2: schema for AI Chatbot-facing views.
-- Kept separate from mart_aggregated/mart_cleaned/analyst_views so Milestone 4.3
-- can GRANT per-view/per-kelompok-akses here without touching the reverse-ETL
-- writer roles' schemas. Unlike analyst_views (M3.2), this schema also holds
-- row-level lookup views over mart_cleaned -- chatbot credentials never get a
-- raw GRANT on mart_cleaned tables (decisions.md Keputusan #2).
CREATE SCHEMA IF NOT EXISTS chatbot_views;
