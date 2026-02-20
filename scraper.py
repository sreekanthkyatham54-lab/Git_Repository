"""
scraper.py — Live SME IPO Data Scraper
Sources:
  - IPO List + Dates: ipowatch.in/upcoming-sme-ipo-list/
  - GMP Data:        ipowatch.in/ipo-grey-market-premium-latest-ipo-gmp/
  - IPO Detail:      ipowatch.in/<ipo-slug>-ipo-date-review-price-allotment-details/

Run manually:  python scraper.py
Schedule daily: Add to Windows Task Scheduler or cron (Linux/Mac)

Output: data/live_ipo_data.json  (read by the Streamlit app automatically)
"""

import requests
from bs4 import BeautifulSoup
import json
import os
import re
import time
from datetime import datetime, date

# ── CONFIG ────────────────────────────────────────────────────────────────────
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

BASE_URL = "https://ipowatch.in"
OUTPUT_FILE = os.path.join(os.path.dirname(__file__), "data", "live_ipo_data.json")
DELAY = 1.5  # seconds between requests — be polite to the server


# ── HELPERS ───────────────────────────────────────────────────────────────────
def fetch(url: str) -> BeautifulSoup | None:
    """Fetch a URL and return BeautifulSoup, or None on failure."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        return BeautifulSoup(resp.text, "html.parser")
    except Exception as e:
        print(f"  ⚠ Failed to fetch {url}: {e}")
        return None


def parse_price(text: str) -> float:
    """Extract numeric price from strings like '₹46', '₹43 to ₹46', '₹108'."""
    if not text:
        return 0.0
    # Take the last number (upper band if range)
    nums = re.findall(r"[\d,]+\.?\d*", text.replace(",", ""))
    return float(nums[-1]) if nums else 0.0


def parse_size_cr(text: str) -> float:
    """Extract crore value from strings like '₹26 Cr.'"""
    nums = re.findall(r"[\d,]+\.?\d*", text.replace(",", ""))
    return float(nums[0]) if nums else 0.0


def parse_date_range(text: str) -> tuple[str, str]:
    """
    Parse date strings like '23-25 Feb', '20-24 Feb', '18-20 Feb', '30-03 Feb'.
    Returns (open_date, close_date) as 'YYYY-MM-DD'.
    Handles year rollover (Dec→Jan) and cross-month ranges (e.g. 30 Jan - 3 Feb).
    """
    today = date.today()
    month_map = {
        "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
        "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
    }
    text = text.strip().lower()

    # Pattern: "20-24 feb" or "23-25 feb 2026" or "30-03 feb" (cross-month)
    match = re.search(r"(\d+)[-–](\d+)\s+([a-z]+)(?:\s+(\d{4}))?", text)
    if not match:
        # Single date: "23 feb"
        match2 = re.search(r"(\d+)\s+([a-z]+)(?:\s+(\d{4}))?", text)
        if not match2:
            return "", ""
        d1 = d2 = int(match2.group(1))
        mon = month_map.get(match2.group(2)[:3], today.month)
        yr = int(match2.group(3)) if match2.group(3) else today.year
        try:
            open_d = date(yr, mon, d1).strftime("%Y-%m-%d")
            return open_d, open_d
        except Exception:
            return "", ""

    d1 = int(match.group(1))
    d2 = int(match.group(2))
    mon = month_map.get(match.group(3)[:3], today.month)
    yr = int(match.group(4)) if match.group(4) else today.year

    try:
        # Handle cross-month: open day > close day means open is in previous month
        # e.g. "30-03 Feb" = open Jan 30, close Feb 3
        if d1 > d2 and d1 > 20:
            open_mon = mon - 1 if mon > 1 else 12
            open_yr = yr if mon > 1 else yr - 1
            open_d = date(open_yr, open_mon, d1).strftime("%Y-%m-%d")
            close_d = date(yr, mon, d2).strftime("%Y-%m-%d")
        else:
            open_d = date(yr, mon, d1).strftime("%Y-%m-%d")
            close_d = date(yr, mon, d2).strftime("%Y-%m-%d")

        # Year sanity: if the computed date is > 6 months in past, bump year
        open_date_obj = datetime.strptime(open_d, "%Y-%m-%d").date()
        if (today - open_date_obj).days > 180:
            # Likely next year
            open_d = date(yr + 1, mon, d1).strftime("%Y-%m-%d")
            close_d = date(yr + 1, mon, d2).strftime("%Y-%m-%d")

        return open_d, close_d
    except Exception:
        return "", ""


def determine_status(open_date: str, close_date: str) -> str:
    """Return 'Open', 'Upcoming', or 'Closed' based on today's date."""
    try:
        today = date.today()
        od = datetime.strptime(open_date, "%Y-%m-%d").date()
        cd = datetime.strptime(close_date, "%Y-%m-%d").date()
        if od <= today <= cd:
            return "Open"
        elif today < od:
            return "Upcoming"
        else:
            return "Closed"
    except Exception:
        return "Upcoming"


