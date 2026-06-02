"""
agents/simulator.py — Shariah Board Simulator Agent (Gemini)

MIGRATION: Replaced Anthropic SDK with lib.llm.chat(). Logic unchanged.
"""

import json
from state import AuditState
from lib.llm import chat

RISK_SCORE_THRESHOLD = 0.6

SYSTEM_PROMPT = """You are a Shariah Supervisory Board simulator for Bank Islam Malaysia Berhad.
You receive a compliance report and adversarial findings, then produce a structured audit decision.

Weigh BOTH the compliance report (standard view) AND the adversarial findings (worst-case view).
Be balanced but err on the side of caution.

Output format (JSON object, not array):
{
  "audit_summary": "2-3 sentence executive summary",
  "key_concerns": ["issue 1", "issue 2"],
  "risk_score": 0.75,
  "recommendation": "ESCALATE",
  "reasoning": "Detailed paragraph explaining your recommendation",
  "conditions": ["Condition that must be met before approval"]
}

Risk score: 0.0-0.3 low | 0.3-0.6 moderate | 0.6-0.8 high | 0.8-1.0 critical
Recommendation: "APPROVE" (risk < 0.6, no high findings) or "ESCALATE" (anything else)
Return ONLY valid JSON."""


def run_simulator_agent(state: AuditState) -> dict:
    """Synthesises all findings into a final board-level audit report."""
    print("🕌 [Shariah Board Simulator] Deliberating on audit findings...")

    raw = chat(
        system=SYSTEM_PROMPT,
        user=(
            f"Contract ID: {state['contract_id']}\n\n"
            f"COMPLIANCE REPORT:\n{json.dumps(state.get('compliance_report', []), indent=2)}\n\n"
            f"DEVIL'S ADVOCATE FINDINGS:\n{json.dumps(state.get('adversarial_findings', []), indent=2)}\n\n"
            "Produce the final Shariah board audit decision."
        ),
        max_tokens=3000,
    )

    board_decision = json.loads(_clean_json(raw))
    risk_score     = board_decision.get("risk_score", 0.5)
    recommendation = board_decision.get("recommendation", "ESCALATE")

    has_high = any(f.get("severity") == "high" for f in state.get("adversarial_findings", []))
    contradictions = _has_contradictions(state)
    needs_human = recommendation == "ESCALATE" or risk_score >= RISK_SCORE_THRESHOLD or has_high or contradictions

    print(f"   ✓ Risk score: {risk_score:.2f} | Recommendation: {recommendation}")
    if contradictions: print("   ⚠️  Contradictory findings detected")
    print(f"   → Routing: {'ESCALATE to human' if needs_human else 'AUTO-APPROVE'}")

    return {
        "audit_report":       json.dumps(board_decision, indent=2),
        "risk_score":         risk_score,
        "needs_human_review": needs_human,
    }


def _has_contradictions(state: AuditState) -> bool:
    compliant_ids  = {r["clause_id"] for r in state.get("compliance_report", []) if r.get("status") == "compliant"}
    high_risk_ids  = {f["clause_id"] for f in state.get("adversarial_findings", []) if f.get("severity") == "high"}
    return bool(compliant_ids & high_risk_ids)


def _clean_json(text):
    text = text.strip()
    if text.startswith("```"):
        parts = text.split("```")
        text = parts[1]
        if text.startswith("json"):
            text = text[4:]
    return text.strip()
