"""
scraper.py — All India IPO Scraper (Mainboard + SME)
Sources:
  - All IPO List + GMP: ipowatch.in
    - SME:       /upcoming-sme-ipo-list/
    - Mainboard: /upcoming-ipo-list/
    - GMP:       /ipo-grey-market-premium-latest-ipo-gmp/
  - Historical:  /ipo-performance-tracker/

Run manually:  python scraper.py
Output: data/live_ipo_data.json
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
BASE_URL   = "https://ipowatch.in"
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
    yr = int(match.group(4)) if match.group(4) else today.year
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


def classify_ipo_type(company, exchange, issue_size_cr):
    """Classify IPO as Mainboard or SME based on exchange and issue size."""
    ex = (exchange or "").upper()
    if "BSE SME" in ex or "NSE EMERGE" in ex or "NSE SME" in ex:
        return "SME"
    # Mainboard threshold: typically >₹25Cr and on BSE/NSE mainboard
    if issue_size_cr and float(issue_size_cr) >= 25:
        return "Mainboard"
    return "SME"


# ── SCRAPER 1A: SME IPO LIST ──────────────────────────────────────────────────
def scrape_sme_ipo_list():
    print("📋 Scraping SME IPO list...")
    soup = fetch(f"{BASE_URL}/upcoming-sme-ipo-list/")
    if not soup: return []
    return _parse_ipo_table(soup, default_type="SME")


# ── SCRAPER 1B: MAINBOARD IPO LIST ───────────────────────────────────────────
def scrape_mainboard_ipo_list():
    print("📋 Scraping Mainboard IPO list...")
    soup = fetch(f"{BASE_URL}/upcoming-ipo-list/")
    if not soup: return []
    return _parse_ipo_table(soup, default_type="Mainboard")


def _parse_ipo_table(soup, default_type="SME"):
    """Parse IPO table rows — shared logic for SME and Mainboard."""
    ipos = []
    ipo_id_counter = len(ipos)
    tables = soup.find_all("table")
    for table in tables:
        rows = table.find_all("tr")
        for row in rows[1:]:
            cols = row.find_all("td")
            if len(cols) < 4: continue
            try:
                name_cell = cols[0]
                link_tag  = name_cell.find("a")
                if not link_tag: continue
                company = link_tag.get_text(strip=True)
                if not company or len(company) < 3: continue
                detail_url = link_tag.get("href", "")
                if detail_url and not detail_url.startswith("http"):
                    detail_url = BASE_URL + detail_url

                date_text = cols[1].get_text(strip=True) if len(cols) > 1 else ""
                price_text = cols[2].get_text(strip=True) if len(cols) > 2 else ""
                size_text  = cols[3].get_text(strip=True) if len(cols) > 3 else ""

                open_date, close_date = parse_date_range(date_text)
                if not open_date: continue

                status = determine_status(open_date, close_date)
                if status == "Closed": continue

                issue_price   = parse_price(price_text)
                issue_size_cr = parse_size_cr(size_text)

                # Detect exchange from text hints
                row_text = row.get_text(" ").upper()
                if "NSE EMERGE" in row_text or "NSE SME" in row_text:
                    exchange = "NSE Emerge"
                elif "BSE SME" in row_text:
                    exchange = "BSE SME"
                elif default_type == "Mainboard":
                    exchange = "BSE / NSE"
                else:
                    exchange = "BSE SME"

                ipo_type = "Mainboard" if default_type == "Mainboard" else "SME"

                ipo_id_counter += 1
                ipos.append({
                    "id": f"ipo_{ipo_id_counter:03d}",
                    "company": company,
                    "exchange": exchange,
                    "ipo_type": ipo_type,          # NEW: "SME" or "Mainboard"
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
                print(f"  ⚠ Row parse error: {e}")
                continue
    return ipos


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
                company = cols[0].get_text(strip=True)
                if not company: continue
                gmp_text = cols[2].get_text(strip=True) if len(cols) > 2 else ""
                price_text = cols[1].get_text(strip=True) if len(cols) > 1 else ""
                gmp_val   = parse_price(gmp_text)
                issue_p   = parse_price(price_text)
                gmp_pct   = round(gmp_val / issue_p * 100, 1) if issue_p > 0 else 0.0
                gmp_map[slug_from_name(company)] = {
                    "company": company,
                    "gmp": gmp_val,
                    "gmp_percent": gmp_pct,
                    "issue_price": issue_p,
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
    price_match = re.search(r"(?:issue price|price band)[:\s]*₹?([\d,]+(?:\s*(?:to|-)\s*[\d,]+)?)", text, re.I)
    if price_match and not ipo["issue_price"]:
        ipo["issue_price"] = parse_price(price_match.group(1))

    # Lot size
    lot_match = re.search(r"lot size[:\s]*([\d,]+)\s*(?:shares?|equity)", text, re.I)
    if lot_match: ipo["lot_size"] = int(lot_match.group(1).replace(",", ""))

    # Lead manager
    lm_match = re.search(r"(?:lead manager|book running)[:\s]+([A-Z][^\n\.]{5,60}?)(?:\n|\.|\band\b)", text, re.I)
    if lm_match: ipo["lead_manager"] = lm_match.group(1).strip()

    # Registrar
    reg_match = re.search(r"registrar[:\s]+([A-Z][^\n\.]{5,60}?)(?:\n|\.)", text, re.I)
    if reg_match: ipo["registrar"] = reg_match.group(1).strip()

    # Summary — first substantive paragraph
    paras = [p.get_text(strip=True) for p in soup.find_all("p") if len(p.get_text(strip=True)) > 80]
    if paras: ipo["summary"] = paras[0][:400]

    # Sector from page title or content
    sector_match = re.search(r"(?:industry|sector)[:\s]+([A-Z][a-zA-Z &]{3,40})", text, re.I)
    if sector_match: ipo["sector"] = sector_match.group(1).strip()

    # Detect exchange from page text
    if ipo["exchange"] == "BSE SME" or ipo["exchange"] == "—":
        if "nse emerge" in text.lower(): ipo["exchange"] = "NSE Emerge"
        elif "bse sme" in text.lower(): ipo["exchange"] = "BSE SME"
        elif "nse" in text.lower() and "bse" in text.lower() and ipo.get("ipo_type") == "Mainboard":
            ipo["exchange"] = "BSE / NSE"

    # Promoter holding
    promo_match = re.search(r"promoter[^%]*?([\d.]+)\s*%", text, re.I)
    if promo_match: ipo["promoter_holding"] = float(promo_match.group(1))

    # Risk level
    t_lower = text.lower()
    if "high risk" in t_lower: ipo["risk"] = "High"
    elif "low risk" in t_lower: ipo["risk"] = "Low"
    else: ipo["risk"] = "Medium"

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
        for row in rows[1:30]:  # top 30
            cols = row.find_all("td")
            if len(cols) < 4: continue
            try:
                company = cols[0].get_text(strip=True)
                if not company or len(company) < 3: continue
                nums = []
                for col in cols[1:]:
                    txt = col.get_text(strip=True)
                    found = re.findall(r"[\d,]+\.?\d*", txt.replace(",", ""))
                    if found: nums.append(float(found[0]))
                if len(nums) >= 2:
                    issue_price   = nums[0]
                    listing_price = nums[1]
                    current_price = nums[2] if len(nums) > 2 else listing_price
                    listing_gain  = round(((listing_price - issue_price) / issue_price) * 100, 1) if issue_price else 0

                    # Try to detect if mainboard from issue size (usually large)
                    ipo_type = "Mainboard" if issue_price > 500 else "SME"

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
                        "exchange": "BSE SME",
                        "ipo_type": ipo_type,
                    })
            except: continue
    print(f"  → {len(historical)} historical IPOs")
    return historical


# ── MAIN ──────────────────────────────────────────────────────────────────────
def run_scraper():
    print("=" * 60)
    print(f"🚀 TradeSage IPO Scraper — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("   Covering: Mainboard + SME (BSE SME + NSE Emerge)")
    print("=" * 60)

    # Step 1: Scrape both SME and Mainboard lists
    sme_ipos = scrape_sme_ipo_list()
    time.sleep(DELAY)
    mainboard_ipos = scrape_mainboard_ipo_list()
    all_ipos = sme_ipos + mainboard_ipos

    # Deduplicate by company name
    seen = set()
    deduped = []
    for ipo in all_ipos:
        key = slug_from_name(ipo["company"])
        if key not in seen:
            seen.add(key)
            deduped.append(ipo)
    all_ipos = deduped
    print(f"  → {len(sme_ipos)} SME + {len(mainboard_ipos)} Mainboard = {len(all_ipos)} unique IPOs")

    if not all_ipos:
        print("❌ No IPOs scraped."); return

    # Step 2: GMP data
    time.sleep(DELAY)
    gmp_map = scrape_gmp_data()

    # Step 3: Match GMP
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

    # Step 4: Detail pages
    print("🔍 Enriching with detail pages...")
    for i, ipo in enumerate(all_ipos):
        time.sleep(DELAY)
        all_ipos[i] = scrape_ipo_detail(ipo)
        print(f"  [{i+1}/{len(all_ipos)}] {ipo['company']} ({ipo.get('ipo_type','?')})")

    # Step 5: Separate active vs upcoming
    active   = [i for i in all_ipos if i["subscription_status"] == "Open"]
    upcoming = [i for i in all_ipos if i["subscription_status"] == "Upcoming"]

    # Step 6: Historical
    time.sleep(DELAY)
    historical = scrape_historical_ipos()

    # Step 7: Save
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
    print(f"   Active:    {len(active)} ({sum(1 for i in active if i.get('ipo_type')=='Mainboard')} mainboard, {sum(1 for i in active if i.get('ipo_type')=='SME')} SME)")
    print(f"   Upcoming:  {len(upcoming)} ({sum(1 for i in upcoming if i.get('ipo_type')=='Mainboard')} mainboard, {sum(1 for i in upcoming if i.get('ipo_type')=='SME')} SME)")
    print(f"   Historical:{len(historical)}")
    print(f"   GMP matched: {sum(1 for i in all_ipos if i['gmp'] != 0)}/{len(all_ipos)}")
    print("=" * 60)


if __name__ == "__main__":
    run_scraper()
