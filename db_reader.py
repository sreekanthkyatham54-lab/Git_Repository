"""
db_reader.py — Read DRHP sections + enriched IPO data from SQLite.
Option A: smart section-based context for AI (question routing).
"""
import sqlite3, json, os

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "drhp.db")

# Keywords that map user questions to the right DRHP section
QUESTION_ROUTING = {
    "risk_factors": [
        "risk","danger","concern","worry","problem","issue","threat","challenge",
        "red flag","negative","downside","caution","careful","beware","pitfall",
    ],
    "litigation": [
        "litigation","legal","court","case","lawsuit","dispute","pending","proceeding",
        "criminal","fraud","sebi","regulatory","fine","penalty","complaint",
    ],
    "financials": [
        "revenue","profit","loss","financial","income","ebitda","margin","growth",
        "sales","turnover","pat","cash flow","balance sheet","debt","ratio","pe",
        "valuation","expensive","cheap","worth","price","earning",
    ],
    "objects": [
        "use","fund","proceed","money","invest","capex","purpose","plan","expansion",
        "working capital","objective","object","utilise","utilization","spend",
    ],
    "promoters": [
        "promoter","founder","management","director","background","experience",
        "pledge","holding","stake","who","team","leadership","ceo","md",
    ],
    "overview": [
        "business","company","what does","what is","product","service","sector",
        "industry","operation","client","customer","market","compete","peer",
    ],
}


def get_connection():
    if not os.path.exists(DB_PATH): return None
    return sqlite3.connect(DB_PATH)


def route_question(user_question: str) -> list[str]:
    """
    Returns ordered list of section keys most relevant to the user's question.
    First match wins; always append risk_factors + litigation as safety net.
    """
    q = user_question.lower()
    scores = {key: 0 for key in QUESTION_ROUTING}
    for key, keywords in QUESTION_ROUTING.items():
        for kw in keywords:
            if kw in q:
                scores[key] += 1
    # Sort by score descending
    ranked = [k for k,_ in sorted(scores.items(), key=lambda x: -x[1]) if scores[k] > 0]
    # Always include risk + litigation as they're universally useful
    for always in ["risk_factors", "litigation"]:
        if always not in ranked:
            ranked.append(always)
    return ranked if ranked else list(QUESTION_ROUTING.keys())


def get_drhp_context(ipo_id: str, user_question: str = "") -> str:
    """
    Option A: returns relevant DRHP sections based on the user's question.
    Falls back gracefully if DB doesn't exist or IPO not scraped yet.
    """
    conn = get_connection()
    if conn is None: return ""

    try:
        row = conn.execute("""
            SELECT risk_factors, objects, financials, promoters, litigation,
                   overview, data_quality, sections_found
            FROM drhp WHERE ipo_id = ?
        """, (ipo_id,)).fetchone()

        if not row: return ""

        section_map = {
            "risk_factors": row[0] or "",
            "objects":      row[1] or "",
            "financials":   row[2] or "",
            "promoters":    row[3] or "",
            "litigation":   row[4] or "",
            "overview":     row[5] or "",
        }
        quality        = row[6] or "limited"
        sections_found = json.loads(row[7]) if row[7] else []

        # If no sections were extracted, nothing useful to return
        if not any(section_map.values()):
            return ""

        # Route question to relevant sections
        if user_question:
            ordered_keys = route_question(user_question)
        else:
            # Default order for general AI scorecard
            ordered_keys = ["risk_factors","litigation","financials","objects","promoters","overview"]

        # Build context — include top relevant sections, cap total at ~10K chars
        parts   = []
        total   = 0
        max_ctx = 10000

        for key in ordered_keys:
            text = section_map.get(key, "").strip()
            if not text: continue
            label  = key.replace("_"," ").title()
            chunk  = f"## {label} (from DRHP)\n{text}"
            if total + len(chunk) > max_ctx: break
            parts.append(chunk)
            total += len(chunk)

        if not parts: return ""

        quality_note = {
            "full_drhp": "Full DRHP analysed — all major sections extracted.",
            "partial":   "Partial DRHP — some sections extracted, others unavailable.",
            "limited":   "Limited data — only summary available, full DRHP not yet loaded.",
        }.get(quality, "")

        return (
            f"\n\n---\n**DRHP DATA [{quality.upper()}] — {quality_note}**\n"
            f"Sections available: {', '.join(sections_found)}\n\n"
            + "\n\n".join(parts)
        )

    except Exception as e:
        print(f"DB read error: {e}")
        return ""
    finally:
        conn.close()


