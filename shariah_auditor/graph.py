"""
graph.py — LangGraph Orchestration

This is the brain of the system. It wires all four agents into a directed graph
and defines HOW they connect, including the conditional HITL branching.

KEY LANGGRAPH CONCEPTS (for those new to agents):

  StateGraph  : A graph where each node (agent) shares a common state dict.
                Nodes read from the state and return partial updates.

  add_node()  : Register a function as a node in the graph.
                The function signature must be: fn(state: AuditState) -> dict

  add_edge()  : Always go from A → B (deterministic).

  add_conditional_edges() : Choose the next node based on a routing function.
                            Returns a string key that maps to a node name.

  interrupt() : Inside a node, pauses the ENTIRE graph and returns control
                to the caller. Execution resumes when the caller calls
                graph.invoke(Command(resume=value), config).

  MemorySaver : Stores graph state between invocations (required for HITL).
                Without this, the graph forgets state when interrupted.

GRAPH SHAPE:

  START
    │
    ▼
  [extraction]          ← parses contract into clauses
    │
    ▼
  [compliance]          ← checks clauses against BNM guidelines
    │
    ▼
  [devils_advocate]     ← adversarially probes for loopholes
    │
    ▼
  [simulator]           ← synthesises final audit report + risk score
    │
    ├─── risk < 0.6, no high flags ──► [approve] ──► END
    │
    └─── risk >= 0.6 or high flags ──► [hitl_review] ──► END
"""

from langgraph.graph import StateGraph, END, START
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import interrupt

from state import AuditState
from agents.extraction import run_extraction_agent
from agents.compliance import run_compliance_agent
from agents.devils_advocate import run_devils_advocate_agent
from agents.simulator import run_simulator_agent


# ── Node functions ─────────────────────────────────────────────────────────────
# Each node function wraps an agent. Thin wrappers kept here for graph clarity.

def extraction_node(state: AuditState) -> dict:
    return run_extraction_agent(state)


def compliance_node(state: AuditState) -> dict:
    return run_compliance_agent(state)


def devils_advocate_node(state: AuditState) -> dict:
    return run_devils_advocate_agent(state)


def simulator_node(state: AuditState) -> dict:
    return run_simulator_agent(state)


def hitl_review_node(state: AuditState) -> dict:
    """
    Human-in-the-Loop gate.

    Calling interrupt() here:
    1. Pauses graph execution immediately
    2. Serialises the payload (what to show the human) and returns it to the caller
    3. Waits — graph will not advance until the caller resumes it with Command(resume=...)

    The Shariah officer sees the audit summary, risk score, and flagged concerns,
    then provides a structured decision.
    """
    import json
    report = json.loads(state["audit_report"])

    # Build the review dossier shown to the Shariah officer
    review_payload = {
        "contract_id":         state["contract_id"],
        "risk_score":          state["risk_score"],
        "audit_summary":       report.get("audit_summary", ""),
        "key_concerns":        report.get("key_concerns", []),
        "recommendation":      report.get("recommendation", ""),
        "reasoning":           report.get("reasoning", ""),
        "conditions":          report.get("conditions", []),
        "adversarial_findings": [
            f for f in state.get("adversarial_findings", [])
            if f.get("severity") == "high"
        ],
        "instructions": (
            "Provide your decision as: "
            "{'decision': 'APPROVE' or 'REJECT', 'justification': 'your written reason'}"
        )
    }

    # Graph pauses here. main.py receives this payload and prompts the officer.
    decision = interrupt(review_payload)

    return {
        "human_decision":        decision.get("decision"),
        "officer_justification": decision.get("justification"),
    }


def approve_node(state: AuditState) -> dict:
    """Auto-approval path. Only reached when risk is low and no high-severity flags."""
    import json
    report = json.loads(state["audit_report"])
    print("\n" + "="*60)
    print("  ✅ AUTO-APPROVED: Contract cleared by audit system")
    print("="*60)
    print(f"  Risk score : {state['risk_score']:.2f}")
    print(f"  Summary    : {report.get('audit_summary', '')}")
    print("="*60 + "\n")
    return {"human_decision": "AUTO_APPROVED"}


# ── Routing function ───────────────────────────────────────────────────────────

def route_after_simulation(state: AuditState) -> str:
    """
    Called after simulator_node completes.
    Returns the NAME of the next node to execute.
    Must match the keys in the dict passed to add_conditional_edges().
    """
    if state.get("needs_human_review"):
        return "escalate"
    return "approve"


# ── Graph builder ──────────────────────────────────────────────────────────────

def build_graph():
    """
    Constructs and compiles the LangGraph state machine.

    Call this once in main.py. The returned graph object is reusable
    across multiple contract audits (each gets its own thread_id).
    """
    builder = StateGraph(AuditState)

    # Register nodes
    builder.add_node("extraction",      extraction_node)
    builder.add_node("compliance",      compliance_node)
    builder.add_node("devils_advocate", devils_advocate_node)
    builder.add_node("simulator",       simulator_node)
    builder.add_node("hitl_review",     hitl_review_node)
    builder.add_node("approve",         approve_node)

    # Wire deterministic edges (always go A → B)
    builder.add_edge(START,             "extraction")
    builder.add_edge("extraction",      "compliance")
    builder.add_edge("compliance",      "devils_advocate")
    builder.add_edge("devils_advocate", "simulator")

    # Conditional routing after simulation (go to hitl_review OR approve)
    builder.add_conditional_edges(
        "simulator",
        route_after_simulation,
        {
            "escalate": "hitl_review",
            "approve":  "approve",
        }
    )

    # Both terminal paths end at END
    builder.add_edge("hitl_review", END)
    builder.add_edge("approve",     END)

    # MemorySaver is REQUIRED for interrupt() to work.
    # It checkpoints the graph state so execution can be resumed after HITL pause.
    memory = MemorySaver()
    return builder.compile(checkpointer=memory)
