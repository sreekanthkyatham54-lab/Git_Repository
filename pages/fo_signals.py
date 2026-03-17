"""
F&O Signal Intelligence — Streamlit Page
Integrates into TradeSage as pages/fo_signals.py

Navigation: added automatically by Streamlit multipage routing
via app.py sidebar or top nav depending on your app.py setup.
"""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from datetime import datetime, time as dtime
import sys
import os

# Allow imports from parent directory
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.fo_data import (
    get_global_markets,
    get_asian_markets,
    get_gift_nifty,
    get_fii_dii_data,
    get_fii_trend,
    get_india_vix,
    get_block_deals,
    get_nifty_daily_ohlcv,
    compute_ema_status,
    compute_sr_levels,
    compute_morning_bias,
    get_nse_options_chain,
    get_eod_summary,
)

# ─── PAGE CONFIG ─────────────────────────────────────────────────────────────
# Only set if running this file directly (not as a page in multipage app)
if __name__ == "__main__":
    st.set_page_config(
        page_title="F&O Signals — TradeSage",
        page_icon="⚡",
        layout="wide",
        initial_sidebar_state="collapsed",
    )

# ─── STYLING — matches TradeSage green theme ──────────────────────────────────
st.markdown("""
<style>
/* Import fonts matching TradeSage */
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

/* TradeSage color variables */
:root {
    --ts-green:       #1a7f5a;
    --ts-green-light: #f0faf5;
    --ts-green-mid:   #b8dece;
    --ts-amber:       #d97706;
    --ts-amber-light: #fffbeb;
    --ts-red:         #e53e3e;
    --ts-red-light:   #fef2f2;
    --ts-blue:        #2563eb;
    --ts-blue-light:  #eff6ff;
    --ts-gray:        #6b7280;
    --ts-border:      #e8e8e8;
    --ts-bg:          #f0f2f6;
    --ts-text:        #1a1a2e;
}

/* Metric card matching TradeSage */
.fo-metric-card {
    background: white;
    border: 1px solid var(--ts-border);
    border-radius: 8px;
    padding: 16px 20px;
    margin-bottom: 12px;
}
.fo-metric-label {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 13px;
    color: var(--ts-gray);
    margin-bottom: 4px;
}
.fo-metric-val {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 28px;
    font-weight: 600;
    line-height: 1.1;
}
.fo-metric-sub {
    font-size: 12px;
    color: var(--ts-gray);
    margin-top: 2px;
}

/* Badge — matches TradeSage OPEN / NEUTRAL AI / AVOID AI */
.badge {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 2px 10px;
    border-radius: 12px;
    font-size: 11px;
    font-weight: 600;
    font-family: 'Space Grotesk', sans-serif;
}
.badge-green  { background: #e8f5ee; color: #1a7f5a; border: 1px solid #b8dece; }
.badge-red    { background: #fef2f2; color: #e53e3e; border: 1px solid #fecaca; }
.badge-yellow { background: #fffbeb; color: #d97706; border: 1px solid #fed7aa; }
.badge-blue   { background: #eff6ff; color: #2563eb; border: 1px solid #bfdbfe; }
.badge-gray   { background: #f3f4f6; color: #6b7280; border: 1px solid #e5e7eb; }

/* Alert card */
.alert-card {
    background: white;
    border: 1px solid var(--ts-border);
    border-radius: 8px;
    padding: 16px 20px;
    margin-bottom: 12px;
}
.alert-momentum { border-left: 4px solid #d97706; }
.alert-squeeze  { border-left: 4px solid #e53e3e; }
.alert-watch    { border-left: 4px solid #2563eb; }

/* Data row */
.data-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 7px 0;
    border-bottom: 1px solid #f3f4f6;
    font-size: 13px;
    font-family: 'Space Grotesk', sans-serif;
}
.data-row:last-child { border-bottom: none; }
.data-label { color: #6b7280; }
.up   { color: #1a7f5a; font-weight: 500; }
.down { color: #e53e3e; font-weight: 500; }
.warn { color: #d97706; font-weight: 500; }
.neutral { color: #6b7280; }

/* Section header */
.section-hdr {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 11px;
    font-weight: 600;
    color: #9ca3af;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    margin: 12px 0 6px;
}

/* Info box */
.info-box {
    padding: 10px 14px;
    border-radius: 6px;
    font-size: 12px;
    font-family: 'Space Grotesk', sans-serif;
    margin-top: 10px;
}
.info-green  { background: #f0faf5; color: #1a7f5a; border: 1px solid #b8dece; }
.info-yellow { background: #fffbeb; color: #d97706; border: 1px solid #fed7aa; }
.info-red    { background: #fef2f2; color: #e53e3e; border: 1px solid #fecaca; }
.info-blue   { background: #eff6ff; color: #2563eb; border: 1px solid #bfdbfe; }

/* Mock data warning */
.mock-badge {
    background: #fffbeb;
    border: 1px solid #fed7aa;
    border-radius: 6px;
    padding: 6px 12px;
    font-size: 11px;
    color: #d97706;
    margin-bottom: 10px;
    display: inline-block;
}
</style>
""", unsafe_allow_html=True)


