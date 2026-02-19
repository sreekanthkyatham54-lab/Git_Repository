"""
drhp_scraper.py — DRHP PDF Pipeline
=====================================
For each IPO:
  1. Scrapes ipowatch.in detail page → grabs financials + DRHP/RHP PDF URL
  2. Downloads the PDF
  3. Extracts full text with pdfplumber
  4. Stores in SQLite: data/drhp.db

Run: python drhp_scraper.py
Runs automatically as part of scraper.py daily job.

Install dependencies first:
    pip install pdfplumber requests beautifulsoup4
"""

import os
import re
import json
import time
import sqlite3
import requests
import pdfplumber
from io import BytesIO
from datetime import datetime
from bs4 import BeautifulSoup

# ── CONFIG ────────────────────────────────────────────────────────────────────
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}
DB_PATH   = os.path.join(os.path.dirname(__file__), "data", "drhp.db")
PDF_DIR   = os.path.join(os.path.dirname(__file__), "data", "drhp_pdfs")
DELAY     = 2.0   # seconds between requests
MAX_PAGES = 80    # max PDF pages to extract (DRHPs are 200-400 pages; we take key sections)

os.makedirs(PDF_DIR, exist_ok=True)
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)


# ── DATABASE ──────────────────────────────────────────────────────────────────
def init_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS drhp (
            ipo_id       TEXT PRIMARY KEY,
            company      TEXT,
            drhp_url     TEXT,
            rhp_url      TEXT,
            drhp_text    TEXT,       -- full extracted text (trimmed to MAX_PAGES)
            financials   TEXT,       -- JSON: {revenue_cr, profit_cr, years}
            promoters    TEXT,       -- extracted promoter info
            objects      TEXT,       -- objects of issue
            risk_factors TEXT,       -- key risk factors
            peers        TEXT,       -- peer comparison (JSON list)
            scraped_at   TEXT
        )
    """)
    # Also add financials columns to main ipo table if they exist
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ipo_enriched (
            ipo_id          TEXT PRIMARY KEY,
            company         TEXT,
            revenue_cr      TEXT,   -- JSON list
            profit_cr       TEXT,   -- JSON list
            years           TEXT,   -- JSON list
            lot_size        INTEGER,
            lead_manager    TEXT,
            registrar       TEXT,
            listing_date    TEXT,
            promoter_hold   REAL,
            pe_ratio        REAL,
            sector          TEXT,
            summary         TEXT,
            scraped_at      TEXT
        )
    """)
    conn.commit()
    return conn


def already_scraped(conn: sqlite3.Connection, ipo_id: str) -> bool:
    row = conn.execute(
        "SELECT ipo_id FROM drhp WHERE ipo_id=? AND drhp_text IS NOT NULL AND length(drhp_text) > 100",
        (ipo_id,)
    ).fetchone()
    return row is not None


