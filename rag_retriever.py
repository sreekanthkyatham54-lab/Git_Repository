"""
rag_retriever.py — RAG Retrieval via Pinecone (cloud) or SQLite (local fallback)
=================================================================================
Priority:
  1. Pinecone  — used on Streamlit Cloud (no local DB needed)
  2. SQLite    — used locally if Pinecone not configured

Both backends expose the same interface:
  retrieve_chunks(ipo_id, question, top_k)
  retrieve_for_scorecard(ipo_id)
  has_rag_index(ipo_id)

No section labels — pure cosine similarity on all chunks.
"""

import os, json
import numpy as np
from dotenv import load_dotenv

load_dotenv()

# ── CONFIG ────────────────────────────────────────────────────────────────────
DB_PATH        = os.path.join(os.path.dirname(__file__), "data", "drhp.db")
PINECONE_INDEX = "tradesage-drhp"
TOP_K          = 12   # Cast wider net — filter by similarity threshold
MIN_SIMILARITY = 0.25

SCORECARD_QUERIES = {
    "risks":      "risk factors investment risks red flags material risks threats to business",
    "financials": "revenue from operations profit after tax PAT EBITDA net worth financial performance restated financial statements",
    "valuation":  "basis of offer price quantitative factors EPS earnings per share P/E ratio price earnings weighted average NAV net asset value RoNW return on net worth",
    "peers":      "peer comparison listed industry peers comparable companies Indira IVF fertility sector competition",
    "promoters":  "promoter background experience qualifications managing director board of directors",
    "litigation": "outstanding litigation legal proceedings court cases tax proceedings regulatory actions",
    "objects":    "objects of the offer use of IPO proceeds capital expenditure working capital expansion",
}

# ── EMBEDDING MODEL ───────────────────────────────────────────────────────────
_model = None

def get_embedding_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model

def embed_question(question: str) -> list:
    return get_embedding_model().encode([question])[0].tolist()

# ── BACKEND DETECTION ─────────────────────────────────────────────────────────
_pinecone_index   = None
_pinecone_checked = False

def get_pinecone_index():
    global _pinecone_index, _pinecone_checked
    if _pinecone_checked:
        return _pinecone_index
    _pinecone_checked = True
    api_key = os.environ.get("PINECONE_API_KEY")
    if not api_key:
        return None
    try:
        from pinecone import Pinecone
        pc       = Pinecone(api_key=api_key)
        existing = [idx.name for idx in pc.list_indexes()]
        if PINECONE_INDEX not in existing:
            print(f"  Pinecone index '{PINECONE_INDEX}' not found — using SQLite")
            return None
        _pinecone_index = pc.Index(PINECONE_INDEX)
        print("  Using Pinecone for RAG retrieval")
        return _pinecone_index
    except Exception as e:
        print(f"  Pinecone connection failed: {e} — using SQLite")
        return None

def use_pinecone() -> bool:
    return get_pinecone_index() is not None

# ── PINECONE RETRIEVAL ────────────────────────────────────────────────────────
def _pinecone_query(ipo_id: str, embedding: list, top_k: int) -> list:
    index = get_pinecone_index()
    if not index: return []
    try:
        results = index.query(
            vector=embedding,
            top_k=top_k,
            filter={"ipo_id": {"$eq": ipo_id}},
            include_metadata=True,
        )
        chunks = []
        for match in results.matches:
            if match.score < MIN_SIMILARITY: continue
            meta = match.metadata
            chunks.append({
                "chunk_id":    match.id,
                "page_number": int(meta.get("page_number", 0)),
                "text":        meta.get("text", ""),
                "similarity":  round(float(match.score), 4),
            })
        return chunks
    except Exception as e:
        print(f"  Pinecone query error: {e}")
        return []

