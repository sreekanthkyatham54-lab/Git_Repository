"""
drhp_scraper.py — DRHP PDF Pipeline (Option A: Section-Based Extraction)
=========================================================================
For each IPO:
  1. Scrapes ipowatch.in detail page -> finds DRHP/RHP PDF URL
  2. Downloads the full PDF (all pages, no page limit)
  3. Scans ALL pages for SEBI-standard section headers
  4. Extracts each section into its own DB column:
       risk_factors / objects / financials / promoters / litigation / overview
  5. Stores in SQLite: data/drhp.db

Run: python drhp_scraper.py
"""

import os, re, json, time, sqlite3, requests
import pdfplumber
from io import BytesIO
from datetime import datetime
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}
DB_PATH = os.path.join(os.path.dirname(__file__), "data", "drhp.db")
PDF_DIR = os.path.join(os.path.dirname(__file__), "data", "drhp_pdfs")
DELAY   = 2.0

os.makedirs(PDF_DIR, exist_ok=True)
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

# ── SEBI SECTION HEADER PATTERNS ─────────────────────────────────────────────
SECTION_PATTERNS = [
    ("risk_factors", [
        r"SECTION\s+II[\s\-]+RISK\s+FACTORS",
        r"CHAPTER\s+II[\s\-]+RISK\s+FACTORS",
        r"^RISK\s+FACTORS$",
        r"RISK\s+FACTORS\s+AND\s+MATERIAL",
    ]),
    ("objects", [
        r"OBJECTS?\s+OF\s+THE\s+(?:OFFER|ISSUE)",
        r"USE\s+OF\s+(?:IPO\s+)?PROCEEDS",
        r"SECTION\s+IV[\s\-]+OBJECTS",
    ]),
    ("financials", [
        r"FINANCIAL\s+STATEMENTS?",
        r"RESTATED\s+(?:CONSOLIDATED\s+)?FINANCIAL",
        r"AUDITED\s+FINANCIAL",
        r"SECTION\s+(?:V|VI)[\s\-]+FINANCIAL",
    ]),
    ("promoters", [
        r"(?:OUR\s+)?PROMOTERS?\s+AND\s+PROMOTER\s+GROUP",
        r"PROMOTER\s+BACKGROUND",
        r"SECTION\s+(?:VI|VII)[\s\-]+PROMOTER",
    ]),
    ("litigation", [
        r"LEGAL?\s+(?:AND\s+OTHER\s+)?PROCEEDINGS?",
        r"OUTSTANDING\s+LITIGATION",
        r"SECTION\s+(?:VII|VIII)[\s\-]+(?:LEGAL|OUTSTANDING)",
    ]),
    ("overview", [
        r"(?:OUR\s+)?BUSINESS\s+OVERVIEW",
        r"SECTION\s+(?:III|IV)[\s\-]+(?:BUSINESS|COMPANY)",
        r"INDUSTRY\s+OVERVIEW",
    ]),
]

SECTION_MAX = {
    "risk_factors": 6000,
    "objects":      3000,
    "financials":   5000,
    "promoters":    3000,
    "litigation":   4000,
    "overview":     3000,
}


