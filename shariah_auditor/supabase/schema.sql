-- ============================================================
-- Shariah Audit System — Supabase Schema
-- ============================================================
-- HOW TO USE:
--   1. Open your Supabase project → SQL Editor
--   2. Paste this entire file and click Run
--   3. All tables, indexes, RLS policies, and triggers are created
--
-- RE-RUNNING: Safe to re-run — uses CREATE IF NOT EXISTS and
-- CREATE OR REPLACE throughout.
-- ============================================================


-- ── 1. AUDITS TABLE ────────────────────────────────────────────
-- Core table: one row per contract audit run.
-- Agent outputs (clauses, compliance, findings) stored as JSONB
-- so they can be queried and filtered without schema changes.

CREATE TABLE IF NOT EXISTS audits (
  id                        UUID        DEFAULT gen_random_uuid() PRIMARY KEY,
  contract_id               TEXT        UNIQUE NOT NULL,
  contract_text             TEXT,

  -- Pipeline phase tracking
  phase                     TEXT        NOT NULL DEFAULT 'queued',
  started_at                TIMESTAMPTZ DEFAULT NOW(),
  completed_at              TIMESTAMPTZ,

  -- Agent outputs (written progressively as each agent completes)
  clauses                   JSONB       DEFAULT '[]'::jsonb,
  compliance_report         JSONB       DEFAULT '[]'::jsonb,
  adversarial_findings      JSONB       DEFAULT '[]'::jsonb,
  devils_advocate_iterations INTEGER    DEFAULT 0,

  -- Final synthesis (written by Shariah Board Simulator)
  audit_report              TEXT,
  risk_score                FLOAT,
  needs_human_review        BOOLEAN     DEFAULT FALSE,

  -- HITL decision (written when officer submits review)
  human_decision            TEXT,
  officer_justification     TEXT,
  officer_id                TEXT,

  created_at                TIMESTAMPTZ DEFAULT NOW(),
  updated_at                TIMESTAMPTZ DEFAULT NOW()
);

-- Index for fast lookups by phase (used by dashboard alert counts)
CREATE INDEX IF NOT EXISTS idx_audits_phase
  ON audits(phase);

-- Index for dashboard chronological sort
CREATE INDEX IF NOT EXISTS idx_audits_started_at
  ON audits(started_at DESC);

-- Index for risk score filtering (high-risk reports)
CREATE INDEX IF NOT EXISTS idx_audits_risk_score
  ON audits(risk_score);


-- ── 2. AUDIT EVENTS TABLE ──────────────────────────────────────
-- Append-only event log: records every phase transition and
-- every human decision with a timestamp. This is the immutable
-- audit trail required for BNM governance compliance.

CREATE TABLE IF NOT EXISTS audit_events (
  id            UUID        DEFAULT gen_random_uuid() PRIMARY KEY,
  contract_id   TEXT        NOT NULL REFERENCES audits(contract_id) ON DELETE CASCADE,
  event_type    TEXT        NOT NULL,  -- 'phase_change' | 'agent_complete' | 'hitl_decision' | 'error'
  event_data    JSONB       DEFAULT '{}'::jsonb,
  actor         TEXT,                  -- 'system' | officer name for HITL events
  created_at    TIMESTAMPTZ DEFAULT NOW()
);

-- Index for fetching all events for a contract (audit timeline view)
CREATE INDEX IF NOT EXISTS idx_audit_events_contract_id
  ON audit_events(contract_id, created_at ASC);


-- ── 3. AUTO-UPDATE updated_at TRIGGER ─────────────────────────
-- Keeps updated_at current whenever a row is modified.
-- Replaces manual updated_at management in application code.

CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS set_audits_updated_at ON audits;
CREATE TRIGGER set_audits_updated_at
  BEFORE UPDATE ON audits
  FOR EACH ROW EXECUTE FUNCTION update_updated_at();


-- ── 4. ROW LEVEL SECURITY ──────────────────────────────────────
-- Enables RLS on both tables. For MVP we allow all operations
-- using the service role key (server-side only).
-- Tighten these policies before production to restrict by user role.

ALTER TABLE audits       ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_events ENABLE ROW LEVEL SECURITY;

-- Allow full access via service role key (used by Next.js API routes
-- and Python backend — never exposed to the browser)
CREATE POLICY IF NOT EXISTS "Service role full access — audits"
  ON audits FOR ALL
  USING (true) WITH CHECK (true);

CREATE POLICY IF NOT EXISTS "Service role full access — audit_events"
  ON audit_events FOR ALL
  USING (true) WITH CHECK (true);


-- ── 5. SEED DATA (optional — comment out in production) ────────
-- Provides realistic data for the dashboard audit log on first load.
-- Delete these rows or comment this block out for a clean production start.

INSERT INTO audits (
  contract_id, phase, started_at, completed_at,
  risk_score, human_decision, officer_justification, officer_id
) VALUES
(
  'MUR-2024-0081', 'approved',
  NOW() - INTERVAL '3 hours', NOW() - INTERVAL '2 hours 50 minutes',
  0.18, 'AUTO_APPROVED', NULL, NULL
),
(
  'MUR-2024-0082', 'rejected',
  NOW() - INTERVAL '6 hours', NOW() - INTERVAL '5 hours 30 minutes',
  0.91, 'REJECT',
  'Clause 3 constitutes Riba. Variable profit rate tied to KLIBOR is non-compliant with SGF 2019 Para 7.1.',
  'Dr. Aminah binti Yusof'
),
(
  'MUR-2024-0085', 'approved',
  NOW() - INTERVAL '24 hours', NOW() - INTERVAL '23 hours 30 minutes',
  0.42, 'APPROVE',
  'Concerns noted but bank confirmed constructive possession procedures. Approved with conditions.',
  'Ustaz Hafiz bin Rahman'
)
ON CONFLICT (contract_id) DO NOTHING;
