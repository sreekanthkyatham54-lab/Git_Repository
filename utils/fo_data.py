"""
F&O Data Fetchers — Free sources only
Pre-Market: Yahoo Finance, Investing.com proxy, NSE
EOD: NSE FII/DII data, daily OHLCV
"""

import requests
import pandas as pd
import numpy as np
from datetime import datetime, date, timedelta
import time
import logging

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.nseindia.com",
}


# ─── GLOBAL MARKETS ──────────────────────────────────────────────────────────

def get_global_markets() -> dict:
    """
    Fetch US indices and key macro data via Yahoo Finance.
    Returns dict with S&P, Dow, Nasdaq, VIX, US10Y, DXY.
    """
    tickers = {
        "sp500":   "^GSPC",
        "dow":     "^DJI",
        "nasdaq":  "^IXIC",
        "vix":     "^VIX",
        "us10y":   "^TNX",
        "dxy":     "DX-Y.NYB",
    }

    results = {}
    for key, symbol in tickers.items():
        try:
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=2d"
            r = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
            if r.status_code == 200:
                data = r.json()
                meta = data["chart"]["result"][0]["meta"]
                current = meta.get("regularMarketPrice", 0)
                prev    = meta.get("previousClose", current)
                change  = current - prev
                pct     = (change / prev * 100) if prev else 0
                results[key] = {
                    "price":   round(current, 2),
                    "change":  round(change, 2),
                    "pct":     round(pct, 2),
                    "prev":    round(prev, 2),
                }
            time.sleep(0.1)
        except Exception as e:
            logger.warning(f"Yahoo fetch failed for {symbol}: {e}")
            results[key] = {"price": 0, "change": 0, "pct": 0, "prev": 0}

    return results


def get_asian_markets() -> dict:
    """Fetch Asian index data."""
    tickers = {
        "nikkei":   "^N225",
        "hangseng": "^HSI",
        "kospi":    "^KS11",
        "shanghai": "000001.SS",
    }
    results = {}
    for key, symbol in tickers.items():
        try:
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=2d"
            r = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
            if r.status_code == 200:
                data = r.json()
                meta = data["chart"]["result"][0]["meta"]
                current = meta.get("regularMarketPrice", 0)
                prev    = meta.get("previousClose", current)
                pct     = ((current - prev) / prev * 100) if prev else 0
                results[key] = {
                    "price": round(current, 2),
                    "pct":   round(pct, 2),
                }
            time.sleep(0.1)
        except Exception as e:
            logger.warning(f"Asian market fetch failed {symbol}: {e}")
            results[key] = {"price": 0, "pct": 0}
    return results


def get_gift_nifty() -> dict:
    """
    Gift Nifty (NSE IFSC) — use Nifty futures as proxy via Yahoo Finance.
    Symbol: ^NSEI for spot, NI=F for futures proxy.
    """
    try:
        # Nifty 50 spot as proxy for Gift Nifty signal
        url = "https://query1.finance.yahoo.com/v8/finance/chart/^NSEI?interval=1d&range=2d"
        r = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        if r.status_code == 200:
            data  = r.json()
            meta  = data["chart"]["result"][0]["meta"]
            price = meta.get("regularMarketPrice", 0)
            prev  = meta.get("previousClose", price)
            chg   = round(price - prev, 2)
            pct   = round((chg / prev * 100) if prev else 0, 2)

            if chg > 50:
                signal = "GAP_UP"
            elif chg < -50:
                signal = "GAP_DOWN"
            else:
                signal = "FLAT"

            return {
                "price":   round(price, 2),
                "prev":    round(prev, 2),
                "change":  chg,
                "pct":     pct,
                "signal":  signal,
                "source":  "Yahoo Finance (Nifty spot proxy)",
                "timestamp": datetime.now().strftime("%H:%M:%S"),
            }
    except Exception as e:
        logger.error(f"Gift Nifty fetch error: {e}")

    return {
        "price": 0, "prev": 0, "change": 0, "pct": 0,
        "signal": "UNKNOWN", "source": "unavailable",
        "timestamp": datetime.now().strftime("%H:%M:%S"),
    }


