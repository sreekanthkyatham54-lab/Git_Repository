"""
rag_indexer.py — RAG Pipeline: Chunk PDFs and store embeddings in SQLite
=========================================================================
Reads every PDF from data/drhp_pdfs/, splits into overlapping chunks,
generates embeddings using sentence-transformers (free, runs locally),
and stores everything in data/drhp.db (new 'chunks' table).

Run ONCE after drhp_scraper.py has downloaded PDFs:
    python rag_indexer.py

Re-run whenever new IPO PDFs are added — already-indexed IPOs are skipped.

Architecture:
    PDF on disk
        → pdfplumber extracts text page by page (with page numbers)
        → split into 800-token chunks with 100-token overlap
        → sentence-transformers generates embedding per chunk (free, local)
        → stored in SQLite chunks table
        → ready for retrieval at query time
"""

import os, json, re, sqlite3, time
import pdfplumber
from datetime import datetime

# ── CONFIGURATION ─────────────────────────────────────────────────────────────
DB_PATH  = os.path.join(os.path.dirname(__file__), "data", "drhp.db")
PDF_DIR  = os.path.join(os.path.dirname(__file__), "data", "drhp_pdfs")

CHUNK_SIZE    = 800   # tokens per chunk (~3200 chars)
CHUNK_OVERLAP = 100   # tokens overlap between consecutive chunks (~400 chars)
CHARS_PER_TOK = 4     # approximate

CHUNK_SIZE_CHARS    = CHUNK_SIZE    * CHARS_PER_TOK   # 3200
CHUNK_OVERLAP_CHARS = CHUNK_OVERLAP * CHARS_PER_TOK   # 400

# SEBI section header patterns — used to label each chunk's section
SECTION_LABELS = [
    ("risk_factors", [
        r"SECTION\s+II[\s\-–]+RISK\s+FACTORS",
        r"CHAPTER\s+II[\s\-–]+RISK\s+FACTORS",
        r"^\s*RISK\s+FACTORS\s*$",
        r"RISK\s+FACTORS\s+AND\s+MATERIAL",
    ]),
    ("objects", [
        r"OBJECTS?\s+OF\s+THE\s+(?:OFFER|ISSUE)",
        r"USE\s+OF\s+(?:IPO\s+)?PROCEEDS",
    ]),
    ("financials", [
        r"FINANCIAL\s+STATEMENTS?",
        r"RESTATED\s+(?:CONSOLIDATED\s+)?FINANCIAL",
        r"AUDITED\s+FINANCIAL",
        r"FINANCIAL\s+INFORMATION",
    ]),
    ("promoters", [
        r"(?:OUR\s+)?PROMOTERS?\s+AND\s+PROMOTER\s+GROUP",
        r"PROMOTER\s+BACKGROUND",
        r"ABOUT\s+THE\s+PROMOTER",
    ]),
    ("litigation", [
        r"LEGAL?\s+(?:AND\s+OTHER\s+)?PROCEEDINGS?",
        r"OUTSTANDING\s+LITIGATION",
        r"PENDING\s+LITIGATION",
    ]),
    ("overview", [
        r"(?:OUR\s+)?BUSINESS\s+OVERVIEW",
        r"INDUSTRY\s+OVERVIEW",
        r"ABOUT\s+(?:US|OUR\s+COMPANY|THE\s+COMPANY)",
        r"BUSINESS\s+DESCRIPTION",
    ]),
]


