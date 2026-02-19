"""
db_reader.py — Read enriched IPO data from SQLite DRHP database.
Called by the app to augment scraped IPO data with DRHP financials.
"""
import sqlite3
import json
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "drhp.db")


def get_connection() -> sqlite3.Connection | None:
    if not os.path.exists(DB_PATH):
        return None
    return sqlite3.connect(DB_PATH)


def enrich_ipo_with_drhp(ipo: dict) -> dict:
    """
    Takes an IPO dict, looks up DRHP data from DB, returns enriched copy.
    Safe to call even if DB doesn't exist yet.
    """
    conn = get_connection()
    if conn is None:
        return ipo

    enriched = dict(ipo)

    try:
        # Get financial + detail data
        row = conn.execute("""
            SELECT revenue_cr, profit_cr, years, lot_size, lead_manager,
                   registrar, listing_date, sector, summary
            FROM ipo_enriched WHERE ipo_id = ?
        """, (ipo["id"],)).fetchone()

        if row:
            rev  = json.loads(row[0]) if row[0] else []
            prof = json.loads(row[1]) if row[1] else []
            yrs  = json.loads(row[2]) if row[2] else []
            if rev:  enriched["revenue_cr"]  = rev
            if prof: enriched["profit_cr"]   = prof
            if yrs:  enriched["years"]       = yrs
            if row[3]: enriched["lot_size"]    = row[3]
            if row[4]: enriched["lead_manager"] = row[4]
            if row[5]: enriched["registrar"]    = row[5]
            if row[6]: enriched["listing_date"] = row[6]
            if row[7]: enriched["sector"]       = row[7]
            if row[8]: enriched["summary"]      = row[8]

        # Get DRHP content
        drhp_row = conn.execute("""
            SELECT promoters, objects, risk_factors, peers, drhp_url, rhp_url
            FROM drhp WHERE ipo_id = ?
        """, (ipo["id"],)).fetchone()

        if drhp_row:
            if drhp_row[0]: enriched["promoters"]    = drhp_row[0]
            if drhp_row[1]: enriched["objects"]      = drhp_row[1]
            if drhp_row[2]: enriched["risks_text"]   = drhp_row[2]
            peers = json.loads(drhp_row[3]) if drhp_row[3] else []
            if peers: enriched["peers"] = peers
            if drhp_row[4]: enriched["drhp_url"]  = drhp_row[4]
            if drhp_row[5]: enriched["rhp_url"]   = drhp_row[5]

    except Exception as e:
        print(f"⚠ DB read error for {ipo.get('company')}: {e}")
    finally:
        conn.close()

    return enriched


def get_drhp_text(ipo_id: str) -> str:
    """Get full DRHP text for an IPO (used by AI for deep analysis)."""
    conn = get_connection()
    if conn is None:
        return ""
    try:
        row = conn.execute(
            "SELECT drhp_text FROM drhp WHERE ipo_id = ?", (ipo_id,)
        ).fetchone()
        return row[0] if row and row[0] else ""
    except Exception:
        return ""
    finally:
        conn.close()


def get_db_stats() -> dict:
    """Return stats about what's in the DB — shown in sidebar."""
    conn = get_connection()
    if conn is None:
        return {"ipos_with_drhp": 0, "ipos_with_financials": 0, "total_pdf_size_mb": 0}
    try:
        n_drhp = conn.execute(
            "SELECT COUNT(*) FROM drhp WHERE drhp_text IS NOT NULL AND length(drhp_text) > 100"
        ).fetchone()[0]
        n_fin = conn.execute(
            "SELECT COUNT(*) FROM ipo_enriched WHERE revenue_cr IS NOT NULL AND revenue_cr != '[]'"
        ).fetchone()[0]

        pdf_dir = os.path.join(os.path.dirname(__file__), "data", "drhp_pdfs")
        total_bytes = sum(
            os.path.getsize(os.path.join(pdf_dir, f))
            for f in os.listdir(pdf_dir)
            if f.endswith(".pdf")
        ) if os.path.exists(pdf_dir) else 0

        return {
            "ipos_with_drhp": n_drhp,
            "ipos_with_financials": n_fin,
            "total_pdf_size_mb": round(total_bytes / 1_000_000, 1),
        }
    except Exception:
        return {"ipos_with_drhp": 0, "ipos_with_financials": 0, "total_pdf_size_mb": 0}
    finally:
        conn.close()
