-- L1/L2/L3 fix workflow state and audit trail, 
CREATE TABLE IF NOT EXISTS fix_runs (
    ticket_id   TEXT PRIMARY KEY,
    stage       TEXT NOT NULL DEFAULT 'new',      -- new, l1, l2, l3, approved, rejected
    status      TEXT NOT NULL DEFAULT 'open',
    outputs     JSONB NOT NULL DEFAULT '{}'::jsonb,
    run_by      TEXT,
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS fix_audit_log (
    id          BIGSERIAL PRIMARY KEY,
    ticket_id   TEXT NOT NULL,
    action      TEXT NOT NULL,                    -- stage_run, approved, rejected
    actor       TEXT,
    detail      JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_fix_audit_ticket ON fix_audit_log (ticket_id, created_at);
CREATE TABLE IF NOT EXISTS l0_sessions (
    id          TEXT PRIMARY KEY,
    unit_id     TEXT,
    outcome     TEXT NOT NULL DEFAULT 'open',    -- open, resolved, ticket_created
    ticket_ref  TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
