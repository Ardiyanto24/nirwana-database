-- Milestone 2.4: row-count-parity sync log, additive to the shared monitoring
-- schema (see CLAUDE.md "monitoring schema -- the shared backbone"). Lives in
-- the PRODUCTION Supabase project (monitoring.*), NOT the new serving
-- project -- decisions.md Decision 6: monitoring stays centralized in one
-- place regardless of where the serving layer physically lives.
-- One row per sync_table() call in scripts/reverse_etl/sync.py.

CREATE TABLE IF NOT EXISTS monitoring.reverse_etl_sync_log (
    id            bigserial PRIMARY KEY,
    table_name    text NOT NULL,
    bq_row_count  bigint NOT NULL,
    pg_row_count  bigint NOT NULL,
    status        text NOT NULL CHECK (status IN ('synced', 'mismatch_aborted')),
    synced_at     timestamptz NOT NULL DEFAULT now()
);