# ── STEP 1: SCRAPE IPOWATCH DETAIL PAGE ──────────────────────────────────────
def scrape_detail_page(ipo: dict) -> dict:
    """
    Scrape ipowatch.in IPO detail page.
    Returns enriched dict with financials, lot_size, pdf_urls, etc.
    """
    url = ipo.get("detail_url", "")
    if not url:
        return {}

    print(f"  📄 Scraping detail: {ipo['company']}...")
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
    except Exception as e:
        print(f"    ⚠ Failed: {e}")
        return {}

    text = soup.get_text(separator=" ", strip=True)
    result = {}

    # ── DRHP / RHP PDF links
    for a in soup.find_all("a", href=True):
        href = a["href"]
        label = a.get_text(strip=True).upper()
        if href.endswith(".pdf") or ".pdf" in href.lower():
            if "DRHP" in label or "DRAFT" in label:
                result["drhp_url"] = href
            elif "RHP" in label or "PROSPECTUS" in label:
                result["rhp_url"] = href
            # Fallback: any PDF link in the details table
            if "drhp_url" not in result and ("DRAFT" in href.upper() or "DRHP" in href.upper() or "DP_" in href):
                result["drhp_url"] = href
            if "rhp_url" not in result and ("PROSPECTUS" in href.upper() or "RHP" in href.upper()):
                result["rhp_url"] = href

    # ── Revenue & Profit — ipowatch writes them in a standard sentence:
    # "The company reported revenue of ₹X crores in YYYY against ₹Y crores in ZZZZ"
    rev_matches = re.findall(
        r"revenue of ₹?([\d,]+\.?\d*)\s*crores?\s+in\s+(\d{4})",
        text, re.IGNORECASE
    )
    profit_matches = re.findall(
        r"profit of ₹?([\d,]+\.?\d*)\s*crores?\s+in\s+(\d{4})",
        text, re.IGNORECASE
    )

    if rev_matches:
        # Sort by year ascending
        rev_data = sorted([(int(y), float(v.replace(",", ""))) for v, y in rev_matches])
        result["revenue_cr"] = [v for _, v in rev_data]
        result["years"]      = [f"FY{str(y)[2:]}" for _, y in rev_data]

    if profit_matches:
        profit_data = sorted([(int(y), float(v.replace(",", ""))) for v, y in profit_matches])
        result["profit_cr"] = [v for _, v in profit_data]

    # ── Lot size
    lot_match = re.search(r"(?:minimum|min)[^\d]*(\d[\d,]+)\s*shares", text, re.IGNORECASE)
    if not lot_match:
        lot_match = re.search(r"lot size[^\d]*(\d[\d,]+)", text, re.IGNORECASE)
    if lot_match:
        result["lot_size"] = int(lot_match.group(1).replace(",", ""))

    # ── Listing date
    list_match = re.search(
        r"list(?:ing)?\s+(?:on\s+)?(?:BSE|NSE)[^\n]*?(\w+ \d{1,2},? \d{4}|\d{1,2} \w+ \d{4})",
        text, re.IGNORECASE
    )
    if list_match:
        result["listing_date"] = list_match.group(1)

    # ── Lead manager
    for pattern in [
        r"(?:lead manager|book running)[^\n:]{0,20}[:\-]\s*([A-Z][^\n,\.]{5,60})",
        r"BRLM[^\n:]{0,10}[:\-]\s*([A-Z][^\n,\.]{5,60})",
    ]:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            result["lead_manager"] = m.group(1).strip()
            break

    # ── Registrar
    reg_match = re.search(
        r"registrar[^\n:]{0,20}[:\-]\s*([A-Z][^\n,\.]{5,60})",
        text, re.IGNORECASE
    )
    if reg_match:
        result["registrar"] = reg_match.group(1).strip()

    # ── Sector / business description
    # ipowatch often has a paragraph describing the business
    paras = [p.get_text(strip=True) for p in soup.find_all("p") if len(p.get_text(strip=True)) > 80]
    if paras:
        result["summary"] = paras[0][:600]

    # ── Review / recommendation
    review_match = re.search(r"\*\*Review[:\*\s]+(\w+)", text, re.IGNORECASE)
    if review_match:
        verdict = review_match.group(1).upper()
        if "SUBSCRIBE" in verdict:
            result["recommendation"] = "SUBSCRIBE"
        elif "AVOID" in verdict:
            result["recommendation"] = "AVOID"
        else:
            result["recommendation"] = "NEUTRAL"

    print(f"    ✓ Rev: {result.get('revenue_cr')} | DRHP: {'✓' if result.get('drhp_url') else '✗'} | RHP: {'✓' if result.get('rhp_url') else '✗'}")
    return result


# ── STEP 2: DOWNLOAD & PARSE PDF ─────────────────────────────────────────────
def download_and_parse_pdf(url: str, ipo_id: str) -> str:
    """
    Download a DRHP/RHP PDF and extract text.
    Returns extracted text string (trimmed to MAX_PAGES pages).
    Saves PDF locally for caching.
    """
    local_path = os.path.join(PDF_DIR, f"{ipo_id}.pdf")

    # Use cached PDF if available
    if os.path.exists(local_path) and os.path.getsize(local_path) > 1000:
        print(f"    📁 Using cached PDF: {local_path}")
        pdf_bytes = open(local_path, "rb").read()
    else:
        print(f"    ⬇ Downloading PDF: {url[:80]}...")
        try:
            resp = requests.get(url, headers=HEADERS, timeout=60, stream=True)
            resp.raise_for_status()
            pdf_bytes = resp.content
            # Save locally
            with open(local_path, "wb") as f:
                f.write(pdf_bytes)
            print(f"    ✓ Downloaded {len(pdf_bytes)//1024} KB → {local_path}")
        except Exception as e:
            print(f"    ⚠ PDF download failed: {e}")
            return ""

    # Extract text with pdfplumber
    try:
        text_parts = []
        with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
            total = len(pdf.pages)
            print(f"    📖 PDF has {total} pages — extracting key sections...")

            # Strategy: extract first 20 pages (company overview, objects, risk factors)
            # + pages 20-50 (financials usually here)
            # + last 10 pages (sometimes financials summary)
            key_pages = (
                list(range(0, min(25, total))) +           # intro + objects
                list(range(25, min(60, total))) +          # financials
                list(range(max(0, total-10), total))       # appendix
            )
            seen = set()
            for i in key_pages:
                if i in seen or i >= total:
                    continue
                seen.add(i)
                page = pdf.pages[i]
                txt = page.extract_text() or ""
                if txt.strip():
                    text_parts.append(f"\n--- PAGE {i+1} ---\n{txt}")

        full_text = "\n".join(text_parts)
        # Trim to ~200K chars (enough for Claude context)
        if len(full_text) > 200_000:
            full_text = full_text[:200_000] + "\n...[truncated]"

        print(f"    ✓ Extracted {len(full_text):,} characters from {len(seen)} pages")
        return full_text

    except Exception as e:
        print(f"    ⚠ PDF parse failed: {e}")
        return ""


