"""
lib/db.py — Python Supabase Client

WHAT THIS DOES:
Provides database operations for the Python backend (shariah_auditor).
Called by main.py and graph.py to write audit progress and results
to Supabase as each agent completes.

SETUP:
1. pip install supabase
2. Add to .env:
     SUPABASE_URL=https://your-project.supabase.co
     SUPABASE_SERVICE_KEY=your-service-role-key   ← NOT the anon key

USAGE:
    from lib.db import audit_db

    audit_db.create_audit(contract_id, contract_text)
    audit_db.update_phase(contract_id, "extraction")
    audit_db.write_clauses(contract_id, clauses)
    audit_db.write_final(contract_id, audit_report, risk_score)
    audit_db.record_decision(contract_id, "APPROVE", "Justification", "Officer Name")
"""

import os
from typing import Optional

try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False

from dotenv import load_dotenv
load_dotenv()


class AuditDB:
    """
    Thin wrapper around the Supabase Python client.
    All methods degrade silently if Supabase is not configured —
    the pipeline still runs; results just won't be persisted to the cloud.
    """

    def __init__(self):
        self._client: Optional[Client] = None
        self._ready  = False
        self._init()

    def _init(self):
        if not SUPABASE_AVAILABLE:
            print("[DB] supabase-py not installed. Run: pip install supabase")
            return

        url = os.environ.get("SUPABASE_URL", "")
        key = os.environ.get("SUPABASE_SERVICE_KEY", "")

        if not url or not key:
            print("[DB] ⚠  SUPABASE_URL or SUPABASE_SERVICE_KEY not set.")
            print("[DB] ↳  Audit results will not be persisted. Add keys to .env to enable.")
            return

        try:
            self._client = create_client(url, key)
            self._ready  = True
            print("[DB] ✓ Supabase connected")
        except Exception as e:
            print(f"[DB] ⚠  Connection failed: {e}")

    # ── Write operations ─────────────────────────────────────────────────────

    def create_audit(self, contract_id: str, contract_text: str) -> bool:
        """
        Creates a new audit record with phase='queued'.
        Called at the start of every pipeline run.
        """
        return self._upsert("audits", {
            "contract_id":   contract_id,
            "contract_text": contract_text,
            "phase":         "queued",
        })

    def update_phase(self, contract_id: str, phase: str) -> bool:
        """Updates the pipeline phase. Called after each agent completes."""
        return self._update(contract_id, {"phase": phase})

    def write_clauses(self, contract_id: str, clauses: list) -> bool:
        """Persists extracted clauses. Called after extraction agent."""
        return self._update(contract_id, {
            "clauses": clauses,
            "phase":   "compliance",
        })

    def write_compliance(self, contract_id: str, compliance_report: list) -> bool:
        """Persists compliance results. Called after compliance agent."""
        return self._update(contract_id, {
            "compliance_report": compliance_report,
            "phase":             "devils_advocate",
        })

    def write_adversarial(
        self,
        contract_id: str,
        findings: list,
        iterations: int
    ) -> bool:
        """Persists devil's advocate findings."""
        return self._update(contract_id, {
            "adversarial_findings":       findings,
            "devils_advocate_iterations": iterations,
            "phase":                      "simulator",
        })

    def write_final(
        self,
        contract_id: str,
        audit_report: str,
        risk_score: float,
        needs_human_review: bool,
    ) -> bool:
        """Persists the simulator's final report and sets routing phase."""
        return self._update(contract_id, {
            "audit_report":       audit_report,
            "risk_score":         risk_score,
            "needs_human_review": needs_human_review,
            "phase":              "hitl_required" if needs_human_review else "approved",
        })

    def record_decision(
        self,
        contract_id: str,
        decision: str,
        justification: str,
        officer_id: str,
    ) -> bool:
        """
        Records the Shariah officer's HITL decision.
        Also appends an immutable event to audit_events for the audit trail.
        """
        import datetime
        now = datetime.datetime.utcnow().isoformat()

        success = self._update(contract_id, {
            "human_decision":       decision,
            "officer_justification": justification,
            "officer_id":           officer_id,
            "phase":                "approved" if decision == "APPROVE" else "rejected",
            "completed_at":         now,
        })

        # Append immutable event to audit trail
        self._append_event(contract_id, "hitl_decision", {
            "decision":      decision,
            "justification": justification,
            "timestamp":     now,
        }, actor=officer_id)

        return success

    def log_event(
        self,
        contract_id: str,
        event_type: str,
        data: dict,
        actor: str = "system",
    ) -> bool:
        """Appends a generic event to the immutable audit trail."""
        return self._append_event(contract_id, event_type, data, actor)

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _update(self, contract_id: str, patch: dict) -> bool:
        if not self._ready:
            return False
        try:
            self._client.table("audits")\
                .update(patch)\
                .eq("contract_id", contract_id)\
                .execute()
            return True
        except Exception as e:
            print(f"[DB] Update failed for {contract_id}: {e}")
            return False

    def _upsert(self, table: str, data: dict) -> bool:
        if not self._ready:
            return False
        try:
            self._client.table(table).upsert(data).execute()
            return True
        except Exception as e:
            print(f"[DB] Upsert failed: {e}")
            return False

    def _append_event(
        self,
        contract_id: str,
        event_type: str,
        data: dict,
        actor: str = "system",
    ) -> bool:
        if not self._ready:
            return False
        try:
            self._client.table("audit_events").insert({
                "contract_id": contract_id,
                "event_type":  event_type,
                "event_data":  data,
                "actor":       actor,
            }).execute()
            return True
        except Exception as e:
            print(f"[DB] Event log failed: {e}")
            return False


# ── Module-level singleton ────────────────────────────────────────────────────
# Import this in any file that needs DB access:
#   from lib.db import audit_db
audit_db = AuditDB()
