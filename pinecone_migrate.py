"""
pinecone_migrate.py — One-time migration from SQLite to Pinecone
================================================================
Reads all chunks + embeddings from local drhp.db and uploads
them to Pinecone so Streamlit Cloud can query without the DB file.

Run ONCE locally after re-indexing:
    python pinecone_migrate.py

Safe to re-run — existing vectors are overwritten not duplicated.

Requirements:
    pip install pinecone python-dotenv
"""

import os, json, sqlite3, time
from dotenv import load_dotenv

load_dotenv()

DB_PATH       = os.path.join(os.path.dirname(__file__), "data", "drhp.db")
INDEX_NAME    = "tradesage-drhp"
DIMENSION     = 384          # all-MiniLM-L6-v2 output size
BATCH_SIZE    = 100          # Pinecone upsert batch size
METRIC        = "cosine"


def get_pinecone_client():
    api_key = os.environ.get("PINECONE_API_KEY")
    if not api_key:
        raise ValueError("PINECONE_API_KEY not found in .env file")
    from pinecone import Pinecone
    return Pinecone(api_key=api_key)


def ensure_index(pc):
    """Create index if it doesn't exist."""
    existing = [idx.name for idx in pc.list_indexes()]
    if INDEX_NAME not in existing:
        print(f"  Creating index '{INDEX_NAME}'...")
        from pinecone import ServerlessSpec
        pc.create_index(
            name   = INDEX_NAME,
            dimension = DIMENSION,
            metric = METRIC,
            spec   = ServerlessSpec(cloud="aws", region="us-east-1"),
        )
        # Wait for index to be ready
        print("  Waiting for index to be ready...")
        while not pc.describe_index(INDEX_NAME).status["ready"]:
            time.sleep(2)
        print("  Index ready.")
    else:
        print(f"  Index '{INDEX_NAME}' already exists.")
    return pc.Index(INDEX_NAME)


def load_chunks_from_db():
    """Load all chunks with embeddings from SQLite."""
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute("""
        SELECT chunk_id, ipo_id, company, page_number, chunk_index, text, embedding
        FROM chunks
        WHERE embedding IS NOT NULL
        ORDER BY ipo_id, chunk_index
    """).fetchall()
    conn.close()
    print(f"  Loaded {len(rows)} chunks from drhp.db")
    return rows


def migrate():
    print("\n" + "="*60)
    print("  TradeSage — Pinecone Migration")
    print("="*60)

    if not os.path.exists(DB_PATH):
        print(f"❌ drhp.db not found at {DB_PATH}")
        return

    print("\n  Connecting to Pinecone...")
    pc    = get_pinecone_client()
    index = ensure_index(pc)

    print("\n  Loading chunks from local DB...")
    rows  = load_chunks_from_db()

    if not rows:
        print("❌ No chunks found in DB — run rag_indexer.py first")
        return

    # Build Pinecone vectors
    # Each vector: id, values (embedding), metadata (everything else)
    print(f"\n  Uploading {len(rows)} vectors to Pinecone in batches of {BATCH_SIZE}...")

    total_uploaded = 0
    batch          = []

    for chunk_id, ipo_id, company, page_number, chunk_index, text, embedding_json in rows:
        try:
            embedding = json.loads(embedding_json)
        except Exception:
            continue

        # Store text and metadata alongside the vector
        # Pinecone metadata is used to return chunk text at query time
        vector = {
            "id":     chunk_id,
            "values": embedding,
            "metadata": {
                "ipo_id":      ipo_id,
                "company":     company,
                "page_number": page_number or 0,
                "chunk_index": chunk_index or 0,
                # Pinecone metadata values must be < 40KB
                # Truncate text to be safe
                "text":        text[:8000] if text else "",
            }
        }
        batch.append(vector)

        if len(batch) >= BATCH_SIZE:
            index.upsert(vectors=batch)
            total_uploaded += len(batch)
            print(f"  ↑ Uploaded {total_uploaded}/{len(rows)} vectors...")
            batch = []
            time.sleep(0.2)  # rate limit safety

    # Upload remaining
    if batch:
        index.upsert(vectors=batch)
        total_uploaded += len(batch)

    print(f"\n  ✅ Done — {total_uploaded} vectors uploaded to Pinecone")

    # Verify
    stats = index.describe_index_stats()
    print(f"  Pinecone reports: {stats.total_vector_count} vectors stored")

    # Show breakdown by IPO
    print("\n  Vectors by IPO:")
    conn = sqlite3.connect(DB_PATH)
    ipos = conn.execute(
        "SELECT ipo_id, company, COUNT(*) FROM chunks GROUP BY ipo_id ORDER BY ipo_id"
    ).fetchall()
    conn.close()
    for ipo_id, company, count in ipos:
        print(f"    {ipo_id} | {company:30s} | {count} chunks")

    print("\n" + "="*60)
    print("  Migration complete.")
    print("  Streamlit Cloud will now use Pinecone for RAG retrieval.")
    print("="*60)


if __name__ == "__main__":
    migrate()