def slug_from_name(company: str) -> str:
    """Convert 'Accord Transformer' → 'accord-transformer'"""
    slug = company.lower().strip()
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    slug = re.sub(r"\s+", "-", slug)
    return slug


# ── SCRAPER 1: IPO LIST ───────────────────────────────────────────────────────
def scrape_sme_ipo_list() -> list[dict]:
    """
    Scrape the SME IPO list from ipowatch.in.
    The page shows one table with open + upcoming + recent closed IPOs.
    We filter by date to keep only Open and Upcoming.
    """
    print("📋 Scraping SME IPO list from ipowatch.in...")
    soup = fetch(f"{BASE_URL}/upcoming-sme-ipo-list/")
    if not soup:
        return []

    ipos = []
    tables = soup.find_all("table")
    for table in tables:
        rows = table.find_all("tr")
        for row in rows[1:]:  # skip header row
            cols = row.find_all("td")
            if len(cols) < 4:
                continue
            try:
                # Col 0: Company name + detail link
                name_cell = cols[0]
                link_tag = name_cell.find("a")
                if not link_tag:
                    continue
                company = link_tag.get_text(strip=True)
                if not company or len(company) < 3:
                    continue
                detail_url = link_tag.get("href", "")
                if detail_url and not detail_url.startswith("http"):
                    detail_url = BASE_URL + detail_url

                # Col 1: Date range e.g. "23-25 Feb" or "20-24 Feb"
                date_text = cols[1].get_text(strip=True)

                # Handle "TBA" / "To be announced" dates — still show as upcoming
                if any(x in date_text.upper() for x in ["TBA", "TO BE", "ANNOUNCED", "-"]):
                    if date_text.strip() in ["-", "TBA", "—"]:
                        open_date = (date.today()).strftime("%Y-%m-%d")
                        close_date = open_date
                        status = "Upcoming"
                    else:
                        open_date, close_date = parse_date_range(date_text)
                        if not open_date:
                            continue
                        status = determine_status(open_date, close_date)
                else:
                    open_date, close_date = parse_date_range(date_text)
                    if not open_date:
                        continue
                    status = determine_status(open_date, close_date)

                # Skip IPOs that have already closed
                if status == "Closed":
                    continue

                # Col 2: Issue size
                size_text = cols[2].get_text(strip=True)
                issue_size = parse_size_cr(size_text)

                # Col 3: Price band — take upper end of range
                price_text = cols[3].get_text(strip=True)
                issue_price = parse_price(price_text)

                # Col 4: Exchange platform
                platform = cols[4].get_text(strip=True) if len(cols) > 4 else "BSE SME"
                if "NSE" in platform.upper():
                    exchange = "NSE Emerge"
                else:
                    exchange = "BSE SME"

                ipo_id = f"ipo_{slug_from_name(company)}"

                ipos.append({
                    "id": ipo_id,
                    "company": company,
                    "exchange": exchange,
                    "open_date": open_date,
                    "close_date": close_date,
                    "issue_price": issue_price,
                    "issue_size_cr": issue_size,
                    "subscription_status": status,
                    "detail_url": detail_url,
                    # Fields enriched later
                    "sector": "—",
                    "lot_size": 0,
                    "subscription_times": 0.0,
                    "gmp": 0,
                    "gmp_percent": 0.0,
                    "lead_manager": "—",
                    "registrar": "—",
                    "objects": "—",
                    "revenue_cr": [],
                    "profit_cr": [],
                    "years": [],
                    "peers": [],
                    "pe_ratio": 0.0,
                    "industry_pe": 0.0,
                    "promoter_holding": 0.0,
                    "listing_date": "",
                    "recommendation": "—",
                    "risk": "Medium",
                    "summary": f"{company} SME IPO opening {open_date} on {exchange}.",
                    "risks_text": "See DRHP for detailed risk factors.",
                    "drhp_highlights": "Scraping detail page...",
                })

                status_icon = "🟢" if status == "Open" else "🔵"
                print(f"  {status_icon} {company} ({status}) | ₹{issue_price} | {exchange} | {open_date} to {close_date}")

            except Exception as e:
                print(f"  ⚠ Row parse error: {e}")
                continue

    print(f"\n  → {sum(1 for i in ipos if i['subscription_status'] == 'Open')} Open, "
          f"{sum(1 for i in ipos if i['subscription_status'] == 'Upcoming')} Upcoming\n")
    return ipos


