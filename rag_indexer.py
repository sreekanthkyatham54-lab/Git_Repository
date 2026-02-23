"""
rag_indexer.py — Semantic Chunking + Embedding Pipeline
========================================================
Splits PDF text at MEANING BOUNDARIES not fixed token counts.

How semantic chunking works:
  1. Extract text page by page (preserving page numbers)
  2. Split into sentences
  3. Embed each sentence
  4. Measure similarity between consecutive sentences
  5. When similarity drops sharply → topic changed → split here
  6. Merge small chunks, cap large ones

Result: chunks follow actual content structure.
"Basis for Offer Price" stays together as one chunk.
Financial tables don't get cut mid-row.

No section labels stored — retrieval uses pure cosine similarity.

Run: python rag_indexer.py
Re-run safely — already-indexed IPOs are skipped.
"""

import os, json, re, sqlite3, time
import numpy as np
import pdfplumber
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "drhp.db")
PDF_DIR = os.path.join(os.path.dirname(__file__), "data", "drhp_pdfs")

# Semantic chunking config
SIMILARITY_THRESHOLD  = 0.45   # below this → topic changed → split
MIN_CHUNK_CHARS       = 300    # merge chunks smaller than this
MAX_CHUNK_CHARS       = 4000   # split chunks larger than this
CHARS_PER_TOK         = 4