# ─── NSE OPTIONS CHAIN ────────────────────────────────────────────────────────

def get_nse_options_chain(symbol: str = "NIFTY") -> dict:
    """
    Fetch live Nifty options chain from NSE free API.
    Includes OI, IV, LTP, PCR, Max Pain calculation.
    """
    session = requests.Session()
    session.headers.update(HEADERS)

    try:
        # Cookie refresh — NSE requires this
        session.get("https://www.nseindia.com", timeout=10)
        time.sleep(0.5)

        url = f"https://www.nseindia.com/api/option-chain-indices?symbol={symbol}"
        r   = session.get(url, timeout=15)

        if r.status_code != 200:
            return _mock_options_chain()

        raw        = r.json()
        records    = raw.get("records", {})
        data       = raw.get("filtered", {}).get("data", [])
        underlying = records.get("underlyingValue", 22000)
        expiries   = records.get("expiryDates", [])

        strikes = {}
        for item in data:
            strike = item.get("strikePrice")
            ce     = item.get("CE", {})
            pe     = item.get("PE", {})
            if not strike:
                continue
            strikes[strike] = {
                "CE": {
                    "oi":        ce.get("openInterest", 0),
                    "oi_change": ce.get("changeinOpenInterest", 0),
                    "volume":    ce.get("totalTradedVolume", 0),
                    "iv":        ce.get("impliedVolatility", 0),
                    "ltp":       ce.get("lastPrice", 0),
                    "bid":       ce.get("bidprice", 0),
                    "ask":       ce.get("askPrice", 0),
                },
                "PE": {
                    "oi":        pe.get("openInterest", 0),
                    "oi_change": pe.get("changeinOpenInterest", 0),
                    "volume":    pe.get("totalTradedVolume", 0),
                    "iv":        pe.get("impliedVolatility", 0),
                    "ltp":       pe.get("lastPrice", 0),
                    "bid":       pe.get("bidprice", 0),
                    "ask":       pe.get("askPrice", 0),
                },
            }

        total_call_oi = sum(v["CE"]["oi"] for v in strikes.values())
        total_put_oi  = sum(v["PE"]["oi"] for v in strikes.values())
        pcr           = round(total_put_oi / total_call_oi, 3) if total_call_oi > 0 else 0
        max_pain      = _calc_max_pain(strikes)

        # Top OI strikes
        call_wall = max(strikes.keys(), key=lambda k: strikes[k]["CE"]["oi"]) if strikes else 0
        put_floor = max(strikes.keys(), key=lambda k: strikes[k]["PE"]["oi"]) if strikes else 0

        return {
            "underlying":    underlying,
            "timestamp":     datetime.now().strftime("%H:%M:%S"),
            "expiry_dates":  expiries[:4] if expiries else [],
            "strikes":       strikes,
            "pcr":           pcr,
            "max_pain":      max_pain,
            "call_wall":     call_wall,
            "put_floor":     put_floor,
            "total_call_oi": total_call_oi,
            "total_put_oi":  total_put_oi,
            "is_mock":       False,
        }

    except Exception as e:
        logger.error(f"NSE options chain error: {e}")
        return _mock_options_chain()


def _calc_max_pain(strikes: dict) -> int:
    if not strikes:
        return 0
    min_pain = float("inf")
    max_pain_strike = list(strikes.keys())[0]
    for test in sorted(strikes.keys()):
        pain = 0
        for strike, d in strikes.items():
            if test > strike:
                pain += (test - strike) * d["CE"]["oi"]
            if test < strike:
                pain += (strike - test) * d["PE"]["oi"]
        if pain < min_pain:
            min_pain = pain
            max_pain_strike = test
    return max_pain_strike


# ─── FII / DII DATA ──────────────────────────────────────────────────────────

