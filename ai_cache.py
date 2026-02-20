"""
ai_cache.py — Pre-generate and cache AI content for all IPOs
Run by GitHub Actions twice daily alongside scraper.py
Saves results to data/ai_cache.json
"""
import json, os, sys, time
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))

CACHE_FILE = os.path.join(os.path.dirname(__file__), "data", "ai_cache.json")


def load_cache():
    if os.path.exists(CACHE_FILE):
        try:
            return json.load(open(CACHE_FILE))
        except:
            pass
    return {}


def save_cache(cache):
    os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
    json.dump(cache, open(CACHE_FILE, "w"), indent=2)


def get_cached(ipo_id, content_type, cache=None):
    """Get cached content for an IPO. Returns None if not cached."""
    if cache is None:
        cache = load_cache()
    return cache.get(ipo_id, {}).get(content_type)


def run_cache_generation(api_key):
    """Generate and cache AI content for all active/upcoming IPOs."""
    from data_loader import load_ipo_data
    from utils.ai_utils import get_ai_recommendation, compare_with_industry, chat_with_ipo

    data = load_ipo_data()
    all_ipos = data["active_ipos"] + data["upcoming_ipos"]
    cache = load_cache()

    print(f"Caching AI content for {len(all_ipos)} IPOs...")

    for ipo in all_ipos:
        ipo_id = ipo["id"]
        company = ipo["company"]

        if ipo_id not in cache:
            cache[ipo_id] = {}

        # 1. Scorecard
        try:
            print(f"  [{company}] Generating scorecard...")
            result = get_ai_recommendation(api_key, ipo)
            cache[ipo_id]["scorecard"] = result
            cache[ipo_id]["scorecard_at"] = datetime.now().isoformat()
            time.sleep(2)
        except Exception as e:
            print(f"  [{company}] Scorecard error: {e}")

        # 2. Industry analysis
        try:
            print(f"  [{company}] Generating industry analysis...")
            analysis = compare_with_industry(api_key, ipo)
            cache[ipo_id]["industry"] = analysis
            cache[ipo_id]["industry_at"] = datetime.now().isoformat()
            time.sleep(2)
        except Exception as e:
            print(f"  [{company}] Industry error: {e}")

        # 3. News summary
        try:
            print(f"  [{company}] Generating news summary...")
            news_prompt = (
                f"Summarise what is publicly known about {company} IPO — "
                f"any news, analyst views, subscription trends, GMP movement, "
                f"or market sentiment. Keep it concise and factual."
            )
            news = chat_with_ipo(api_key, ipo, [], news_prompt)
            cache[ipo_id]["news"] = news
            cache[ipo_id]["news_at"] = datetime.now().isoformat()
            time.sleep(2)
        except Exception as e:
            print(f"  [{company}] News error: {e}")

        save_cache(cache)  # Save after each IPO so partial progress is kept

    print(f"Done. Cache saved to {CACHE_FILE}")
    return cache


if __name__ == "__main__":
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        # Try reading from .streamlit/secrets.toml locally
        try:
            import toml
            secrets = toml.load(".streamlit/secrets.toml")
            api_key = secrets.get("ANTHROPIC_API_KEY", "")
        except:
            pass
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY not found in environment or secrets.toml")
        sys.exit(1)
    run_cache_generation(api_key)