# ── DATABASE ──────────────────────────────────────────────────────────────────
def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS drhp (
            ipo_id          TEXT PRIMARY KEY,
            company         TEXT,
            drhp_url        TEXT,
            rhp_url         TEXT,
            risk_factors    TEXT,
            objects         TEXT,
            financials      TEXT,
            promoters       TEXT,
            litigation      TEXT,
            overview        TEXT,
            financials_json TEXT,
            peers_json      TEXT,
            sections_found  TEXT,
            total_pages     INTEGER,
            data_quality    TEXT,
            scraped_at      TEXT
        )
    """)
    existing = [r[1] for r in conn.execute("PRAGMA table_info(drhp)").fetchall()]
    for col, typ in [("litigation","TEXT"),("overview","TEXT"),("financials_json","TEXT"),
                     ("peers_json","TEXT"),("sections_found","TEXT"),
                     ("total_pages","INTEGER"),("data_quality","TEXT")]:
        if col not in existing:
            conn.execute(f"ALTER TABLE drhp ADD COLUMN {col} {typ}")

    conn.execute("""
        CREATE TABLE IF NOT EXISTS ipo_enriched (
            ipo_id        TEXT PRIMARY KEY,
            company       TEXT,
            revenue_cr    TEXT,
            profit_cr     TEXT,
            years         TEXT,
            lot_size      INTEGER,
            lead_manager  TEXT,
            registrar     TEXT,
            listing_date  TEXT,
            sector        TEXT,
            summary       TEXT,
            scraped_at    TEXT
        )
    """)
    conn.commit()
    return conn


def already_scraped(conn, ipo_id):
    row = conn.execute(
        "SELECT ipo_id FROM drhp WHERE ipo_id=? AND (risk_factors IS NOT NULL OR financials IS NOT NULL)",
        (ipo_id,)
    ).fetchone()
    return row is not None


# ── DETAIL PAGE SCRAPER ───────────────────────────────────────────────────────
def scrape_detail_page(ipo):
    url = ipo.get("detail_url","")
    if not url: return {}
    print(f"  Scraping detail: {ipo['company']}...")
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
    except Exception as e:
        print(f"    Failed: {e}"); return {}

    text   = soup.get_text(separator=" ", strip=True)
    result = {}

    for a in soup.find_all("a", href=True):
        href  = a["href"]
        label = a.get_text(strip=True).upper()
        if ".pdf" in href.lower():
            if "DRHP" in label or "DRAFT" in label or "DRHP" in href.upper():
                result["drhp_url"] = href
            if "RHP" in label or "PROSPECTUS" in label:
                result["rhp_url"] = href
            if "drhp_url" not in result and any(k in href.upper() for k in ["DP_","OFFER","PROSP"]):
                result["drhp_url"] = href

    rev_m = re.findall(r"revenue of ([\d,]+\.?\d*)\s*crores?\s+in\s+(\d{4})", text, re.I)
    prf_m = re.findall(r"profit of ([\d,]+\.?\d*)\s*crores?\s+in\s+(\d{4})", text, re.I)
    if rev_m:
        rd = sorted([(int(y),float(v.replace(",",""))) for v,y in rev_m])
        result["revenue_cr"] = [v for _,v in rd]
        result["years"]      = [f"FY{str(y)[2:]}" for _,y in rd]
    if prf_m:
        pd2 = sorted([(int(y),float(v.replace(",",""))) for v,y in prf_m])
        result["profit_cr"] = [v for _,v in pd2]

    lm = re.search(r"lot size[^\d]*(\d[\d,]+)", text, re.I)
    if lm: result["lot_size"] = int(lm.group(1).replace(",",""))
    bm = re.search(r"(?:lead manager|BRLM)[^\n:]{0,20}[:\-]\s*([A-Z][^\n,\.]{5,60})", text, re.I)
    if bm: result["lead_manager"] = bm.group(1).strip()
    rm = re.search(r"registrar[^\n:]{0,20}[:\-]\s*([A-Z][^\n,\.]{5,60})", text, re.I)
    if rm: result["registrar"] = rm.group(1).strip()
    paras = [p.get_text(strip=True) for p in soup.find_all("p") if len(p.get_text(strip=True)) > 80]
    if paras: result["summary"] = paras[0][:600]

    print(f"    DRHP:{'Y' if result.get('drhp_url') else 'N'} RHP:{'Y' if result.get('rhp_url') else 'N'} Rev:{result.get('revenue_cr','?')}")
    return result


# ── PDF DOWNLOAD & EXTRACTION ─────────────────────────────────────────────────
def download_and_extract_pdf(url, ipo_id):
    local = os.path.join(PDF_DIR, f"{ipo_id}.pdf")
    if os.path.exists(local) and os.path.getsize(local) > 1000:
        print(f"    Cached: {local}")
        pdf_bytes = open(local,"rb").read()
    else:
        print(f"    Downloading: {url[:70]}...")
        try:
            r = requests.get(url, headers=HEADERS, timeout=60, stream=True)
            r.raise_for_status()
            pdf_bytes = r.content
            open(local,"wb").write(pdf_bytes)
            print(f"    Downloaded {len(pdf_bytes)//1024}KB")
        except Exception as e:
            print(f"    Download failed: {e}"); return "", 0

    try:
        pages_text = []
        with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
            total = len(pdf.pages)
            print(f"    Extracting {total} pages...")
            for page in pdf.pages:
                try:
                    t = page.extract_text()
                    if t: pages_text.append(t)
                except: pass
        full = "\n".join(pages_text)
        print(f"    Extracted {len(full):,} chars from {total} pages")
        return full, total
    except Exception as e:
        print(f"    PDF parse error: {e}"); return "", 0


# ── OPTION A: SECTION EXTRACTION ─────────────────────────────────────────────
def extract_sections(full_text):
    sections       = {k:"" for k,_ in SECTION_PATTERNS}
    sections_found = []
    lines          = full_text.split("\n")
    section_starts = {}

    for i, line in enumerate(lines):
        ls = line.strip()
        if not ls or len(ls) < 5: continue
        for section_key, patterns in SECTION_PATTERNS:
            if section_key in section_starts: continue
            for pat in patterns:
                if re.search(pat, ls, re.IGNORECASE):
                    section_starts[i] = section_key
                    sections_found.append(section_key)
                    print(f"    [{section_key}] line {i}: {ls[:55]}")
                    break

    if not section_starts:
        print("    No headers found — using fallback regex")
        return _fallback_sections(full_text), []

    sorted_starts = sorted(section_starts.items())
    for idx, (start, key) in enumerate(sorted_starts):
        end = sorted_starts[idx+1][0] if idx+1 < len(sorted_starts) else min(start+600, len(lines))
        text = "\n".join(lines[start:end]).strip()
        sections[key] = text[:SECTION_MAX.get(key, 3000)]

    return sections, sections_found


def _fallback_sections(text):
    s = {k:"" for k,_ in SECTION_PATTERNS}
    patterns = [
        ("risk_factors", r"risk\s+factors?(.*?)(?:our\s+business|objects\s+of)", 6000),
        ("objects",      r"objects?\s+of\s+(?:the\s+)?(?:offer|issue)(.*?)(?:means\s+of|general\s+corporate)", 3000),
        ("promoters",    r"(?:our\s+)?promoters?\s+and\s+promoter\s+group(.*?)(?:management|our\s+business)", 3000),
        ("litigation",   r"(?:outstanding|legal)\s+(?:litigation|proceedings?)(.*?)(?:government\s+approval|material)", 4000),
        ("financials",   r"revenue\s+from\s+operations.{0,2000}profit\s+(?:after\s+tax|for\s+the)", 5000),
    ]
    for key, pat, maxc in patterns:
        m = re.search(pat, text, re.I | re.DOTALL)
        if m: s[key] = m.group(0 if key=="financials" else 1).strip()[:maxc]
    return s


# ── STRUCTURED NUMBER EXTRACTION ──────────────────────────────────────────────
def extract_numbers(sections, detail):
    fin_text = sections.get("financials","") + "\n" + sections.get("overview","")

    rev_vals = []
    for v in re.findall(r"revenue\s+from\s+operations[^\d]*([\d,]+\.?\d*)", fin_text, re.I)[:4]:
        try:
            n = float(v.replace(",",""))
            rev_vals.append(round(n/100,2) if n > 10000 else n)
        except: pass

    prf_vals = []
    for v in re.findall(r"(?:profit\s+after\s+tax|PAT|net\s+profit)[^\d]*([\d,]+\.?\d*)", fin_text, re.I)[:4]:
        try:
            n = float(v.replace(",",""))
            prf_vals.append(round(n/100,2) if n > 10000 else n)
        except: pass

    peers = list(set(p.strip() for p in re.findall(
        r"([A-Z][A-Za-z\s&\.]{5,40}(?:Ltd|Limited|Industries|Corp|Technologies))\s*[\|\t]",
        sections.get("financials","")
    )[:6]))

    promo_pct = 0.0
    pm = re.search(r"promoter[^%]*?([\d.]+)\s*%", sections.get("promoters",""), re.I)
    if pm:
        try: promo_pct = float(pm.group(1))
        except: pass

    lit_count = len(re.findall(
        r"(?:case|suit|matter|proceeding)\s+(?:is\s+)?pending",
        sections.get("litigation",""), re.I
    ))

    return {
        "revenue_cr":       rev_vals or detail.get("revenue_cr",[]),
        "profit_cr":        prf_vals or detail.get("profit_cr",[]),
        "years":            detail.get("years",[]),
        "promoter_holding": promo_pct,
        "peers":            peers,
        "litigation_count": lit_count,
    }


def assess_quality(sections_found, fin_json):
    key = {"risk_factors","financials","objects"}
    found = set(sections_found)
    if len(found & key) >= 3 and fin_json.get("revenue_cr"): return "full_drhp"
    if len(found) >= 2 or "risk_factors" in found:           return "partial"
    return "limited"


# ── MAIN PIPELINE ─────────────────────────────────────────────────────────────
def process_ipo_drhp(ipo, conn):
    ipo_id  = ipo["id"]
    company = ipo["company"]

    if already_scraped(conn, ipo_id):
        print(f"  Skipping (already done): {company}")
        return {}

    time.sleep(DELAY)
    detail = scrape_detail_page(ipo)

    pdf_url = detail.get("rhp_url") or detail.get("drhp_url") or ""
    full_text, total_pages = "", 0
    if pdf_url:
        time.sleep(DELAY)
        full_text, total_pages = download_and_extract_pdf(pdf_url, ipo_id)

    sections, sections_found = ({}, [])
    if full_text:
        sections, sections_found = extract_sections(full_text)
    else:
        print("    No PDF — detail page data only")

    fin_json = extract_numbers(sections, detail)
    quality  = assess_quality(sections_found, fin_json)

    conn.execute("""
        INSERT OR REPLACE INTO drhp
        (ipo_id, company, drhp_url, rhp_url,
         risk_factors, objects, financials, promoters, litigation, overview,
         financials_json, peers_json, sections_found, total_pages, data_quality, scraped_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        ipo_id, company,
        detail.get("drhp_url",""), detail.get("rhp_url",""),
        sections.get("risk_factors",""), sections.get("objects",""),
        sections.get("financials",""),   sections.get("promoters",""),
        sections.get("litigation",""),   sections.get("overview",""),
        json.dumps(fin_json), json.dumps(fin_json.get("peers",[])),
        json.dumps(sections_found), total_pages, quality,
        datetime.now().isoformat(),
    ))
    conn.execute("""
        INSERT OR REPLACE INTO ipo_enriched
        (ipo_id, company, revenue_cr, profit_cr, years, lot_size,
         lead_manager, registrar, listing_date, sector, summary, scraped_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        ipo_id, company,
        json.dumps(fin_json["revenue_cr"]), json.dumps(fin_json["profit_cr"]),
        json.dumps(fin_json["years"]),
        detail.get("lot_size",0), detail.get("lead_manager",""),
        detail.get("registrar",""), detail.get("listing_date",""),
        detail.get("sector") or ipo.get("sector",""),
        detail.get("summary") or ipo.get("summary",""),
        datetime.now().isoformat(),
    ))
    conn.commit()

    print(f"    [{quality}] Sections:{sections_found} Rev:{fin_json['revenue_cr']} Litigations:{fin_json.get('litigation_count',0)}")
    return {**fin_json, **sections, "data_quality": quality, "drhp_url": pdf_url}


def run_drhp_pipeline(ipos):
    print("\n" + "="*60)
    print(f"DRHP Pipeline (Option A) — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"  {len(ipos)} IPOs | Section-based extraction")
    print("="*60)
    conn    = init_db()
    results = {"full_drhp":0,"partial":0,"limited":0,"failed":0}
    for i, ipo in enumerate(ipos):
        print(f"\n[{i+1}/{len(ipos)}] {ipo['company']}")
        try:
            r = process_ipo_drhp(ipo, conn)
            q = r.get("data_quality","failed")
            results[q] = results.get(q,0) + 1
        except Exception as e:
            print(f"  Error: {e}"); results["failed"] += 1
    conn.close()
    print(f"\nDone. Full:{results['full_drhp']} Partial:{results['partial']} Limited:{results['limited']} Failed:{results['failed']}")


if __name__ == "__main__":
    import sys
    sys.path.insert(0, os.path.dirname(__file__))
    from data_loader import load_ipo_data
    data = load_ipo_data()
    run_drhp_pipeline(data["active_ipos"] + data["upcoming_ipos"])
