"""
inspect_db.py — Show exactly what is stored in drhp.db
Run: python inspect_db.py

This script lets you see precisely what Claude is reading when
it answers questions. No guessing — raw truth.
"""
import sqlite3, json, os

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "drhp.db")

def hr(char="─", width=70):
    print(char * width)

def show_db():
    if not os.path.exists(DB_PATH):
        print(f"❌ DB not found at: {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)

    # ── 1. OVERVIEW ───────────────────────────────────────────────────────────
    hr("═")
    print("  DATABASE INSPECTION REPORT")
    print(f"  File: {os.path.abspath(DB_PATH)}")
    print(f"  Size: {os.path.getsize(DB_PATH) / 1024:.1f} KB")
    hr("═")

    rows = conn.execute("""
        SELECT ipo_id, company, data_quality, sections_found,
               total_pages,
               length(risk_factors)  as rf_len,
               length(objects)       as obj_len,
               length(financials)    as fin_len,
               length(promoters)     as pro_len,
               length(litigation)    as lit_len,
               length(overview)      as ov_len,
               financials_json
        FROM drhp ORDER BY ipo_id
    """).fetchall()

    print(f"\n  {len(rows)} IPOs in database\n")

    for row in rows:
        ipo_id, company, quality, sections_found, total_pages, \
        rf_len, obj_len, fin_len, pro_len, lit_len, ov_len, fin_json = row

        sections = json.loads(sections_found) if sections_found else []

        hr()
        print(f"  IPO:     {ipo_id}  |  {company}")
        print(f"  Quality: {quality}  |  PDF pages: {total_pages}")
        print(f"  Sections detected: {sections if sections else '⚠ NONE'}")
        print()

        # Show what's stored per section
        section_data = [
            ("risk_factors", rf_len),
            ("objects",      obj_len),
            ("financials",   fin_len),
            ("promoters",    pro_len),
            ("litigation",   lit_len),
            ("overview",     ov_len),
        ]

        total_stored = 0
        for name, length in section_data:
            length = length or 0
            total_stored += length
            if length > 100:
                status = f"✅ {length:,} chars stored"
            elif length > 0:
                status = f"⚠  {length} chars — too short, likely garbage"
            else:
                status = "❌ EMPTY — not extracted"
            print(f"    {name:<15} {status}")

        # PDF size estimate
        if total_pages:
            full_pdf_chars = total_pages * 2000  # ~2000 chars/page average
            pct = round(total_stored / full_pdf_chars * 100, 1) if full_pdf_chars else 0
            print(f"\n  Total stored: {total_stored:,} chars")
            print(f"  Estimated full PDF: ~{full_pdf_chars:,} chars")
            print(f"  Coverage: ~{pct}% of document")

        # Show verified financials
        print()
        if fin_json:
            try:
                fin = json.loads(fin_json)
                print(f"  Verified financials:")
                print(f"    Revenue (Cr): {fin.get('revenue_cr', 'NOT EXTRACTED')}")
                print(f"    Profit  (Cr): {fin.get('profit_cr',  'NOT EXTRACTED')}")
                print(f"    Years:        {fin.get('years',      'NOT EXTRACTED')}")
                print(f"    Litigation hits: {fin.get('litigation_count', 0)}")
            except:
                print("  ⚠ financials_json is corrupted")
        else:
            print("  ❌ No verified financials stored")

    hr("═")

    # ── 2. SHOW ACTUAL RAW TEXT for one IPO ───────────────────────────────────
    print("\n  RAW TEXT PREVIEW (what Claude actually reads)")
    print("  Enter an ipo_id from the list above to inspect it")
    print("  (or press Enter to skip)\n")

    choice = input("  ipo_id > ").strip()
    if not choice:
        conn.close()
        return

    row = conn.execute("""
        SELECT company, risk_factors, financials, objects,
               promoters, litigation, overview
        FROM drhp WHERE ipo_id = ?
    """, (choice,)).fetchone()

    if not row:
        print(f"  ❌ ipo_id '{choice}' not found")
        conn.close()
        return

    company = row[0]
    sections = {
        "risk_factors": row[1],
        "financials":   row[2],
        "objects":      row[3],
        "promoters":    row[4],
        "litigation":   row[5],
        "overview":     row[6],
    }

    print(f"\n  Company: {company}")
    print("  Which section to inspect?")
    for i, name in enumerate(sections.keys(), 1):
        length = len(sections[name]) if sections[name] else 0
        print(f"  {i}. {name} ({length:,} chars)")

    sec_choice = input("\n  Section number > ").strip()
    try:
        sec_name = list(sections.keys())[int(sec_choice) - 1]
        text = sections[sec_name]
    except:
        print("  Invalid choice")
        conn.close()
        return

    hr("═")
    print(f"\n  FULL STORED TEXT: {sec_name} for {company}")
    print(f"  Length: {len(text) if text else 0} chars\n")
    hr()

    if not text:
        print("  ❌ EMPTY — nothing stored for this section")
    else:
        # Show in chunks so it's readable
        chunk = 500
        parts = [text[i:i+chunk] for i in range(0, len(text), chunk)]
        for i, part in enumerate(parts):
            print(f"\n  --- chunk {i+1}/{len(parts)} ---")
            print(part)
            if i < len(parts) - 1:
                cont = input("\n  Press Enter for next chunk (q to quit)... ")
                if cont.strip().lower() == 'q':
                    break

    hr("═")
    print("\n  This is EXACTLY what Claude sees when answering questions.")
    print("  If this text looks wrong, Claude's answers will be wrong.\n")
    conn.close()


if __name__ == "__main__":
    show_db()


def show_chunks():
    """Show what's in the RAG chunks table."""
    conn = sqlite3.connect(DB_PATH)

    hr("═")
    print("  RAG CHUNKS TABLE")
    hr("═")

    # Check table exists
    exists = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='chunks'"
    ).fetchone()
    if not exists:
        print("  ❌ chunks table does not exist — run rag_indexer.py first")
        conn.close()
        return

    total = conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
    ipos  = conn.execute("SELECT COUNT(DISTINCT ipo_id) FROM chunks").fetchone()[0]
    print(f"\n  Total chunks: {total} across {ipos} IPOs\n")

    # Per IPO breakdown
    rows = conn.execute("""
        SELECT ipo_id, company,
               COUNT(*) as chunks,
               MIN(page_number) as first_page,
               MAX(page_number) as last_page,
               COUNT(DISTINCT section) as sections
        FROM chunks
        GROUP BY ipo_id
        ORDER BY ipo_id
    """).fetchall()

    for ipo_id, company, chunks, first_page, last_page, sections in rows:
        print(f"  {ipo_id}  |  {company}")
        print(f"    Chunks: {chunks}  |  Pages: {first_page}–{last_page}  |  Sections detected: {sections}")

        # Section breakdown
        sec_rows = conn.execute("""
            SELECT section, COUNT(*) as n
            FROM chunks WHERE ipo_id = ?
            GROUP BY section ORDER BY n DESC
        """, (ipo_id,)).fetchall()
        sec_str = "  ".join(f"{s}({n})" for s, n in sec_rows)
        print(f"    {sec_str}")
        print()

    # Ask to preview a chunk
    hr("═")
    print("  CHUNK PREVIEW")
    print("  Enter an ipo_id to see its best chunks (or press Enter to skip)\n")
    choice = input("  ipo_id > ").strip()
    if not choice:
        conn.close()
        return

    # Show top chunks per section for this IPO
    sections = conn.execute("""
        SELECT DISTINCT section FROM chunks WHERE ipo_id = ?
        ORDER BY section
    """, (choice,)).fetchall()

    for (section,) in sections:
        print(f"\n  {'─'*50}")
        print(f"  Section: {section}")

        # Get a sample chunk from this section
        chunk = conn.execute("""
            SELECT chunk_id, page_number, text
            FROM chunks
            WHERE ipo_id = ? AND section = ?
            ORDER BY chunk_index
            LIMIT 1
        """, (choice, section)).fetchone()

        if chunk:
            chunk_id, page_num, text = chunk
            print(f"  chunk_id: {chunk_id}  |  page: {page_num}")
            print(f"  Text preview (first 400 chars):")
            print(f"  {text[:400]}")

        cont = input("\n  Press Enter for next section (q to quit)... ")
        if cont.strip().lower() == 'q':
            break

    conn.close()


if __name__ == "__main__":
    show_db()
    print("\n")
    show_chunks()
