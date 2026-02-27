"""
pages/stock_research.py — TradeSage Stock Research
Single-stock multi-agent analysis: Technical, Trend, News, Fundamentals.
"""

import streamlit as st

QUICK_PICKS = ["RELIANCE", "TATAMOTORS", "HDFCBANK", "INFY",
               "ZOMATO", "DIXON", "LT", "SUNPHARMA"]

GREEN  = "#1a7f37"; RED = "#cf222e"; YELLOW = "#9a6700"; BLUE = "#0969da"
BORDER = "#d0d7de"; CARD = "#ffffff"; CARD2 = "#eef1f5"; MUTED = "#57606a"


def _pill(label, color):
    bg = color.replace(")", ",0.12)").replace("rgb", "rgba") if "rgb" in color else f"{color}1a"
    return (f'<span style="display:inline-block;padding:2px 10px;border-radius:20px;'
            f'font-size:0.72rem;font-weight:700;background:{color}1a;'
            f'color:{color};border:1px solid {color};margin:2px 3px 2px 0;">'
            f'{label}</span>')


def _agent_card(icon, title, body_html, accent):
    return f"""
<div style="background:{CARD};border:1.5px solid {BORDER};border-radius:12px;
            padding:18px;border-top:3px solid {accent};height:100%;">
  <div style="font-size:0.78rem;font-weight:700;color:{accent};
              text-transform:uppercase;letter-spacing:1px;margin-bottom:12px;">
    {icon} {title}
  </div>
  {body_html}
</div>"""


def _fmt_price(p):
    return f"₹{p:,.2f}"


