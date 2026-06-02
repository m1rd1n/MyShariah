"""
agents/compliance.py — Compliance Checker Agent (Gemini + RAG)

MIGRATION: Replaced Anthropic SDK with lib.llm.chat(). RAG unchanged.
"""

import json
from state import AuditState
from lib.llm import chat, extract_json
from lib.rag import query_policy

BASE_SYSTEM_PROMPT = """You are a Shariah compliance auditor for an Islamic bank regulated by BNM Malaysia.
Your task: check each contract clause against the BNM policy references provided below.

{policy_context}

For EVERY clause provided, return a compliance assessment. Output format:
[
  {{
    "clause_id": "C001",
    "status": "compliant",
    "bnm_reference": "SGF 2019, Para 7.1",
    "explanation": "Clear, specific explanation citing the policy passage above.",
    "confidence": 0.95
  }}
]

Status values:
- "compliant"     : Fully meets BNM/AAOIFI requirements
- "non_compliant" : Clearly violates a specific guideline
- "ambiguous"     : Requires further clarification or is borderline

Confidence: 0.0 to 1.0
Every clause MUST appear in your output. Return ONLY valid JSON."""


def run_compliance_agent(state: AuditState) -> dict:
    """Checks each clause against BNM guidelines via RAG-retrieved context."""
    print("⚖️  [Compliance Agent] Retrieving BNM policy passages via RAG...")

    clauses = state["clauses"]
    combined_text  = " ".join(c["text"] for c in clauses)
    policy_context = query_policy(combined_text, n_results=5)
    system_prompt  = BASE_SYSTEM_PROMPT.format(policy_context=policy_context)

    raw = chat(
        system=system_prompt,
        user=f"Check these {len(clauses)} clauses for Shariah compliance:\n\n{json.dumps(clauses, indent=2)}",
        max_tokens=4000,
    )

    compliance_report = json.loads(extract_json(raw))
    by_status = _count_by_status(compliance_report)
    print(f"   ✓ {len(compliance_report)} clauses — "
          f"✅ {by_status['compliant']} compliant  "
          f"❌ {by_status['non_compliant']} non-compliant  "
          f"⚠️  {by_status['ambiguous']} ambiguous")

    return {"compliance_report": compliance_report}


def _count_by_status(report):
    counts = {"compliant": 0, "non_compliant": 0, "ambiguous": 0}
    for r in report:
        counts[r.get("status", "ambiguous")] = counts.get(r.get("status", "ambiguous"), 0) + 1
    return counts
