-- Milestone 4.5: audit log for every AI Chatbot API request (success or
-- denied), additive to the shared monitoring schema (CLAUDE.md "monitoring
-- schema -- the shared backbone"). Lives in the PRODUCTION Supabase project
-- (monitoring.*), same convention as monitoring.reverse_etl_sync_log (M2.4
-- Keputusan #6) -- monitoring stays centralized regardless of where the
-- system being observed (here: scripts/chatbot_api/, serving project)
-- physically lives.
--
-- This table only ever sees requests that already passed Lapis 1 (the
-- chatbot application's own intent validation -- out of scope for this repo,
-- see decisions.md M4.5 Keputusan #7). role_title/employee_id here are
-- CLAIMS forwarded by Lapis 1 to this API, not independently verified
-- identity -- Lapis 2 (this API) validates the claim against
-- mart_cleaned.role_permissions and records what it decided. That decision
-- record is exactly the defense-in-depth evidence this table exists to
-- capture, not a ground-truth log of who really used the chatbot.
--
-- One row per API request, written by chatbot_audit_writer (INSERT-only,
-- scripts/chatbot_audit/setup_audit_writer.py) from scripts/chatbot_api/audit.py.

CREATE TABLE IF NOT EXISTS monitoring.chatbot_query_log (
    id                    bigserial PRIMARY KEY,
    role_title            text,
    domain                text NOT NULL,
    view_name             text,
    employee_id           text,
    access_scope          text,
    resolved_property_id  text,
    status                text NOT NULL CHECK (status IN ('success', 'denied')),
    denial_reason         text,
    row_count             integer,
    requested_at          timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_chatbot_query_log_requested_at
    ON monitoring.chatbot_query_log (requested_at DESC);
CREATE INDEX IF NOT EXISTS idx_chatbot_query_log_status
    ON monitoring.chatbot_query_log (status, requested_at DESC);