def render():
    # ── SESSION STATE ─────────────────────────────────────────────────────────
    if "research_symbol" not in st.session_state:
        st.session_state.research_symbol = ""

    # ── A. TITLE ─────────────────────────────────────────────────────────────
    st.markdown(f"""
<div style="margin-bottom:20px;">
  <div style="font-size:1.3rem;font-weight:800;letter-spacing:-0.3px;">Stock Research</div>
  <div style="font-size:0.82rem;color:{MUTED};margin-top:3px;">
    Four AI agents analyse any NSE stock — Technical · Trend · News · Fundamentals
  </div>
</div>""", unsafe_allow_html=True)

    # ── B. SEARCH ROW ────────────────────────────────────────────────────────
    search_col, btn_col = st.columns([5, 1])
    with search_col:
        typed = st.text_input("", placeholder="Enter NSE symbol  e.g.  RELIANCE",
                              label_visibility="collapsed",
                              value=st.session_state.research_symbol)
    with btn_col:
        analyse = st.button("Analyse", use_container_width=True)

    if analyse and typed.strip():
        st.session_state.research_symbol = typed.strip().upper()
        st.rerun()

    # Quick picks
    st.markdown(f"<div style='font-size:0.72rem;color:{MUTED};margin:4px 0 6px;'>Quick picks →</div>",
                unsafe_allow_html=True)
    qcols = st.columns(len(QUICK_PICKS))
    for i, sym in enumerate(QUICK_PICKS):
        with qcols[i]:
            if st.button(sym, key=f"qp_{sym}", use_container_width=True):
                st.session_state.research_symbol = sym
                st.rerun()

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    symbol = st.session_state.research_symbol

    # ── C. LANDING STATE ─────────────────────────────────────────────────────
    if not symbol:
        agents = [
            ("📊", "Technical Agent",     "RSI · MACD · 50 DMA · 200 DMA · Volume analysis"),
            ("🌊", "Trend Agent",         "Sector momentum · 52-week range · Relative performance"),
            ("📰", "News Agent",          "Latest headlines from Google News · ET · Moneycontrol"),
            ("📋", "Fundamentals Agent",  "Revenue · Profit · PE ratio · Market cap from filings"),
        ]
        c1, c2 = st.columns(2)
        for i, (icon, name, desc) in enumerate(agents):
            col = c1 if i % 2 == 0 else c2
            with col:
                st.markdown(f"""
<div style="background:{CARD};border:1.5px solid {BORDER};border-radius:12px;
            padding:20px;margin-bottom:14px;text-align:center;">
  <div style="font-size:2rem;margin-bottom:8px;">{icon}</div>
  <div style="font-size:0.95rem;font-weight:700;">{name}</div>
  <div style="font-size:0.78rem;color:{MUTED};margin-top:6px;">{desc}</div>
</div>""", unsafe_allow_html=True)
        return

    # ── D. FETCH DATA ─────────────────────────────────────────────────────────
    with st.spinner(f"Running 4 agents on {symbol}…"):
        from utils.market_data import get_stock_analysis
        d = get_stock_analysis(symbol)

    if d.get("mock"):
        st.info(f"⚠ Live data unavailable for **{symbol}** — showing sample analysis.", icon="ℹ️")

    price   = d["price"]
    pct_chg = d["pct_chg"]
    chg_clr = GREEN if pct_chg >= 0 else RED
    chg_sign = "▲" if pct_chg >= 0 else "▼"

    # ── E. STOCK HEADER ───────────────────────────────────────────────────────
    overall_signal = "BULLISH" if (d["above_200dma"] and d["macd_bull"]) else \
                     ("BEARISH" if (not d["above_200dma"] and not d["macd_bull"]) else "NEUTRAL")
    sig_clr = GREEN if overall_signal == "BULLISH" else (RED if overall_signal == "BEARISH" else YELLOW)

    st.markdown(f"""
<div style="background:{CARD};border:1.5px solid {BORDER};border-radius:12px;
            padding:18px 22px;margin-bottom:18px;display:flex;
            align-items:center;justify-content:space-between;">
  <div>
    <div style="font-size:1.3rem;font-weight:800;">{d['name']}</div>
    <div style="margin-top:6px;display:flex;gap:6px;align-items:center;">
      <span style="font-size:0.7rem;padding:2px 9px;border-radius:20px;
                   background:rgba(9,105,218,0.1);color:{BLUE};
                   border:1px solid {BLUE};font-weight:700;">NSE: {symbol}</span>
      <span style="font-size:0.7rem;padding:2px 9px;border-radius:20px;
                   background:{sig_clr}1a;color:{sig_clr};
                   border:1px solid {sig_clr};font-weight:700;">{overall_signal}</span>
      {f'<span style="font-size:0.7rem;color:{MUTED};">{d["sector"]}</span>' if d.get("sector") else ""}
    </div>
  </div>
  <div style="text-align:right;">
    <div style="font-size:1.8rem;font-weight:800;font-family:\'JetBrains Mono\',monospace;">
        ₹{price:,.2f}
    </div>
    <div style="font-size:1rem;font-weight:700;color:{chg_clr};">
        {chg_sign} {abs(pct_chg):.2f}%
    </div>
  </div>
</div>""", unsafe_allow_html=True)

    # ── F. METRICS ROW ────────────────────────────────────────────────────────
    m1, m2, m3, m4, m5 = st.columns(5)
    rsi_clr = RED if d["rsi"] > 70 else (GREEN if d["rsi"] < 30 else YELLOW)
    with m1:
        st.markdown(f"""
<div style="background:{CARD};border:1.5px solid {BORDER};border-radius:10px;padding:14px;text-align:center;">
  <div style="font-size:0.65rem;color:{MUTED};text-transform:uppercase;letter-spacing:0.8px;">RSI (14)</div>
  <div style="font-size:1.2rem;font-weight:800;font-family:'JetBrains Mono',monospace;
              color:{rsi_clr};margin-top:4px;">{d['rsi']:.1f}</div>
  <div style="font-size:0.68rem;color:{rsi_clr};">{'Overbought' if d['rsi']>70 else ('Oversold' if d['rsi']<30 else 'Neutral')}</div>
</div>""", unsafe_allow_html=True)

    for col, label, above, val in [
        (m2, "50 DMA", d["above_50dma"],  d["dma50"]),
        (m3, "200 DMA", d["above_200dma"], d["dma200"]),
    ]:
        clr = GREEN if above else RED
        tag = "Above" if above else "Below"
        with col:
            st.markdown(f"""
<div style="background:{CARD};border:1.5px solid {BORDER};border-radius:10px;padding:14px;text-align:center;">
  <div style="font-size:0.65rem;color:{MUTED};text-transform:uppercase;letter-spacing:0.8px;">{label}</div>
  <div style="font-size:1.2rem;font-weight:800;font-family:'JetBrains Mono',monospace;
              color:{clr};margin-top:4px;">{tag}</div>
  <div style="font-size:0.68rem;color:{MUTED};">₹{val:,.2f}</div>
</div>""", unsafe_allow_html=True)

    with m4:
        pe_txt = f"{d['pe']:.1f}x" if d.get("pe") else "N/A"
        st.markdown(f"""
<div style="background:{CARD};border:1.5px solid {BORDER};border-radius:10px;padding:14px;text-align:center;">
  <div style="font-size:0.65rem;color:{MUTED};text-transform:uppercase;letter-spacing:0.8px;">P/E Ratio</div>
  <div style="font-size:1.2rem;font-weight:800;font-family:'JetBrains Mono',monospace;margin-top:4px;">{pe_txt}</div>
  <div style="font-size:0.68rem;color:{MUTED};">Trailing</div>
</div>""", unsafe_allow_html=True)

    with m5:
        st.markdown(f"""
<div style="background:{CARD};border:1.5px solid {BORDER};border-radius:10px;padding:14px;text-align:center;">
  <div style="font-size:0.65rem;color:{MUTED};text-transform:uppercase;letter-spacing:0.8px;">Market Cap</div>
  <div style="font-size:1.05rem;font-weight:800;font-family:'JetBrains Mono',monospace;margin-top:4px;">{d['mktcap']}</div>
  <div style="font-size:0.68rem;color:{MUTED};">NSE</div>
</div>""", unsafe_allow_html=True)

    st.markdown("<div style='height:22px'></div>", unsafe_allow_html=True)

    # ── G. AGENT HEADER ───────────────────────────────────────────────────────
    st.markdown(f"""
<div style="margin-bottom:16px;">
  <div style="font-size:1.1rem;font-weight:800;">AI Agent Analysis</div>
  <div style="font-size:0.78rem;color:{MUTED};margin-top:2px;">
    Four independent agents · Real-time data · Powered by TradeSage
  </div>
</div>""", unsafe_allow_html=True)

    # ── H. 2x2 AGENT GRID ────────────────────────────────────────────────────
    row1_c1, row1_c2 = st.columns(2)
    row2_c1, row2_c2 = st.columns(2)

    # Technical Agent
    macd_status = "Bullish" if d["macd_bull"] else "Bearish"
    macd_clr    = GREEN if d["macd_bull"] else RED
    vol_status  = "High volume" if d["vol_ratio"] > 1.3 else ("Low volume" if d["vol_ratio"] < 0.7 else "Normal volume")
    tech_body = f"""
<div style="font-size:0.82rem;line-height:1.8;color:var(--text);">
  <div><b>Price:</b> ₹{price:,.2f} &nbsp;
    {'<span style="color:'+GREEN+';">▲ Above</span>' if d['above_50dma'] else '<span style="color:'+RED+';">▼ Below</span>'} 50 DMA &nbsp;|&nbsp;
    {'<span style="color:'+GREEN+';">▲ Above</span>' if d['above_200dma'] else '<span style="color:'+RED+';">▼ Below</span>'} 200 DMA
  </div>
  <div><b>RSI(14):</b> {d['rsi']:.1f} &nbsp;&nbsp;</div>
  <div style="margin-top:6px;">
    {_pill('RSI: '+('Overbought' if d['rsi']>70 else 'Oversold' if d['rsi']<30 else 'Neutral'), rsi_clr)}
    {_pill('MACD: '+macd_status, macd_clr)}
    {_pill(vol_status, BLUE)}
    {_pill('Vol ratio: '+str(d['vol_ratio'])+'x', MUTED)}
  </div>
</div>"""
    with row1_c1:
        st.markdown(_agent_card("📊", "Technical Agent", tech_body, BLUE), unsafe_allow_html=True)

    # Trend Agent
    range_pct = round((price - d["low_52w"]) / max(d["high_52w"] - d["low_52w"], 1) * 100, 0)
    trend_body = f"""
<div style="font-size:0.82rem;line-height:1.9;color:var(--text);">
  <div><b>Sector:</b> {d.get('sector','—')}</div>
  <div><b>52W Range:</b> ₹{d['low_52w']:,.2f} – ₹{d['high_52w']:,.2f}</div>
  <div><b>Position in range:</b> {range_pct:.0f}%</div>
  <div><b>Trend bias:</b>
    <span style="color:{GREEN if d['above_200dma'] else RED};font-weight:700;">
      {'Long-term Bullish' if d['above_200dma'] else 'Long-term Bearish'}
    </span>
  </div>
  <div style="font-size:0.75rem;color:{MUTED};margin-top:6px;">
    {'Institutional activity likely — high volume with upward drift.' if d['vol_ratio']>1.2 and pct_chg>0
     else 'Watch for volume confirmation before adding position.'}
  </div>
</div>"""
    with row1_c2:
        st.markdown(_agent_card("🌊", "Trend Agent", trend_body, GREEN), unsafe_allow_html=True)

    # News Agent
    news = d.get("news", [])
    if news:
        news_items_html = "".join(
            f'<div style="padding:6px 0;border-bottom:1px solid {BORDER};font-size:0.8rem;line-height:1.4;">'
            f'<span style="color:{MUTED};font-size:0.7rem;">'
            f'{n["date"]}{"  ·  " + n["source"] if n.get("source") else ""} · </span>'
            f'{n["title"]}</div>'
            for n in news[:3]
        )
    else:
        news_items_html = f'<div style="color:{MUTED};font-size:0.82rem;">No recent news found for {symbol}.</div>'
    news_body = f'<div style="font-size:0.82rem;">{news_items_html}</div>'
    with row2_c1:
        st.markdown(_agent_card("📰", "News Agent", news_body, YELLOW), unsafe_allow_html=True)

    # Fundamentals Agent
    fund_body = f"""
<div style="font-size:0.82rem;line-height:1.9;color:var(--text);">
  <div><b>Revenue:</b> {d.get('revenue','N/A')}</div>
  <div><b>Net Profit:</b> {d.get('net_income','N/A')}</div>
  <div><b>P/E Ratio:</b> {f"{d['pe']:.1f}x" if d.get('pe') else 'N/A'}</div>
  <div><b>Market Cap:</b> {d.get('mktcap','N/A')}</div>
  <div style="margin-top:8px;font-size:0.72rem;color:{MUTED};
              background:{CARD2};border-radius:6px;padding:8px;">
    📌 Full annual report analysis (DRHP/Annual Report AI Q&A) coming in next release.
  </div>
</div>"""
    with row2_c2:
        st.markdown(_agent_card("📋", "Fundamentals Agent", fund_body, "#9b59b6"), unsafe_allow_html=True)

    st.markdown("<div style='height:22px'></div>", unsafe_allow_html=True)

    # ── I. SYNTHESIS CARD ─────────────────────────────────────────────────────
    if overall_signal == "BULLISH":
        score, score_clr, syn_title = 7.0, GREEN, "Bullish Setup"
        syn_sub  = "Technical and trend indicators aligned to the upside"
        bullets  = [
            f"Price trading above both 50 DMA (₹{d['dma50']:,.2f}) and 200 DMA (₹{d['dma200']:,.2f})",
            f"RSI at {d['rsi']:.1f} — momentum healthy, not yet overbought",
            f"MACD {'bullish' if d['macd_bull'] else 'bearish'} — {'supports' if d['macd_bull'] else 'caution on'} continued upside",
            f"Volume ratio {d['vol_ratio']:.2f}x — {'above-average participation' if d['vol_ratio']>1 else 'below-average, watch for confirmation'}",
        ]
    elif overall_signal == "BEARISH":
        score, score_clr, syn_title = 3.0, RED, "Bearish Setup"
        syn_sub  = "Price action and momentum indicators point to weakness"
        bullets  = [
            f"Price below 200 DMA (₹{d['dma200']:,.2f}) — long-term trend is down",
            f"RSI at {d['rsi']:.1f} — {'still room for more downside' if d['rsi']>35 else 'approaching oversold — watch for bounce'}",
            f"MACD {'bearish crossover in effect' if not d['macd_bull'] else 'showing tentative recovery'}",
            f"52W range position: {range_pct:.0f}% — closer to {'52W high, risk of further fall' if range_pct>60 else '52W low, potential support zone'}",
        ]
    else:
        score, score_clr, syn_title = 5.0, YELLOW, "Neutral / Wait & Watch"
        syn_sub  = "Mixed signals — no clear trend confirmation yet"
        bullets  = [
            f"Price {'above' if d['above_50dma'] else 'below'} 50 DMA but {'above' if d['above_200dma'] else 'below'} 200 DMA — mixed",
            f"RSI at {d['rsi']:.1f} — momentum neutral",
            f"MACD {'positive' if d['macd_bull'] else 'negative'} — watch for confirmation",
            "Wait for a clear 200 DMA crossover or MACD signal before taking a position",
        ]

    bullets_html = "".join(
        f'<div style="display:flex;gap:8px;margin-bottom:6px;">'
        f'<span style="color:{score_clr};font-weight:700;flex-shrink:0;">→</span>'
        f'<span style="font-size:0.82rem;">{b}</span></div>'
        for b in bullets
    )

    st.markdown(f"""
<div style="background:{CARD};border:1.5px solid {BORDER};border-radius:12px;
            padding:22px;display:flex;gap:24px;align-items:flex-start;">
  <div style="text-align:center;flex-shrink:0;">
    <div style="width:72px;height:72px;border-radius:50%;background:{score_clr}1a;
                border:3px solid {score_clr};display:flex;flex-direction:column;
                align-items:center;justify-content:center;">
      <div style="font-size:1.4rem;font-weight:900;font-family:'JetBrains Mono',monospace;
                  color:{score_clr};">{score:.1f}</div>
    </div>
    <div style="font-size:0.65rem;color:{MUTED};margin-top:4px;">/ 10</div>
  </div>
  <div style="flex:1;">
    <div style="font-size:1rem;font-weight:800;">{syn_title}</div>
    <div style="font-size:0.78rem;color:{MUTED};margin-bottom:12px;">{syn_sub}</div>
    {bullets_html}
  </div>
  <div style="width:200px;flex-shrink:0;font-size:0.7rem;color:{MUTED};
              background:{CARD2};border-radius:8px;padding:10px;line-height:1.6;">
    ⚠ This analysis is algorithmic and for informational purposes only.
    Not SEBI-registered investment advice. Do your own due diligence before investing.
  </div>
</div>""", unsafe_allow_html=True)

    # ── J. DISCLAIMER ─────────────────────────────────────────────────────────
    st.markdown(f"""
<div style="margin-top:20px;font-size:0.72rem;color:{MUTED};
            border-top:1px solid {BORDER};padding-top:12px;line-height:1.6;">
  Data sourced from Yahoo Finance. Technical indicators are computed from historical OHLCV data.
  TradeSage is not a SEBI-registered investment advisor. All analysis is educational.
  Consult a qualified financial advisor before making investment decisions.
</div>""", unsafe_allow_html=True)
