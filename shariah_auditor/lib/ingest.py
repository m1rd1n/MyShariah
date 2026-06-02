"""
lib/ingest.py — BNM Policy Document Ingestion Pipeline

WHAT THIS DOES:
1. Scans data/bnm_policies/ for all .pdf and .txt files
2. Extracts text from each file (PyMuPDF for PDFs, direct read for .txt)
3. Splits text into overlapping chunks (~400 words, 50-word overlap)
4. Embeds each chunk using the local sentence-transformer model
5. Stores all chunks + embeddings in the ChromaDB vector store

RUN THIS:
    python lib/ingest.py

When to re-run:
- When you add new BNM policy PDFs to data/bnm_policies/
- When BNM updates a guideline and you replace an existing PDF
- When you want to clear and rebuild the vector store from scratch

The ChromaDB is persisted at ./chroma_db/ — it survives between
server restarts, so you only need to re-run ingest when docs change.
"""

import os
import sys
from pathlib import Path

# Ensure project root is on sys.path when running as a script
sys.path.insert(0, str(Path(__file__).parent.parent))

import chromadb
from chromadb.config import Settings
try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    raise SystemExit("sentence-transformers not installed. Run: pip install sentence-transformers")

try:
    import fitz   # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False
    print("⚠  PyMuPDF not installed. PDF files will be skipped.")
    print("   Install with: pip install PyMuPDF")

# ── Config ────────────────────────────────────────────────────────────────────

POLICIES_DIR    = Path(__file__).parent.parent / "data" / "bnm_policies"
CHROMA_PATH     = Path(__file__).parent.parent / "chroma_db"
COLLECTION_NAME = "bnm_policies"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"

CHUNK_SIZE      = 400   # words per chunk
CHUNK_OVERLAP   = 50    # words of overlap between consecutive chunks


# ── Text extraction ───────────────────────────────────────────────────────────

def extract_text_from_pdf(path: Path) -> list[dict]:
    """
    Extracts text from a PDF page by page using PyMuPDF.
    Returns a list of dicts: {text, page, source}
    """
    if not PYMUPDF_AVAILABLE:
        return []

    pages = []
    try:
        doc = fitz.open(str(path))
        for page_num, page in enumerate(doc, start=1):
            text = page.get_text("text").strip()
            if text:   # skip blank pages
                pages.append({
                    "text":   text,
                    "page":   str(page_num),
                    "source": path.name,
                })
        doc.close()
        print(f"   ✓ Extracted {len(pages)} pages from {path.name}")
    except Exception as e:
        print(f"   ✗ Failed to read {path.name}: {e}")

    return pages


def extract_text_from_txt(path: Path) -> list[dict]:
    """
    Reads a plain-text policy document.
    Splits into logical sections using blank-line separators.
    """
    try:
        full_text = path.read_text(encoding="utf-8")
        # Split on double newlines to get sections
        raw_sections = [s.strip() for s in full_text.split("\n\n") if s.strip()]
        pages = []
        for i, section in enumerate(raw_sections):
            pages.append({
                "text":   section,
                "page":   str(i + 1),
                "source": path.name,
            })
        print(f"   ✓ Extracted {len(pages)} sections from {path.name}")
        return pages
    except Exception as e:
        print(f"   ✗ Failed to read {path.name}: {e}")
        return []


# ── Text chunking ─────────────────────────────────────────────────────────────

