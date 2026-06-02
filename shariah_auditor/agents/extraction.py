"""
agents/extraction.py — Extraction Agent (Gemini)

MIGRATION: Replaced direct Anthropic SDK calls with lib.llm.chat().
System prompt and output format unchanged.
"""

import json
from state import AuditState
from lib.llm import chat

SYSTEM_PROMPT = """You are a legal clause extraction specialist for Islamic finance contracts,
specifically Murabaha agreements regulated by Bank Negara Malaysia (BNM).

Your job:
1. Read the contract text carefully
2. Identify every distinct contractual clause
3. Categorise each clause by type
4. Return strictly structured JSON

Clause types:
- "pricing"            : Cost price, profit margin, selling price, payment terms
- "tenure"             : Duration, maturity date, installment schedule
- "penalty"            : Late payment charges, default consequences, ta'widh
- "ownership_transfer" : Asset transfer conditions, title deed, constructive possession
- "governing_law"      : Jurisdiction, applicable law, dispute resolution
- "other"              : Any other significant clause

CRITICAL: Return ONLY a valid JSON array. No explanation, no markdown fences.

Output format:
[
  {
    "clause_id": "C001",
    "clause_type": "pricing",
    "text": "exact verbatim clause text copied from the contract"
  }
]"""


def run_extraction_agent(state: AuditState) -> dict:
    """Parses contract text into a structured list of clauses."""
    print("🔍 [Extraction Agent] Parsing contract clauses...")

    raw = chat(
        system=SYSTEM_PROMPT,
        user=f"Extract all clauses from this Murabaha contract:\n\n{state['contract_text']}",
        max_tokens=3000,
    )

    clauses = json.loads(_clean_json(raw))
    print(f"   ✓ Extracted {len(clauses)} clauses: {[c['clause_type'] for c in clauses]}")
    return {"clauses": clauses}


def _clean_json(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        parts = text.split("```")
        text = parts[1]
        if text.startswith("json"):
            text = text[4:]
    return text.strip()