def enrich_ipo_with_drhp(ipo: dict) -> dict:
    """Merges DB financial data into an IPO dict. Safe if DB absent."""
    conn = get_connection()
    if conn is None: return ipo
    enriched = dict(ipo)
    try:
        row = conn.execute("""
            SELECT revenue_cr, profit_cr, years, lot_size, lead_manager,
                   registrar, listing_date, sector, summary
            FROM ipo_enriched WHERE ipo_id = ?
        """, (ipo["id"],)).fetchone()
        if row:
            if row[0]: enriched["revenue_cr"]  = json.loads(row[0])
            if row[1]: enriched["profit_cr"]   = json.loads(row[1])
            if row[2]: enriched["years"]        = json.loads(row[2])
            if row[3]: enriched["lot_size"]     = row[3]
            if row[4]: enriched["lead_manager"] = row[4]
            if row[5]: enriched["registrar"]    = row[5]
            if row[6]: enriched["listing_date"] = row[6]
            if row[7]: enriched["sector"]       = row[7]
            if row[8]: enriched["summary"]      = row[8]

        drow = conn.execute("""
            SELECT promoters, objects, risk_factors, peers_json, drhp_url, rhp_url, data_quality
            FROM drhp WHERE ipo_id = ?
        """, (ipo["id"],)).fetchone()
        if drow:
            if drow[0]: enriched["promoters"]    = drow[0]
            if drow[1]: enriched["objects"]      = drow[1]
            if drow[2]: enriched["risks_text"]   = drow[2]
            peers = json.loads(drow[3]) if drow[3] else []
            if peers: enriched["peers"] = peers
            if drow[4]: enriched["drhp_url"]     = drow[4]
            if drow[5]: enriched["rhp_url"]      = drow[5]
            if drow[6]: enriched["data_quality"] = drow[6]
    except Exception as e:
        print(f"DB enrich error for {ipo.get('company')}: {e}")
    finally:
        conn.close()
    return enriched


def get_db_stats() -> dict:
    conn = get_connection()
    if conn is None:
        return {"ipos_with_drhp": 0, "ipos_with_financials": 0, "total_pdf_size_mb": 0}
    try:
        n_drhp = conn.execute(
            "SELECT COUNT(*) FROM drhp WHERE risk_factors IS NOT NULL AND length(risk_factors) > 50"
        ).fetchone()[0]
        n_fin = conn.execute(
            "SELECT COUNT(*) FROM ipo_enriched WHERE revenue_cr IS NOT NULL AND revenue_cr != '[]'"
        ).fetchone()[0]
        pdf_dir = os.path.join(os.path.dirname(__file__), "data", "drhp_pdfs")
        total_bytes = sum(
            os.path.getsize(os.path.join(pdf_dir, f))
            for f in os.listdir(pdf_dir) if f.endswith(".pdf")
        ) if os.path.exists(pdf_dir) else 0
        return {
            "ipos_with_drhp": n_drhp,
            "ipos_with_financials": n_fin,
            "total_pdf_size_mb": round(total_bytes / 1_000_000, 1),
        }
    except:
        return {"ipos_with_drhp": 0, "ipos_with_financials": 0, "total_pdf_size_mb": 0}
    finally:
        conn.close()