def get_fii_dii_data() -> dict:
    """
    Fetch FII/DII participant data from NSE.
    Returns net buy/sell for cash + futures.
    """
    try:
        session = requests.Session()
        session.headers.update(HEADERS)
        session.get("https://www.nseindia.com", timeout=10)
        time.sleep(0.3)

        url = "https://www.nseindia.com/api/fiidiiTradeReact"
        r   = session.get(url, timeout=10)

        if r.status_code == 200:
            data   = r.json()
            result = {
                "date":      datetime.now().strftime("%d %b %Y"),
                "fii_cash":  0,
                "dii_cash":  0,
                "fii_fut":   0,
                "raw":       data,
            }
            for item in data:
                cat = item.get("category", "")
                if "FII" in cat or "FPI" in cat:
                    result["fii_cash"] = item.get("netVal", 0)
                elif "DII" in cat:
                    result["dii_cash"] = item.get("netVal", 0)
            return result

    except Exception as e:
        logger.error(f"FII data fetch error: {e}")

    # Mock fallback
    return {
        "date":     datetime.now().strftime("%d %b %Y"),
        "fii_cash": 1420.0,
        "dii_cash": 680.0,
        "fii_fut":  840.0,
        "is_mock":  True,
    }


def get_fii_trend(days: int = 5) -> list:
    """
    Returns list of last N days FII net positions.
    Uses mock trend data (NSE historical FII not free without login).
    In production: replace with database of daily FII figures.
    """
    # Placeholder — in production pull from your DB or a paid feed
    trend = []
    base  = 800
    for i in range(days, 0, -1):
        d   = date.today() - timedelta(days=i)
        val = round(base + np.random.uniform(-400, 600), 1)
        trend.append({
            "date":    d.strftime("%d %b"),
            "net":     val,
            "label":   "Net Long" if val > 0 else "Net Short",
        })
        base = val
    return trend


# ─── INDIA VIX ───────────────────────────────────────────────────────────────

def get_india_vix() -> dict:
    """Fetch India VIX from NSE."""
    try:
        session = requests.Session()
        session.headers.update(HEADERS)
        session.get("https://www.nseindia.com", timeout=10)
        time.sleep(0.2)

        url = "https://www.nseindia.com/api/allIndices"
        r   = session.get(url, timeout=10)
        if r.status_code == 200:
            data = r.json()
            for idx in data.get("data", []):
                if idx.get("index") == "INDIA VIX":
                    val  = idx.get("last", 0)
                    chg  = idx.get("percentChange", 0)
                    lvl  = "Low" if val < 14 else "Elevated" if val < 18 else "High"
                    ok   = val < 18
                    return {
                        "value":   round(val, 2),
                        "change":  round(chg, 2),
                        "level":   lvl,
                        "tradeable": ok,
                    }
    except Exception as e:
        logger.error(f"India VIX error: {e}")

    return {"value": 13.8, "change": -0.4, "level": "Low", "tradeable": True, "is_mock": True}


# ─── BLOCK DEALS ─────────────────────────────────────────────────────────────

def get_block_deals() -> list:
    """
    Fetch today's block deals from NSE.
    Filters for Nifty ETFs and top heavyweights.
    """
    NIFTY_ETFS   = ["NIFTYBEES", "SETFNIF50", "ICICINIFTY", "UTINIFTY"]
    HEAVYWEIGHTS = ["RELIANCE", "HDFCBANK", "ICICIBANK", "INFY", "TCS",
                    "KOTAKBANK", "LT", "AXISBANK", "BAJFINANCE", "HINDUNILVR"]
    WATCHLIST    = set(NIFTY_ETFS + HEAVYWEIGHTS)

    try:
        session = requests.Session()
        session.headers.update(HEADERS)
        session.get("https://www.nseindia.com", timeout=10)
        time.sleep(0.3)

        today = date.today().strftime("%d-%m-%Y")
        url   = f"https://www.nseindia.com/api/block-deal?date={today}"
        r     = session.get(url, timeout=10)

        if r.status_code == 200:
            data  = r.json()
            deals = []
            for d in data.get("data", []):
                sym = d.get("symbol", "").upper()
                if sym in WATCHLIST:
                    qty   = d.get("quantity", 0)
                    price = d.get("price", 0)
                    val   = round((qty * price) / 1e7, 1)  # in crores
                    side  = d.get("buySell", "BUY")
                    deals.append({
                        "symbol":   sym,
                        "side":     side,
                        "value_cr": val,
                        "price":    price,
                        "time":     d.get("dealTime", "—"),
                        "type":     "ETF" if sym in NIFTY_ETFS else "HeavyWeight",
                    })
            return deals

    except Exception as e:
        logger.error(f"Block deal fetch error: {e}")

    # Mock for development
    return [
        {"symbol": "NIFTYBEES", "side": "BUY",  "value_cr": 340, "price": 242.5, "time": "08:47", "type": "ETF"},
        {"symbol": "HDFCBANK",  "side": "BUY",  "value_cr": 180, "price": 1842,  "time": "08:52", "type": "HeavyWeight"},
        {"symbol": "INFY",      "side": "SELL", "value_cr": 90,  "price": 1654,  "time": "08:55", "type": "HeavyWeight"},
    ]


