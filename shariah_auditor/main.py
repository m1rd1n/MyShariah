"""
main.py — Entry point for the Shariah Audit MVP (Supabase-enabled)

CHANGES FROM PREVIOUS VERSION:
- Calls audit_db at each pipeline stage to persist results to Supabase
- The pipeline still runs fully even if Supabase is unavailable (graceful fallback)

USAGE:
    python main.py
"""

import os
import json
from dotenv import load_dotenv
from langgraph.types import Command

from graph import build_graph
from lib.db import audit_db

load_dotenv()

SAMPLE_CONTRACT = """
MURABAHA FINANCING AGREEMENT

Contract ID  : MUR-2024-0087
Date         : 1 January 2024
Bank         : Bank Islam Malaysia Berhad ("Bank")
Customer     : Ahmad bin Hassan, NRIC 800101-14-5678 ("Customer")
Jurisdiction : Governed by Malaysian law AND UAE DIFC law for cross-border settlements

CLAUSE 1 - ASSET AND PRICE
The Bank agrees to sell 1,000 units of industrial semiconductor equipment
to the Customer at a selling price of RM 250,000, comprising:
  - Cost price   : RM 200,000
  - Profit margin: RM 50,000 (25% p.a.)
The profit rate shall be reviewed and may be adjusted quarterly
based on prevailing KLIBOR movements at the Bank's discretion.

CLAUSE 2 - PAYMENT TENURE
The Customer shall repay the selling price over 36 monthly instalments
of RM 6,944 each, commencing 30 days from the contract date.

CLAUSE 3 - LATE PAYMENT CHARGES
In the event of late payment, the Customer shall pay a late payment
charge of 1% per month on the outstanding balance. Such charges shall
be recognised as income by the Bank and credited to its profit account.

CLAUSE 4 - ASSET DELIVERY AND OWNERSHIP TRANSFER
The Bank shall arrange for the supplier (TechEquip Sdn Bhd) to deliver
the equipment directly to the Customer's premises prior to contract
execution. Title to the asset shall pass to the Customer upon full
settlement of the selling price.

CLAUSE 5 - DEFAULT AND ACCELERATION
Upon default of two consecutive instalments, the Bank may:
  (a) Accelerate the entire outstanding selling price immediately due;
  (b) Repossess the equipment at market value;
  (c) Recover any shortfall between repossession value and outstanding
      balance from the Customer's personal assets.

CLAUSE 6 - GOVERNING LAW AND DISPUTE RESOLUTION
This agreement is governed by the laws of Malaysia. For transactions
involving cross-border settlement, UAE DIFC Courts shall have
concurrent jurisdiction. Disputes shall be resolved by whichever
forum the Bank elects at its sole discretion.
"""


def run_audit(contract_text: str, contract_id: str) -> None:
    graph  = build_graph()
    config = {"configurable": {"thread_id": contract_id}}

    print(f"\n{'='*62}")
    print(f"  SHARIAH AUDIT SYSTEM — Contract ID: {contract_id}")
    print(f"{'='*62}\n")

    # ── Create initial record in Supabase ──────────────────────────────────
    audit_db.create_audit(contract_id, contract_text)
    audit_db.log_event(contract_id, "phase_change", {"phase": "queued"})

    initial_state = {
        "contract_text":              contract_text,
        "contract_id":                contract_id,
        "clauses":                    [],
        "compliance_report":          [],
        "adversarial_findings":       [],
        "devils_advocate_iterations": 0,
        "audit_report":               "",
        "risk_score":                 0.0,
        "needs_human_review":         False,
        "human_decision":             None,
        "officer_justification":      None,
    }

    # ── Run pipeline — log each completed stage to Supabase ───────────────
    for event in graph.stream(initial_state, config, stream_mode="updates"):
        for node_name, updates in event.items():

            if node_name == "extraction" and updates.get("clauses"):
                audit_db.write_clauses(contract_id, updates["clauses"])
                audit_db.log_event(contract_id, "agent_complete", {
                    "agent": "extraction",
                    "clause_count": len(updates["clauses"]),
                })

            elif node_name == "compliance" and updates.get("compliance_report"):
                audit_db.write_compliance(contract_id, updates["compliance_report"])
                audit_db.log_event(contract_id, "agent_complete", {
                    "agent": "compliance",
                })

            elif node_name == "devils_advocate" and updates.get("adversarial_findings") is not None:
                audit_db.write_adversarial(
                    contract_id,
                    updates.get("adversarial_findings", []),
                    updates.get("devils_advocate_iterations", 0),
                )
                audit_db.log_event(contract_id, "agent_complete", {
                    "agent":    "devils_advocate",
                    "findings": len(updates.get("adversarial_findings", [])),
                })

            elif node_name == "simulator" and updates.get("audit_report"):
                audit_db.write_final(
                    contract_id,
                    updates["audit_report"],
                    updates.get("risk_score", 0.0),
                    updates.get("needs_human_review", False),
                )
                audit_db.log_event(contract_id, "agent_complete", {
                    "agent":      "simulator",
                    "risk_score": updates.get("risk_score"),
                })

    # ── Check if paused at HITL ────────────────────────────────────────────
    graph_state = graph.get_state(config)

    if graph_state.next:
        _display_hitl_dossier(graph_state.values)

        print("\n" + "-"*62)
        officer_name  = input("  Officer name      : ").strip()
        decision      = input("  Decision (APPROVE / REJECT): ").strip().upper()
        justification = input("  Justification     : ").strip()

        if not justification:
            justification = "No justification provided."

        # Resume the LangGraph pipeline
        graph.invoke(
            Command(resume={"decision": decision, "justification": justification}),
            config
        )

        # Persist decision to Supabase
        audit_db.record_decision(contract_id, decision, justification, officer_name)

        print(f"\n  ✅ Decision recorded: {decision}")
        print(f"  📝 Justification    : {justification}")

    final = graph.get_state(config).values
    print(f"\n{'='*62}")
    print(f"  AUDIT COMPLETE")
    print(f"  Final decision : {final.get('human_decision', 'UNKNOWN')}")
    print(f"  Risk score     : {final.get('risk_score', 0):.2f}")
    print(f"{'='*62}\n")


def _display_hitl_dossier(state: dict) -> None:
    report = {}
    if state.get("audit_report"):
        try:
            report = json.loads(state["audit_report"])
        except json.JSONDecodeError:
            report = {}

    print("\n" + "="*62)
    print("  ⚠️   ESCALATED — HUMAN REVIEW REQUIRED")
    print("="*62)
    print(f"\n  Contract ID  : {state.get('contract_id', 'N/A')}")
    print(f"  Risk Score   : {state.get('risk_score', 0):.2f} / 1.00")
    print(f"\n  Audit Summary:\n  {report.get('audit_summary', 'N/A')}")

    concerns = report.get("key_concerns", [])
    if concerns:
        print("\n  Key Concerns:")
        for c in concerns:
            print(f"    • {c}")

    high = [f for f in state.get("adversarial_findings", []) if f.get("severity") == "high"]
    if high:
        print(f"\n  High-Severity Findings ({len(high)}):")
        for f in high:
            print(f"    [{f['risk_type'].upper()}] {f['clause_id']}: {f['finding']}")


if __name__ == "__main__":
    run_audit(SAMPLE_CONTRACT, "MUR-2024-0087")
