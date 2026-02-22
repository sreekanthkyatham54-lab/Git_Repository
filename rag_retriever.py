"""
rag_retriever.py — RAG Retrieval: Find relevant chunks for a user question
==========================================================================
At query time:
  1. Embed the user's question (same model as indexer)
  2. Load all chunk embeddings for that IPO from SQLite
  3. Calculate cosine similarity between question and every chunk
  4. Return top-k most relevant chunks with page citations

No external vector DB needed — SQLite handles storage,
Python handles similarity math. Fast enough for <500 chunks per IPO.
"""

import json, os, sqlite3
import numpy as np

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "drhp.db")

# How many chunks to return to Claude
TOP_K = 6

# Minimum similarity score to include a chunk (0-1 scale)
MIN_SIMILARITY = 0.25


# ── EMBEDDING ─────────────────────────────────────────────────────────────────
_model = None

def get_embedding_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


def embed_question(question: str) -> list:
    """Embed a single question string. Returns embedding vector as list."""
    model = get_embedding_model()
    return model.encode([question])[0].tolist()


# ── SIMILARITY ────────────────────────────────────────────────────────────────
def cosine_similarity(vec_a: list, vec_b: list) -> float:
    """
    Cosine similarity between two vectors.
    Returns float between -1 and 1 (higher = more similar).
    For normalized embeddings this is equivalent to dot product.
    """
    a = np.array(vec_a, dtype=np.float32)
    b = np.array(vec_b, dtype=np.float32)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


# ── RETRIEVAL ─────────────────────────────────────────────────────────────────
def retrieve_chunks(ipo_id: str, question: str, top_k: int = TOP_K) -> list[dict]:
    """
    Main retrieval function.
    
    Args:
        ipo_id:   e.g. "ipo_005"
        question: user's question in natural language
        top_k:    number of chunks to return
        
    Returns:
        List of dicts sorted by relevance:
        [
          {
            "text":        "Revenue from Operations for FY2024...",
            "page_number": 47,
            "section":     "financials",
            "similarity":  0.89,
            "chunk_id":    "ipo_005_chunk_0047",
          },
          ...
        ]
    """
    conn = sqlite3.connect(DB_PATH)
    try:
        # Load all chunks for this IPO
        rows = conn.execute("""
            SELECT chunk_id, page_number, section, text, embedding
            FROM chunks
            WHERE ipo_id = ?
            ORDER BY chunk_index
        """, (ipo_id,)).fetchall()

        if not rows:
            return []

        # Embed the question
        q_embedding = embed_question(question)

        # Calculate similarity for every chunk
        scored = []
        for chunk_id, page_number, section, text, embedding_json in rows:
            if not embedding_json:
                continue
            try:
                chunk_embedding = json.loads(embedding_json)
                score = cosine_similarity(q_embedding, chunk_embedding)
                if score >= MIN_SIMILARITY:
                    scored.append({
                        "chunk_id":    chunk_id,
                        "page_number": page_number,
                        "section":     section or "general",
                        "text":        text,
                        "similarity":  round(score, 4),
                    })
            except Exception:
                continue

        # Sort by similarity descending
        scored.sort(key=lambda x: x["similarity"], reverse=True)

        # Take top_k
        top = scored[:top_k]

        # Re-sort by page number so context flows naturally for Claude
        top.sort(key=lambda x: (x["page_number"], x["similarity"]))

        return top

    finally:
        conn.close()


def retrieve_for_scorecard(ipo_id: str) -> list[dict]:
    """
    For AI Scorecard — retrieve representative chunks from each section.
    Gets best chunk from each of the 6 key sections.
    """
    SCORECARD_QUESTIONS = {
        "risk_factors": "what are the main risks and red flags investors should know",
        "financials":   "revenue profit financial performance growth trends",
        "objects":      "how will IPO proceeds be used capital expenditure",
        "promoters":    "who are the promoters background experience management",
        "litigation":   "outstanding litigation legal cases court proceedings",
        "overview":     "business overview what does the company do products services",
    }

    conn = sqlite3.connect(DB_PATH)
    all_chunks = []

    try:
        for section, question in SCORECARD_QUESTIONS.items():
            q_embedding = embed_question(question)

            rows = conn.execute("""
                SELECT chunk_id, page_number, section, text, embedding
                FROM chunks
                WHERE ipo_id = ? AND section = ?
                ORDER BY chunk_index
            """, (ipo_id, section)).fetchall()

            if not rows:
                # Fall back to general chunks if section not labeled
                rows = conn.execute("""
                    SELECT chunk_id, page_number, section, text, embedding
                    FROM chunks
                    WHERE ipo_id = ?
                    ORDER BY chunk_index
                    LIMIT 50
                """, (ipo_id,)).fetchall()

            best_score  = -1
            best_chunk  = None

            for chunk_id, page_number, sec, text, embedding_json in rows:
                if not embedding_json:
                    continue
                try:
                    chunk_embedding = json.loads(embedding_json)
                    score = cosine_similarity(q_embedding, chunk_embedding)
                    if score > best_score:
                        best_score = score
                        best_chunk = {
                            "chunk_id":    chunk_id,
                            "page_number": page_number,
                            "section":     section,
                            "text":        text,
                            "similarity":  round(score, 4),
                        }
                except Exception:
                    continue

            if best_chunk and best_score >= MIN_SIMILARITY:
                all_chunks.append(best_chunk)

    finally:
        conn.close()

    # Sort by page number for natural reading order
    all_chunks.sort(key=lambda x: x["page_number"])
    return all_chunks


def has_rag_index(ipo_id: str) -> bool:
    """Check if this IPO has been indexed for RAG."""
    try:
        conn = sqlite3.connect(DB_PATH)
        count = conn.execute(
            "SELECT COUNT(*) FROM chunks WHERE ipo_id = ?", (ipo_id,)
        ).fetchone()[0]
        conn.close()
        return count > 0
    except Exception:
        return False


def get_index_stats(ipo_id: str) -> dict:
    """Return indexing stats for an IPO — shown in UI."""
    try:
        conn = sqlite3.connect(DB_PATH)
        total = conn.execute(
            "SELECT COUNT(*) FROM chunks WHERE ipo_id = ?", (ipo_id,)
        ).fetchone()[0]

        sections = conn.execute("""
            SELECT section, COUNT(*) as n
            FROM chunks WHERE ipo_id = ?
            GROUP BY section ORDER BY n DESC
        """, (ipo_id,)).fetchall()

        pages = conn.execute("""
            SELECT MIN(page_number), MAX(page_number)
            FROM chunks WHERE ipo_id = ?
        """, (ipo_id,)).fetchone()

        conn.close()
        return {
            "total_chunks":  total,
            "sections":      {s: n for s, n in sections},
            "page_range":    f"{pages[0]}–{pages[1]}" if pages[0] else "—",
        }
    except Exception:
        return {"total_chunks": 0, "sections": {}, "page_range": "—"}