# ─── DAILY NIFTY OHLCV (for EMA) ─────────────────────────────────────────────

def get_nifty_daily_ohlcv(days: int = 220) -> pd.DataFrame:
    """
    Fetch Nifty 50 daily OHLCV for EMA calculation.
    Uses Yahoo Finance — free and reliable.
    """
    try:
        end   = datetime.now()
        start = end - timedelta(days=days + 30)
        url   = (
            f"https://query1.finance.yahoo.com/v8/finance/chart/^NSEI"
            f"?interval=1d"
            f"&period1={int(start.timestamp())}"
            f"&period2={int(end.timestamp())}"
        )
        r = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
        if r.status_code == 200:
            data      = r.json()
            result    = data["chart"]["result"][0]
            timestamps = result["timestamp"]
            ohlcv     = result["indicators"]["quote"][0]

            df = pd.DataFrame({
                "date":   [datetime.fromtimestamp(t).date() for t in timestamps],
                "open":   ohlcv["open"],
                "high":   ohlcv["high"],
                "low":    ohlcv["low"],
                "close":  ohlcv["close"],
                "volume": ohlcv["volume"],
            }).dropna().tail(days)

            # Calculate EMAs
            df["ema_20"]  = df["close"].ewm(span=20,  adjust=False).mean()
            df["ema_50"]  = df["close"].ewm(span=50,  adjust=False).mean()
            df["ema_200"] = df["close"].ewm(span=200, adjust=False).mean()

            return df.reset_index(drop=True)

    except Exception as e:
        logger.error(f"OHLCV fetch error: {e}")

    return pd.DataFrame()


def compute_ema_status(df: pd.DataFrame) -> dict:
    """Given OHLCV dataframe with EMAs, return current EMA status."""
    if df.empty:
        return {}

    last = df.iloc[-1]
    prev = df.iloc[-2] if len(df) > 1 else last

    close   = last["close"]
    ema20   = last["ema_20"]
    ema50   = last["ema_50"]
    ema200  = last["ema_200"]

    above_20  = close > ema20
    above_50  = close > ema50
    above_200 = close > ema200
    stack_bull = above_20 and above_50 and above_200 and ema20 > ema50 > ema200
    stack_bear = not above_20 and not above_50 and not above_200 and ema20 < ema50 < ema200

    # Previous day values for trend
    prev_close = prev["close"]

    return {
        "close":      round(close, 2),
        "ema_20":     round(ema20, 2),
        "ema_50":     round(ema50, 2),
        "ema_200":    round(ema200, 2),
        "above_20":   above_20,
        "above_50":   above_50,
        "above_200":  above_200,
        "stack_bull": stack_bull,
        "stack_bear": stack_bear,
        "stack_label": "BULLISH ✓" if stack_bull else "BEARISH ✗" if stack_bear else "MIXED",
        "prev_close": round(prev_close, 2),
        "day_change": round(close - prev_close, 2),
        "day_pct":    round((close - prev_close) / prev_close * 100, 2) if prev_close else 0,
    }