# ─── HELPERS ──────────────────────────────────────────────────────────────────

def badge(text: str, color: str = "green") -> str:
    return f'<span class="badge badge-{color}">{text}</span>'

def pct_color(v: float) -> str:
    return "up" if v > 0 else "down" if v < 0 else "neutral"

def data_row(label: str, value: str, color: str = "") -> str:
    css = f' class="{color}"' if color else ""
    return f'<div class="data-row"><span class="data-label">{label}</span><span{css}>{value}</span></div>'

def section_hdr(text: str) -> str:
    return f'<div class="section-hdr">{text}</div>'

def info_box(text: str, color: str = "green") -> str:
    return f'<div class="info-box info-{color}">{text}</div>'

def metric_card(label: str, value: str, sub: str = "", color: str = "") -> str:
    val_style = f' style="color:var(--ts-{color})"' if color else ""
    sub_style = f' class="{color}"' if color in ("up", "down", "warn") else ' class="neutral"'
    return f"""
    <div class="fo-metric-card">
        <div class="fo-metric-label">{label}</div>
        <div class="fo-metric-val"{val_style}>{value}</div>
        <div class="fo-metric-sub"{sub_style}>{sub}</div>
    </div>"""

def is_market_hours() -> bool:
    now = datetime.now().time()
    return dtime(9, 15) <= now <= dtime(15, 30)

def is_eod() -> bool:
    now = datetime.now().time()
    return now >= dtime(15, 30)

def is_premarket() -> bool:
    now = datetime.now().time()
    return now < dtime(9, 15)

def current_session_label() -> str:
    if is_premarket():   return "Pre-Market"
    if is_market_hours(): return "Market Open"
    if is_eod():          return "Post Market"
    return "Closed"


# ─── CACHED DATA FETCHERS ─────────────────────────────────────────────────────
# TTL: pre-market data refreshes every 5 min, EOD every 10 min

@st.cache_data(ttl=300, show_spinner=False)
def cached_global_markets():
    return get_global_markets()

@st.cache_data(ttl=300, show_spinner=False)
def cached_asian_markets():
    return get_asian_markets()

@st.cache_data(ttl=300, show_spinner=False)
def cached_gift_nifty():
    return get_gift_nifty()

@st.cache_data(ttl=600, show_spinner=False)
def cached_fii_data():
    return get_fii_dii_data()

@st.cache_data(ttl=3600, show_spinner=False)
def cached_fii_trend():
    return get_fii_trend(days=5)

@st.cache_data(ttl=300, show_spinner=False)
def cached_vix():
    return get_india_vix()

@st.cache_data(ttl=300, show_spinner=False)
def cached_block_deals():
    return get_block_deals()

@st.cache_data(ttl=600, show_spinner=False)
def cached_ohlcv():
    return get_nifty_daily_ohlcv(days=220)

@st.cache_data(ttl=180, show_spinner=False)
def cached_options_chain():
    return get_nse_options_chain()


# ─── PAGE HEADER ──────────────────────────────────────────────────────────────