# ── SCRAPER 2: GMP DATA ───────────────────────────────────────────────────────
def scrape_gmp_data() -> dict[str, dict]:
    """Scrape GMP from ipowatch.in GMP page. Returns {company_slug: {gmp, gmp_pct}}"""
    print("📊 Scraping GMP data from ipowatch.in...")
    soup = fetch(f"{BASE_URL}/ipo-grey-market-premium-latest-ipo-gmp/")
    if not soup:
        return {}

    gmp_map = {}
    tables = soup.find_all("table")
    for table in tables:
        rows = table.find_all("tr")
        for row in rows[1:]:
            cols = row.find_all("td")
            if len(cols) < 3:
                continue
            try:
                name_cell = cols[0]
                company_name = name_cell.get_text(strip=True)
                slug = slug_from_name(company_name)

                # Find GMP column — usually col 2 or 3
                gmp_text = ""
                for col in cols[1:4]:
                    txt = col.get_text(strip=True)
                    if "₹" in txt or re.search(r"-?\d+", txt):
                        gmp_text = txt
                        break

                # Parse GMP value
                gmp_nums = re.findall(r"-?\d+\.?\d*", gmp_text)
                gmp_val = int(float(gmp_nums[0])) if gmp_nums else 0

                # Find issue price to compute %
                price_text = ""
                for col in cols:
                    txt = col.get_text(strip=True)
                    if "₹" in txt and re.search(r"\d{2,}", txt):
                        price_text = txt
                        break
                price = parse_price(price_text) or 100  # fallback

                gmp_pct = round((gmp_val / price) * 100, 2) if price else 0.0

                gmp_map[slug] = {"gmp": gmp_val, "gmp_percent": gmp_pct}
                if gmp_val != 0:
                    print(f"  ✓ GMP {company_name}: ₹{gmp_val} ({gmp_pct}%)")

            except Exception:
                continue

    print(f"  → Found GMP data for {len(gmp_map)} IPOs\n")
    return gmp_map


# ── SCRAPER 3: IPO DETAIL PAGE ────────────────────────────────────────────────
def scrape_ipo_detail(ipo: dict) -> dict:
    """Scrape individual IPO detail page for lot size, sector, financials etc."""
    url = ipo.get("detail_url", "")
    if not url:
        return ipo

    print(f"  🔍 Detail: {ipo['company']}...")
    soup = fetch(url)
    if not soup:
        return ipo

    full_text = soup.get_text(separator=" ", strip=True)

    # ── Lot size
    lot_match = re.search(r"(?:lot size|market lot)[^\d]*(\d[\d,]*)", full_text, re.IGNORECASE)
    if lot_match:
        ipo["lot_size"] = int(lot_match.group(1).replace(",", ""))

    # ── Sector — look for common keywords
    sector_keywords = [
        "Technology", "Pharma", "Chemical", "FMCG", "Finance", "Banking",
        "Real Estate", "Manufacturing", "Retail", "Logistics", "Healthcare",
        "Education", "Agriculture", "Textile", "Metal", "Engineering",
        "Food", "IT", "Media", "Infrastructure", "Energy", "Auto",
    ]
    for kw in sector_keywords:
        if kw.lower() in full_text.lower():
            ipo["sector"] = kw
            break

    # ── Lead manager
    lm_match = re.search(
        r"(?:lead manager|book running|merchant banker)[^\n:]*[:\s]+([A-Z][^\n,\.]{5,50})",
        full_text, re.IGNORECASE
    )
    if lm_match:
        ipo["lead_manager"] = lm_match.group(1).strip()

    # ── Registrar
    reg_match = re.search(
        r"registrar[^\n:]*[:\s]+([A-Z][^\n,\.]{5,50})",
        full_text, re.IGNORECASE
    )
    if reg_match:
        ipo["registrar"] = reg_match.group(1).strip()

    # ── Summary — grab first meaningful paragraph after h1
    paras = soup.find_all("p")
    for p in paras:
        txt = p.get_text(strip=True)
        if len(txt) > 100 and ipo["company"].split()[0].lower() in txt.lower():
            ipo["summary"] = txt[:400]
            break

    # ── Objects of issue
    obj_match = re.search(
        r"objects? of (?:the )?issue[^\n]*\n([^\n]{30,300})",
        full_text, re.IGNORECASE
    )
    if obj_match:
        ipo["objects"] = obj_match.group(1).strip()

    # ── Subscription times (if open)
    sub_match = re.search(
        r"(?:subscribed|subscription)[^\d]*(\d+\.?\d*)\s*(?:times|x)",
        full_text, re.IGNORECASE
    )
    if sub_match:
        ipo["subscription_times"] = float(sub_match.group(1))

    # ── Listing date
    listing_match = re.search(
        r"listing (?:date|on)[^\d]*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\w+ \d{1,2},? \d{4})",
        full_text, re.IGNORECASE
    )
    if listing_match:
        ipo["listing_date"] = listing_match.group(1)

    return ipo


