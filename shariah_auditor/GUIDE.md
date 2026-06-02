# Shariah Contract Audit — Agent Pipeline Implementation Guide

## What you're building

A 4-agent LangGraph pipeline that autonomously audits Murabaha contracts
against BNM Shariah guidelines, with a human-in-the-loop gate for high-risk cases.

```
START → [Extraction] → [Compliance] → [Devil's Advocate] → [Simulator]
                                                                  │
                                            risk < 0.6 ──────► [Auto-Approve] → END
                                            risk ≥ 0.6 ──────► [HITL Review]  → END
```

---

## Project structure

```
shariah_auditor/
├── .env.example              ← copy to .env and add your API key
├── requirements.txt
├── state.py                  ← shared data structure (all agents read/write this)
├── graph.py                  ← LangGraph wiring (the orchestrator)
├── main.py                   ← entry point + HITL console handler
└── agents/
    ├── __init__.py
    ├── extraction.py         ← Agent 1: parses contract into clauses
    ├── compliance.py         ← Agent 2: checks clauses vs BNM guidelines
    ├── devils_advocate.py    ← Agent 3: adversarially probes for loopholes
    └── simulator.py          ← Agent 4: synthesises final audit report
```

---

## Setup

```bash
# 1. Clone / copy the project folder
cd shariah_auditor

# 2. Create a virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Add your API key
cp .env.example .env
# Edit .env and replace sk-ant-your-key-here with your real key

# 5. Run
python main.py
```

---

## Key concept: LangGraph state

The `AuditState` (in `state.py`) is a TypedDict that flows through every agent.
Think of it as a shared clipboard.

```
Initial state                  After extraction          After compliance
─────────────────              ─────────────────         ─────────────────
contract_text: "..."    ──►    clauses: [C001,...]  ──►  compliance_report: [...]
contract_id: "MUR-..."         ...                        ...
clauses: []
compliance_report: []
...
```

Each agent function returns only the keys it changed.
LangGraph merges the update back into the full state automatically.

```python
# Example: extraction agent only returns the 'clauses' key
def run_extraction_agent(state: AuditState) -> dict:
    clauses = ...  # call Claude, parse response
    return {"clauses": clauses}  # LangGraph merges this into the full state
```

---

## Key concept: HITL with interrupt()

When the simulator flags a contract as high-risk, the graph pauses at
`hitl_review_node` using `interrupt()`. Here is what happens:

```
graph.invoke(initial_state, config)
    ↓
[extraction] → [compliance] → [devils_advocate] → [simulator]
    ↓
[hitl_review] calls interrupt(payload)
    ↓
graph.invoke() RETURNS EARLY — execution paused
    ↓
main.py checks: graph.get_state(config).next  →  truthy = paused
    ↓
Display dossier to Shariah officer
Officer inputs decision
    ↓
graph.invoke(Command(resume={decision}), config)  →  graph resumes from pause point
    ↓
hitl_review_node receives the decision and writes it to state
    ↓
graph reaches END
```

The `MemorySaver` checkpointer in `graph.py` stores the state between
the pause and the resume. Without it, interrupt() would not work.

---

## How the routing works

After `simulator_node` runs, LangGraph calls `route_after_simulation()`:

```python
def route_after_simulation(state: AuditState) -> str:
    if state.get("needs_human_review"):
        return "escalate"   # → hitl_review node
    return "approve"        # → approve node
```

`needs_human_review` is set to True by the simulator if ANY of these are true:
- Simulator recommends "ESCALATE"
- Risk score >= 0.6
- Any adversarial finding with severity "high"
- Contradictory findings (compliance said OK, devil's advocate said HIGH)

---

## Understanding the sample contract

The sample contract in `main.py` has 4 intentional Shariah issues:

| Clause | Issue | Type |
|--------|-------|------|
| Clause 1 | Profit rate adjustable quarterly via KLIBOR | Riba |
| Clause 3 | Late payment charges go to bank income | Ta'widh violation |
| Clause 4 | Direct delivery before constructive possession | Ownership gap |
| Clause 6 | Dual jurisdiction, bank chooses forum | Gharar / conflict |

Running the system on this contract should produce a risk score > 0.6
and trigger the HITL escalation path.

---

## Customising for your demo

### Swap the BNM policy context for real RAG

In `agents/compliance.py`, replace the hardcoded `BNM_POLICY_CONTEXT` string
with a ChromaDB query:

```python
# Instead of hardcoded string:
import chromadb
client_db = chromadb.Client()
collection = client_db.get_collection("bnm_policies")
results = collection.query(query_texts=[clause_text], n_results=3)
policy_context = "\n".join(results["documents"][0])
```

### Add real PDF parsing

In `main.py`, load a real PDF instead of the sample string:

```python
import fitz  # PyMuPDF

def load_contract_pdf(path: str) -> str:
    doc = fitz.open(path)
    return "\n".join(page.get_text() for page in doc)

contract_text = load_contract_pdf("contracts/MUR-2024-0087.pdf")
run_audit(contract_text, "MUR-2024-0087")
```

### Replace console HITL with a web UI

The `interrupt()` payload can be sent to any frontend.
Replace the `input()` prompts in `main.py` with API calls to your
Next.js frontend. The graph stays paused until you call
`graph.invoke(Command(resume=...), config)` from your backend route.

---

## Common errors

| Error | Cause | Fix |
|-------|-------|-----|
| `AuthenticationError` | Missing or wrong API key | Check `.env` file |
| `json.JSONDecodeError` | Claude returned markdown fences | Already handled by `_clean_json()` |
| `KeyError: 'next'` | LangGraph version mismatch | `pip install --upgrade langgraph` |
| Graph never pauses | `MemorySaver` not passed to `compile()` | Check `graph.py` build_graph() |
| `ModuleNotFoundError` | Not in venv or missing package | `pip install -r requirements.txt` |

---

## Next steps after the demo

1. **RAG**: Replace hardcoded BNM context with ChromaDB vector search
2. **PDF ingestion**: Add PyMuPDF for real contract uploads
3. **Web UI**: Build the Shariah officer dashboard in Next.js
4. **Database**: Log all audit decisions to Supabase for the audit trail
5. **Parallel agents**: Run compliance and devil's advocate simultaneously
   using LangGraph's `Send` API for faster throughput
6. **Notifications**: Send HITL escalation alerts via email or Telegram Bot
