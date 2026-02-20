"""
scraper.py — All India IPO Scraper (Mainboard + SME)
Source: ipowatch.in
  - All IPOs:   /upcoming-ipo-list/      (mainboard + SME mixed)
  - GMP:        /ipo-grey-market-premium-latest-ipo-gmp/
  - Historical: /ipo-performance-tracker/

Classification logic:
  - Row contains "BSE SME" or "NSE Emerge/SME" → SME
  - Otherwise large issue size or BSE/NSE mainboard → Mainboard
"""

import requests
from bs4 import BeautifulSoup
import json, os, re, time
from datetime import datetime, date

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}
BASE_URL    = "https://ipowatch.in"
OUTPUT_FILE = os.path.join(os.path.dirname(__file__), "data", "live_ipo_data.json")
DELAY = 1.5


def fetch(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        r.raise_for_status()
        return BeautifulSoup(r.text, "html.parser")
    except Exception as e:
        print(f"  ⚠ Failed {url}: {e}")
        return None


def parse_price(text):
    if not text: return 0.0
    nums = re.findall(r"[\d,]+\.?\d*", text.replace(",", ""))
    return float(nums[-1]) if nums else 0.0


def parse_size_cr(text):
    nums = re.findall(r"[\d,]+\.?\d*", text.replace(",", ""))
    return float(nums[0]) if nums else 0.0


def parse_date_range(text):
    today = date.today()
    month_map = {"jan":1,"feb":2,"mar":3,"apr":4,"may":5,"jun":6,
                 "jul":7,"aug":8,"sep":9,"oct":10,"nov":11,"dec":12}
    text = text.strip().lower()
    match = re.search(r"(\d+)[-–](\d+)\s+([a-z]+)(?:\s+(\d{4}))?", text)
    if not match:
        match2 = re.search(r"(\d+)\s+([a-z]+)(?:\s+(\d{4}))?", text)
        if not match2: return "", ""
        d1 = int(match2.group(1)); mon = month_map.get(match2.group(2)[:3], today.month)
        yr = int(match2.group(3)) if match2.group(3) else today.year
        try:
            od = date(yr, mon, d1).strftime("%Y-%m-%d"); return od, od
        except: return "", ""
    d1, d2 = int(match.group(1)), int(match.group(2))
    mon = month_map.get(match.group(3)[:3], today.month)
    yr  = int(match.group(4)) if match.group(4) else today.year
    try:
        if d1 > d2 and d1 > 20:
            om = mon-1 if mon>1 else 12; oy = yr if mon>1 else yr-1
            od = date(oy, om, d1).strftime("%Y-%m-%d"); cd = date(yr, mon, d2).strftime("%Y-%m-%d")
        else:
            od = date(yr, mon, d1).strftime("%Y-%m-%d"); cd = date(yr, mon, d2).strftime("%Y-%m-%d")
        if (today - datetime.strptime(od, "%Y-%m-%d").date()).days > 180:
            od = date(yr+1, mon, d1).strftime("%Y-%m-%d"); cd = date(yr+1, mon, d2).strftime("%Y-%m-%d")
        return od, cd
    except: return "", ""


def determine_status(open_date, close_date):
    try:
        today = date.today()
        od = datetime.strptime(open_date, "%Y-%m-%d").date()
        cd = datetime.strptime(close_date, "%Y-%m-%d").date()
        if od <= today <= cd: return "Open"
        elif today < od: return "Upcoming"
        else: return "Closed"
    except: return "Upcoming"


def slug_from_name(company):
    slug = company.lower().strip()
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    slug = re.sub(r"\s+", "-", slug)
    return slug


def detect_exchange_and_type(row_text, company_text="", issue_size_cr=0):
    """
    Detect exchange and IPO type from row text content.
    SME keywords: BSE SME, NSE Emerge, NSE SME, Emerge
    Mainboard: BSE, NSE (without SME/Emerge qualifier), or large issue size
    """
    t = row_text.upper()

    # Explicit SME markers
    if "BSE SME" in t:
        return "BSE SME", "SME"
    if "NSE EMERGE" in t or "NSE SME" in t or "EMERGE" in t:
        return "NSE Emerge", "SME"

    # Mainboard markers
    if "BSE" in t and "NSE" in t:
        return "BSE / NSE", "Mainboard"
    if "BSE" in t:
        return "BSE", "Mainboard"
    if "NSE" in t:
        return "NSE", "Mainboard"

    # Fallback: large issue size = mainboard
    if issue_size_cr and float(issue_size_cr) >= 100:
        return "BSE / NSE", "Mainboard"

    # Default to SME for small/unknown
    return "BSE SME", "SME"


# ── SCRAPER 1: UNIFIED IPO LIST ───────────────────────────────────────────────
def scrape_all_ipos():
    """
    Scrape the main upcoming IPO list from ipowatch.in.
    This page contains BOTH mainboard and SME IPOs.
    We classify each row by reading the exchange column.
    """
    print("📋 Scraping all IPOs (Mainboard + SME)...")
    
    # Try the all-IPO page first, fall back to SME-only
    urls_to_try = [
        (f"{BASE_URL}/upcoming-ipo-list/", "mixed"),
        (f"{BASE_URL}/upcoming-sme-ipo-list/", "sme_only"),
    ]
    
    all_ipos = []
    seen = set()
    
    for url, mode in urls_to_try:
        soup = fetch(url)
        if not soup:
            print(f"  ⚠ Skipping {url}")
            continue
        
        tables = soup.find_all("table")
        for table in tables:
            rows = table.find_all("tr")
            # Try to detect header columns
            header_row = rows[0] if rows else None
            headers = [th.get_text(strip=True).lower() for th in (header_row.find_all(["th","td"]) if header_row else [])]
            
            # Find column indices
            col_name     = next((i for i,h in enumerate(headers) if "company" in h or "ipo" in h or "name" in h), 0)
            col_date     = next((i for i,h in enumerate(headers) if "date" in h or "open" in h), 1)
            col_price    = next((i for i,h in enumerate(headers) if "price" in h), 2)
            col_size     = next((i for i,h in enumerate(headers) if "size" in h or "issue" in h), 3)
            col_exchange = next((i for i,h in enumerate(headers) if "exchange" in h or "type" in h or "board" in h), -1)

            for row in rows[1:]:
                cols = row.find_all("td")
                if len(cols) < 4: continue
                try:
                    name_cell = cols[col_name]
                    link_tag  = name_cell.find("a")
                    if not link_tag: continue
                    company = link_tag.get_text(strip=True)
                    if not company or len(company) < 3: continue
                    
                    # Skip duplicates
                    key = slug_from_name(company)
                    if key in seen: continue
                    seen.add(key)

                    detail_url = link_tag.get("href", "")
                    if detail_url and not detail_url.startswith("http"):
                        detail_url = BASE_URL + detail_url

                    date_text  = cols[col_date].get_text(strip=True)  if len(cols) > col_date  else ""
                    price_text = cols[col_price].get_text(strip=True) if len(cols) > col_price else ""
                    size_text  = cols[col_size].get_text(strip=True)  if len(cols) > col_size  else ""

                    open_date, close_date = parse_date_range(date_text)
                    if not open_date: continue
                    status = determine_status(open_date, close_date)
                    if status == "Closed": continue

                    issue_price   = parse_price(price_text)
                    issue_size_cr = parse_size_cr(size_text)

                    # Exchange detection: use dedicated exchange col if present, else full row text
                    if col_exchange >= 0 and len(cols) > col_exchange:
                        exchange_text = cols[col_exchange].get_text(strip=True)
                    else:
                        exchange_text = row.get_text(" ")

                    # If SME-only page, default to SME if not detected otherwise
                    if mode == "sme_only":
                        exchange, ipo_type = detect_exchange_and_type(exchange_text, company, issue_size_cr)
                        if ipo_type == "Mainboard" and issue_size_cr < 50:
                            ipo_type = "SME"
                            exchange = "BSE SME"
                    else:
                        exchange, ipo_type = detect_exchange_and_type(exchange_text, company, issue_size_cr)

                    all_ipos.append({
                        "id": f"ipo_{len(all_ipos)+1:03d}",
                        "company": company,
                        "exchange": exchange,
                        "ipo_type": ipo_type,
                        "sector": "—",
                        "open_date": open_date,
                        "close_date": close_date,
                        "issue_price": issue_price,
                        "issue_size_cr": issue_size_cr,
                        "lot_size": 0,
                        "subscription_status": status,
                        "subscription_times": 0.0,
                        "gmp": 0,
                        "gmp_percent": 0.0,
                        "lead_manager": "",
                        "registrar": "",
                        "objects": "",
                        "revenue_cr": [],
                        "profit_cr": [],
                        "years": [],
                        "peers": [],
                        "pe_ratio": 0.0,
                        "industry_pe": 0.0,
                        "promoter_holding": 0.0,
                        "listing_date": "",
                        "recommendation": "NEUTRAL",
                        "risk": "Medium",
                        "summary": "",
                        "risks_text": "",
                        "drhp_highlights": "",
                        "detail_url": detail_url,
                    })
                except Exception as e:
                    continue

        print(f"  → {url.split('/')[-2]}: found {len(all_ipos)} so far")

    return all_ipos


# ── SCRAPER 2: GMP DATA ───────────────────────────────────────────────────────
def scrape_gmp_data():
    print("📊 Scraping GMP data...")
    soup = fetch(f"{BASE_URL}/ipo-grey-market-premium-latest-ipo-gmp/")
    if not soup: return {}
    gmp_map = {}
    tables = soup.find_all("table")
    for table in tables:
        rows = table.find_all("tr")
        for row in rows[1:]:
            cols = row.find_all("td")
            if len(cols) < 3: continue
            try:
                company    = cols[0].get_text(strip=True)
                if not company: continue
                price_text = cols[1].get_text(strip=True)
                gmp_text   = cols[2].get_text(strip=True)
                gmp_val    = parse_price(gmp_text)
                issue_p    = parse_price(price_text)
                gmp_pct    = round(gmp_val / issue_p * 100, 1) if issue_p > 0 else 0.0
                
                # Also detect exchange from GMP row for better classification
                row_text = row.get_text(" ")
                exchange, ipo_type = detect_exchange_and_type(row_text, company, issue_p)
                
                gmp_map[slug_from_name(company)] = {
                    "company": company,
                    "gmp": gmp_val,
                    "gmp_percent": gmp_pct,
                    "issue_price": issue_p,
                    "exchange": exchange,
                    "ipo_type": ipo_type,
                }
            except: continue
    print(f"  → {len(gmp_map)} GMP entries found")
    return gmp_map


# ── SCRAPER 3: IPO DETAIL PAGE ────────────────────────────────────────────────
def scrape_ipo_detail(ipo):
    url = ipo.get("detail_url", "")
    if not url:
        url = f"{BASE_URL}/{slug_from_name(ipo['company'])}-ipo-date-review-price-allotment-details/"
    soup = fetch(url)
    if not soup: return ipo

    text = soup.get_text(" ", strip=True)

    # Issue price
    if not ipo["issue_price"]:
        pm = re.search(r"(?:issue price|price band)[:\s]*₹?([\d,]+(?:\s*(?:to|-)\s*[\d,]+)?)", text, re.I)
        if pm: ipo["issue_price"] = parse_price(pm.group(1))

    # Lot size
    lm = re.search(r"lot size[:\s]*([\d,]+)\s*(?:shares?|equity)", text, re.I)
    if lm: ipo["lot_size"] = int(lm.group(1).replace(",",""))

    # Lead manager
    ll = re.search(r"(?:lead manager|book running)[:\s]+([A-Z][^\n\.]{5,60}?)(?:\n|\.|\band\b)", text, re.I)
    if ll: ipo["lead_manager"] = ll.group(1).strip()

    # Registrar
    rl = re.search(r"registrar[:\s]+([A-Z][^\n\.]{5,60}?)(?:\n|\.)", text, re.I)
    if rl: ipo["registrar"] = rl.group(1).strip()

    # Summary
    paras = [p.get_text(strip=True) for p in soup.find_all("p") if len(p.get_text(strip=True)) > 80]
    if paras: ipo["summary"] = paras[0][:400]

    # Sector
    sm = re.search(r"(?:industry|sector)[:\s]+([A-Z][a-zA-Z &]{3,40})", text, re.I)
    if sm: ipo["sector"] = sm.group(1).strip()

    # Refine exchange/type from detail page (most accurate source)
    page_text_upper = text.upper()
    if "BSE SME" in page_text_upper:
        ipo["exchange"] = "BSE SME"; ipo["ipo_type"] = "SME"
    elif "NSE EMERGE" in page_text_upper or "NSE SME" in page_text_upper:
        ipo["exchange"] = "NSE Emerge"; ipo["ipo_type"] = "SME"
    elif "MAINBOARD" in page_text_upper or "MAIN BOARD" in page_text_upper:
        ipo["ipo_type"] = "Mainboard"
        if "BSE" in page_text_upper and "NSE" in page_text_upper:
            ipo["exchange"] = "BSE / NSE"

    # Promoter holding
    pm2 = re.search(r"promoter[^%]*?([\d.]+)\s*%", text, re.I)
    if pm2: ipo["promoter_holding"] = float(pm2.group(1))

    # Risk
    t_lower = text.lower()
    if "high risk" in t_lower: ipo["risk"] = "High"
    elif "low risk" in t_lower: ipo["risk"] = "Low"

    return ipo


# ── SCRAPER 4: HISTORICAL IPOS ────────────────────────────────────────────────
def scrape_historical_ipos():
    print("📜 Scraping historical IPO performance...")
    soup = fetch(f"{BASE_URL}/ipo-performance-tracker/")
    if not soup: return []
    historical = []
    tables = soup.find_all("table")
    for table in tables:
        rows = table.find_all("tr")
        for row in rows[1:50]:
            cols = row.find_all("td")
            if len(cols) < 4: continue
            try:
                company = cols[0].get_text(strip=True)
                if not company or len(company) < 3: continue
                nums = []
                for col in cols[1:]:
                    txt = col.get_text(strip=True)
                    found = re.findall(r"[\d,]+\.?\d*", txt.replace(",",""))
                    if found: nums.append(float(found[0]))
                if len(nums) >= 2:
                    issue_price   = nums[0]
                    listing_price = nums[1]
                    current_price = nums[2] if len(nums) > 2 else listing_price
                    listing_gain  = round(((listing_price - issue_price) / issue_price) * 100, 1) if issue_price else 0
                    
                    # Detect type from row text
                    row_text = row.get_text(" ")
                    exchange, ipo_type = detect_exchange_and_type(row_text, company, issue_price)
                    
                    historical.append({
                        "company": company,
                        "listing_date": "",
                        "issue_price": issue_price,
                        "listing_price": listing_price,
                        "current_price": current_price,
                        "gmp_before_listing": None,
                        "gmp_predicted_gain": None,
                        "actual_listing_gain": listing_gain,
                        "gmp_accurate": None,
                        "sector": "—",
                        "exchange": exchange,
                        "ipo_type": ipo_type,
                    })
            except: continue
    print(f"  → {len(historical)} historical IPOs")
    return historical


# ── MAIN ──────────────────────────────────────────────────────────────────────
def run_scraper():
    print("=" * 60)
    print(f"🚀 TradeSage IPO Scraper — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("   Covering: Mainboard + BSE SME + NSE Emerge")
    print("=" * 60)

    # Step 1: Unified IPO list
    all_ipos = scrape_all_ipos()
    sme_count = sum(1 for i in all_ipos if i.get("ipo_type") == "SME")
    mb_count  = sum(1 for i in all_ipos if i.get("ipo_type") == "Mainboard")
    print(f"  → {sme_count} SME + {mb_count} Mainboard = {len(all_ipos)} total")

    if not all_ipos:
        print("❌ No IPOs scraped — check network or site structure."); return

    # Step 2: GMP data
    time.sleep(DELAY)
    gmp_map = scrape_gmp_data()

    # Step 3: Match GMP + use GMP data to improve exchange/type classification
    for ipo in all_ipos:
        slug = slug_from_name(ipo["company"])
        gmp_data = gmp_map.get(slug)
        if not gmp_data:
            for gs, gv in gmp_map.items():
                if slug.split("-")[0] in gs or gs.split("-")[0] in slug:
                    gmp_data = gv; break
        if gmp_data:
            ipo["gmp"] = gmp_data["gmp"]
            ipo["gmp_percent"] = gmp_data["gmp_percent"]
            if not ipo["issue_price"] and gmp_data["issue_price"]:
                ipo["issue_price"] = gmp_data["issue_price"]
            # GMP page often has exchange info — use it to improve classification
            if gmp_data.get("exchange") and ipo["exchange"] in ("BSE SME", "BSE / NSE"):
                ipo["exchange"] = gmp_data["exchange"]
                ipo["ipo_type"] = gmp_data["ipo_type"]

    # Step 4: Enrich with detail pages
    print("🔍 Enriching with detail pages...")
    for i, ipo in enumerate(all_ipos):
        time.sleep(DELAY)
        all_ipos[i] = scrape_ipo_detail(ipo)
        print(f"  [{i+1}/{len(all_ipos)}] {ipo['company']} → {ipo.get('ipo_type','?')} | {ipo.get('exchange','?')}")

    # Step 5: Separate active vs upcoming
    active   = [i for i in all_ipos if i["subscription_status"] == "Open"]
    upcoming = [i for i in all_ipos if i["subscription_status"] == "Upcoming"]

    # Step 6: Historical
    time.sleep(DELAY)
    historical = scrape_historical_ipos()

    # Step 7: Save
    sme_a  = sum(1 for i in active   if i.get("ipo_type") == "SME")
    mb_a   = sum(1 for i in active   if i.get("ipo_type") == "Mainboard")
    sme_u  = sum(1 for i in upcoming if i.get("ipo_type") == "SME")
    mb_u   = sum(1 for i in upcoming if i.get("ipo_type") == "Mainboard")

    output = {
        "scraped_at": datetime.now().isoformat(),
        "source": "live",
        "active_ipos": active,
        "upcoming_ipos": upcoming,
        "historical_ipos": historical,
        "gmp_history": {},
    }
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 60)
    print(f"✅ Done! → {OUTPUT_FILE}")
    print(f"   Active:    {len(active)} ({mb_a} Mainboard, {sme_a} SME)")
    print(f"   Upcoming:  {len(upcoming)} ({mb_u} Mainboard, {sme_u} SME)")
    print(f"   Historical:{len(historical)}")
    print(f"   GMP matched: {sum(1 for i in all_ipos if i['gmp'] != 0)}/{len(all_ipos)}")
    print("=" * 60)


if __name__ == "__main__":
    run_scraper()
