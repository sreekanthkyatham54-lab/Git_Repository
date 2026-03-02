"""
pages/portfolio_ai.py — TradeSage Portfolio AI
Upload a broker screenshot → Claude vision extracts holdings → AI generates observations.
Works with Zerodha, Groww, Angel One, Upstox.
"""

import streamlit as st
import json

GREEN  = "#1a7f37"; RED = "#cf222e"; YELLOW = "#9a6700"; BLUE = "#0969da"
BORDER = "#d0d7de"; CARD = "#ffffff"; CARD2 = "#eef1f5"; MUTED = "#57606a"

# ── SAMPLE DATA ───────────────────────────────────────────────────────────────
SAMPLE_PORTFOLIO = {
    "broker": "Zerodha (Sample)",
    "total_value": 276548,
    "total_pnl_pct": 6.8,
    "holdings": [
        {"name":"HDFC Bank",    "symbol":"HDFCBANK",   "quantity":20,  "avg_price":1580, "current_price":1709, "current_value":34180,  "pnl_pct":+8.2,  "sector":"Banking"},
        {"name":"Tata Motors",  "symbol":"TATAMOTORS", "quantity":50,  "avg_price":962,  "current_price":841,  "current_value":42050,  "pnl_pct":-12.5, "sector":"Auto"},
        {"name":"Infosys",      "symbol":"INFY",       "quantity":30,  "avg_price":1412, "current_price":1724, "current_value":51720,  "pnl_pct":+22.1, "sector":"IT"},
        {"name":"Welspun India","symbol":"WELSPUNIND", "quantity":120, "avg_price":542,  "current_price":712,  "current_value":85440,  "pnl_pct":+31.4, "sector":"Infrastructure"},
        {"name":"Paytm",        "symbol":"PAYTM",      "quantity":185, "avg_price":554,  "current_price":341,  "current_value":63085,  "pnl_pct":-38.5, "sector":"Fintech"},
    ],
}

SAMPLE_OBSERVATIONS = [
    {"type":"risk",     "text":"Paytm down 38.5% — bearish technical setup persists, no institutional buying visible. Original thesis changed post-RBI action on payments bank."},
    {"type":"warning",  "text":"Banking (HDFC Bank) + Auto (Tata Motors) = 37% of portfolio. Both are rate-sensitive. Same macro risk concentrated in one factor."},
    {"type":"positive", "text":"Welspun India best positioned — confirmed breakout above 200 DMA, record order book, Q3 beat estimates. Up 31.4% and still in uptrend."},
    {"type":"positive", "text":"Portfolio +6.8% vs Nifty +8.2% YTD — marginally underperforming. Drag entirely from Paytm (-38.5%). Rest of portfolio outperforming."},
    {"type":"info",     "text":"Zero exposure to Pharma, Defence & Aerospace, Renewable Energy — three of the top four performing sectors of the last 12 months."},
    {"type":"warning",  "text":"Tata Motors down 12.5% — EV transition costs elevated, China JV facing demand headwinds. No clear catalyst for reversal near-term."},
]


# ── CLAUDE API CALLS ──────────────────────────────────────────────────────────
def _extract_holdings(api_key, image_bytes, media_type):
    """Call Claude vision to extract holdings JSON from broker screenshot."""
    import anthropic, base64
    client = anthropic.Anthropic(api_key=api_key)
    img_b64 = base64.standard_b64encode(image_bytes).decode("utf-8")

    prompt = """You are a financial data extractor. Analyse this Indian broker portfolio screenshot.
Extract all holdings and return ONLY valid JSON in this exact format — no markdown, no explanation:
{
  "holdings": [
    {
      "name": "Company Name",
      "symbol": "NSESYMBOL",
      "quantity": 100,
      "avg_price": 1500.0,
      "current_price": 1724.0,
      "current_value": 172400.0,
      "pnl_pct": 14.93,
      "sector": "IT"
    }
  ],
  "total_value": 500000.0,
  "total_pnl_pct": 8.5,
  "broker": "Zerodha"
}
If you cannot read a field clearly, use null. Sector should be one of: Banking, IT, Auto, Pharma, FMCG, Fintech, Infrastructure, Energy, Telecom, Consumer, Other."""

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2000,
        messages=[{
            "role": "user",
            "content": [
                {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": img_b64}},
                {"type": "text",  "text": prompt},
            ],
        }],
    )
    raw = response.content[0].text.strip()
    # Strip markdown code blocks if present
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw.strip())


def _generate_observations(api_key, portfolio):
    """Call Claude to generate analyst observations on the portfolio."""
    import anthropic
    client = anthropic.Anthropic(api_key=api_key)

    holdings_txt = "\n".join(
        f"- {h['name']} ({h['symbol']}): qty={h['quantity']}, avg=₹{h['avg_price']}, "
        f"current=₹{h['current_price']}, P&L={h['pnl_pct']}%, sector={h['sector']}"
        for h in portfolio.get("holdings", [])
    )

    prompt = f"""You are an independent Indian equity analyst reviewing a retail investor's portfolio.
Portfolio summary:
Total value: ₹{portfolio.get('total_value', 0):,.0f}
Total P&L: {portfolio.get('total_pnl_pct', 0):.1f}%
Holdings:
{holdings_txt}

Generate 4–6 concise, specific analyst observations about this portfolio.
Focus on: concentration risk, underperformers, outperformers, sector gaps, vs Nifty comparison, specific risks.
Use actual numbers from the portfolio.
This is educational analysis, NOT investment advice.

Return ONLY valid JSON — no markdown, no explanation:
[
  {{"type": "risk|positive|info|warning", "text": "observation text with specific numbers"}}
]"""

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = response.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw.strip())


