"""
pages/market_pulse.py — TradeSage Market Pulse homepage
Shows Nifty/Sensex indices, bullish/bearish signals, sector momentum, roadmap.
"""

import streamlit as st

# ── CACHED DATA FETCH ──────────────────────────────────────────────────────────
@st.cache_data(ttl=3600)
def _load_pulse():
    from utils.market_data import get_market_pulse
    return get_market_pulse()

@st.cache_data(ttl=3600)
def _load_indices():
    from utils.market_data import get_nifty_indices
    return get_nifty_indices()


# ── HELPERS ────────────────────────────────────────────────────────────────────
def _chg_color(val):
    if val > 0:  return "var(--green)"
    if val < 0:  return "var(--red)"
    return "var(--muted)"

def _chg_sign(val):
    return f"+{val:.2f}%" if val > 0 else f"{val:.2f}%"

def _signal_row(item, accent):
    sign = "▲" if item["pct_chg"] >= 0 else "▼"
    clr  = "var(--green)" if item["pct_chg"] >= 0 else "var(--red)"
    return f"""
<div style="display:flex;align-items:center;justify-content:space-between;
            padding:8px 0;border-bottom:1px solid var(--border);">
  <div>
    <div style="font-size:0.83rem;font-weight:700;color:var(--text);">{item['symbol']}</div>
    <div style="font-size:0.7rem;color:{accent};margin-top:1px;">{item['reason']}</div>
  </div>
  <div style="text-align:right;">
    <div style="font-size:0.82rem;font-weight:600;font-family:'JetBrains Mono',monospace;
                color:var(--text);">₹{item['price']:,.2f}</div>
    <div style="font-size:0.72rem;font-weight:700;color:{clr};">{sign}{abs(item['pct_chg']):.2f}%</div>
  </div>
</div>"""


