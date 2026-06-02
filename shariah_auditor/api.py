"""
api.py — FastAPI server for the Shariah Audit backend

WHY THIS EXISTS:
main.py is a CLI script — fine for local testing but can't receive
HTTP requests from the Next.js dashboard. This file exposes the same
pipeline as a REST API that Railway will run in production.

ENDPOINTS:
  POST /audit/start          Start a new audit (runs pipeline in background)
  GET  /audit/{id}           Get current audit status (reads from Supabase)
  POST /audit/{id}/review    Submit officer HITL decision
  GET  /health               Health check (used by Railway)

RUN LOCALLY:
  uvicorn api:app --reload --port 8000
"""

import asyncio
import json
import os
from contextlib import asynccontextmanager
from typing import Optional

from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from langgraph.types import Command
from pydantic import BaseModel

load_dotenv()

# ── Lazy imports (agents need ANTHROPIC_API_KEY set first) ────────────────────
from graph import build_graph
from lib.db import audit_db

# ── In-memory graph store (MVP — one Railway instance is enough for demo) ─────
# Stores active LangGraph instances keyed by contract_id so we can
# resume paused graphs when the officer submits a review decision.
_active_graphs: dict = {}   # contract_id -> (graph, config)


# ── FastAPI app ───────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Shariah Audit API starting...")
    yield
    print("Shariah Audit API shutting down.")

app = FastAPI(
    title="Shariah Audit API",
    description="Agentic Shariah contract auditing — Bank Islam Malaysia",
    version="1.0.0",
    lifespan=lifespan,
)

# Allow Next.js frontend to call this API (update origins for production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",                        # local dev
        os.environ.get("FRONTEND_URL", ""),             # set in Railway env vars
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request / Response models ─────────────────────────────────────────────────

class StartAuditRequest(BaseModel):
    contract_id:   str
    contract_text: str

class ReviewRequest(BaseModel):
    decision:      str   # "APPROVE" | "REJECT"
    justification: str
    officer_name:  str


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    """Railway uses this to confirm the service is up."""
    return {"status": "ok", "service": "shariah-audit-api"}


@app.post("/audit/start")
async def start_audit(req: StartAuditRequest, background: BackgroundTasks):
    """
    Starts the audit pipeline in the background.
    The Supabase record is created by the Next.js API route before this is called,
    so we skip creation here and go straight to running the pipeline.
    Returns immediately — the frontend polls /audit/{id} for live status.
    """
    # Run the full pipeline in the background (non-blocking)
    background.add_task(_run_pipeline, req.contract_id, req.contract_text)

    return {"contract_id": req.contract_id, "status": "started"}


@app.get("/audit/{contract_id}")
async def get_audit(contract_id: str):
    """Returns the current audit state from Supabase."""
    from supabase import create_client
    client = create_client(
        os.environ["SUPABASE_URL"],
        os.environ["SUPABASE_SERVICE_KEY"],
    )
    result = client.table("audits").select("*").eq("contract_id", contract_id).single().execute()
    if not result.data:
        raise HTTPException(404, f"Audit not found: {contract_id}")
    return result.data


@app.post("/audit/{contract_id}/review")
async def submit_review(contract_id: str, req: ReviewRequest):
    """
    Receives the Shariah officer's decision.
    If the LangGraph pipeline is paused at HITL, resumes it.
    Either way, persists the decision to Supabase.
    """
    if req.decision not in ("APPROVE", "REJECT"):
        raise HTTPException(400, "Decision must be APPROVE or REJECT")
    if not req.justification.strip():
        raise HTTPException(400, "Justification is required")
    if not req.officer_name.strip():
        raise HTTPException(400, "Officer name is required")

    # Resume LangGraph if still paused in memory
    if contract_id in _active_graphs:
        graph, config = _active_graphs[contract_id]
        graph.invoke(
            Command(resume={
                "decision":      req.decision,
                "justification": req.justification,
            }),
            config,
        )
        del _active_graphs[contract_id]

    # Persist decision to Supabase (immutable audit trail)
    audit_db.record_decision(
        contract_id,
        req.decision,
        req.justification,
        req.officer_name,
    )

    return {
        "success":     True,
        "contract_id": contract_id,
        "decision":    req.decision,
    }


# ── Background pipeline runner ────────────────────────────────────────────────

async def _run_pipeline(contract_id: str, contract_text: str):
    """
    Runs the full LangGraph audit pipeline in a background task.
    Writes results to Supabase at each stage via audit_db.
    Stores the graph in _active_graphs if it pauses at HITL.
    """
    graph  = build_graph()
    config = {"configurable": {"thread_id": contract_id}}

    _active_graphs[contract_id] = (graph, config)

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

    try:
        for event in graph.stream(initial_state, config, stream_mode="updates"):
            for node_name, updates in event.items():

                if node_name == "extraction" and updates.get("clauses"):
                    audit_db.write_clauses(contract_id, updates["clauses"])

                elif node_name == "compliance" and updates.get("compliance_report"):
                    audit_db.write_compliance(contract_id, updates["compliance_report"])

                elif node_name == "devils_advocate" and updates.get("adversarial_findings") is not None:
                    audit_db.write_adversarial(
                        contract_id,
                        updates.get("adversarial_findings", []),
                        updates.get("devils_advocate_iterations", 0),
                    )

                elif node_name == "simulator" and updates.get("audit_report"):
                    audit_db.write_final(
                        contract_id,
                        updates["audit_report"],
                        updates.get("risk_score", 0.0),
                        updates.get("needs_human_review", False),
                    )

                elif node_name == "approve":
                    audit_db.record_decision(contract_id, "AUTO_APPROVED", "", "system")
                    if contract_id in _active_graphs:
                        del _active_graphs[contract_id]

    except Exception as e:
        print(f"[pipeline] Error for {contract_id}: {e}")
        audit_db.log_event(contract_id, "error", {"message": str(e)})
        if contract_id in _active_graphs:
            del _active_graphs[contract_id]