def compute_sr_levels(df: pd.DataFrame) -> dict:
    """
    Compute key S/R levels from recent price data.
    Uses swing highs/lows from last 20 sessions.
    """
    if df.empty or len(df) < 5:
        return {}

    recent = df.tail(20)
    last   = df.iloc[-1]
    prev   = df.iloc[-2]

    # Previous day levels — most reliable intraday S/R
    prev_high  = round(prev["high"], 2)
    prev_low   = round(prev["low"], 2)
    prev_close = round(prev["close"], 2)

    # 20-session high and low
    swing_high = round(recent["high"].max(), 2)
    swing_low  = round(recent["low"].min(), 2)

    # Round number proximity
    close = last["close"]
    round_levels = [round(close / 100) * 100 + i * 50 for i in range(-4, 5)]

    return {
        "prev_high":  prev_high,
        "prev_low":   prev_low,
        "prev_close": prev_close,
        "swing_high": swing_high,
        "swing_low":  swing_low,
        "round_levels": round_levels,
        "key_resistance": prev_high,
        "key_support":    prev_low,
    }


# ─── MORNING BIAS SCORE ───────────────────────────────────────────────────────

def compute_morning_bias(
    global_mkts: dict,
    asian_mkts:  dict,
    gift_nifty:  dict,
    fii_trend:   list,
    vix:         dict,
    ema_status:  dict,
    block_deals: list,
) -> dict:
    """
    Combine all pre-market signals into a single morning bias score.
    Returns score 0-100, direction, confidence, and per-signal breakdown.
    """
    signals   = []
    score     = 0
    bull_pts  = 0
    bear_pts  = 0

    # 1. Global markets
    sp500_pct = global_mkts.get("sp500", {}).get("pct", 0)
    if sp500_pct > 0.5:
        score    += 12; bull_pts += 12
        signals.append({"label": "S&P 500", "value": f"+{sp500_pct:.1f}%", "bias": "BULL", "pts": 12})
    elif sp500_pct < -0.5:
        score    += 12; bear_pts += 12
        signals.append({"label": "S&P 500", "value": f"{sp500_pct:.1f}%", "bias": "BEAR", "pts": 12})
    else:
        signals.append({"label": "S&P 500", "value": f"{sp500_pct:.1f}%", "bias": "NEUTRAL", "pts": 0})

    # 2. US VIX
    us_vix = global_mkts.get("vix", {}).get("price", 15)
    if us_vix < 16:
        score    += 5; bull_pts += 5
        signals.append({"label": "US VIX", "value": f"{us_vix:.1f} Calm", "bias": "BULL", "pts": 5})
    elif us_vix > 20:
        score    += 8; bear_pts += 8
        signals.append({"label": "US VIX", "value": f"{us_vix:.1f} Elevated", "bias": "BEAR", "pts": 8})
    else:
        signals.append({"label": "US VIX", "value": f"{us_vix:.1f}", "bias": "NEUTRAL", "pts": 0})

    # 3. Dollar Index
    dxy_pct = global_mkts.get("dxy", {}).get("pct", 0)
    if dxy_pct < -0.2:
        score    += 5; bull_pts += 5
        signals.append({"label": "Dollar Index", "value": f"Weak {dxy_pct:.2f}%", "bias": "BULL", "pts": 5})
    elif dxy_pct > 0.2:
        score    += 5; bear_pts += 5
        signals.append({"label": "Dollar Index", "value": f"Strong +{dxy_pct:.2f}%", "bias": "BEAR", "pts": 5})
    else:
        signals.append({"label": "Dollar Index", "value": "Stable", "bias": "NEUTRAL", "pts": 0})

    # 4. Asian markets
    asian_bull = sum(1 for v in asian_mkts.values() if v.get("pct", 0) > 0.3)
    asian_bear = sum(1 for v in asian_mkts.values() if v.get("pct", 0) < -0.3)
    if asian_bull >= 3:
        score    += 8; bull_pts += 8
        signals.append({"label": "Asian Markets", "value": f"{asian_bull}/4 up", "bias": "BULL", "pts": 8})
    elif asian_bear >= 3:
        score    += 8; bear_pts += 8
        signals.append({"label": "Asian Markets", "value": f"{asian_bear}/4 down", "bias": "BEAR", "pts": 8})
    else:
        signals.append({"label": "Asian Markets", "value": "Mixed", "bias": "NEUTRAL", "pts": 0})

    # 5. Gift Nifty
    gift_chg = gift_nifty.get("change", 0)
    if gift_chg > 50:
        score    += 15; bull_pts += 15
        signals.append({"label": "Gift Nifty", "value": f"+{gift_chg:.0f} pts GAP UP", "bias": "BULL", "pts": 15})
    elif gift_chg < -50:
        score    += 15; bear_pts += 15
        signals.append({"label": "Gift Nifty", "value": f"{gift_chg:.0f} pts GAP DOWN", "bias": "BEAR", "pts": 15})
    else:
        signals.append({"label": "Gift Nifty", "value": f"{gift_chg:+.0f} pts Flat", "bias": "NEUTRAL", "pts": 0})

    # 6. FII 3-day trend
    if len(fii_trend) >= 3:
        last3    = [t["net"] for t in fii_trend[-3:]]
        all_long = all(v > 0 for v in last3)
        all_short = all(v < 0 for v in last3)
        net_sum   = sum(last3)
        if all_long:
            score    += 20; bull_pts += 20
            signals.append({"label": "FII 3-Day Trend", "value": f"Accumulating ₹{net_sum/100:.0f}cr", "bias": "BULL", "pts": 20})
        elif all_short:
            score    += 20; bear_pts += 20
            signals.append({"label": "FII 3-Day Trend", "value": f"Distributing", "bias": "BEAR", "pts": 20})
        else:
            signals.append({"label": "FII 3-Day Trend", "value": "Mixed", "bias": "NEUTRAL", "pts": 0})

    # 7. India VIX
    vix_val = vix.get("value", 15)
    if vix_val > 18:
        # High VIX = anti-trigger (no trade)
        signals.append({"label": "India VIX", "value": f"{vix_val:.1f} HIGH — No trade", "bias": "BLOCK", "pts": 0})
    else:
        score += 5; bull_pts += 5
        signals.append({"label": "India VIX", "value": f"{vix_val:.1f} Acceptable", "bias": "OK", "pts": 5})

    # 8. EMA stack
    if ema_status.get("stack_bull"):
        score    += 15; bull_pts += 15
        signals.append({"label": "Daily EMA Stack", "value": "Bullish (20>50>200)", "bias": "BULL", "pts": 15})
    elif ema_status.get("stack_bear"):
        score    += 15; bear_pts += 15
        signals.append({"label": "Daily EMA Stack", "value": "Bearish (20<50<200)", "bias": "BEAR", "pts": 15})
    else:
        signals.append({"label": "Daily EMA Stack", "value": "Mixed", "bias": "NEUTRAL", "pts": 0})

    # 9. Block deals
    etf_buy  = sum(d["value_cr"] for d in block_deals if d["side"] == "BUY"  and d["type"] == "ETF")
    etf_sell = sum(d["value_cr"] for d in block_deals if d["side"] == "SELL" and d["type"] == "ETF")
    net_etf  = etf_buy - etf_sell
    if net_etf > 100:
        score    += 10; bull_pts += 10
        signals.append({"label": "Block Deals (ETF)", "value": f"Net Buy ₹{net_etf:.0f}cr", "bias": "BULL", "pts": 10})
    elif net_etf < -100:
        score    += 10; bear_pts += 10
        signals.append({"label": "Block Deals (ETF)", "value": f"Net Sell ₹{abs(net_etf):.0f}cr", "bias": "BEAR", "pts": 10})
    else:
        signals.append({"label": "Block Deals (ETF)", "value": "No significant blocks", "bias": "NEUTRAL", "pts": 0})

    # Final direction
    blocked   = any(s["bias"] == "BLOCK" for s in signals)
    direction = "BULLISH" if bull_pts > bear_pts and not blocked else "BEARISH" if bear_pts > bull_pts else "NEUTRAL"
    confidence = "High" if abs(bull_pts - bear_pts) > 20 else "Medium" if abs(bull_pts - bear_pts) > 10 else "Low"
    trade_today = not blocked and direction != "NEUTRAL" and confidence != "Low"

    return {
        "score":       min(score, 100),
        "direction":   direction,
        "confidence":  confidence,
        "trade_today": trade_today,
        "bull_pts":    bull_pts,
        "bear_pts":    bear_pts,
        "signals":     signals,
        "blocked":     blocked,
        "timestamp":   datetime.now().strftime("%I:%M %p"),
    }


