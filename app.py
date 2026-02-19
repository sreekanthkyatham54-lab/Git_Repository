"""
SME IPO Research Platform — Main App
Run with: streamlit run app.py
"""
import streamlit as st
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from data_loader import load_ipo_data

st.set_page_config(
    page_title="SME IPO Research | India",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Session state — must be before anything reads it
if "api_key" not in st.session_state:
    st.session_state.api_key = ""
if "selected_ipo_id" not in st.session_state:
    st.session_state.selected_ipo_id = None
if "chat_histories" not in st.session_state:
    st.session_state.chat_histories = {}
if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = False   # Light by default
if "current_page" not in st.session_state:
    st.session_state.current_page = "🏠 Dashboard"

dark = st.session_state.dark_mode

if dark:
    bg_primary = "#0d1117"; bg_card = "#161b22"; bg_card2 = "#21262d"
    text_primary = "#f0f6fc"; text_muted = "#8b949e"; border = "#30363d"
    accent_green = "#3fb950"; accent_red = "#f85149"
    accent_yellow = "#d29922"; accent_blue = "#58a6ff"
else:
    bg_primary = "#f6f8fa"; bg_card = "#ffffff"; bg_card2 = "#eef1f5"
    text_primary = "#1a1a2e"; text_muted = "#57606a"; border = "#d0d7de"
    accent_green = "#1a7f37"; accent_red = "#cf222e"
    accent_yellow = "#9a6700"; accent_blue = "#0969da"


st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;600&display=swap');
:root {{
    --bg-primary:{bg_primary};--bg-card:{bg_card};--bg-card2:{bg_card2};
    --text-primary:{text_primary};--text-muted:{text_muted};--border:{border};
    --green:{accent_green};--red:{accent_red};--yellow:{accent_yellow};--blue:{accent_blue};
}}
html,body,.stApp{{background-color:var(--bg-primary)!important;font-family:'Inter',sans-serif!important;color:var(--text-primary)!important;}}
p,span,div,label,h1,h2,h3,h4,h5,li,td,th{{color:var(--text-primary)!important;}}
#MainMenu,footer{{visibility:hidden;}}
.stDeployButton{{display:none;}}
[data-testid="stSidebar"]{{background:var(--bg-card)!important;border-right:2px solid var(--border)!important;}}
[data-testid="stSidebar"] *{{color:var(--text-primary)!important;}}
[data-testid="collapsedControl"]{{background:var(--green)!important;border-radius:0 8px 8px 0!important;opacity:1!important;visibility:visible!important;display:flex!important;color:white!important;}}
.ipo-card{{background:var(--bg-card);border:1.5px solid var(--border);border-radius:12px;padding:20px;margin-bottom:14px;}}
.ipo-card:hover{{border-color:var(--green);box-shadow:0 2px 12px rgba(0,0,0,0.08);}}
.ipo-company{{font-size:1.05rem;font-weight:700;color:var(--text-primary)!important;}}
.ipo-sector{{font-size:0.75rem;color:var(--text-muted)!important;text-transform:uppercase;letter-spacing:1px;margin:4px 0 12px;}}
.badge{{display:inline-block;padding:3px 10px;border-radius:20px;font-size:0.72rem;font-weight:600;}}
.badge-open{{background:rgba(63,185,80,0.15);color:var(--green)!important;border:1px solid var(--green);}}
.badge-upcoming{{background:rgba(88,166,255,0.15);color:var(--blue)!important;border:1px solid var(--blue);}}
.badge-bse{{background:rgba(210,153,34,0.15);color:var(--yellow)!important;border:1px solid var(--yellow);}}
.badge-nse{{background:rgba(88,166,255,0.15);color:var(--blue)!important;border:1px solid var(--blue);}}
.metric-row{{display:flex;gap:16px;margin-top:12px;flex-wrap:wrap;}}
.metric-item{{flex:1;min-width:80px;}}
.metric-label{{font-size:0.68rem;color:var(--text-muted)!important;text-transform:uppercase;letter-spacing:0.8px;}}
.metric-value{{font-size:0.92rem;font-weight:600;font-family:'JetBrains Mono',monospace;color:var(--text-primary)!important;}}
.metric-value.positive{{color:var(--green)!important;}}
.metric-value.negative{{color:var(--red)!important;}}
.metric-value.neutral{{color:var(--yellow)!important;}}
.rec-subscribe{{background:rgba(63,185,80,0.12);color:var(--green)!important;border:1.5px solid var(--green);padding:3px 12px;border-radius:20px;font-size:0.78rem;font-weight:700;}}
.rec-avoid{{background:rgba(248,81,73,0.12);color:var(--red)!important;border:1.5px solid var(--red);padding:3px 12px;border-radius:20px;font-size:0.78rem;font-weight:700;}}
.rec-neutral{{background:rgba(210,153,34,0.12);color:var(--yellow)!important;border:1.5px solid var(--yellow);padding:3px 12px;border-radius:20px;font-size:0.78rem;font-weight:700;}}
.alert-green{{background:rgba(63,185,80,0.08);border-left:3px solid var(--green);padding:12px 16px;border-radius:0 8px 8px 0;margin:8px 0;}}
.alert-red{{background:rgba(248,81,73,0.08);border-left:3px solid var(--red);padding:12px 16px;border-radius:0 8px 8px 0;margin:8px 0;}}
.alert-yellow{{background:rgba(210,153,34,0.08);border-left:3px solid var(--yellow);padding:12px 16px;border-radius:0 8px 8px 0;margin:8px 0;}}
.chat-message-user{{background:rgba(88,166,255,0.08);border:1px solid rgba(88,166,255,0.2);border-radius:12px 12px 2px 12px;padding:12px 16px;margin:8px 0;font-size:0.9rem;}}
.chat-message-ai{{background:var(--bg-card);border:1px solid var(--border);border-radius:12px 12px 12px 2px;padding:12px 16px;margin:8px 0;font-size:0.9rem;line-height:1.6;}}
.stButton>button{{background:var(--green)!important;color:white!important;border:none!important;border-radius:8px!important;font-weight:600!important;padding:8px 20px!important;}}
.stButton>button:hover{{opacity:0.88!important;}}
.stTextInput>div>div>input{{background:var(--bg-card)!important;border:1.5px solid var(--border)!important;color:var(--text-primary)!important;border-radius:8px!important;}}
.stSelectbox>div>div{{background:var(--bg-card)!important;border:1.5px solid var(--border)!important;color:var(--text-primary)!important;}}
.stTabs [data-baseweb="tab-list"]{{background:var(--bg-card2)!important;border-radius:10px!important;padding:4px!important;border:1px solid var(--border)!important;}}
.stTabs [data-baseweb="tab"]{{color:var(--text-muted)!important;border-radius:7px!important;}}
.stTabs [aria-selected="true"]{{background:var(--bg-card)!important;color:var(--green)!important;font-weight:600!important;}}
[data-testid="stMetric"]{{background:var(--bg-card)!important;border:1.5px solid var(--border)!important;border-radius:10px!important;padding:16px!important;}}
[data-testid="stMetricValue"]{{color:var(--text-primary)!important;font-family:'JetBrains Mono',monospace!important;}}
[data-testid="stMetricLabel"]{{color:var(--text-muted)!important;}}
hr{{border-color:var(--border)!important;}}
.section-header{{display:flex;align-items:center;gap:10px;margin-bottom:18px;padding-bottom:10px;border-bottom:1.5px solid var(--border);}}
.section-title{{font-size:1.05rem;font-weight:700;color:var(--text-primary)!important;}}
.section-count{{background:var(--bg-card2);color:var(--text-muted)!important;font-size:0.72rem;padding:2px 8px;border-radius:10px;border:1px solid var(--border);}}
</style>
""", unsafe_allow_html=True)

# ── SIDEBAR ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(f"<div style='padding:8px 0 16px'><div style='font-size:1.2rem;font-weight:700;'>📈 IPO Research</div><div style='font-size:0.72rem;color:{text_muted};margin-top:2px;'>SME · BSE · NSE Emerge</div></div>", unsafe_allow_html=True)

    theme_label = "☀️ Switch to Light" if dark else "🌙 Switch to Dark"
    if st.button(theme_label, key="theme_toggle"):
        st.session_state.dark_mode = not st.session_state.dark_mode
        st.rerun()

    st.markdown("---")
    api_key = st.text_input("🔑 Claude API Key", type="password", value=st.session_state.api_key, placeholder="sk-ant-...", help="Get at console.anthropic.com")
    if api_key:
        st.session_state.api_key = api_key
        st.markdown(f'<div style="color:{accent_green};font-size:0.78rem;margin-top:-6px;">✓ API key saved</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div style="color:{text_muted};font-size:0.78rem;margin-top:-6px;">AI features need API key</div>', unsafe_allow_html=True)

    st.markdown("---")
    pages = ["🏠 Dashboard", "🔍 IPO Detail", "📊 GMP Tracker", "📜 Historical Data"]
    current_idx = pages.index(st.session_state.current_page) if st.session_state.current_page in pages else 0
    page = st.radio("Navigate", pages, index=current_idx, label_visibility="collapsed")
    st.session_state.current_page = page

    st.markdown("---")
    st.markdown(f'<div style="font-size:0.72rem;color:{text_muted};line-height:1.8;"><strong style="color:{text_primary};">Data Sources</strong><br>BSE SME · NSE Emerge · SEBI<br>ipowatch.in · InvestorGain<br><br><strong style="color:{text_primary};">Disclaimer</strong><br>Research only, not financial advice.</div>', unsafe_allow_html=True)
    st.markdown("---")
    st.markdown(f'<div style="font-size:0.72rem;color:{accent_blue};line-height:1.8;">🔮 Coming Soon<br><span style="color:{text_muted};">• MF Screener<br>• F&O Copilot<br>• Crypto Tracker</span></div>', unsafe_allow_html=True)

# ── LOAD DATA ─────────────────────────────────────────────────────────────────
data = load_ipo_data()
ACTIVE_IPOS     = data["active_ipos"]
UPCOMING_IPOS   = data["upcoming_ipos"]
HISTORICAL_IPOS = data["historical_ipos"]
GMP_HISTORY     = data.get("gmp_history", {})
DATA_SOURCE     = data.get("source", "seed")
SCRAPED_AT      = data.get("scraped_at")

with st.sidebar:
    st.markdown("---")
    if DATA_SOURCE == "live":
        ts = SCRAPED_AT[:16] if SCRAPED_AT else "recently"
        st.markdown(f'<div style="background:rgba(26,127,55,0.1);border:1px solid {accent_green};border-radius:8px;padding:8px 10px;font-size:0.72rem;">🟢 <strong style="color:{accent_green};">LIVE DATA</strong><br><span style="color:{text_muted};">Updated: {ts}</span></div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div style="background:rgba(154,103,0,0.1);border:1px solid {accent_yellow};border-radius:8px;padding:8px 10px;font-size:0.72rem;">🟡 <strong style="color:{accent_yellow};">DEMO DATA</strong><br><span style="color:{text_muted};">Run scraper.py for live IPOs</span></div>', unsafe_allow_html=True)

# ── PAGE ROUTING ──────────────────────────────────────────────────────────────
current = st.session_state.current_page

if "Dashboard" in current:
    from pages.dashboard import render
    render(ACTIVE_IPOS, UPCOMING_IPOS)

elif "IPO Detail" in current:
    from pages.ipo_detail import render
    render(ACTIVE_IPOS + UPCOMING_IPOS)

elif "GMP Tracker" in current:
    from pages.gmp_tracker import render
    render(ACTIVE_IPOS + UPCOMING_IPOS, GMP_HISTORY)

elif "Historical" in current:
    from pages.historical import render
    render(HISTORICAL_IPOS)
