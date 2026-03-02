"""
utils/market_data.py — Market data engine for TradeSage Long-Term Module
Fetches live data from Yahoo Finance via yfinance.
All functions handle exceptions gracefully and return fallback data on failure.
"""

import time

# ── STOCK UNIVERSE ─────────────────────────────────────────────────────────────
STOCK_UNIVERSE = [
    "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK",
    "HINDUNILVR", "ITC", "SBIN", "BHARTIARTL", "KOTAKBANK",
    "LT", "AXISBANK", "MARUTI", "TITAN", "SUNPHARMA",
    "WIPRO", "TATAMOTORS", "BAJFINANCE", "DRREDDY", "DIVISLAB",
    "WELSPUNIND", "MANKIND", "ZOMATO", "PAYTM", "DIXON",
    "HFCL", "COCHINSHIP", "ADANIPORTS", "TATASTEEL", "JSWSTEEL",
    "NTPC", "POWERGRID", "COALINDIA", "TECHM", "HCLTECH",
]

STOCK_NAMES = {
    "RELIANCE":"Reliance Industries", "TCS":"Tata Consultancy Services",
    "HDFCBANK":"HDFC Bank", "INFY":"Infosys", "ICICIBANK":"ICICI Bank",
    "HINDUNILVR":"Hindustan Unilever", "ITC":"ITC Ltd", "SBIN":"State Bank of India",
    "BHARTIARTL":"Bharti Airtel", "KOTAKBANK":"Kotak Mahindra Bank",
    "LT":"Larsen & Toubro", "AXISBANK":"Axis Bank", "MARUTI":"Maruti Suzuki",
    "TITAN":"Titan Company", "SUNPHARMA":"Sun Pharmaceutical",
    "WIPRO":"Wipro", "TATAMOTORS":"Tata Motors", "BAJFINANCE":"Bajaj Finance",
    "DRREDDY":"Dr Reddy's Laboratories", "DIVISLAB":"Divi's Laboratories",
    "WELSPUNIND":"Welspun India", "MANKIND":"Mankind Pharma",
    "ZOMATO":"Zomato", "PAYTM":"One97 Communications (Paytm)",
    "DIXON":"Dixon Technologies", "HFCL":"HFCL Ltd",
    "COCHINSHIP":"Cochin Shipyard", "ADANIPORTS":"Adani Ports",
    "TATASTEEL":"Tata Steel", "JSWSTEEL":"JSW Steel",
    "NTPC":"NTPC Ltd", "POWERGRID":"Power Grid Corporation",
    "COALINDIA":"Coal India", "TECHM":"Tech Mahindra", "HCLTECH":"HCL Technologies",
}

SECTOR_MAP = {
    "RELIANCE":"Energy", "TCS":"IT Services", "HDFCBANK":"Banking & NBFC",
    "INFY":"IT Services", "ICICIBANK":"Banking & NBFC",
    "HINDUNILVR":"FMCG", "ITC":"FMCG", "SBIN":"Banking & NBFC",
    "BHARTIARTL":"Telecom", "KOTAKBANK":"Banking & NBFC",
    "LT":"Capital Goods", "AXISBANK":"Banking & NBFC",
    "MARUTI":"Auto", "TITAN":"Consumer", "SUNPHARMA":"Pharma & Healthcare",
    "WIPRO":"IT Services", "TATAMOTORS":"Auto", "BAJFINANCE":"Banking & NBFC",
    "DRREDDY":"Pharma & Healthcare", "DIVISLAB":"Pharma & Healthcare",
    "WELSPUNIND":"Capital Goods", "MANKIND":"Pharma & Healthcare",
    "ZOMATO":"Consumer Tech", "PAYTM":"Consumer Tech",
    "DIXON":"Capital Goods", "HFCL":"Telecom",
    "COCHINSHIP":"Defence & Aerospace", "ADANIPORTS":"Infrastructure",
    "TATASTEEL":"Capital Goods", "JSWSTEEL":"Capital Goods",
    "NTPC":"Renewable Energy", "POWERGRID":"Infrastructure",
    "COALINDIA":"Energy", "TECHM":"IT Services", "HCLTECH":"IT Services",
}


# ── TECHNICAL HELPERS ─────────────────────────────────────────────────────────
def _rsi(close, period=14):
    delta = close.diff()
    gain  = delta.clip(lower=0)
    loss  = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1/period, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1/period, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, 1e-10)
    return 100 - (100 / (1 + rs))


def _macd(close, fast=12, slow=26, signal=9):
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    macd_line   = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    return macd_line, signal_line


# ── PUBLIC FUNCTIONS ──────────────────────────────────────────────────────────

