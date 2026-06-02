"""
state.py — Shared state for the Shariah Audit multi-agent pipeline.

In LangGraph, "state" is a dictionary that flows through every node (agent).
Each agent reads from it and returns a partial update — only the keys it changes.
Think of it as a shared whiteboard all agents read from and write to.
"""

from typing import TypedDict, List, Optional


# ── Sub-types (building blocks of the main state) ────────────────────────────

class ClauseItem(TypedDict):
    clause_id: str    # e.g. "C001"
    clause_type: str  # pricing | tenure | penalty | ownership_transfer | governing_law | other
    text: str         # verbatim clause text from contract


class ComplianceResult(TypedDict):
    clause_id: str      # matches a ClauseItem
    status: str         # "compliant" | "non_compliant" | "ambiguous"
    bnm_reference: str  # e.g. "SGF 2019, Para 7.1"
    explanation: str    # human-readable reasoning
    confidence: float   # 0.0 – 1.0


class AdversarialFinding(TypedDict):
    clause_id: str   # matches a ClauseItem
    risk_type: str   # "riba" | "gharar" | "maysir" | "jurisdictional" | "documentation"
    severity: str    # "high" | "medium" | "low"
    finding: str     # what the devil's advocate found
    loophole: str    # specific scenario where this could be exploited


# ── Main state ────────────────────────────────────────────────────────────────

class AuditState(TypedDict):
    # ── Inputs (set once at the start, never changed)
    contract_text: str   # raw contract string or extracted PDF text
    contract_id: str     # unique identifier e.g. "MUR-2024-0087"

    # ── Agent outputs (each agent writes its own section)
    clauses: List[ClauseItem]                   # written by: Extraction Agent
    compliance_report: List[ComplianceResult]   # written by: Compliance Agent
    adversarial_findings: List[AdversarialFinding]  # written by: Devil's Advocate
    devils_advocate_iterations: int             # guardrail counter (max 3)

    # ── Final synthesis (written by: Shariah Board Simulator)
    audit_report: str    # JSON string of the board's structured decision
    risk_score: float    # 0.0 – 1.0

    # ── Routing + HITL
    needs_human_review: bool        # set by simulator; controls graph routing
    human_decision: Optional[str]   # "APPROVE" | "REJECT" | "AUTO_APPROVED"
    officer_justification: Optional[str]  # mandatory text when human intervenes