def render_page_header(nifty_close: float, nifty_pct: float, vix_val: float):
    session = current_session_label()
    pct_cls = "up" if nifty_pct >= 0 else "down"
    pct_str = f"+{nifty_pct:.2f}%" if nifty_pct >= 0 else f"{nifty_pct:.2f}%"

    col1, col2, col3, col4, col5 = st.columns([3, 1, 1, 1, 1])
    with col1:
        st.markdown(f"""
        <div style="display:flex;align-items:center;gap:12px;padding:4px 0;">
            <span style="font-size:20px;font-weight:700;font-family:'Space Grotesk',sans-serif;">
                ⚡ F&O Signal Intelligence
            </span>
            <span class="badge badge-{'green' if session == 'Market Open' else 'gray'}">{session}</span>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.metric("NIFTY 50", f"{nifty_close:,.0f}", f"{pct_str}")
    with col3:
        vix_color = "normal" if vix_val < 18 else "inverse"
        st.metric("India VIX", f"{vix_val:.1f}", delta_color=vix_color)
    with col4:
        st.markdown(
            f'<div style="font-size:11px;color:#9ca3af;padding-top:8px;">'
            f'{datetime.now().strftime("%d %b %Y %H:%M")}</div>',
            unsafe_allow_html=True
        )
    with col5:
        if st.button("🔄 Refresh", key="fo_refresh"):
            st.cache_data.clear()
            st.rerun()


# ─── PRE-MARKET VIEW ─────────────────────────────────────────────────────────

def render_premarket():
    st.markdown("---")

    with st.spinner("Fetching global markets..."):
        global_mkts = cached_global_markets()
        asian_mkts  = cached_asian_markets()
        gift        = cached_gift_nifty()
        fii         = cached_fii_data()
        fii_trend   = cached_fii_trend()
        vix         = cached_vix()
        blocks      = cached_block_deals()
        df          = cached_ohlcv()
        ema         = compute_ema_status(df) if not df.empty else {}
        sr          = compute_sr_levels(df)  if not df.empty else {}
        bias        = compute_morning_bias(global_mkts, asian_mkts, gift, fii_trend, vix, ema, blocks)

    # Mock data warning
    if gift.get("source", "").startswith("Yahoo"):
        st.markdown(
            '<div class="mock-badge">⚠️ Using Yahoo Finance proxy for Nifty/Gift Nifty — '
            'connect TrueData feed for live Gift Nifty</div>',
            unsafe_allow_html=True
        )

    # ── Top 4 metric cards ────────────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)

    direction_color = "green" if bias["direction"] == "BULLISH" else "red" if bias["direction"] == "BEARISH" else "amber"
    with c1:
        st.markdown(metric_card(
            "Morning Bias",
            bias["direction"],
            f"+ {bias['confidence']} Confidence",
            direction_color
        ), unsafe_allow_html=True)

    with c2:
        gift_chg = gift.get("change", 0)
        gift_lbl = "GAP UP 🟢" if gift_chg > 50 else "GAP DOWN 🔴" if gift_chg < -50 else "FLAT ⚪"
        st.markdown(metric_card(
            "Gift Nifty Signal",
            f"{gift_chg:+.0f} pts",
            gift_lbl,
        ), unsafe_allow_html=True)

    with c3:
        fii_net3 = sum(t["net"] for t in fii_trend[-3:]) if len(fii_trend) >= 3 else 0
        fii_lbl  = "Accumulating ▲" if fii_net3 > 0 else "Distributing ▼"
        st.markdown(metric_card(
            "FII 3-Day Trend",
            "Net Long" if fii_net3 > 0 else "Net Short",
            fii_lbl,
        ), unsafe_allow_html=True)

    with c4:
        trade_lbl = "✓ Trade Today" if bias["trade_today"] else "✗ Sit Out"
        st.markdown(metric_card(
            "Bias Score",
            f"{bias['score']}/100",
            trade_lbl,
        ), unsafe_allow_html=True)

    st.markdown("---")

    # ── Main columns ──────────────────────────────────────────────────────────
    col_l, col_r = st.columns([1, 1])

    with col_l:
        # Global markets card
        sp  = global_mkts.get("sp500", {})
        dow = global_mkts.get("dow",   {})
        nq  = global_mkts.get("nasdaq",{})
        uv  = global_mkts.get("vix",   {})
        t10 = global_mkts.get("us10y", {})
        dxy = global_mkts.get("dxy",   {})

        st.markdown("**🌎 Global Markets — Last Night**")
        rows_html = ""
        rows_html += data_row("S&P 500",     f"{sp.get('pct',0):+.2f}%",  pct_color(sp.get('pct',0)))
        rows_html += data_row("Dow Jones",   f"{dow.get('pct',0):+.2f}%", pct_color(dow.get('pct',0)))
        rows_html += data_row("Nasdaq",      f"{nq.get('pct',0):+.2f}%",  pct_color(nq.get('pct',0)))
        rows_html += data_row("US VIX",      f"{uv.get('price',0):.1f} — {'Calm' if uv.get('price',15)<16 else 'Elevated'}", "neutral")
        rows_html += data_row("US 10Y Yield",f"{t10.get('price',0):.2f}%", "neutral")
        dxy_pct = dxy.get("pct", 0)
        rows_html += data_row("Dollar Index",f"{dxy.get('price',0):.1f} ({'Weak ↓' if dxy_pct < 0 else 'Strong ↑'})", pct_color(-dxy_pct))
        st.markdown(f'<div style="background:white;border:1px solid #e8e8e8;border-radius:8px;padding:14px 18px;">{rows_html}</div>', unsafe_allow_html=True)
        st.markdown("")

        # Asian markets
        st.markdown("**🌏 Asian Markets**")
        nk  = asian_mkts.get("nikkei",   {})
        hs  = asian_mkts.get("hangseng", {})
        ks  = asian_mkts.get("kospi",    {})
        sh  = asian_mkts.get("shanghai", {})

        rows_html2 = ""
        rows_html2 += data_row("Nikkei 225",  f"{nk.get('pct',0):+.2f}%",  pct_color(nk.get('pct',0)))
        rows_html2 += data_row("Hang Seng",   f"{hs.get('pct',0):+.2f}%",  pct_color(hs.get('pct',0)))
        rows_html2 += data_row("Kospi",       f"{ks.get('pct',0):+.2f}%",  pct_color(ks.get('pct',0)))
        rows_html2 += data_row("Shanghai",    f"{sh.get('pct',0):+.2f}%",  pct_color(sh.get('pct',0)))
        st.markdown(f'<div style="background:white;border:1px solid #e8e8e8;border-radius:8px;padding:14px 18px;">{rows_html2}</div>', unsafe_allow_html=True)
        st.markdown("")

        # FII trend chart
        st.markdown("**📊 FII 5-Day Trend**")
        if fii_trend:
            df_fii = pd.DataFrame(fii_trend)
            colors = ["#1a7f5a" if v > 0 else "#e53e3e" for v in df_fii["net"]]
            fig = go.Figure(go.Bar(
                x=df_fii["date"],
                y=df_fii["net"],
                marker_color=colors,
                text=[f"₹{v:.0f}cr" for v in df_fii["net"]],
                textposition="outside",
            ))
            fig.update_layout(
                height=180,
                margin=dict(l=0, r=0, t=10, b=0),
                paper_bgcolor="white",
                plot_bgcolor="white",
                showlegend=False,
                yaxis=dict(showgrid=True, gridcolor="#f3f4f6", zeroline=True, zerolinecolor="#e8e8e8"),
                xaxis=dict(showgrid=False),
                font=dict(family="Space Grotesk", size=11),
            )
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    with col_r:
        # Gift Nifty
        st.markdown("**⚡ Gift Nifty Signal**")
        gift_color = "green" if gift.get("change", 0) > 50 else "red" if gift.get("change", 0) < -50 else "gray"
        gift_html = f"""
        <div style="background:white;border:1px solid #e8e8e8;border-radius:8px;padding:14px 18px;">
            <div style="display:flex;align-items:center;gap:14px;margin-bottom:10px;">
                <div style="font-size:32px;font-weight:700;color:{'#1a7f5a' if gift_color=='green' else '#e53e3e' if gift_color=='red' else '#6b7280'};">
                    {gift.get('change',0):+.0f} pts
                </div>
                <div>
                    <div style="font-weight:600;font-size:13px;color:{'#1a7f5a' if gift_color=='green' else '#e53e3e' if gift_color=='red' else '#6b7280'};">
                        {gift.get('signal','—')}
                    </div>
                    <div style="font-size:11px;color:#9ca3af;">vs prev close {gift.get('prev',0):,.0f}</div>
                </div>
            </div>
            {data_row("Gift Nifty Price", f"{gift.get('price',0):,.2f}")}
            {data_row("Expected Gap Open", f"~{gift.get('change',0):+.0f} pts")}
            {data_row("Source", gift.get("source","—"))}
        </div>"""
        st.markdown(gift_html, unsafe_allow_html=True)
        st.markdown("")

        # Block deals
        st.markdown("**📦 Pre-Market Block Deals**")
        if blocks:
            deals_html = '<div style="background:white;border:1px solid #e8e8e8;border-radius:8px;padding:14px 18px;">'
            for d in blocks:
                side_color = "up" if d["side"] == "BUY" else "down"
                deals_html += f"""
                <div class="data-row">
                    <div>
                        <span style="font-weight:500;">{d['symbol']}</span>
                        <span style="font-size:10px;color:#9ca3af;margin-left:6px;">{d['type']} · {d.get('time','—')}</span>
                    </div>
                    <span class="{side_color}">₹{d['value_cr']:.0f}cr {d['side']}</span>
                </div>"""
            net_etf  = sum(d["value_cr"] for d in blocks if d["type"] == "ETF" and d["side"] == "BUY") - \
                       sum(d["value_cr"] for d in blocks if d["type"] == "ETF" and d["side"] == "SELL")
            net_color = "green" if net_etf > 0 else "red"
            deals_html += f'{info_box(f"Net institutional (ETF): {'Bullish' if net_etf > 0 else 'Bearish'} ₹{abs(net_etf):.0f}cr", net_color)}'
            deals_html += "</div>"
            st.markdown(deals_html, unsafe_allow_html=True)
        else:
            st.info("Block deal window 8:45–9:00 AM. No qualifying deals yet.")
        st.markdown("")

        # Key levels
        st.markdown("**📍 Today's Key Levels**")
        if sr and ema:
            chain    = cached_options_chain()
            max_pain = chain.get("max_pain", 0)
            call_wall= chain.get("call_wall", 0)
            put_floor= chain.get("put_floor", 0)

            levels_html = '<div style="background:white;border:1px solid #e8e8e8;border-radius:8px;padding:14px 18px;">'
            levels_html += data_row("Resistance (Prev High)", f"{sr.get('prev_high',0):,.2f}", "down")
            levels_html += data_row("Call Wall (OI)", f"{call_wall:,}", "down")
            levels_html += data_row("Max Pain", f"{max_pain:,}", "warn")
            levels_html += data_row("Put Floor (OI)", f"{put_floor:,}", "up")
            levels_html += data_row("Support (Prev Low)", f"{sr.get('prev_low',0):,.2f}", "up")
            levels_html += data_row("200 Day EMA", f"{ema.get('ema_200',0):,.2f}", "up" if ema.get('above_200') else "down")
            levels_html += "</div>"
            st.markdown(levels_html, unsafe_allow_html=True)

    st.markdown("---")

    # ── Morning Bias Score breakdown ──────────────────────────────────────────
    st.markdown("**🧮 Morning Bias Score Breakdown**")

    score_col, breakdown_col = st.columns([1, 2])

    with score_col:
        score_color = "#1a7f5a" if bias["direction"] == "BULLISH" else "#e53e3e" if bias["direction"] == "BEARISH" else "#d97706"
        trade_msg   = "✅ Trade today" if bias["trade_today"] else "❌ Sit out today"
        trade_color = "#1a7f5a" if bias["trade_today"] else "#e53e3e"

        st.markdown(f"""
        <div style="background:white;border:1px solid #e8e8e8;border-radius:8px;padding:20px;text-align:center;">
            <div style="font-size:52px;font-weight:700;color:{score_color};line-height:1;">
                {bias['score']}
            </div>
            <div style="font-size:13px;color:#9ca3af;margin-bottom:10px;">out of 100</div>
            <div style="font-size:16px;font-weight:600;color:{score_color};">{bias['direction']}</div>
            <div style="font-size:13px;color:#9ca3af;">{bias['confidence']} Confidence</div>
            <div style="margin-top:12px;padding:8px;background:{'#f0faf5' if bias['trade_today'] else '#fef2f2'};
                border-radius:6px;font-size:13px;color:{trade_color};font-weight:500;">
                {trade_msg}
            </div>
        </div>
        """, unsafe_allow_html=True)

    with breakdown_col:
        st.markdown('<div style="background:white;border:1px solid #e8e8e8;border-radius:8px;padding:14px 18px;">', unsafe_allow_html=True)
        rows = []
        for s in bias.get("signals", []):
            bias_cls = "up" if s["bias"] == "BULL" else "down" if s["bias"] in ("BEAR","BLOCK") else "neutral"
            icon     = "✓" if s["bias"] == "BULL" else "✗" if s["bias"] in ("BEAR","BLOCK") else "–"
            pts_str  = f'+{s["pts"]}' if s["pts"] > 0 else "—"
            rows.append(f"""
            <div class="data-row">
                <span style="display:flex;align-items:center;gap:6px;">
                    <span class="{bias_cls}" style="font-size:12px;">{icon}</span>
                    <span class="data-label">{s['label']}</span>
                </span>
                <div style="display:flex;align-items:center;gap:10px;">
                    <span style="font-size:11px;color:#9ca3af;">{s['value']}</span>
                    <span class="{bias_cls}" style="font-weight:600;min-width:28px;text-align:right;">{pts_str}</span>
                </div>
            </div>""")
        st.markdown("".join(rows) + "</div>", unsafe_allow_html=True)


# ─── EOD REPORT VIEW ─────────────────────────────────────────────────────────

def render_eod():
    st.markdown("---")

    with st.spinner("Loading EOD data..."):
        df      = cached_ohlcv()
        chain   = cached_options_chain()
        fii     = cached_fii_data()
        ema     = compute_ema_status(df) if not df.empty else {}
        eod     = get_eod_summary(df, chain, fii)
        fii_trend = cached_fii_trend()

    if not eod:
        st.warning("EOD data unavailable. Market data not yet loaded.")
        return

    levels = eod.get("levels", {})

    # ── Top metrics ───────────────────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    day_pct   = eod.get("day_pct", 0)
    day_color = "green" if day_pct >= 0 else "red"

    with c1:
        st.markdown(metric_card(
            "Nifty Close",
            f"{eod.get('today_close',0):,.2f}",
            f"{'+' if day_pct>=0 else ''}{day_pct:.2f}% today",
        ), unsafe_allow_html=True)
    with c2:
        st.markdown(metric_card(
            "Day Range",
            f"{eod.get('today_low',0):,.0f} – {eod.get('today_high',0):,.0f}",
            f"Range {eod.get('today_high',0)-eod.get('today_low',0):.0f} pts",
        ), unsafe_allow_html=True)
    with c3:
        pcr_color = "green" if chain.get("pcr", 1) > 1 else "red"
        st.markdown(metric_card(
            "PCR (End of Day)",
            f"{chain.get('pcr', 0):.3f}",
            "Bullish" if chain.get("pcr", 1) > 1.1 else "Bearish" if chain.get("pcr", 1) < 0.9 else "Neutral",
        ), unsafe_allow_html=True)
    with c4:
        fii_net = fii.get("fii_cash", 0)
        st.markdown(metric_card(
            "FII Net (Cash)",
            f"₹{abs(fii_net):.0f}cr",
            f"{'Net Buyer' if fii_net > 0 else 'Net Seller'} today",
        ), unsafe_allow_html=True)

    st.markdown("---")

    col_l, col_r = st.columns([1, 1])

    with col_l:
        # Price chart — OHLCV with EMAs
        st.markdown("**📈 Nifty 50 — Last 60 Days with EMAs**")
        if not df.empty:
            plot_df = df.tail(60)
            fig = go.Figure()

            # Candlesticks
            fig.add_trace(go.Candlestick(
                x=plot_df["date"].astype(str),
                open=plot_df["open"], high=plot_df["high"],
                low=plot_df["low"],   close=plot_df["close"],
                increasing_line_color="#1a7f5a",
                decreasing_line_color="#e53e3e",
                name="NIFTY", showlegend=False,
            ))

            # EMAs
            for col, color, label in [
                ("ema_20", "#2563eb", "EMA 20"),
                ("ema_50", "#d97706", "EMA 50"),
                ("ema_200","#e53e3e", "EMA 200"),
            ]:
                fig.add_trace(go.Scatter(
                    x=plot_df["date"].astype(str),
                    y=plot_df[col],
                    line=dict(color=color, width=1.5),
                    name=label,
                ))

            fig.update_layout(
                height=280,
                margin=dict(l=0, r=0, t=10, b=0),
                paper_bgcolor="white",
                plot_bgcolor="white",
                xaxis=dict(showgrid=False, rangeslider_visible=False),
                yaxis=dict(showgrid=True, gridcolor="#f3f4f6"),
                legend=dict(orientation="h", y=1.02, font=dict(size=10)),
                font=dict(family="Space Grotesk", size=11),
            )
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

        # EMA status
        st.markdown("**📐 Daily EMA Status**")
        if ema:
            ema_html = '<div style="background:white;border:1px solid #e8e8e8;border-radius:8px;padding:14px 18px;">'
            ema_html += data_row("20 EMA", f"{ema.get('ema_20',0):,.2f} — {'Above ✓' if ema.get('above_20') else 'Below ✗'}", "up" if ema.get("above_20") else "down")
            ema_html += data_row("50 EMA", f"{ema.get('ema_50',0):,.2f} — {'Above ✓' if ema.get('above_50') else 'Below ✗'}", "up" if ema.get("above_50") else "down")
            ema_html += data_row("200 EMA",f"{ema.get('ema_200',0):,.2f} — {'Above ✓' if ema.get('above_200') else 'Below ✗'}", "up" if ema.get("above_200") else "down")
            stack_label = ema.get("stack_label", "MIXED")
            stack_color = "green" if "BULL" in stack_label else "red" if "BEAR" in stack_label else "yellow"
            ema_html += info_box(f"EMA Stack: {stack_label}", stack_color)
            ema_html += "</div>"
            st.markdown(ema_html, unsafe_allow_html=True)

    with col_r:
        # Updated levels for tomorrow
        st.markdown("**📍 Updated Levels — Watch Tomorrow**")
        if levels:
            lvl_data = [
                (f"{levels.get('new_resistance',0):,.2f}", "Today's high → new resistance", "red"),
                (f"{levels.get('call_wall',0):,}",        "Call wall — OI resistance",     "red"),
                (f"{levels.get('max_pain',0):,}",         "Max pain — gravitational pull", "warn"),
                (f"{levels.get('prev_close',0):,.2f}",    "Today's close → tomorrow pivot","neutral"),
                (f"{levels.get('put_floor',0):,}",        "Put floor — OI support",        "up"),
                (f"{levels.get('new_support',0):,.2f}",   "Today's low → support",         "up"),
            ]
            level_badges = {
                "red":     ("Resistance",   "badge-red"),
                "warn":    ("Max Pain",     "badge-yellow"),
                "neutral": ("Pivot",        "badge-gray"),
                "up":      ("Support",      "badge-green"),
            }
            lvl_html = '<div style="background:white;border:1px solid #e8e8e8;border-radius:8px;padding:14px 18px;">'
            for val, desc, color in lvl_data:
                b_label, b_class = level_badges[color]
                lvl_html += f"""
                <div class="data-row">
                    <div>
                        <div style="font-size:13px;font-weight:600;color:{'#e53e3e' if color in ('red','down') else '#1a7f5a' if color=='up' else '#d97706' if color=='warn' else '#1a1a2e'};">{val}</div>
                        <div style="font-size:11px;color:#9ca3af;">{desc}</div>
                    </div>
                    <span class="badge {b_class}">{b_label}</span>
                </div>"""
            lvl_html += "</div>"
            st.markdown(lvl_html, unsafe_allow_html=True)

        st.markdown("")

        # FII EOD data
        st.markdown("**🏦 FII / DII Data — Today**")
        fii_html = '<div style="background:white;border:1px solid #e8e8e8;border-radius:8px;padding:14px 18px;">'
        fii_html += data_row("FII Cash Market",    f"₹{fii.get('fii_cash',0):+.0f} cr", "up" if fii.get("fii_cash",0)>0 else "down")
        fii_html += data_row("FII Index Futures",  f"₹{fii.get('fii_fut',0):+.0f} cr",  "up" if fii.get("fii_fut",0)>0 else "down")
        fii_html += data_row("DII Cash Market",    f"₹{fii.get('dii_cash',0):+.0f} cr", "up" if fii.get("dii_cash",0)>0 else "down")
        net4 = sum(t["net"] for t in fii_trend[-4:]) if len(fii_trend) >= 4 else 0
        trend_msg = f"FII net {'long' if net4 > 0 else 'short'} for 4 consecutive days — {'Bullish' if net4 > 0 else 'Bearish'} bias tomorrow"
        fii_html += info_box(trend_msg, "green" if net4 > 0 else "red")
        fii_html += "</div>"
        st.markdown(fii_html, unsafe_allow_html=True)

        st.markdown("")

        # Tomorrow's watchlist
        st.markdown("**🔭 Tomorrow's Watchlist**")
        if levels and ema:
            call_wall  = levels.get("call_wall", 0)
            put_floor  = levels.get("put_floor", 0)
            ema_200    = levels.get("ema_200", 0)
            max_pain   = levels.get("max_pain", 0)
            resistance = levels.get("new_resistance", 0)

            watch_items = [
                f"Opening range breakout above <b>{resistance:,.0f}</b> (today's high) = bullish",
                f"Straddle VWAP break — watch premium buildup at ATM",
                f"200 EMA retest on 15-min near <b>{ema_200:,.0f}</b> — high quality bounce setup",
                f"Gamma squeeze if Nifty approaches call wall at <b>{call_wall:,.0f}</b>",
                f"Put floor defense at <b>{put_floor:,.0f}</b> — institutional support level",
            ]
            watch_html = '<div style="background:white;border:1px solid #e8e8e8;border-radius:8px;padding:14px 18px;">'
            for item in watch_items:
                watch_html += f'<div style="padding:6px 0;border-bottom:1px solid #f3f4f6;font-size:12px;color:#555;line-height:1.5;">{item}</div>'

            bias_dir   = "BULLISH" if ema.get("stack_bull") else "BEARISH" if ema.get("stack_bear") else "NEUTRAL"
            bias_color = "green" if bias_dir == "BULLISH" else "red" if bias_dir == "BEARISH" else "yellow"
            watch_html += info_box(f"Bias: {bias_dir} — EMA stack {'intact' if bias_dir != 'NEUTRAL' else 'mixed'}", bias_color)
            watch_html += "</div>"
            st.markdown(watch_html, unsafe_allow_html=True)


# ─── MAIN RENDER ─────────────────────────────────────────────────────────────

def render():
    """Main entry point — called by app.py"""

    # Fetch core data for header
    vix   = cached_vix()
    ohlcv = cached_ohlcv()
    ema   = compute_ema_status(ohlcv) if not ohlcv.empty else {}

    nifty_close = ema.get("close", 0)
    nifty_pct   = ema.get("day_pct", 0)
    vix_val     = vix.get("value", 0)

    render_page_header(nifty_close, nifty_pct, vix_val)

    # Sub-tabs — Pre-Market and EOD
    tab_pre, tab_eod = st.tabs(["🌅 Pre-Market Report", "🌆 EOD Report"])

    with tab_pre:
        render_premarket()

    with tab_eod:
        render_eod()


# ─── STANDALONE RUN ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    render()