def get_nifty_indices():
    """Fetch Nifty 50 and Sensex current price + % change."""
    try:
        import yfinance as yf
        tickers = yf.download(["^NSEI", "^BSESN"], period="2d", interval="1d",
                               progress=False, show_errors=False)
        close = tickers["Close"]
        nifty_vals  = close["^NSEI"].dropna()
        sensex_vals = close["^BSESN"].dropna()
        nifty  = round(float(nifty_vals.iloc[-1]), 2)
        sensex = round(float(sensex_vals.iloc[-1]), 2)
        nifty_chg  = round((nifty_vals.iloc[-1]  / nifty_vals.iloc[-2]  - 1) * 100, 2) if len(nifty_vals)  > 1 else 0.0
        sensex_chg = round((sensex_vals.iloc[-1] / sensex_vals.iloc[-2] - 1) * 100, 2) if len(sensex_vals) > 1 else 0.0
        return {"nifty": nifty, "nifty_chg": nifty_chg,
                "sensex": sensex, "sensex_chg": sensex_chg}
    except Exception:
        return {"nifty": 25287.75, "nifty_chg": -0.82,
                "sensex": 81659.73, "sensex_chg": -0.72}


def get_market_pulse(max_stocks=35):
    """
    Scan stock universe for recent trend changes (last 1-2 days).
    Returns {bullish: [...], bearish: [...]} — each item has
    {symbol, name, price, pct_chg, reason, sector}.
    """
    try:
        import yfinance as yf
        import pandas as pd

        symbols = [s + ".NS" for s in STOCK_UNIVERSE[:max_stocks]]
        raw = yf.download(symbols, period="1y", interval="1d",
                          progress=False, show_errors=False, group_by="ticker")

        bullish, bearish = [], []

        for sym_ns in symbols:
            sym = sym_ns.replace(".NS", "")
            try:
                if len(symbols) == 1:
                    close = raw["Close"].dropna()
                else:
                    close = raw[sym_ns]["Close"].dropna() if sym_ns in raw.columns.get_level_values(0) else None

                if close is None or len(close) < 210:
                    continue

                price   = round(float(close.iloc[-1]), 2)
                pct_chg = round((close.iloc[-1] / close.iloc[-2] - 1) * 100, 2) if len(close) > 1 else 0.0

                dma50  = close.rolling(50).mean()
                dma200 = close.rolling(200).mean()
                macd_line, signal_line = _macd(close)
                hist = macd_line - signal_line

                item = {
                    "symbol":  sym,
                    "name":    STOCK_NAMES.get(sym, sym),
                    "price":   price,
                    "pct_chg": pct_chg,
                    "sector":  SECTOR_MAP.get(sym, ""),
                }

                # Crossed above 200 DMA (in last 2 days)
                if (close.iloc[-1] > dma200.iloc[-1] and
                        close.iloc[-2] <= dma200.iloc[-2]):
                    bullish.append({**item, "reason": "Crossed above 200 DMA"})
                    continue
                # Crossed above 50 DMA
                elif (close.iloc[-1] > dma50.iloc[-1] and
                        close.iloc[-2] <= dma50.iloc[-2]):
                    bullish.append({**item, "reason": "Crossed above 50 DMA"})
                    continue
                # MACD bullish crossover
                elif (hist.iloc[-1] > 0 and hist.iloc[-2] <= 0):
                    bullish.append({**item, "reason": "MACD bullish crossover"})
                    continue

                # Crossed below 200 DMA
                if (close.iloc[-1] < dma200.iloc[-1] and
                        close.iloc[-2] >= dma200.iloc[-2]):
                    bearish.append({**item, "reason": "Crossed below 200 DMA"})
                    continue
                # Crossed below 50 DMA
                elif (close.iloc[-1] < dma50.iloc[-1] and
                        close.iloc[-2] >= dma50.iloc[-2]):
                    bearish.append({**item, "reason": "Crossed below 50 DMA"})
                    continue
                # MACD bearish crossover
                elif (hist.iloc[-1] < 0 and hist.iloc[-2] >= 0):
                    bearish.append({**item, "reason": "MACD bearish crossover"})
                    continue

            except Exception:
                continue

        if not bullish and not bearish:
            return _mock_market_pulse()

        return {"bullish": bullish, "bearish": bearish}

    except Exception:
        return _mock_market_pulse()