# ── STEP 3: AI EXTRACTION FROM DRHP TEXT ─────────────────────────────────────
def extract_structured_data(drhp_text: str, company: str) -> dict:
    """
    Use regex + heuristics to extract structured fields from DRHP text.
    For best results this can also be done via Claude API,
    but regex works well for standard SEBI DRHP format.
    """
    result = {
        "promoters": "",
        "objects": "",
        "risk_factors": "",
        "peers": [],
        "revenue_cr": [],
        "profit_cr": [],
        "years": [],
    }

    # ── Objects of Issue
    obj_match = re.search(
        r"objects?\s+of\s+(?:the\s+)?(?:offer|issue)(.*?)(?:means\s+of\s+finance|general\s+corporate|section\s+[IVX]+)",
        drhp_text, re.IGNORECASE | re.DOTALL
    )
    if obj_match:
        result["objects"] = obj_match.group(1).strip()[:800]

    # ── Risk Factors (grab first 1500 chars of risk section)
    risk_match = re.search(
        r"risk\s+factors?(.*?)(?:our\s+business|management|section\s+[IVX]+|chapter)",
        drhp_text, re.IGNORECASE | re.DOTALL
    )
    if risk_match:
        result["risk_factors"] = risk_match.group(1).strip()[:1500]

    # ── Promoters
    promo_match = re.search(
        r"(?:our\s+)?promoters?\s+(?:and\s+promoter\s+group\s+)?(.*?)(?:promoter\s+group|our\s+management|section)",
        drhp_text, re.IGNORECASE | re.DOTALL
    )
    if promo_match:
        result["promoters"] = promo_match.group(1).strip()[:600]

    # ── Revenue from operations (standard SEBI format)
    # Looks for table rows like: Revenue from Operations | 32,496.XX | 5,925.XX
    rev_pattern = re.findall(
        r"revenue\s+from\s+operations[^\d]*([\d,]+\.?\d*)",
        drhp_text, re.IGNORECASE
    )
    if rev_pattern:
        vals = []
        for v in rev_pattern[:3]:
            try:
                val = float(v.replace(",", ""))
                # Convert lakhs to crores if very large
                if val > 10000:
                    val = round(val / 100, 2)
                vals.append(val)
            except:
                pass
        if vals:
            result["revenue_cr"] = vals

    # ── Net Profit / PAT
    profit_pattern = re.findall(
        r"(?:profit\s+(?:after\s+tax|for\s+the\s+(?:year|period))|PAT)[^\d]*([\d,]+\.?\d*)",
        drhp_text, re.IGNORECASE
    )
    if profit_pattern:
        vals = []
        for v in profit_pattern[:3]:
            try:
                val = float(v.replace(",", ""))
                if val > 10000:
                    val = round(val / 100, 2)
                vals.append(val)
            except:
                pass
        if vals:
            result["profit_cr"] = vals

    # ── Peers (listed companies mentioned in comparison table)
    peer_pattern = re.findall(
        r"(?:BSE|NSE)[:\s]+(\d{6,})[^\n]*\n?([A-Z][A-Za-z\s&\.]{5,40}(?:Ltd|Limited|Industries|Corp))",
        drhp_text
    )
    if peer_pattern:
        result["peers"] = [name.strip() for _, name in peer_pattern[:6]]

    return result