# ── SCRAPER 4: HISTORICAL IPO DATA ───────────────────────────────────────────
def scrape_historical_ipos() -> list[dict]:
    """Scrape recent listed SME IPOs and their listing performance."""
    print("📜 Scraping historical IPO performance...")
    soup = fetch(f"{BASE_URL}/ipo-performance-tracker/")
    if not soup:
        return []

    historical = []
    tables = soup.find_all("table")
    for table in tables:
        rows = table.find_all("tr")
        for row in rows[1:21]:  # top 20 historical
            cols = row.find_all("td")
            if len(cols) < 4:
                continue
            try:
                name_cell = cols[0]
                company = name_cell.get_text(strip=True)
                if not company or len(company) < 3:
                    continue

                # Try to extract issue price, listing price, current price
                nums = []
                for col in cols[1:]:
                    txt = col.get_text(strip=True)
                    found = re.findall(r"[\d,]+\.?\d*", txt.replace(",", ""))
                    if found:
                        nums.append(float(found[0]))

                if len(nums) >= 2:
                    issue_price = nums[0]
                    listing_price = nums[1]
                    current_price = nums[2] if len(nums) > 2 else listing_price
                    listing_gain = round(((listing_price - issue_price) / issue_price) * 100, 1) if issue_price else 0

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
                    })

            except Exception:
                continue

    print(f"  → Found {len(historical)} historical IPOs\n")
    return historical


# ── MAIN RUNNER ───────────────────────────────────────────────────────────────
def run_scraper():
    print("=" * 60)
    print(f"🚀 SME IPO Scraper — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # Step 1: Get IPO list
    all_ipos = scrape_sme_ipo_list()

    if not all_ipos:
        print("❌ No IPOs scraped — check network or site structure changed.")
        return

    # Step 2: Get GMP data
    time.sleep(DELAY)
    gmp_map = scrape_gmp_data()

    # Step 3: Match GMP to IPOs
    for ipo in all_ipos:
        slug = slug_from_name(ipo["company"])
        # Try exact match first, then partial
        gmp_data = gmp_map.get(slug)
        if not gmp_data:
            for gmp_slug, gmp_vals in gmp_map.items():
                # Match on first significant word
                if slug.split("-")[0] in gmp_slug or gmp_slug.split("-")[0] in slug:
                    gmp_data = gmp_vals
                    break
        if gmp_data:
            ipo["gmp"] = gmp_data["gmp"]
            ipo["gmp_percent"] = gmp_data["gmp_percent"]

    # Step 4: Enrich with detail pages (throttled)
    print("🔍 Fetching IPO detail pages...")
    for i, ipo in enumerate(all_ipos):
        time.sleep(DELAY)
        all_ipos[i] = scrape_ipo_detail(ipo)

    # Step 5: Separate active vs upcoming
    active = [i for i in all_ipos if i["subscription_status"] == "Open"]
    upcoming = [i for i in all_ipos if i["subscription_status"] == "Upcoming"]

    # Step 6: Get historical data
    time.sleep(DELAY)
    historical = scrape_historical_ipos()

    # Step 7: Save to JSON
    output = {
        "scraped_at": datetime.now().isoformat(),
        "active_ipos": active,
        "upcoming_ipos": upcoming,
        "historical_ipos": historical,
        "gmp_history": {},  # GMP trend history — requires daily tracking over time
    }

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 60)
    print(f"✅ Done! Saved to {OUTPUT_FILE}")
    print(f"   Active IPOs:   {len(active)}")
    print(f"   Upcoming IPOs: {len(upcoming)}")
    print(f"   Historical:    {len(historical)}")
    print(f"   GMP matched:   {sum(1 for i in all_ipos if i['gmp'] != 0)}")
    print("=" * 60)


if __name__ == "__main__":
    run_scraper()