def _mock_market_pulse():
    return {
        "bullish": [
            {"symbol":"LT",       "name":"Larsen & Toubro",       "price":3612.45, "pct_chg":+1.82, "reason":"Crossed above 200 DMA",     "sector":"Capital Goods"},
            {"symbol":"COCHINSHIP","name":"Cochin Shipyard",       "price":1724.30, "pct_chg":+3.14, "reason":"MACD bullish crossover",     "sector":"Defence & Aerospace"},
            {"symbol":"SUNPHARMA", "name":"Sun Pharmaceutical",    "price":1821.75, "pct_chg":+1.22, "reason":"Crossed above 50 DMA",      "sector":"Pharma & Healthcare"},
            {"symbol":"NTPC",      "name":"NTPC Ltd",              "price": 368.90, "pct_chg":+0.95, "reason":"MACD bullish crossover",     "sector":"Renewable Energy"},
        ],
        "bearish": [
            {"symbol":"PAYTM",    "name":"One97 (Paytm)",          "price": 341.20, "pct_chg":-2.85, "reason":"Crossed below 200 DMA",     "sector":"Consumer Tech"},
            {"symbol":"TATAMOTORS","name":"Tata Motors",           "price": 841.50, "pct_chg":-1.95, "reason":"MACD bearish crossover",    "sector":"Auto"},
            {"symbol":"AXISBANK", "name":"Axis Bank",              "price":1124.60, "pct_chg":-0.88, "reason":"Crossed below 50 DMA",      "sector":"Banking & NBFC"},
        ],
    }