# ─── EOD DATA ─────────────────────────────────────────────────────────────────

def get_eod_summary(df: pd.DataFrame, chain: dict, fii: dict) -> dict:
    """Build EOD summary from available data."""
    if df.empty:
        return {}

    last      = df.iloc[-1]
    prev      = df.iloc[-2] if len(df) > 1 else last

    today_high   = round(last["high"], 2)
    today_low    = round(last["low"], 2)
    today_close  = round(last["close"], 2)
    today_open   = round(last["open"], 2)
    prev_close   = round(prev["close"], 2)
    day_change   = round(today_close - prev_close, 2)
    day_pct      = round((day_change / prev_close * 100) if prev_close else 0, 2)

    # Updated levels for tomorrow
    levels = {
        "new_resistance":  today_high,
        "new_support":     today_low,
        "prev_close":      today_close,
        "max_pain":        chain.get("max_pain", 0),
        "call_wall":       chain.get("call_wall", 0),
        "put_floor":       chain.get("put_floor", 0),
        "ema_20":          round(last.get("ema_20", 0), 2),
        "ema_50":          round(last.get("ema_50", 0), 2),
        "ema_200":         round(last.get("ema_200", 0), 2),
    }

    return {
        "date":          last["date"].strftime("%d %b %Y") if hasattr(last["date"], "strftime") else str(last["date"]),
        "today_open":    today_open,
        "today_high":    today_high,
        "today_low":     today_low,
        "today_close":   today_close,
        "day_change":    day_change,
        "day_pct":       day_pct,
        "levels":        levels,
        "fii":           fii,
        "pcr":           chain.get("pcr", 0),
        "underlying":    chain.get("underlying", 0),
    }