# ── RENDER ────────────────────────────────────────────────────────────────────
def render():
    api_key = st.session_state.get("api_key", "")

    # ── A. TITLE ─────────────────────────────────────────────────────────────
    st.markdown(f"""
<div style="margin-bottom:20px;">
  <div style="font-size:1.3rem;font-weight:800;letter-spacing:-0.3px;">Portfolio AI</div>
  <div style="font-size:0.82rem;color:{MUTED};margin-top:3px;">
    Upload your broker screenshot · Claude extracts holdings · AI generates observations
  </div>
  <div style="display:flex;gap:6px;margin-top:8px;flex-wrap:wrap;">
    {"".join(f'<span style="font-size:0.68rem;padding:2px 9px;border-radius:20px;background:{CARD2};color:{MUTED};border:1px solid {BORDER};font-weight:600;">{b}</span>'
             for b in ["Zerodha","Groww","Angel One","Upstox","Kite","5paisa"])}
  </div>
</div>""", unsafe_allow_html=True)

    # ── B. API KEY WARNING ────────────────────────────────────────────────────
    if not api_key:
        st.markdown(f"""
<div style="background:rgba(154,103,0,0.08);border-left:3px solid {YELLOW};
            border-radius:0 8px 8px 0;padding:12px 16px;margin-bottom:16px;">
  <div style="font-size:0.85rem;font-weight:700;color:{YELLOW};">⚠ Anthropic API Key Required</div>
  <div style="font-size:0.78rem;color:{MUTED};margin-top:4px;">
    Enter your Anthropic API key in the sidebar to use AI analysis.
    You can still view the sample portfolio below.
  </div>
</div>""", unsafe_allow_html=True)

    # ── C. UPLOAD + SAMPLE ────────────────────────────────────────────────────
    col_up, col_btn = st.columns([3, 1])
    with col_up:
        uploaded = st.file_uploader(
            "Upload portfolio screenshot",
            type=["png", "jpg", "jpeg"],
            label_visibility="collapsed",
        )
    with col_btn:
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        use_sample = st.button("Use Sample Portfolio", use_container_width=True)

    # ── D. LOGIC ──────────────────────────────────────────────────────────────
    if use_sample:
        st.session_state["portfolio_data"]   = SAMPLE_PORTFOLIO
        st.session_state["portfolio_obs"]    = SAMPLE_OBSERVATIONS
        st.session_state["portfolio_source"] = "sample"
        st.rerun()

    if uploaded is not None and "portfolio_source" not in st.session_state:
        if not api_key:
            st.warning("Please enter your Anthropic API key in the sidebar to analyse your portfolio.")
        else:
            img_bytes  = uploaded.read()
            media_type = f"image/{uploaded.type.split('/')[-1]}"
            if media_type == "image/jpg":
                media_type = "image/jpeg"

            try:
                with st.spinner("📸 Extracting holdings from screenshot…"):
                    portfolio = _extract_holdings(api_key, img_bytes, media_type)
                with st.spinner("🤖 Generating analyst observations…"):
                    observations = _generate_observations(api_key, portfolio)
                st.session_state["portfolio_data"]   = portfolio
                st.session_state["portfolio_obs"]    = observations
                st.session_state["portfolio_source"] = "upload"
                st.rerun()
            except Exception as e:
                st.error(f"Analysis failed: {e}. Please check your API key and try again.")
                return

    # ── G. RESULTS ────────────────────────────────────────────────────────────
    if "portfolio_data" not in st.session_state:
        # Landing state
        st.markdown(f"""
<div style="background:{CARD};border:1.5px solid {BORDER};border-radius:12px;
            padding:40px;text-align:center;margin-top:20px;">
  <div style="font-size:2.5rem;margin-bottom:12px;">📸</div>
  <div style="font-size:1rem;font-weight:700;margin-bottom:6px;">Upload your portfolio screenshot</div>
  <div style="font-size:0.82rem;color:{MUTED};max-width:400px;margin:0 auto;line-height:1.6;">
    Take a screenshot from your broker app (Zerodha, Groww, Angel One etc.)
    and upload it above. Claude AI will extract your holdings automatically.
  </div>
</div>""", unsafe_allow_html=True)
        return

    portfolio    = st.session_state["portfolio_data"]
    observations = st.session_state.get("portfolio_obs", [])
    holdings     = portfolio.get("holdings", [])
    total_val    = portfolio.get("total_value", 0)
    total_pnl    = portfolio.get("total_pnl_pct", 0)
    broker       = portfolio.get("broker", "Unknown")

    pnl_clr  = GREEN if total_pnl >= 0 else RED
    pnl_sign = "+" if total_pnl >= 0 else ""

    # Portfolio header card
    st.markdown(f"""
<div style="background:{CARD};border:1.5px solid {BORDER};border-radius:12px;
            padding:18px 22px;margin-bottom:18px;display:flex;
            align-items:center;justify-content:space-between;">
  <div>
    <div style="font-size:1.1rem;font-weight:800;">Portfolio Summary</div>
    <div style="font-size:0.78rem;color:{MUTED};margin-top:3px;">
      {broker} · {len(holdings)} holdings
    </div>
  </div>
  <div style="text-align:right;">
    <div style="font-size:1.5rem;font-weight:800;font-family:'JetBrains Mono',monospace;">
      ₹{total_val:,.0f}
    </div>
    <div style="font-size:0.95rem;font-weight:700;color:{pnl_clr};">
      {pnl_sign}{total_pnl:.1f}% overall
    </div>
  </div>
</div>""", unsafe_allow_html=True)

    # Holdings rows
    if holdings:
        total_val_safe = total_val or 1
        rows_html = ""
        for h in holdings:
            hpnl    = h.get("pnl_pct", 0) or 0
            hval    = h.get("current_value", 0) or 0
            weight  = round(hval / total_val_safe * 100, 1)
            hclr    = GREEN if hpnl >= 0 else RED
            hsign   = "+" if hpnl >= 0 else ""
            rows_html += f"""
<div style="display:flex;align-items:center;justify-content:space-between;
            padding:10px 0;border-bottom:1px solid {BORDER};">
  <div style="flex:1;">
    <div style="font-size:0.85rem;font-weight:700;">{h.get('name','—')}</div>
    <div style="display:flex;gap:6px;margin-top:3px;align-items:center;">
      <span style="font-size:0.65rem;padding:1px 7px;border-radius:20px;
                   background:{CARD2};color:{MUTED};border:1px solid {BORDER};
                   font-weight:600;">{h.get('symbol','—')}</span>
      <span style="font-size:0.65rem;color:{MUTED};">{h.get('sector','')}</span>
      <span style="font-size:0.65rem;color:{MUTED};">Weight: {weight:.1f}%</span>
    </div>
  </div>
  <div style="text-align:right;">
    <div style="font-size:0.85rem;font-weight:700;font-family:'JetBrains Mono',monospace;">
      ₹{hval:,.0f}
    </div>
    <div style="font-size:0.8rem;font-weight:700;color:{hclr};">{hsign}{hpnl:.1f}%</div>
  </div>
</div>"""

        st.markdown(f"""
<div style="background:{CARD};border:1.5px solid {BORDER};border-radius:12px;
            padding:18px 22px;margin-bottom:18px;">
  <div style="font-size:0.78rem;font-weight:700;color:{MUTED};
              text-transform:uppercase;letter-spacing:1px;margin-bottom:8px;">
    Holdings
  </div>
  {rows_html}
</div>""", unsafe_allow_html=True)

    # AI Observations
    if observations:
        type_styles = {
            "risk":     (RED,    "⚠"),
            "warning":  (YELLOW, "⚡"),
            "positive": (GREEN,  "✓"),
            "info":     (BLUE,   "ℹ"),
        }
        obs_rows = ""
        for obs in observations:
            clr, icon = type_styles.get(obs.get("type","info"), (BLUE,"ℹ"))
            obs_rows += f"""
<div style="display:flex;gap:10px;padding:10px 0;border-bottom:1px solid {BORDER};align-items:flex-start;">
  <span style="font-size:0.9rem;color:{clr};flex-shrink:0;font-weight:700;">{icon}</span>
  <div style="font-size:0.82rem;line-height:1.55;color:var(--text);">{obs.get('text','')}</div>
</div>"""

        st.markdown(f"""
<div style="background:{CARD};border:1.5px solid {BORDER};border-radius:12px;
            padding:18px 22px;margin-bottom:18px;">
  <div style="font-size:0.78rem;font-weight:700;color:{MUTED};
              text-transform:uppercase;letter-spacing:1px;margin-bottom:4px;">
    AI Observations
  </div>
  {obs_rows}
</div>""", unsafe_allow_html=True)

    # ── H. DISCLAIMER ─────────────────────────────────────────────────────────
    st.markdown(f"""
<div style="font-size:0.72rem;color:{MUTED};border-top:1px solid {BORDER};
            padding-top:12px;line-height:1.6;">
  Portfolio analysis is generated by Claude AI and is for educational purposes only.
  TradeSage is not a SEBI-registered investment advisor. Holdings extracted from
  screenshots may contain errors — verify against your broker account.
  Do not make investment decisions based solely on this analysis.
</div>""", unsafe_allow_html=True)

    # ── I. CLEAR BUTTON ───────────────────────────────────────────────────────
    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
    if st.button("Clear & Upload New"):
        for key in ["portfolio_data", "portfolio_obs", "portfolio_source"]:
            st.session_state.pop(key, None)
        st.rerun()