# ── MAIN PIPELINE ─────────────────────────────────────────────────────────────
def process_ipo_drhp(ipo: dict, conn: sqlite3.Connection) -> dict:
    """Full pipeline for one IPO: scrape → download PDF → extract → store."""
    ipo_id  = ipo["id"]
    company = ipo["company"]

    if already_scraped(conn, ipo_id):
        print(f"  ⏭ Already scraped: {company}")
        # Still return enriched data from DB
        row = conn.execute(
            "SELECT financials, promoters, objects, risk_factors, peers, drhp_url FROM drhp WHERE ipo_id=?",
            (ipo_id,)
        ).fetchone()
        if row:
            fin = json.loads(row[0]) if row[0] else {}
            return {**fin, "promoters": row[1], "objects": row[2],
                    "risk_factors": row[3], "peers": json.loads(row[4]) if row[4] else [],
                    "drhp_url": row[5]}
        return {}

    # Step 1: Scrape detail page
    time.sleep(DELAY)
    detail = scrape_detail_page(ipo)

    # Step 2: Download & parse DRHP PDF
    # Prefer RHP (final prospectus) over DRHP (draft) as it has final financials
    pdf_url   = detail.get("rhp_url") or detail.get("drhp_url") or ""
    drhp_text = ""

    if pdf_url:
        time.sleep(DELAY)
        drhp_text = download_and_parse_pdf(pdf_url, ipo_id)

    # Step 3: Extract structured data from PDF text
    structured = {}
    if drhp_text:
        structured = extract_structured_data(drhp_text, company)

    # Merge: PDF-extracted data + detail page data
    # Detail page financials take priority if PDF extraction failed
    financials = {
        "revenue_cr": structured.get("revenue_cr") or detail.get("revenue_cr") or [],
        "profit_cr":  structured.get("profit_cr")  or detail.get("profit_cr")  or [],
        "years":      detail.get("years") or [],
    }

    # Step 4: Store in DB
    conn.execute("""
        INSERT OR REPLACE INTO drhp
        (ipo_id, company, drhp_url, rhp_url, drhp_text, financials, promoters, objects, risk_factors, peers, scraped_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        ipo_id,
        company,
        detail.get("drhp_url", ""),
        detail.get("rhp_url", ""),
        drhp_text[:300_000] if drhp_text else "",   # cap at 300K chars
        json.dumps(financials),
        structured.get("promoters") or "",
        structured.get("objects") or detail.get("objects", ""),
        structured.get("risk_factors") or "",
        json.dumps(structured.get("peers") or []),
        datetime.now().isoformat(),
    ))

    # Also store enriched IPO data
    conn.execute("""
        INSERT OR REPLACE INTO ipo_enriched
        (ipo_id, company, revenue_cr, profit_cr, years, lot_size, lead_manager, registrar,
         listing_date, sector, summary, scraped_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        ipo_id, company,
        json.dumps(financials["revenue_cr"]),
        json.dumps(financials["profit_cr"]),
        json.dumps(financials["years"]),
        detail.get("lot_size", 0),
        detail.get("lead_manager", ""),
        detail.get("registrar", ""),
        detail.get("listing_date", ""),
        detail.get("sector") or ipo.get("sector", ""),
        detail.get("summary") or ipo.get("summary", ""),
        datetime.now().isoformat(),
    ))
    conn.commit()

    print(f"    ✅ Stored in DB: revenue={financials['revenue_cr']}, profit={financials['profit_cr']}")

    return {
        **financials,
        "promoters":    structured.get("promoters", ""),
        "objects":      structured.get("objects") or detail.get("objects", ""),
        "risk_factors": structured.get("risk_factors", ""),
        "peers":        structured.get("peers") or [],
        "lot_size":     detail.get("lot_size", 0),
        "lead_manager": detail.get("lead_manager", ""),
        "listing_date": detail.get("listing_date", ""),
        "summary":      detail.get("summary", ""),
        "drhp_url":     pdf_url,
    }


def run_drhp_pipeline(ipos: list[dict]) -> None:
    """Process DRHP for a list of IPOs."""
    print("\n" + "="*60)
    print(f"📚 DRHP Pipeline — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   Processing {len(ipos)} IPOs")
    print("="*60)

    conn = init_db()
    success = 0

    for ipo in ipos:
        print(f"\n[{ipos.index(ipo)+1}/{len(ipos)}] {ipo['company']}")
        try:
            result = process_ipo_drhp(ipo, conn)
            if result.get("revenue_cr"):
                success += 1
        except Exception as e:
            print(f"  ⚠ Error: {e}")

    conn.close()
    print(f"\n{'='*60}")
    print(f"✅ DRHP Pipeline complete. {success}/{len(ipos)} IPOs have financial data.")
    print(f"   DB: {DB_PATH}")
    print(f"   PDFs: {PDF_DIR}/")
    print("="*60)


if __name__ == "__main__":
    # Load IPOs from live data or seed data and run pipeline
    import sys
    sys.path.insert(0, os.path.dirname(__file__))
    from data_loader import load_ipo_data

    data   = load_ipo_data()
    ipos   = data["active_ipos"] + data["upcoming_ipos"]
    run_drhp_pipeline(ipos)
