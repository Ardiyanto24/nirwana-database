-- Milestone 2.4 -- serving layer schema (project Supabase BARU, terpisah dari
-- production). mart_cleaned di sini menampung 23 tabel hasil reverse ETL dari
-- BigQuery, satu per satu, via full refresh + swap table (scripts/reverse_etl/sync.py).
CREATE SCHEMA IF NOT EXISTS mart_cleaned;