# ── SQLITE RETRIEVAL ──────────────────────────────────────────────────────────
def _sqlite_query(ipo_id: str, embedding: list, top_k: int) -> list:
    import sqlite3
    if not os.path.exists(DB_PATH): return []
    conn = sqlite3.connect(DB_PATH)
    try:
        rows = conn.execute("""
            SELECT chunk_id, page_number, text, embedding
            FROM chunks WHERE ipo_id = ?
            ORDER BY chunk_index
        """, (ipo_id,)).fetchall()
    finally:
        conn.close()
    a  = np.array(embedding, dtype=np.float32)
    na = np.linalg.norm(a)
    scored = []
    for chunk_id, page_number, text, embedding_json in rows:
        if not embedding_json: continue
        try:
            b  = np.array(json.loads(embedding_json), dtype=np.float32)
            nb = np.linalg.norm(b)
            if na == 0 or nb == 0: continue
            score = float(np.dot(a, b) / (na * nb))
            if score >= MIN_SIMILARITY:
                scored.append({
                    "chunk_id":    chunk_id,
                    "page_number": page_number,
                    "text":        text,
                    "similarity":  round(score, 4),
                })
        except Exception:
            continue
    scored.sort(key=lambda x: x["similarity"], reverse=True)
    return scored[:top_k]

def _query(ipo_id: str, embedding: list, top_k: int) -> list:
    if use_pinecone():
        return _pinecone_query(ipo_id, embedding, top_k)
    return _sqlite_query(ipo_id, embedding, top_k)

# ── PUBLIC API ────────────────────────────────────────────────────────────────
def retrieve_chunks(ipo_id: str, question: str, top_k: int = TOP_K) -> list:
    embedding = embed_question(question)
    chunks    = _query(ipo_id, embedding, top_k)
    chunks.sort(key=lambda x: x["page_number"])
    return chunks

def retrieve_for_scorecard(ipo_id: str) -> list:
    seen_ids   = set()
    all_chunks = []
    for topic, query in SCORECARD_QUERIES.items():
        embedding = embed_question(query)
        results   = _query(ipo_id, embedding, top_k=10)
        count = 0
        for chunk in results:
            if chunk["chunk_id"] in seen_ids: continue
            seen_ids.add(chunk["chunk_id"])
            chunk["topic"] = topic
            all_chunks.append(chunk)
            count += 1
            if count >= 2: break
    all_chunks.sort(key=lambda x: x["page_number"])
    return all_chunks

def has_rag_index(ipo_id: str) -> bool:
    if use_pinecone():
        try:
            index   = get_pinecone_index()
            results = index.query(
                vector=[0.0] * 384, top_k=1,
                filter={"ipo_id": {"$eq": ipo_id}},
                include_metadata=False,
            )
            return len(results.matches) > 0
        except Exception:
            return False
    try:
        import sqlite3
        conn  = sqlite3.connect(DB_PATH)
        count = conn.execute(
            "SELECT COUNT(*) FROM chunks WHERE ipo_id = ?", (ipo_id,)
        ).fetchone()[0]
        conn.close()
        return count > 0
    except Exception:
        return False

def get_index_stats(ipo_id: str) -> dict:
    if use_pinecone():
        try:
            index   = get_pinecone_index()
            results = index.query(
                vector=[0.0] * 384, top_k=10000,
                filter={"ipo_id": {"$eq": ipo_id}},
                include_metadata=True,
            )
            pages = [int(m.metadata.get("page_number", 0)) for m in results.matches]
            return {
                "total_chunks": len(results.matches),
                "page_range":   f"{min(pages)}-{max(pages)}" if pages else "-",
                "backend":      "Pinecone",
            }
        except Exception:
            return {"total_chunks": 0, "page_range": "-", "backend": "Pinecone"}
    try:
        import sqlite3
        conn  = sqlite3.connect(DB_PATH)
        total = conn.execute(
            "SELECT COUNT(*) FROM chunks WHERE ipo_id = ?", (ipo_id,)
        ).fetchone()[0]
        pages = conn.execute(
            "SELECT MIN(page_number), MAX(page_number) FROM chunks WHERE ipo_id = ?",
            (ipo_id,)
        ).fetchone()
        conn.close()
        return {
            "total_chunks": total,
            "page_range":   f"{pages[0]}-{pages[1]}" if pages[0] else "-",
            "backend":      "SQLite",
        }
    except Exception:
        return {"total_chunks": 0, "page_range": "-", "backend": "SQLite"}