# ─── MOCK FALLBACK ────────────────────────────────────────────────────────────

def _mock_options_chain() -> dict:
    """Return realistic mock options chain when NSE is unreachable."""
    underlying = 22387
    strikes    = {}
    for i in range(-5, 6):
        strike   = underlying + i * 50
        dist     = abs(i)
        call_oi  = max(5000, 380000 - dist * 60000)
        put_oi   = max(5000, 380000 - dist * 55000)
        strikes[strike] = {
            "CE": {"oi": call_oi, "oi_change": int(call_oi * 0.05), "volume": call_oi * 2,
                   "iv": 12 + dist, "ltp": max(5, 200 - i * 40), "bid": 0, "ask": 0},
            "PE": {"oi": put_oi,  "oi_change": int(put_oi * 0.03),  "volume": put_oi * 1.5,
                   "iv": 13 + dist, "ltp": max(5, 200 + i * 40), "bid": 0, "ask": 0},
        }
    total_ce = sum(v["CE"]["oi"] for v in strikes.values())
    total_pe = sum(v["PE"]["oi"] for v in strikes.values())
    return {
        "underlying": underlying, "timestamp": datetime.now().strftime("%H:%M:%S"),
        "expiry_dates": ["13-Mar-2025", "20-Mar-2025"],
        "strikes": strikes, "pcr": round(total_pe / total_ce, 3),
        "max_pain": underlying - 50, "call_wall": underlying + 100,
        "put_floor": underlying - 100,
        "total_call_oi": total_ce, "total_put_oi": total_pe, "is_mock": True,
    }
