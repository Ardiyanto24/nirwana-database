-- Milestone 2.1: cursor tracking state for incremental extraction, additive
-- to the shared monitoring schema (see CLAUDE.md "monitoring schema -- the
-- shared backbone"). One row per (schema_name, table_name) synced by
-- scripts/extract/extract.py -- last_cursor is the highest cursor_column
-- value seen so far for that table (see decisions.md for why this is a
-- primary-key-or-date value, not a CDC log position).

CREATE TABLE IF NOT EXISTS monitoring.extract_cursor (
    schema_name  text NOT NULL,
    table_name   text NOT NULL,
    last_cursor  text,
    updated_at   timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (schema_name, table_name)
);