# ── DATABASE ──────────────────────────────────────────────────────────────────
def init_chunks_table(conn):
    """Add chunks table to existing drhp.db."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS chunks (
            chunk_id     TEXT PRIMARY KEY,
            ipo_id       TEXT NOT NULL,
            company      TEXT NOT NULL,
            page_number  INTEGER,
            section      TEXT,
            chunk_index  INTEGER,
            text         TEXT NOT NULL,
            token_count  INTEGER,
            embedding    TEXT,
            indexed_at   TEXT,
            FOREIGN KEY (ipo_id) REFERENCES drhp(ipo_id)
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_chunks_ipo ON chunks(ipo_id)")
    conn.commit()


def already_indexed(conn, ipo_id):
    """Return True if this IPO already has chunks in the DB."""
    row = conn.execute(
        "SELECT COUNT(*) FROM chunks WHERE ipo_id = ?", (ipo_id,)
    ).fetchone()
    return row[0] > 0


def get_ipo_id_from_filename(filename, conn):
    """
    Map PDF filename to ipo_id and company name.
    Filenames are: ipo_001.pdf, ipo_002.pdf, ipo-gaudium-ivf.pdf etc.
    Match against drhp table records.
    """
    base = os.path.splitext(filename)[0]  # e.g. "ipo_005"

    # Direct match first
    row = conn.execute(
        "SELECT ipo_id, company FROM drhp WHERE ipo_id = ?", (base,)
    ).fetchone()
    if row:
        return row[0], row[1]

    # Try slug match — ipo-gaudium-ivf → match company containing "gaudium"
    slug = base.replace("ipo-", "").replace("ipo_", "").replace("-", " ").replace("_", " ")
    rows = conn.execute("SELECT ipo_id, company FROM drhp").fetchall()
    for ipo_id, company in rows:
        if slug.lower() in company.lower() or company.lower().replace(" ", "") in slug.lower().replace(" ", ""):
            return ipo_id, company

    # Return base as ipo_id with unknown company — still index it
    return base, "Unknown"


# ── PDF EXTRACTION ────────────────────────────────────────────────────────────
def extract_pages(pdf_path):
    """
    Extract text from PDF page by page.
    Returns list of (page_number, text) tuples.
    Preserves page boundaries for accurate citations.
    """
    pages = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            total = len(pdf.pages)
            print(f"    Extracting {total} pages...")
            for i, page in enumerate(pdf.pages):
                try:
                    text = page.extract_text(x_tolerance=3, y_tolerance=3) or ""
                    # Clean up common PDF extraction artifacts
                    text = re.sub(r'\x00', '', text)           # null bytes
                    text = re.sub(r'[ \t]+', ' ', text)        # multiple spaces
                    text = re.sub(r'\n{3,}', '\n\n', text)     # excessive newlines
                    text = text.strip()
                    if text:
                        pages.append((i + 1, text))
                except Exception:
                    continue
            print(f"    Extracted text from {len(pages)}/{total} pages")
    except Exception as e:
        print(f"    PDF read error: {e}")
    return pages


def detect_section(text):
    """
    Detect which DRHP section this text belongs to.
    Returns section label string or 'general'.
    """
    text_upper = text[:500].upper()  # check start of chunk
    for section_name, patterns in SECTION_LABELS:
        for pat in patterns:
            if re.search(pat, text_upper):
                return section_name
    return "general"


# ── CHUNKING ──────────────────────────────────────────────────────────────────
def chunk_pages(pages):
    """
    Split page texts into overlapping chunks.
    Respects: section headers > paragraph breaks > sentence ends > character limit.
    Returns list of dicts: {text, page_number, section, chunk_index}
    """
    chunks = []
    chunk_index = 0
    current_section = "general"

    # Build one long text with page markers embedded
    # Format: [PAGE:47] ...text...
    full_text_parts = []
    for page_num, text in pages:
        full_text_parts.append(f"[PAGE:{page_num}]\n{text}")
    full_text = "\n\n".join(full_text_parts)

    # Split into paragraphs first
    paragraphs = re.split(r'\n\n+', full_text)

    current_chunk_text = ""
    current_chunk_page = pages[0][0] if pages else 1

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        # Extract page number if this paragraph starts with a page marker
        page_match = re.match(r'\[PAGE:(\d+)\]\n?', para)
        if page_match:
            current_chunk_page = int(page_match.group(1))
            para = para[page_match.end():].strip()
            if not para:
                continue

        # Detect section from paragraph content
        detected = detect_section(para)
        if detected != "general":
            current_section = detected

        # If adding this paragraph exceeds chunk size, save current and start new
        combined = current_chunk_text + "\n\n" + para if current_chunk_text else para

        if len(combined) > CHUNK_SIZE_CHARS and current_chunk_text:
            # Save current chunk
            if len(current_chunk_text.strip()) > 100:  # min meaningful length
                chunks.append({
                    "text":        current_chunk_text.strip(),
                    "page_number": current_chunk_page,
                    "section":     current_section,
                    "chunk_index": chunk_index,
                    "token_count": len(current_chunk_text) // CHARS_PER_TOK,
                })
                chunk_index += 1

            # Start new chunk with overlap — take last CHUNK_OVERLAP_CHARS
            overlap = current_chunk_text[-CHUNK_OVERLAP_CHARS:] if len(current_chunk_text) > CHUNK_OVERLAP_CHARS else current_chunk_text
            current_chunk_text = overlap + "\n\n" + para
        else:
            current_chunk_text = combined

    # Don't forget the last chunk
    if current_chunk_text.strip() and len(current_chunk_text.strip()) > 100:
        chunks.append({
            "text":        current_chunk_text.strip(),
            "page_number": current_chunk_page,
            "section":     current_section,
            "chunk_index": chunk_index,
            "token_count": len(current_chunk_text) // CHARS_PER_TOK,
        })

    # Remove [PAGE:N] markers from stored text — we have page_number field
    for chunk in chunks:
        chunk["text"] = re.sub(r'\[PAGE:\d+\]\n?', '', chunk["text"]).strip()

    return chunks


# ── EMBEDDINGS ────────────────────────────────────────────────────────────────
_model = None

def get_embedding_model():
    """Load sentence-transformers model once and reuse."""
    global _model
    if _model is None:
        try:
            from sentence_transformers import SentenceTransformer
            print("  Loading embedding model (first time takes ~30 seconds)...")
            _model = SentenceTransformer("all-MiniLM-L6-v2")
            print("  Embedding model loaded.")
        except ImportError:
            print("  ❌ sentence-transformers not installed.")
            print("     Run: pip install sentence-transformers")
            raise
    return _model


def embed_texts(texts):
    """
    Generate embeddings for a list of texts.
    Returns list of embedding vectors (as Python lists).
    all-MiniLM-L6-v2 produces 384-dimensional vectors.
    """
    model = get_embedding_model()
    embeddings = model.encode(texts, batch_size=32, show_progress_bar=False)
    return [emb.tolist() for emb in embeddings]


# ── MAIN INDEXER ──────────────────────────────────────────────────────────────
def index_pdf(pdf_path, ipo_id, company, conn):
    """
    Full pipeline for one PDF:
    1. Extract text by page
    2. Chunk with overlap
    3. Embed each chunk
    4. Store in DB
    """
    print(f"  Indexing: {company} ({ipo_id})")
    print(f"  File: {os.path.basename(pdf_path)}")

    # Step 1: Extract
    pages = extract_pages(pdf_path)
    if not pages:
        print("  ❌ No text extracted from PDF")
        return 0

    # Step 2: Chunk
    chunks = chunk_pages(pages)
    print(f"  Chunked into {len(chunks)} pieces")
    if not chunks:
        print("  ❌ No chunks produced")
        return 0

    # Step 3: Embed all chunks in one batch (faster than one-by-one)
    print(f"  Generating embeddings for {len(chunks)} chunks...")
    texts = [c["text"] for c in chunks]
    embeddings = embed_texts(texts)
    print(f"  Embeddings generated ({len(embeddings[0])} dimensions each)")

    # Step 4: Store
    now = datetime.now().isoformat()
    rows = []
    for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
        chunk_id = f"{ipo_id}_chunk_{chunk['chunk_index']:04d}"
        rows.append((
            chunk_id,
            ipo_id,
            company,
            chunk["page_number"],
            chunk["section"],
            chunk["chunk_index"],
            chunk["text"],
            chunk["token_count"],
            json.dumps(embedding),
            now,
        ))

    conn.executemany("""
        INSERT OR REPLACE INTO chunks
        (chunk_id, ipo_id, company, page_number, section, chunk_index,
         text, token_count, embedding, indexed_at)
        VALUES (?,?,?,?,?,?,?,?,?,?)
    """, rows)
    conn.commit()

    print(f"  ✅ {len(rows)} chunks stored in DB")

    # Show section distribution
    from collections import Counter
    section_counts = Counter(c["section"] for c in chunks)
    for section, count in sorted(section_counts.items()):
        print(f"    {section}: {count} chunks")

    return len(rows)


def run_indexer():
    """Index all PDFs that haven't been indexed yet."""
    print("\n" + "=" * 60)
    print(f"RAG Indexer — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"  PDF folder: {PDF_DIR}")
    print(f"  DB:         {DB_PATH}")
    print("=" * 60)

    if not os.path.exists(PDF_DIR):
        print(f"❌ PDF folder not found: {PDF_DIR}")
        print("   Run drhp_scraper.py first to download PDFs")
        return

    if not os.path.exists(DB_PATH):
        print(f"❌ DB not found: {DB_PATH}")
        print("   Run drhp_scraper.py first")
        return

    conn = sqlite3.connect(DB_PATH)
    init_chunks_table(conn)

    pdf_files = sorted(f for f in os.listdir(PDF_DIR) if f.endswith(".pdf"))
    if not pdf_files:
        print("❌ No PDF files found in drhp_pdfs/")
        return

    print(f"\n  Found {len(pdf_files)} PDFs\n")

    total_chunks = 0
    skipped      = 0
    failed       = 0

    for pdf_file in pdf_files:
        ipo_id, company = get_ipo_id_from_filename(pdf_file, conn)

        if already_indexed(conn, ipo_id):
            count = conn.execute(
                "SELECT COUNT(*) FROM chunks WHERE ipo_id = ?", (ipo_id,)
            ).fetchone()[0]
            print(f"  ⏭  Skipping {company} ({ipo_id}) — already indexed ({count} chunks)")
            skipped += 1
            continue

        print(f"\n{'─'*60}")
        pdf_path = os.path.join(PDF_DIR, pdf_file)
        try:
            n = index_pdf(pdf_path, ipo_id, company, conn)
            total_chunks += n
        except Exception as e:
            print(f"  ❌ Failed: {e}")
            failed += 1

    print(f"\n{'='*60}")
    print(f"  Done.")
    print(f"  Indexed:  {len(pdf_files) - skipped - failed} PDFs → {total_chunks} new chunks")
    print(f"  Skipped:  {skipped} (already done)")
    print(f"  Failed:   {failed}")

    # Summary of what's in DB
    total = conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
    ipos  = conn.execute("SELECT COUNT(DISTINCT ipo_id) FROM chunks").fetchone()[0]
    print(f"\n  Total in DB: {total} chunks across {ipos} IPOs")
    conn.close()


if __name__ == "__main__":
    run_indexer()
