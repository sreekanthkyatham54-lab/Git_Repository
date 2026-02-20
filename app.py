# v2.7 - fixed blank top space, branding header, no duplicate title
"""TradeSage — SME IPO Research Platform"""
import streamlit as st
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from data_loader import load_ipo_data

st.set_page_config(
    page_title="TradeSage | SME IPO Research",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── SESSION STATE ──────────────────────────────────────────────────────────────
if "selected_ipo_id" not in st.session_state: st.session_state.selected_ipo_id = None
if "chat_histories"  not in st.session_state: st.session_state.chat_histories  = {}
if "dark_mode"       not in st.session_state: st.session_state.dark_mode       = False
if "current_page"    not in st.session_state: st.session_state.current_page    = "🏠 Dashboard"
if "api_key"         not in st.session_state:
    try:    st.session_state.api_key = st.secrets["ANTHROPIC_API_KEY"]
    except: st.session_state.api_key = os.environ.get("ANTHROPIC_API_KEY", "")

dark = st.session_state.dark_mode
if dark:
    bg="#0d1117"; card="#161b22"; card2="#21262d"; text="#f0f6fc"
    muted="#8b949e"; border="#30363d"; green="#3fb950"; red="#f85149"
    yellow="#d29922"; blue="#58a6ff"; sidebar="#161b22"; tog="#238636"
    hero_bg="linear-gradient(135deg,#0d1117 0%,#161b22 50%,#0d2818 100%)"
else:
    bg="#f6f8fa"; card="#ffffff"; card2="#eef1f5"; text="#1a1a2e"
    muted="#57606a"; border="#d0d7de"; green="#1a7f37"; red="#cf222e"
    yellow="#9a6700"; blue="#0969da"; sidebar="#ffffff"; tog="#1a7f37"
    hero_bg="linear-gradient(135deg,#f0fdf4 0%,#dcfce7 40%,#f0f9ff 100%)"

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Sora:wght@400;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap');
:root{{
    --bg:{bg};--card:{card};--card2:{card2};--text:{text};--muted:{muted};
    --border:{border};--green:{green};--red:{red};--yellow:{yellow};--blue:{blue};
}}
html,body,.stApp{{background-color:var(--bg)!important;font-family:'Sora',sans-serif!important;color:var(--text)!important;}}
p,span,div,label,h1,h2,h3,h4,h5,li,td,th{{color:var(--text)!important;}}
#MainMenu,footer,header{{visibility:hidden;}}
[data-testid="stSidebarNav"]{{display:none!important;}}
[data-testid="stToolbar"]{{display:none!important;}}
.stDeployButton{{display:none;}}

/* ── REMOVE STREAMLIT DEFAULT TOP PADDING ── */
.stApp > div:first-child {{padding-top:0!important;}}
.block-container {{padding-top:0!important;margin-top:0!important;}}
[data-testid="stAppViewContainer"] > section > div:first-child {{padding-top:0!important;}}
.main .block-container {{padding-top:0!important;padding-bottom:1rem!important;}}

/* ── TOP BRANDING BAR ── */
.tradesage-header{{
    background:{hero_bg};
    border-bottom:2px solid var(--border);
    padding:18px 32px 16px;
    margin:0 -1rem 1.5rem -1rem;
    display:flex;
    align-items:center;
    justify-content:space-between;
    flex-wrap:wrap;
    gap:12px;
}}
.tradesage-logo{{
    display:flex;
    align-items:center;
    gap:12px;
}}
.tradesage-logo-icon{{
    width:42px;height:42px;
    background:var(--green);
    border-radius:10px;
    display:flex;align-items:center;justify-content:center;
    font-size:1.3rem;
    box-shadow:0 4px 12px rgba(26,127,55,0.3);
}}
.tradesage-logo-text{{
    font-size:1.5rem;
    font-weight:800;
    color:var(--text)!important;
    letter-spacing:-0.5px;
}}
.tradesage-logo-text span{{color:var(--green)!important;}}
.tradesage-tagline{{
    font-size:0.72rem;
    color:var(--muted)!important;
    letter-spacing:2px;
    text-transform:uppercase;
    margin-top:2px;
}}
.tradesage-badges{{
    display:flex;gap:8px;flex-wrap:wrap;align-items:center;
}}
.ts-badge{{
    padding:4px 12px;border-radius:20px;font-size:0.7rem;font-weight:600;
    letter-spacing:0.5px;
}}
.ts-badge-green{{background:rgba(26,127,55,0.12);color:{green}!important;border:1px solid {green};}}
.ts-badge-blue{{background:rgba(9,105,218,0.12);color:{blue}!important;border:1px solid {blue};}}
.ts-badge-yellow{{background:rgba(154,103,0,0.12);color:{yellow}!important;border:1px solid {yellow};}}

/* ── SIDEBAR ── */
[data-testid="stSidebar"]{{
    background:{sidebar}!important;
    border-right:2px solid var(--border)!important;
    min-width:260px!important;max-width:260px!important;
}}
[data-testid="stSidebar"] *{{color:var(--text)!important;font-family:'Sora',sans-serif!important;}}

/* ── SIDEBAR TOGGLE — always visible, fixed position ── */
[data-testid="collapsedControl"]{{
    background:{tog}!important;
    border-radius:0 10px 10px 0!important;
    color:white!important;opacity:1!important;
    visibility:visible!important;display:flex!important;
    width:28px!important;min-width:28px!important;height:56px!important;
    align-items:center!important;justify-content:center!important;
    border:none!important;cursor:pointer!important;
    position:fixed!important;top:50vh!important;
    transform:translateY(-50%)!important;
    z-index:999999!important;
    left:0px!important;
    box-shadow:3px 0 10px rgba(0,0,0,0.2)!important;
    transition:width 0.15s ease!important;
}}
[data-testid="collapsedControl"]:hover{{width:36px!important;background:{green}!important;}}
[data-testid="collapsedControl"] svg{{fill:white!important;color:white!important;width:14px!important;height:14px!important;}}
[data-testid="collapsedControl"] button{{background:transparent!important;border:none!important;color:white!important;width:100%!important;height:100%!important;cursor:pointer!important;padding:0!important;}}

/* ── CARDS ── */
.ipo-card{{background:var(--card);border:1.5px solid var(--border);border-radius:12px;padding:20px;margin-bottom:14px;transition:border-color 0.2s,box-shadow 0.2s;}}
.ipo-card:hover{{border-color:var(--green);box-shadow:0 4px 16px rgba(0,0,0,0.08);}}
.ipo-company{{font-size:1.05rem;font-weight:700;color:var(--text)!important;}}
.ipo-sector{{font-size:0.72rem;color:var(--muted)!important;text-transform:uppercase;letter-spacing:1.2px;margin:4px 0 12px;}}
.badge{{display:inline-block;padding:3px 10px;border-radius:20px;font-size:0.7rem;font-weight:600;}}
.badge-open{{background:rgba(63,185,80,0.15);color:var(--green)!important;border:1px solid var(--green);}}
.badge-upcoming{{background:rgba(88,166,255,0.15);color:var(--blue)!important;border:1px solid var(--blue);}}
.badge-bse{{background:rgba(210,153,34,0.15);color:var(--yellow)!important;border:1px solid var(--yellow);}}
.badge-nse{{background:rgba(88,166,255,0.15);color:var(--blue)!important;border:1px solid var(--blue);}}
.metric-row{{display:flex;gap:16px;margin-top:12px;flex-wrap:wrap;}}
.metric-item{{flex:1;min-width:80px;}}
.metric-label{{font-size:0.65rem;color:var(--muted)!important;text-transform:uppercase;letter-spacing:0.8px;}}
.metric-value{{font-size:0.9rem;font-weight:600;font-family:'JetBrains Mono',monospace;color:var(--text)!important;}}
.metric-value.positive{{color:var(--green)!important;}}
.metric-value.negative{{color:var(--red)!important;}}
.metric-value.neutral{{color:var(--yellow)!important;}}
.rec-subscribe{{background:rgba(63,185,80,0.12);color:var(--green)!important;border:1.5px solid var(--green);padding:3px 12px;border-radius:20px;font-size:0.75rem;font-weight:700;}}
.rec-avoid{{background:rgba(248,81,73,0.12);color:var(--red)!important;border:1.5px solid var(--red);padding:3px 12px;border-radius:20px;font-size:0.75rem;font-weight:700;}}
.rec-neutral{{background:rgba(210,153,34,0.12);color:var(--yellow)!important;border:1.5px solid var(--yellow);padding:3px 12px;border-radius:20px;font-size:0.75rem;font-weight:700;}}
.alert-green{{background:rgba(63,185,80,0.08);border-left:3px solid var(--green);padding:12px 16px;border-radius:0 8px 8px 0;margin:8px 0;}}
.alert-red{{background:rgba(248,81,73,0.08);border-left:3px solid var(--red);padding:12px 16px;border-radius:0 8px 8px 0;margin:8px 0;}}
.alert-yellow{{background:rgba(210,153,34,0.08);border-left:3px solid var(--yellow);padding:12px 16px;border-radius:0 8px 8px 0;margin:8px 0;}}
.chat-message-user{{background:rgba(88,166,255,0.08);border:1px solid rgba(88,166,255,0.2);border-radius:12px 12px 2px 12px;padding:12px 16px;margin:8px 0;font-size:0.9rem;}}
.chat-message-ai{{background:var(--card);border:1px solid var(--border);border-radius:12px 12px 12px 2px;padding:12px 16px;margin:8px 0;font-size:0.9rem;line-height:1.6;}}
.stButton>button{{background:var(--green)!important;color:white!important;border:none!important;border-radius:8px!important;font-weight:600!important;padding:8px 20px!important;font-family:'Sora',sans-serif!important;}}
.stButton>button:hover{{opacity:0.88!important;transform:translateY(-1px);}}
.stTextInput>div>div>input{{background:var(--card)!important;border:1.5px solid var(--border)!important;color:var(--text)!important;border-radius:8px!important;}}
.stSelectbox>div>div{{background:var(--card)!important;border:1.5px solid var(--border)!important;color:var(--text)!important;}}
.stTabs [data-baseweb="tab-list"]{{background:var(--card2)!important;border-radius:10px!important;padding:4px!important;border:1px solid var(--border)!important;}}
.stTabs [data-baseweb="tab"]{{color:var(--muted)!important;border-radius:7px!important;font-family:'Sora',sans-serif!important;font-size:0.85rem!important;}}
.stTabs [aria-selected="true"]{{background:var(--card)!important;color:var(--green)!important;font-weight:700!important;}}
[data-testid="stMetric"]{{background:var(--card)!important;border:1.5px solid var(--border)!important;border-radius:10px!important;padding:16px!important;}}
[data-testid="stMetricValue"]{{color:var(--text)!important;font-family:'JetBrains Mono',monospace!important;}}
[data-testid="stMetricLabel"]{{color:var(--muted)!important;font-size:0.75rem!important;}}
hr{{border-color:var(--border)!important;}}
.section-header{{display:flex;align-items:center;gap:10px;margin-bottom:18px;padding-bottom:10px;border-bottom:1.5px solid var(--border);}}
.section-title{{font-size:1.05rem;font-weight:700;color:var(--text)!important;}}
.section-count{{background:var(--card2);color:var(--muted)!important;font-size:0.7rem;padding:2px 8px;border-radius:10px;border:1px solid var(--border);}}
</style>
""", unsafe_allow_html=True)

# ── LOAD DATA ─────────────────────────────────────────────────────────────────
data            = load_ipo_data()
ACTIVE_IPOS     = data["active_ipos"]
UPCOMING_IPOS   = data["upcoming_ipos"]
HISTORICAL_IPOS = data["historical_ipos"]
GMP_HISTORY     = data.get("gmp_history", {})
DATA_SOURCE     = data.get("source", "seed")
SCRAPED_AT      = data.get("scraped_at")

# ── TOP BRANDING BAR ──────────────────────────────────────────────────────────
live_badge = f'<span class="ts-badge ts-badge-green">🟢 LIVE DATA</span>' if DATA_SOURCE == "live" else f'<span class="ts-badge ts-badge-yellow">🟡 DEMO DATA</span>'
st.markdown(f"""
<div class="tradesage-header">
    <div class="tradesage-logo">
        <div class="tradesage-logo-icon">📈</div>
        <div>
            <div class="tradesage-logo-text">Trade<span>Sage</span></div>
            <div class="tradesage-tagline">AI-Powered SME IPO Research · India</div>
        </div>
    </div>
    <div class="tradesage-badges">
        <span class="ts-badge ts-badge-blue">BSE SME</span>
        <span class="ts-badge ts-badge-blue">NSE Emerge</span>
        <span class="ts-badge ts-badge-yellow">SEBI Filings</span>
        {live_badge}
    </div>
</div>
""", unsafe_allow_html=True)

# ── SIDEBAR ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(f"""
    <div style='padding:12px 0 8px;display:flex;align-items:center;gap:10px;'>
        <div style='width:32px;height:32px;background:{green};border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:1rem;'>📈</div>
        <div>
            <div style='font-size:1rem;font-weight:700;'>TradeSage</div>
            <div style='font-size:0.65rem;color:{muted};'>SME IPO · BSE · NSE Emerge</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    theme_label = "☀️ Switch to Light" if dark else "🌙 Switch to Dark"
    if st.button(theme_label, key="theme_toggle"):
        st.session_state.dark_mode = not st.session_state.dark_mode
        st.rerun()

    st.markdown("---")
    pages = ["🏠 Dashboard", "🔍 IPO Detail", "📊 GMP Tracker", "📜 Historical Data"]
    current_idx = pages.index(st.session_state.current_page) if st.session_state.current_page in pages else 0
    page = st.radio("Navigate", pages, index=current_idx, label_visibility="collapsed")
    st.session_state.current_page = page

    st.markdown("---")
    st.markdown(f'<div style="font-size:0.72rem;color:{muted};line-height:1.9;"><strong style="color:{text};">Data Sources</strong><br>BSE SME · NSE Emerge · SEBI<br>ipowatch.in · InvestorGain<br><br><strong style="color:{text};">Disclaimer</strong><br>Research only. Not financial advice.</div>', unsafe_allow_html=True)
    st.markdown("---")
    st.markdown(f'<div style="font-size:0.72rem;color:{blue};line-height:1.9;">🔮 Coming Soon<br><span style="color:{muted};">• MF Screener<br>• F&O Copilot<br>• Crypto Tracker</span></div>', unsafe_allow_html=True)
    st.markdown("---")
    if DATA_SOURCE == "live":
        ts = SCRAPED_AT[:16].replace("T"," ") if SCRAPED_AT else "recently"
        st.markdown(f'<div style="background:rgba(26,127,55,0.1);border:1px solid {green};border-radius:8px;padding:8px 10px;font-size:0.7rem;">🟢 <strong style="color:{green};">LIVE DATA</strong><br><span style="color:{muted};">Updated: {ts}</span></div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div style="background:rgba(154,103,0,0.1);border:1px solid {yellow};border-radius:8px;padding:8px 10px;font-size:0.7rem;">🟡 <strong style="color:{yellow};">DEMO DATA</strong><br><span style="color:{muted};">Run scraper for live data</span></div>', unsafe_allow_html=True)

# ── PAGE ROUTING ──────────────────────────────────────────────────────────────
current = st.session_state.current_page
if   "Dashboard" in current:
    from pages.dashboard  import render; render(ACTIVE_IPOS, UPCOMING_IPOS)
elif "IPO Detail" in current:
    from pages.ipo_detail import render; render(ACTIVE_IPOS + UPCOMING_IPOS)
elif "GMP Tracker" in current:
    from pages.gmp_tracker import render; render(ACTIVE_IPOS + UPCOMING_IPOS, GMP_HISTORY)
elif "Historical" in current:
    from pages.historical  import render; render(HISTORICAL_IPOS)