def render():
    green  = "#1a7f37"; red = "#cf222e"; yellow = "#9a6700"; blue = "#0969da"
    border = "#d0d7de"; card = "#ffffff"; card2 = "#eef1f5"; muted = "#57606a"

    # ── A. INDICES STRIP ──────────────────────────────────────────────────────
    indices = _load_indices()
    n_chg   = indices["nifty_chg"]
    s_chg   = indices["sensex_chg"]

    col_n, col_s, col_note = st.columns([1, 1, 2])

    with col_n:
        n_clr = green if n_chg >= 0 else red
        st.markdown(f"""
<div style="background:{card};border:1.5px solid {border};border-radius:12px;
            padding:16px 20px;border-top:3px solid {n_clr};">
  <div style="font-size:0.7rem;color:{muted};text-transform:uppercase;
              letter-spacing:1px;font-weight:600;">Nifty 50</div>
  <div style="font-size:1.5rem;font-weight:800;font-family:'JetBrains Mono',monospace;
              margin:4px 0;">{indices['nifty']:,.2f}</div>
  <div style="font-size:0.85rem;font-weight:700;color:{n_clr};">
      {'▲' if n_chg>=0 else '▼'} {abs(n_chg):.2f}%
  </div>
</div>""", unsafe_allow_html=True)

    with col_s:
        s_clr = green if s_chg >= 0 else red
        st.markdown(f"""
<div style="background:{card};border:1.5px solid {border};border-radius:12px;
            padding:16px 20px;border-top:3px solid {s_clr};">
  <div style="font-size:0.7rem;color:{muted};text-transform:uppercase;
              letter-spacing:1px;font-weight:600;">Sensex</div>
  <div style="font-size:1.5rem;font-weight:800;font-family:'JetBrains Mono',monospace;
              margin:4px 0;">{indices['sensex']:,.2f}</div>
  <div style="font-size:0.85rem;font-weight:700;color:{s_clr};">
      {'▲' if s_chg>=0 else '▼'} {abs(s_chg):.2f}%
  </div>
</div>""", unsafe_allow_html=True)

    with col_note:
        st.markdown(f"""
<div style="height:100%;display:flex;align-items:center;padding-left:12px;">
  <div style="font-size:0.78rem;color:{muted};line-height:1.7;">
    📡 Signals updated daily · Source: Yahoo Finance<br>
    Trend changes detected from last 1–2 trading sessions.<br>
    Not investment advice — do your own research.
  </div>
</div>""", unsafe_allow_html=True)

    st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)

    # ── B. SECTION HEADER ─────────────────────────────────────────────────────
    st.markdown(f"""
<div style="margin-bottom:16px;">
  <div style="font-size:1.2rem;font-weight:800;letter-spacing:-0.3px;">Today's Signals</div>
  <div style="font-size:0.8rem;color:{muted};margin-top:2px;">
    Stocks that just flipped — 200 DMA / 50 DMA crossovers and MACD reversals
  </div>
</div>""", unsafe_allow_html=True)

    # ── C. THREE SIGNAL COLUMNS ───────────────────────────────────────────────
    with st.spinner("Scanning market signals…"):
        pulse = _load_pulse()

    bullish = pulse.get("bullish", [])
    bearish = pulse.get("bearish", [])

    high_impact_news = [
        {"headline": "RBI holds rates; signals accommodative pivot in H2 FY26",
         "tag": "Macro", "impact": "Positive for rate-sensitives"},
        {"headline": "FII net buyers ₹4,820 Cr — third consecutive session of inflows",
         "tag": "Flows",  "impact": "Broad market positive"},
        {"headline": "Q3 GDP at 6.4% — above estimates, capex recovery on track",
         "tag": "Economy","impact": "Positive for infra & capital goods"},
    ]

    col_bull, col_bear, col_news = st.columns(3)

    with col_bull:
        rows_html = "".join(_signal_row(s, green) for s in bullish) or \
                    f"<div style='color:{muted};font-size:0.82rem;padding:12px 0;'>No crossovers detected today</div>"
        st.markdown(f"""
<div style="background:{card};border:1.5px solid {border};border-radius:12px;
            padding:16px;border-top:3px solid {green};">
  <div style="font-size:0.78rem;font-weight:700;color:{green};
              text-transform:uppercase;letter-spacing:1px;margin-bottom:12px;">
    ▲ Turning Bullish ({len(bullish)})
  </div>
  {rows_html}
</div>""", unsafe_allow_html=True)

    with col_bear:
        rows_html = "".join(_signal_row(s, red) for s in bearish) or \
                    f"<div style='color:{muted};font-size:0.82rem;padding:12px 0;'>No crossovers detected today</div>"
        st.markdown(f"""
<div style="background:{card};border:1.5px solid {border};border-radius:12px;
            padding:16px;border-top:3px solid {red};">
  <div style="font-size:0.78rem;font-weight:700;color:{red};
              text-transform:uppercase;letter-spacing:1px;margin-bottom:12px;">
    ▼ Turning Bearish ({len(bearish)})
  </div>
  {rows_html}
</div>""", unsafe_allow_html=True)

    with col_news:
        news_html = ""
        for n in high_impact_news:
            news_html += f"""
<div style="padding:8px 0;border-bottom:1px solid {border};">
  <div style="font-size:0.78rem;font-weight:700;color:var(--text);line-height:1.4;">
      {n['headline']}
  </div>
  <div style="display:flex;gap:6px;margin-top:4px;align-items:center;">
    <span style="font-size:0.62rem;padding:1px 7px;border-radius:20px;
                 background:rgba(154,103,0,0.1);color:{yellow};
                 border:1px solid {yellow};font-weight:600;">{n['tag']}</span>
    <span style="font-size:0.68rem;color:{muted};">{n['impact']}</span>
  </div>
</div>"""
        st.markdown(f"""
<div style="background:{card};border:1.5px solid {border};border-radius:12px;
            padding:16px;border-top:3px solid {yellow};">
  <div style="font-size:0.78rem;font-weight:700;color:{yellow};
              text-transform:uppercase;letter-spacing:1px;margin-bottom:12px;">
    ⚡ High Impact News
  </div>
  {news_html}
</div>""", unsafe_allow_html=True)

    st.markdown("<div style='height:32px'></div>", unsafe_allow_html=True)

    # ── D. SECTOR MOMENTUM HEADER ─────────────────────────────────────────────
    st.markdown(f"""
<div style="margin-bottom:16px;">
  <div style="font-size:1.2rem;font-weight:800;letter-spacing:-0.3px;">Sector Momentum</div>
  <div style="font-size:0.8rem;color:{muted};margin-top:2px;">
    12-month trailing performance across key Indian sectors
  </div>
</div>""", unsafe_allow_html=True)

    # ── E. SECTOR GRID ────────────────────────────────────────────────────────
    from utils.market_data import get_sector_momentum
    sectors = get_sector_momentum()

    cols = st.columns(4)
    for i, sec in enumerate(sectors):
        clr = green if sec["color"] == "green" else (red if sec["color"] == "red" else yellow)
        sign = "+" if sec["pct"] >= 0 else ""
        arrow = "▲" if sec["pct"] >= 0 else "▼"
        with cols[i % 4]:
            st.markdown(f"""
<div style="background:{card};border:1.5px solid {border};border-radius:12px;
            padding:14px 16px;margin-bottom:14px;border-left:3px solid {clr};">
  <div style="font-size:0.78rem;font-weight:700;color:var(--text);
              line-height:1.3;margin-bottom:6px;">{sec['sector']}</div>
  <div style="font-size:1.1rem;font-weight:800;font-family:'JetBrains Mono',monospace;
              color:{clr};">{arrow} {sign}{sec['pct']:.1f}%</div>
  <div style="font-size:0.7rem;color:{muted};margin-top:4px;">{sec['note']}</div>
</div>""", unsafe_allow_html=True)

    st.markdown("<div style='height:32px'></div>", unsafe_allow_html=True)

    # ── F. ROADMAP STRIP ─────────────────────────────────────────────────────
    milestones = [
        ("📄", "IPO Research",    "Live",  green,  True),
        ("📈", "Stock Research",  "Beta",  blue,   True),
        ("⚡", "F&O Intelligence","Q3",    yellow, False),
        ("📂", "MF Screener",     "Q3",    yellow, False),
        ("₿",  "Crypto",          "Q4",    muted,  False),
    ]

    cells = ""
    for i, (icon, name, tag, clr, live) in enumerate(milestones):
        opacity = "1" if live else "0.5"
        arrow   = "<span style='font-size:1.1rem;color:var(--border);margin:0 6px;'>→</span>" if i < len(milestones)-1 else ""
        cells += f"""
<div style="display:flex;align-items:center;">
  <div style="text-align:center;opacity:{opacity};">
    <div style="font-size:1.2rem;">{icon}</div>
    <div style="font-size:0.72rem;font-weight:700;color:var(--text);margin-top:2px;">{name}</div>
    <span style="font-size:0.6rem;padding:1px 7px;border-radius:20px;
                 background:rgba(0,0,0,0.06);color:{clr};border:1px solid {clr};
                 font-weight:700;">{tag}</span>
  </div>
  {arrow}
</div>"""

    st.markdown(f"""
<div style="background:{card2};border:1.5px solid {border};border-radius:14px;
            padding:18px 24px;">
  <div style="font-size:0.65rem;font-weight:700;color:{muted};
              text-transform:uppercase;letter-spacing:2px;margin-bottom:12px;">Product Roadmap</div>
  <div style="display:flex;align-items:center;flex-wrap:wrap;gap:4px;">
    {cells}
  </div>
</div>""", unsafe_allow_html=True)
