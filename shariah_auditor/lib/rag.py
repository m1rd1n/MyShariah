"""
lib/rag.py — RAG (Retrieval-Augmented Generation) module

WHAT THIS REPLACES:
Previously, compliance.py and devils_advocate.py had a hardcoded
BNM_POLICY_CONTEXT string. This module replaces that with a dynamic
ChromaDB query — retrieving only the most relevant policy passages
for each specific clause being checked.

WHY THIS IS BETTER:
- Scales to hundreds of policy documents without hitting context limits
- Retrieves clause-specific context (not a one-size-fits-all string)
- Adding new BNM guidelines = just run ingest.py again

HOW IT WORKS:
1. At import time, connect to the persistent ChromaDB on disk
2. Load the sentence-transformer model (cached after first download)
3. query_policy(clause_text, n=4) embeds the clause and finds the
   top-N most semantically similar policy chunks in the vector store
4. Returns a formatted string ready to inject into a Claude prompt

FIRST-TIME SETUP:
Run `python lib/ingest.py` once before using the agents.
The ChromaDB will be created at ./chroma_db/ and persisted there.
"""

import os
from pathlib import Path
from typing import Optional

import chromadb
from chromadb.config import Settings
try:
    from sentence_transformers import SentenceTransformer
    _ST_AVAILABLE = True
except ImportError:
    _ST_AVAILABLE = False
    SentenceTransformer = None

# ── Constants ────────────────────────────────────────────────────────────────

CHROMA_PATH      = Path(__file__).parent.parent / "chroma_db"
COLLECTION_NAME  = "bnm_policies"
EMBEDDING_MODEL  = "all-MiniLM-L6-v2"   # ~80MB, downloads once, runs on CPU

# Fallback context used when ChromaDB hasn't been seeded yet
# (same as the old hardcoded string — ensures agents always work)
_FALLBACK_CONTEXT = """
Key BNM Shariah Governance Framework Principles (SGF 2019):

1. RIBA — SGF 2019, Para 7.1: Profit rate must be FIXED at contract inception.
   Variable or KLIBOR-linked profit rates are non-compliant.

2. GHARAR — SGF 2019, Para 7.3: All material terms must be certain and known.
   Vague or undefined terms constitute gharar and void the contract.

3. MAYSIR — SGF 2019, Para 7.5: Obligations must not depend on speculative events.

4. OWNERSHIP — SGF 2019, Para 8.2: Bank must hold constructive possession BEFORE
   selling to customer. Direct delivery only valid after bank owns the asset.

5. TA'WIDH — BNM/RH/PD 029-7: Late payment charges must go to charity, NOT bank income.
   Cap: 1% p.a. or actual loss, whichever is lower.

6. CROSS-BORDER — AAOIFI SS No. 8: Single governing law required.
   Dual jurisdiction with unilateral forum selection introduces gharar.
"""

# ── Module-level singletons (loaded once, reused across all agent calls) ─────
_chroma_client:     Optional[chromadb.PersistentClient]  = None
_collection:        Optional[chromadb.Collection]         = None
_embedding_model:   Optional[SentenceTransformer]         = None
_rag_available:     bool                                  = False


def _init() -> None:
    """
    Lazy initialisation — called on first query_policy() call.
    Loads ChromaDB and the embedding model into module-level singletons.
    Silently falls back if ChromaDB is empty or not yet seeded.
    """
    global _chroma_client, _collection, _embedding_model, _rag_available

    if _embedding_model is not None:
        return  # Already initialised

    try:
        print("   [RAG] Loading sentence-transformer model...")
        _embedding_model = SentenceTransformer(EMBEDDING_MODEL)

        print("   [RAG] Connecting to ChromaDB...")
        _chroma_client = chromadb.PersistentClient(
            path=str(CHROMA_PATH),
            settings=Settings(anonymized_telemetry=False),
        )
        _collection = _chroma_client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )

        count = _collection.count()
        if count == 0:
            print("   [RAG] ⚠  ChromaDB is empty — run `python lib/ingest.py` to seed it.")
            print("   [RAG] ↳  Falling back to hardcoded policy context for now.")
            _rag_available = False
        else:
            print(f"   [RAG] ✓ ChromaDB ready — {count} policy chunks loaded.")
            _rag_available = True

    except Exception as e:
        print(f"   [RAG] ⚠  Initialisation failed ({e}). Using fallback context.")
        _rag_available = False


def query_policy(clause_text: str, n_results: int = 4) -> str:
    """
    Retrieves the most relevant BNM policy passages for a given clause.

    Args:
        clause_text:  The raw contract clause to find policy context for.
        n_results:    Number of top policy chunks to retrieve (default 4).

    Returns:
        A formatted string of relevant policy passages, ready to inject
        into a Claude system prompt. Falls back to hardcoded context if
        ChromaDB is not seeded.

    Example:
        context = query_policy("The profit rate shall be adjusted quarterly
                                based on KLIBOR movements.")
        # → Returns SGF 2019 Para 7.1 passages about fixed profit rates
    """
    _init()

    if not _rag_available:
        return _FALLBACK_CONTEXT

    try:
        # Embed the clause text using the local model
        query_embedding = _embedding_model.encode(clause_text).tolist()

        # Query ChromaDB for top-N semantically similar chunks
        results = _collection.query(
            query_embeddings=[query_embedding],
            n_results=min(n_results, _collection.count()),
            include=["documents", "metadatas", "distances"],
        )

        docs      = results["documents"][0]
        metadatas = results["metadatas"][0]
        distances = results["distances"][0]

        if not docs:
            return _FALLBACK_CONTEXT

        # Format retrieved chunks into a readable context block
        context_parts = ["=== RETRIEVED BNM POLICY CONTEXT ===\n"]
        for i, (doc, meta, dist) in enumerate(zip(docs, metadatas, distances)):
            relevance = round((1 - dist) * 100, 1)  # cosine similarity → %
            source    = meta.get("source", "Unknown")
            section   = meta.get("section", "")
            page      = meta.get("page", "")

            header = f"[{i+1}] Source: {source}"
            if section: header += f" | Section: {section}"
            if page:    header += f" | Page: {page}"
            header += f" | Relevance: {relevance}%"

            context_parts.append(header)
            context_parts.append(doc)
            context_parts.append("")   # blank line between chunks

        return "\n".join(context_parts)

    except Exception as e:
        print(f"   [RAG] Query failed ({e}). Using fallback context.")
        return _FALLBACK_CONTEXT


def get_collection_stats() -> dict:
    """Returns basic stats about the ChromaDB collection (for debugging)."""
    _init()
    if not _rag_available or _collection is None:
        return {"status": "unavailable", "count": 0}
    return {
        "status":     "ready",
        "count":      _collection.count(),
        "model":      EMBEDDING_MODEL,
        "chroma_path": str(CHROMA_PATH),
    }
