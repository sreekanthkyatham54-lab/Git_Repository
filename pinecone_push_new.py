"""
pinecone_push_new.py — Incremental Pinecone sync
=================================================
Uploads ONLY chunks that are in SQLite but NOT yet in Pinecone.
Safe to run on every pipeline run — skips already-uploaded chunks.

Used by GitHub Actions after rag_indexer.py runs on new IPOs.
For full re-upload of everything, use pinecone_migrate.py instead.
"""

import os, json, sqlite3, time
from dotenv import load_dotenv

load_dotenv()

DB_PATH    = os.path.join(os.path.dirname(__file__), "data", "drhp.db")
INDEX_NAME = "tradesage-drhp"
BATCH_SIZE = 100


def get_index():
    api_key = os.environ.get("PINECONE_API_KEY")
    if not api_key:
        print("  PINECONE_API_KEY not set — skipping Pinecone sync")
        return None
    from pinecone import Pinecone
    pc = Pinecone(api_key=api_key)
    existing = [idx.name for idx in pc.list_indexes()]
    if INDEX_NAME not in existing:
        print(f"  Index '{INDEX_NAME}' not found — run pinecone_migrate.py first")
        return None
    return pc.Index(INDEX_NAME)


def get_indexed_ipo_ids(index):
    """Get set of ipo_ids already in Pinecone."""
    try:
        stats = index.describe_index_stats()
        # Query each known ipo_id with a zero vector to check existence
        # More efficient: get all unique ipo_ids from SQLite, check each
        return set()  # Will check per-IPO below
    except Exception as e:
        print(f"  Warning: could not get index stats: {e}")
        return set()


def ipo_already_in_pinecone(index, ipo_id):
    """Check if this IPO has any vectors in Pinecone."""
    try:
        results = index.query(
            vector=[0.0] * 384,
            top_k=1,
            filter={"ipo_id": {"$eq": ipo_id}},
            include_metadata=False,
        )
        return len(results.matches) > 0
    except Exception:
        return False


def get_new_ipo_ids(index):
    """Return ipo_ids that are in SQLite but not yet in Pinecone."""
    if not os.path.exists(DB_PATH):
        print("  drhp.db not found — nothing to upload")
        return []

    conn = sqlite3.connect(DB_PATH)
    all_ids = [r[0] for r in conn.execute(
        "SELECT DISTINCT ipo_id FROM chunks WHERE embedding IS NOT NULL"
    ).fetchall()]
    conn.close()

    new_ids = []
    for ipo_id in all_ids:
        if not ipo_already_in_pinecone(index, ipo_id):
            new_ids.append(ipo_id)
            print(f"  New IPO to upload: {ipo_id}")
        else:
            print(f"  Already in Pinecone: {ipo_id} (skipping)")

    return new_ids


def upload_ipo_chunks(index, ipo_id):
    """Upload all chunks for a single IPO to Pinecone."""
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute("""
        SELECT chunk_id, ipo_id, company, page_number, chunk_index, text, embedding
        FROM chunks
        WHERE ipo_id = ? AND embedding IS NOT NULL
        ORDER BY chunk_index
    """, (ipo_id,)).fetchall()
    conn.close()

    if not rows:
        print(f"  No chunks found for {ipo_id}")
        return 0

    batch = []
    total = 0

    for chunk_id, ipo_id, company, page_number, chunk_index, text, embedding_json in rows:
        try:
            embedding = json.loads(embedding_json)
        except Exception:
            continue

        batch.append({
            "id": chunk_id,
            "values": embedding,
            "metadata": {
                "ipo_id":      ipo_id,
                "company":     company,
                "page_number": page_number or 0,
                "chunk_index": chunk_index or 0,
                "text":        text[:8000] if text else "",
            }
        })

        if len(batch) >= BATCH_SIZE:
            index.upsert(vectors=batch)
            total += len(batch)
            batch = []
            time.sleep(0.2)

    if batch:
        index.upsert(vectors=batch)
        total += len(batch)

    return total


def main():
    print("\n" + "="*60)
    print("  Pinecone Incremental Sync")
    print("="*60)

    index = get_index()
    if not index:
        return

    print("\n  Checking for new IPOs not yet in Pinecone...")
    new_ids = get_new_ipo_ids(index)

    if not new_ids:
        print("\n  ✅ All IPOs already in Pinecone — nothing to upload")
        return

    print(f"\n  Found {len(new_ids)} new IPO(s) to upload: {new_ids}")

    total_uploaded = 0
    for ipo_id in new_ids:
        print(f"\n  Uploading {ipo_id}...")
        count = upload_ipo_chunks(index, ipo_id)
        print(f"  ✅ {ipo_id}: {count} chunks uploaded")
        total_uploaded += count

    stats = index.describe_index_stats()
    print(f"\n  Total vectors in Pinecone: {stats.total_vector_count}")
    print(f"  Uploaded this run: {total_uploaded}")
    print("\n" + "="*60)


if __name__ == "__main__":
    main()
