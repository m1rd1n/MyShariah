"""
agents/devils_advocate.py — Devil's Advocate Agent (Gemini + RAG)

MIGRATION: Replaced Anthropic SDK with lib.llm.chat(). RAG + guardrail unchanged.
"""

import json
from state import AuditState
from lib.llm import chat
from lib.rag import query_policy

MAX_ITERATIONS = 3

BASE_SYSTEM_PROMPT = """You are the Devil's Advocate in a Shariah contract audit system.
Your SOLE purpose is to find loopholes, ambiguities, and hidden non-compliance risks.

Use the following BNM policy passages and actively look for ways the contract
could violate or circumvent these specific provisions:

{policy_context}

Probe for: HIDDEN RIBA, GHARAR LOOPHOLES, MAYSIR EXPOSURE, OWNERSHIP GAPS,
JURISDICTION CONFLICTS, DOCUMENTATION GAPS, PENALTY TRAPS.

Rules:
1. Be adversarial — assume bad faith or worst-case interpretation
2. Only flag GENUINE concerns — do not hallucinate issues
3. If no concerns found, return []

Output format:
[
  {{
    "clause_id": "C001",
    "risk_type": "riba",
    "severity": "high",
    "finding": "What the issue is and why it matters",
    "loophole": "Specific scenario where this could be exploited"
  }}
]
Severity: "high" | "medium" | "low"
Return ONLY valid JSON."""


def run_devils_advocate_agent(state: AuditState) -> dict:
    """Adversarially probes clauses for loopholes. Capped at MAX_ITERATIONS."""
    iterations = state.get("devils_advocate_iterations", 0)

    if iterations >= MAX_ITERATIONS:
        print(f"😈 [Devil's Advocate] Max iterations ({MAX_ITERATIONS}) reached.")
        return {"devils_advocate_iterations": iterations}

    print(f"😈 [Devil's Advocate] Adversarial pass {iterations + 1}/{MAX_ITERATIONS}...")

    clauses = state["clauses"]
    adversarial_query = (
        " ".join(c["text"] for c in clauses)
        + " riba gharar maysir constructive possession ta'widh late payment income charity"
    )
    policy_context = query_policy(adversarial_query, n_results=5)
    system_prompt  = BASE_SYSTEM_PROMPT.format(policy_context=policy_context)

    raw = chat(
        system=system_prompt,
        user=(
            f"CONTRACT CLAUSES:\n{json.dumps(clauses, indent=2)}\n\n"
            f"COMPLIANCE CHECKER APPROVED THESE — find what it missed:\n"
            f"{json.dumps(state.get('compliance_report', []), indent=2)}\n\n"
            f"Adversarial pass {iterations + 1} of {MAX_ITERATIONS}. "
            f"Focus on edge cases and hidden risks."
        ),
        max_tokens=4000,
    )

    findings = json.loads(_clean_json(raw))
    by_sev   = {s: sum(1 for f in findings if f.get("severity") == s) for s in ["high","medium","low"]}
    print(f"   ✓ Pass {iterations + 1} — 🔴 {by_sev['high']} high  🟡 {by_sev['medium']} medium  🟢 {by_sev['low']} low")

    return {"adversarial_findings": findings, "devils_advocate_iterations": iterations + 1}


def _clean_json(text):
    text = text.strip()
    if text.startswith("```"):
        parts = text.split("```")
        text = parts[1]
        if text.startswith("json"):
            text = text[4:]
    return text.strip()