def chunk_text(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """
    Splits text into overlapping word-level chunks.

    Example with size=5, overlap=2:
      words = [A, B, C, D, E, F, G]
      chunk 1: [A, B, C, D, E]
      chunk 2: [D, E, F, G]   ← overlaps with chunk 1

    The overlap ensures that context spanning a chunk boundary is not lost.
    """
    words = text.split()
    chunks = []
    start = 0

    while start < len(words):
        end = start + size
        chunk = " ".join(words[start:end])
        if chunk.strip():
            chunks.append(chunk)
        start += size - overlap   # slide forward by (size - overlap)

    return chunks


def detect_section(text: str) -> str:
    """
    Tries to extract a section heading from the start of a text block.
    Used as metadata to make retrieval results more interpretable.
    """
    first_line = text.split("\n")[0].strip()
    # Treat lines under 80 chars with no period as likely headings
    if len(first_line) < 80 and "." not in first_line and first_line:
        return first_line[:60]
    return ""


# ── Main ingestion ────────────────────────────────────────────────────────────

def ingest(clear_existing: bool = False) -> None:
    """
    Full ingestion pipeline:
    1. Scan data/bnm_policies/ for supported files
    2. Extract and chunk text from each file
    3. Embed chunks with sentence-transformers
    4. Store in ChromaDB
    """
    print("\n" + "="*60)
    print("  BNM POLICY INGESTION PIPELINE")
    print("="*60)

    # ── Step 1: Find source files ─────────────────────────────────────────
    supported = [".pdf", ".txt"]
    files = [f for f in POLICIES_DIR.iterdir() if f.suffix.lower() in supported]

    if not files:
        print(f"\n⚠  No policy files found in {POLICIES_DIR}")
        print("   Add .pdf or .txt files and re-run.")
        return

    print(f"\nFound {len(files)} policy file(s) in {POLICIES_DIR.name}/:")
    for f in files:
        print(f"   • {f.name}")

    # ── Step 2: Load embedding model ──────────────────────────────────────
    print(f"\nLoading embedding model: {EMBEDDING_MODEL}")
    print("(This downloads ~80MB on first run — subsequent runs use cache)")
    model = SentenceTransformer(EMBEDDING_MODEL)
    print("✓ Model ready")

    # ── Step 3: Connect to ChromaDB ───────────────────────────────────────
    CHROMA_PATH.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(
        path=str(CHROMA_PATH),
        settings=Settings(anonymized_telemetry=False),
    )

    if clear_existing:
        print(f"\nClearing existing '{COLLECTION_NAME}' collection...")
        try:
            client.delete_collection(COLLECTION_NAME)
            print("✓ Cleared")
        except Exception:
            pass

    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )
    existing_count = collection.count()
    print(f"\nChromaDB collection '{COLLECTION_NAME}': {existing_count} existing chunks")

    # ── Step 4: Extract, chunk, embed, store ─────────────────────────────
    total_chunks = 0

    for file_path in files:
        print(f"\nProcessing: {file_path.name}")

        # Extract pages/sections from file
        if file_path.suffix.lower() == ".pdf":
            pages = extract_text_from_pdf(file_path)
        else:
            pages = extract_text_from_txt(file_path)

        if not pages:
            print(f"   ⚠ No text extracted. Skipping.")
            continue

        # Build chunks with metadata
        file_chunks   = []
        file_metadata = []
        file_ids      = []

        for page_data in pages:
            raw_chunks = chunk_text(page_data["text"])
            for chunk_idx, chunk in enumerate(raw_chunks):
                chunk_id = f"{file_path.stem}_p{page_data['page']}_c{chunk_idx}"

                file_chunks.append(chunk)
                file_metadata.append({
                    "source":  page_data["source"],
                    "page":    page_data["page"],
                    "section": detect_section(chunk),
                })
                file_ids.append(chunk_id)

        if not file_chunks:
            continue

        # Embed all chunks for this file in one batch
        print(f"   Embedding {len(file_chunks)} chunks...")
        embeddings = model.encode(file_chunks, show_progress_bar=False).tolist()

        # Upsert into ChromaDB (upsert = insert or update if ID exists)
        # Process in batches of 100 to avoid memory issues with large docs
        batch_size = 100
        for i in range(0, len(file_chunks), batch_size):
            collection.upsert(
                ids=        file_ids[i:i+batch_size],
                documents=  file_chunks[i:i+batch_size],
                embeddings= embeddings[i:i+batch_size],
                metadatas=  file_metadata[i:i+batch_size],
            )

        total_chunks += len(file_chunks)
        print(f"   ✓ {len(file_chunks)} chunks stored")

    # ── Step 5: Summary ───────────────────────────────────────────────────
    final_count = collection.count()
    print(f"\n{'='*60}")
    print(f"  INGESTION COMPLETE")
    print(f"  Files processed : {len(files)}")
    print(f"  Chunks added    : {total_chunks}")
    print(f"  Total in store  : {final_count}")
    print(f"  ChromaDB path   : {CHROMA_PATH}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Ingest BNM policy documents into ChromaDB")
    parser.add_argument(
        "--clear", action="store_true",
        help="Clear the existing collection before ingesting (full rebuild)"
    )
    args = parser.parse_args()
    ingest(clear_existing=args.clear)