# ── DATABASE ──────────────────────────────────────────────────────────────────
def init_chunks_table(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS chunks (
            chunk_id     TEXT PRIMARY KEY,
            ipo_id       TEXT NOT NULL,
            company      TEXT NOT NULL,
            page_number  INTEGER,
            chunk_index  INTEGER,
            text         TEXT NOT NULL,
            token_count  INTEGER,
            embedding    TEXT,
            indexed_at   TEXT
        )
    """)
    # Remove section column if it exists from old schema — no longer needed
    try:
        conn.execute("ALTER TABLE chunks DROP COLUMN section")
    except Exception:
        pass
    conn.execute("CREATE INDEX IF NOT EXISTS idx_chunks_ipo ON chunks(ipo_id)")
    conn.commit()


def already_indexed(conn, ipo_id):
    row = conn.execute(
        "SELECT COUNT(*) FROM chunks WHERE ipo_id = ?", (ipo_id,)
    ).fetchone()
    return row[0] > 0


def force_reindex(conn, ipo_id):
    conn.execute("DELETE FROM chunks WHERE ipo_id = ?", (ipo_id,))
    conn.commit()


def get_ipo_id_from_filename(filename, conn):
    base = os.path.splitext(filename)[0]
    row = conn.execute(
        "SELECT ipo_id, company FROM drhp WHERE ipo_id = ?", (base,)
    ).fetchone()
    if row: return row[0], row[1]

    slug = base.replace("ipo-","").replace("ipo_","").replace("-"," ").replace("_"," ")
    rows = conn.execute("SELECT ipo_id, company FROM drhp").fetchall()
    for ipo_id, company in rows:
        if slug.lower() in company.lower() or \
           company.lower().replace(" ","") in slug.lower().replace(" ",""):
            return ipo_id, company

    return base, "Unknown"


# ── PDF EXTRACTION ────────────────────────────────────────────────────────────
def extract_pages(pdf_path):
    pages = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            total = len(pdf.pages)
            print(f"    {total} pages...")
            for i, page in enumerate(pdf.pages):
                try:
                    text = page.extract_text(x_tolerance=3, y_tolerance=3) or ""
                    text = re.sub(r'\x00', '', text)
                    text = re.sub(r'[ \t]+', ' ', text)
                    text = re.sub(r'\n{3,}', '\n\n', text)
                    text = text.strip()
                    if text and len(text) > 50:
                        pages.append((i + 1, text))
                except Exception:
                    continue
            print(f"    Text extracted from {len(pages)}/{total} pages")
    except Exception as e:
        print(f"    PDF read error: {e}")
    return pages


# ── SEMANTIC CHUNKING ─────────────────────────────────────────────────────────
def split_into_sentences(text):
    """Split text into sentences for semantic analysis."""
    # Split on sentence boundaries
    parts = re.split(r'(?<=[.!?])\s+(?=[A-Z])|(?<=\n)\n', text)
    sentences = []
    for part in parts:
        part = part.strip()
        if part and len(part) > 20:
            sentences.append(part)
    return sentences if sentences else [text]


def semantic_chunk_pages(pages, model):
    """
    Semantic chunking across all pages.
    Groups sentences by topic similarity, respects page boundaries.
    """
    if not pages:
        return []

    # Build flat list of (page_num, sentence) pairs
    all_sentences = []
    for page_num, text in pages:
        sentences = split_into_sentences(text)
        for sent in sentences:
            all_sentences.append((page_num, sent))

    if not all_sentences:
        return []

    print(f"    Embedding {len(all_sentences)} sentences for semantic chunking...")

    # Embed all sentences in one batch
    texts = [s for _, s in all_sentences]

    # Batch to avoid memory issues on large PDFs
    batch_size = 128
    all_embeddings = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i+batch_size]
        embs = model.encode(batch, show_progress_bar=False)
        all_embeddings.extend(embs)

    # Calculate similarity between consecutive sentences
    similarities = []
    for i in range(len(all_embeddings) - 1):
        a = np.array(all_embeddings[i], dtype=np.float32)
        b = np.array(all_embeddings[i+1], dtype=np.float32)
        na, nb = np.linalg.norm(a), np.linalg.norm(b)
        sim = float(np.dot(a, b) / (na * nb)) if na > 0 and nb > 0 else 0.0
        similarities.append(sim)

    # Find split points where similarity drops (topic change)
    split_indices = {0}  # always start a new chunk at beginning
    for i, sim in enumerate(similarities):
        page_curr = all_sentences[i][0]
        page_next = all_sentences[i+1][0]
        # Split on topic change OR page boundary (major section breaks)
        if sim < SIMILARITY_THRESHOLD or (page_next > page_curr + 2):
            split_indices.add(i + 1)

    # Build chunks from split points
    split_list = sorted(split_indices)
    raw_chunks = []
    for k, start in enumerate(split_list):
        end = split_list[k+1] if k+1 < len(split_list) else len(all_sentences)
        chunk_sentences = all_sentences[start:end]
        if not chunk_sentences:
            continue
        chunk_text = " ".join(s for _, s in chunk_sentences)
        chunk_page = chunk_sentences[0][0]  # page of first sentence
        # Store mean embedding of all sentences in chunk
        chunk_embs = all_embeddings[start:end]
        mean_emb   = np.mean(chunk_embs, axis=0).tolist()
        raw_chunks.append({
            "text":      chunk_text,
            "page":      chunk_page,
            "embedding": mean_emb,
        })

    # Merge tiny chunks with the next chunk
    merged = []
    i = 0
    while i < len(raw_chunks):
        chunk = raw_chunks[i]
        if len(chunk["text"]) < MIN_CHUNK_CHARS and i + 1 < len(raw_chunks):
            # Merge into next
            next_chunk = raw_chunks[i+1]
            merged_text = chunk["text"] + " " + next_chunk["text"]
            # Recompute mean embedding
            embs = [chunk["embedding"], next_chunk["embedding"]]
            mean_emb = np.mean(embs, axis=0).tolist()
            raw_chunks[i+1] = {
                "text":      merged_text,
                "page":      chunk["page"],
                "embedding": mean_emb,
            }
            i += 1
            continue
        merged.append(chunk)
        i += 1

    # Split oversized chunks at paragraph boundaries
    final_chunks = []
    for chunk in merged:
        if len(chunk["text"]) <= MAX_CHUNK_CHARS:
            final_chunks.append(chunk)
            continue
        # Split at paragraph breaks
        paragraphs = re.split(r'\n\n+', chunk["text"])
        current_text = ""
        current_page = chunk["page"]
        for para in paragraphs:
            if len(current_text) + len(para) > MAX_CHUNK_CHARS and current_text:
                # Embed this sub-chunk
                emb = model.encode([current_text])[0].tolist()
                final_chunks.append({
                    "text":      current_text.strip(),
                    "page":      current_page,
                    "embedding": emb,
                })
                current_text = para
            else:
                current_text = (current_text + " " + para).strip() if current_text else para
        if current_text.strip():
            emb = model.encode([current_text])[0].tolist()
            final_chunks.append({
                "text":      current_text.strip(),
                "page":      current_page,
                "embedding": emb,
            })

    return final_chunks


# ── EMBEDDING MODEL ───────────────────────────────────────────────────────────
_model = None

def get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        print("  Loading embedding model...")
        _model = SentenceTransformer("all-MiniLM-L6-v2")
        print("  Model ready.")
    return _model


# ── MAIN INDEXER ──────────────────────────────────────────────────────────────
def index_pdf(pdf_path, ipo_id, company, conn):
    print(f"  Indexing: {company} ({ipo_id})")

    pages = extract_pages(pdf_path)
    if not pages:
        print("  ❌ No text extracted"); return 0

    model  = get_model()
    chunks = semantic_chunk_pages(pages, model)
    print(f"  → {len(chunks)} semantic chunks")

    if not chunks:
        print("  ❌ No chunks produced"); return 0

    now  = datetime.now().isoformat()
    rows = []
    for idx, chunk in enumerate(chunks):
        chunk_id = f"{ipo_id}_chunk_{idx:04d}"
        rows.append((
            chunk_id, ipo_id, company,
            chunk["page"], idx,
            chunk["text"],
            len(chunk["text"]) // CHARS_PER_TOK,
            json.dumps(chunk["embedding"]),
            now,
        ))

    conn.executemany("""
        INSERT OR REPLACE INTO chunks
        (chunk_id, ipo_id, company, page_number, chunk_index,
         text, token_count, embedding, indexed_at)
        VALUES (?,?,?,?,?,?,?,?,?)
    """, rows)
    conn.commit()
    print(f"  ✅ {len(rows)} chunks stored")
    return len(rows)


def run_indexer(force=False):
    print("\n" + "="*60)
    print(f"RAG Semantic Indexer — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"  Similarity threshold: {SIMILARITY_THRESHOLD}")
    print(f"  Min/Max chunk: {MIN_CHUNK_CHARS}/{MAX_CHUNK_CHARS} chars")
    print("="*60)

    if not os.path.exists(PDF_DIR):
        print(f"❌ PDF folder not found: {PDF_DIR}"); return
    if not os.path.exists(DB_PATH):
        print(f"❌ DB not found: {DB_PATH}"); return

    conn = sqlite3.connect(DB_PATH)
    init_chunks_table(conn)

    pdf_files = sorted(f for f in os.listdir(PDF_DIR) if f.endswith(".pdf"))
    if not pdf_files:
        print("❌ No PDFs found"); return

    print(f"\n  Found {len(pdf_files)} PDFs\n")
    total_chunks, skipped, failed = 0, 0, 0

    for pdf_file in pdf_files:
        ipo_id, company = get_ipo_id_from_filename(pdf_file, conn)
        if not force and already_indexed(conn, ipo_id):
            count = conn.execute(
                "SELECT COUNT(*) FROM chunks WHERE ipo_id=?", (ipo_id,)
            ).fetchone()[0]
            print(f"  ⏭  Skipping {company} — already indexed ({count} chunks)")
            skipped += 1
            continue

        print(f"\n{'─'*60}")
        if force:
            force_reindex(conn, ipo_id)
        try:
            n = index_pdf(os.path.join(PDF_DIR, pdf_file), ipo_id, company, conn)
            total_chunks += n
        except Exception as e:
            print(f"  ❌ Failed: {e}"); failed += 1

    print(f"\n{'='*60}")
    print(f"  Done. New chunks: {total_chunks} | Skipped: {skipped} | Failed: {failed}")
    total = conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
    ipos  = conn.execute("SELECT COUNT(DISTINCT ipo_id) FROM chunks").fetchone()[0]
    print(f"  Total in DB: {total} chunks across {ipos} IPOs")
    conn.close()


if __name__ == "__main__":
    import sys
    force = "--force" in sys.argv
    if force:
        print("  ⚠ Force mode — re-indexing ALL IPOs")
    run_indexer(force=force)
