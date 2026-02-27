"""
data_loader.py — loads IPO data and enriches with DRHP DB
"""
import json, os
from datetime import datetime, timedelta, timezone

_IST = timezone(timedelta(hours=5, minutes=30))

def _today_ist():
    return datetime.now(_IST).date()

def _recompute_status(active_ipos, upcoming_ipos):
    """
    Re-evaluate subscription_status using the current IST date.
    Scraper status can be stale between the last daily run and midnight IST,
    causing closed IPOs to linger as 'Open' until the next scrape.
    """
    today = _today_ist()
    active, upcoming = [], []
    for ipo in active_ipos + upcoming_ipos:
        try:
            od = datetime.strptime(ipo["open_date"], "%Y-%m-%d").date()
            cd = datetime.strptime(ipo["close_date"], "%Y-%m-%d").date()
            if od <= today <= cd:
                ipo["subscription_status"] = "Open"
                active.append(ipo)
            elif today < od:
                ipo["subscription_status"] = "Upcoming"
                upcoming.append(ipo)
            # today > cd → IPO closed, drop it silently
        except Exception:
            active.append(ipo)  # keep if dates are unparseable
    return active, upcoming

LIVE_DATA_FILE = os.path.join(os.path.dirname(__file__), "data", "live_ipo_data.json")
MAX_AGE_HOURS  = 12

def _is_fresh(filepath):
    if not os.path.exists(filepath): return False
    mtime = datetime.fromtimestamp(os.path.getmtime(filepath))
    return datetime.now() - mtime < timedelta(hours=MAX_AGE_HOURS)

def _load_seed():
    from data.ipo_data import ACTIVE_IPOS, UPCOMING_IPOS, HISTORICAL_IPOS, GMP_HISTORY
    return {"active_ipos": ACTIVE_IPOS, "upcoming_ipos": UPCOMING_IPOS,
            "historical_ipos": HISTORICAL_IPOS, "gmp_history": GMP_HISTORY, "scraped_at": None}

def load_ipo_data():
    if _is_fresh(LIVE_DATA_FILE):
        try:
            with open(LIVE_DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            data["source"] = "live"
        except Exception as e:
            print(f"⚠ Live data failed: {e}"); data = _load_seed(); data["source"] = "seed"
    else:
        data = _load_seed(); data["source"] = "seed"

    # Re-evaluate open/upcoming status using current IST time — scraper status can be stale
    data["active_ipos"], data["upcoming_ipos"] = _recompute_status(
        data.get("active_ipos", []), data.get("upcoming_ipos", [])
    )

    # Fix historical IPOs: compute gmp_before_listing from issue_price + gmp_predicted_gain if zero/missing
    for ipo in data.get("historical_ipos", []):
        gmp_val = ipo.get("gmp_before_listing", 0)
        if not gmp_val and ipo.get("gmp_predicted_gain") and ipo.get("issue_price"):
            ipo["gmp_before_listing"] = round(ipo["issue_price"] * ipo["gmp_predicted_gain"] / 100)

    # Enrich with DRHP DB if available
    try:
        from db_reader import enrich_ipo_with_drhp, get_db_stats
        data["active_ipos"]   = [enrich_ipo_with_drhp(i) for i in data.get("active_ipos", [])]
        data["upcoming_ipos"] = [enrich_ipo_with_drhp(i) for i in data.get("upcoming_ipos", [])]
        data["db_stats"]      = get_db_stats()
        n = data["db_stats"]["ipos_with_financials"]
        if n: print(f"✅ DRHP DB: {n} IPOs enriched with financials")
    except Exception as e:
        print(f"ℹ DRHP DB not ready yet: {e}")
        data["db_stats"] = {"ipos_with_drhp": 0, "ipos_with_financials": 0, "total_pdf_size_mb": 0}

    return data