def _fetch_google_news(company_name, symbol, max_items=5):
    """
    Fetch recent news via Google News RSS feed.
    Returns list of {title, date, source} dicts. Never raises.
    """
    import requests
    from xml.etree import ElementTree as ET
    from datetime import datetime
    from urllib.parse import quote_plus

    # Search for company name + NSE to get Indian financial news
    query = f"{company_name} {symbol} NSE"
    url   = (f"https://news.google.com/rss/search"
             f"?q={quote_plus(query)}&hl=en-IN&gl=IN&ceid=IN:en")
    try:
        r = requests.get(url, timeout=8,
                         headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
        root  = ET.fromstring(r.content)
        items = root.findall(".//item")[:max_items]
        news  = []
        for item in items:
            title = item.findtext("title", "").strip()
            # Google News titles often have "- Source" suffix — strip it
            if " - " in title:
                title, source = title.rsplit(" - ", 1)
            else:
                source = item.findtext("source", "")
            pub = item.findtext("pubDate", "")
            try:
                dt       = datetime.strptime(pub, "%a, %d %b %Y %H:%M:%S %Z")
                date_str = dt.strftime("%d %b")
            except Exception:
                date_str = ""
            if title:
                news.append({"title": title.strip(), "date": date_str,
                             "source": source.strip()})
        return news
    except Exception:
        return []


def get_stock_analysis(symbol):
    """
    Full technical + fundamental analysis for a single NSE symbol.
    symbol: plain NSE code e.g. 'RELIANCE' (no .NS suffix needed).
    """
    sym_ns = symbol.strip().upper() + ".NS"
    try:
        import yfinance as yf

        ticker = yf.Ticker(sym_ns)
        hist   = ticker.history(period="1y")

        if hist.empty or len(hist) < 50:
            return _mock_stock_analysis(symbol)

        close  = hist["Close"]
        volume = hist["Volume"]

        rsi_series   = _rsi(close)
        macd_line, signal_line = _macd(close)
        dma50  = close.rolling(50).mean()
        dma200 = close.rolling(200).mean() if len(close) >= 200 else close.rolling(len(close)).mean()
        vol_avg = volume.rolling(20).mean()

        price       = round(float(close.iloc[-1]), 2)
        pct_chg     = round((close.iloc[-1] / close.iloc[-2] - 1) * 100, 2) if len(close) > 1 else 0.0
        rsi_val     = round(float(rsi_series.iloc[-1]), 1)
        macd_val    = round(float(macd_line.iloc[-1]), 3)
        signal_val  = round(float(signal_line.iloc[-1]), 3)
        dma50_val   = round(float(dma50.iloc[-1]), 2)
        dma200_val  = round(float(dma200.iloc[-1]), 2)
        vol_ratio   = round(float(volume.iloc[-1] / vol_avg.iloc[-1]), 2) if vol_avg.iloc[-1] > 0 else 1.0
        high_52w    = round(float(close.max()), 2)
        low_52w     = round(float(close.min()), 2)

        # Determine signals
        above_50dma  = price > dma50_val
        above_200dma = price > dma200_val
        macd_bull    = macd_val > signal_val

        # Info from ticker.info
        info = {}
        try:
            info = ticker.info or {}
        except Exception:
            pass

        name       = info.get("longName") or info.get("shortName") or STOCK_NAMES.get(symbol.upper(), symbol.upper())
        sector     = info.get("sector") or SECTOR_MAP.get(symbol.upper(), "")
        pe         = info.get("trailingPE") or info.get("forwardPE")
        pe         = round(float(pe), 1) if pe else None
        mktcap     = info.get("marketCap")
        revenue    = info.get("totalRevenue")
        net_income = info.get("netIncomeToCommon")

        def _fmt_cr(val):
            if not val: return "N/A"
            cr = val / 1e7
            if cr >= 1e5: return f"₹{cr/1e5:.1f}L Cr"
            if cr >= 1e3: return f"₹{cr/1e3:.1f}K Cr"
            return f"₹{cr:.0f} Cr"

        def _fmt_mktcap(val):
            if not val: return "N/A"
            cr = val / 1e7
            if cr >= 1e5: return f"₹{cr/1e5:.2f}L Cr"
            return f"₹{cr/1e3:.1f}K Cr"

        # News — try yfinance first, fall back to Google News RSS
        news_items = []
        try:
            raw_news = ticker.news or []
            for n in raw_news[:5]:
                title = n.get("title", "")
                ts    = n.get("providerPublishTime", 0)
                if title:
                    import datetime
                    date_str = datetime.datetime.fromtimestamp(ts).strftime("%d %b") if ts else ""
                    news_items.append({"title": title, "date": date_str})
        except Exception:
            pass

        if not news_items:
            news_items = _fetch_google_news(name, symbol.upper())

        return {
            "symbol":       symbol.upper(),
            "name":         name,
            "sector":       sector,
            "price":        price,
            "pct_chg":      pct_chg,
            "rsi":          rsi_val,
            "macd":         macd_val,
            "signal":       signal_val,
            "macd_bull":    macd_bull,
            "dma50":        dma50_val,
            "dma200":       dma200_val,
            "above_50dma":  above_50dma,
            "above_200dma": above_200dma,
            "vol_ratio":    vol_ratio,
            "high_52w":     high_52w,
            "low_52w":      low_52w,
            "pe":           pe,
            "mktcap":       _fmt_mktcap(mktcap),
            "revenue":      _fmt_cr(revenue),
            "net_income":   _fmt_cr(net_income),
            "news":         news_items,
            "mock":         False,
        }

    except Exception:
        return _mock_stock_analysis(symbol)


def _mock_stock_analysis(symbol):
    return {
        "symbol":       symbol.upper(),
        "name":         STOCK_NAMES.get(symbol.upper(), symbol.upper()),
        "sector":       SECTOR_MAP.get(symbol.upper(), ""),
        "price":        1724.30,
        "pct_chg":      +1.22,
        "rsi":          58.4,
        "macd":         12.3,
        "signal":       8.7,
        "macd_bull":    True,
        "dma50":        1680.50,
        "dma200":       1590.20,
        "above_50dma":  True,
        "above_200dma": True,
        "vol_ratio":    1.34,
        "high_52w":     1887.00,
        "low_52w":      1358.35,
        "pe":           28.4,
        "mktcap":       "₹7.2L Cr",
        "revenue":      "₹1.47L Cr",
        "net_income":   "₹26,248 Cr",
        "news":         [
            {"title": "Company posts strong quarterly results, beats estimates", "date": "26 Feb"},
            {"title": "Institutional investors increase stake in latest quarter",  "date": "24 Feb"},
            {"title": "Management guidance positive for FY26",                    "date": "20 Feb"},
        ],
        "mock": True,
    }


def get_sector_momentum():
    """Returns hardcoded sector momentum list for the 8 key Indian sectors."""
    return [
        {"sector":"Defence & Aerospace", "pct": +18.4, "note":"Strong order pipeline",       "color":"green"},
        {"sector":"Pharma & Healthcare",  "pct": +12.1, "note":"US FDA approvals rising",     "color":"green"},
        {"sector":"Renewable Energy",     "pct": +15.6, "note":"Policy tailwinds",            "color":"green"},
        {"sector":"Capital Goods",        "pct":  +9.8, "note":"Capex supercycle",            "color":"green"},
        {"sector":"IT Services",          "pct":  +2.3, "note":"Deal wins recovering",        "color":"neutral"},
        {"sector":"FMCG",                 "pct":  +4.1, "note":"Rural demand improving",      "color":"neutral"},
        {"sector":"Banking & NBFC",       "pct":  -1.8, "note":"NIM compression fears",       "color":"red"},
        {"sector":"Real Estate",          "pct":  -3.2, "note":"Rate sensitivity",            "color":"red"},
    ]
