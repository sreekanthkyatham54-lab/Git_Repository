# v3.2 - single nav row with logo, roadmap fix, all issues resolved
"""TradeSage — SME IPO Research Platform"""
import streamlit as st
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from data_loader import load_ipo_data

st.set_page_config(
    page_title="TradeSage | SME IPO Research",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed",
)

if "selected_ipo_id" not in st.session_state: st.session_state.selected_ipo_id = None
if "chat_histories"  not in st.session_state: st.session_state.chat_histories  = {}
if "dark_mode"       not in st.session_state: st.session_state.dark_mode       = False
if "current_page"    not in st.session_state: st.session_state.current_page    = "Dashboard"
if "api_key"         not in st.session_state:
    try:    st.session_state.api_key = st.secrets["ANTHROPIC_API_KEY"]
    except: st.session_state.api_key = os.environ.get("ANTHROPIC_API_KEY", "")

dark = st.session_state.dark_mode
if dark:
    bg="#0d1117"; card="#161b22"; card2="#21262d"; text="#f0f6fc"
    muted="#8b949e"; border="#30363d"; green="#3fb950"; red="#f85149"
    yellow="#d29922"; blue="#58a6ff"; nav_bg="#161b22"
else:
    bg="#f6f8fa"; card="#ffffff"; card2="#eef1f5"; text="#1a1a2e"
    muted="#57606a"; border="#d0d7de"; green="#1a7f37"; red="#cf222e"
    yellow="#9a6700"; blue="#0969da"; nav_bg="#ffffff"

cur = st.session_state.current_page

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Sora:wght@400;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap');
:root{{
    --bg:{bg};--card:{card};--card2:{card2};--text:{text};--muted:{muted};
    --border:{border};--green:{green};--red:{red};--yellow:{yellow};--blue:{blue};
}}
html,body,.stApp{{background-color:var(--bg)!important;font-family:'Sora',sans-serif!important;color:var(--text)!important;}}
p,span,div,label,h1,h2,h3,h4,h5,li,td,th{{color:var(--text)!important;}}
#MainMenu,footer,header{{visibility:hidden!important;display:none!important;}}
[data-testid="stSidebarNav"]{{display:none!important;}}
[data-testid="stToolbar"]{{display:none!important;}}
[data-testid="stSidebar"]{{display:none!important;}}
[data-testid="collapsedControl"]{{display:none!important;}}
.stDeployButton{{display:none!important;}}
.block-container{{padding-top:0!important;padding-bottom:2rem!important;max-width:100%!important;}}
.main .block-container{{padding-top:0!important;}}
section[data-testid="stMain"]>div:first-child{{padding-top:0!important;}}

/* ── NAV ROW: logo + buttons in one flex row ── */
div[data-testid="stHorizontalBlock"].nav-row {{
    background:{nav_bg}!important;
    border-bottom:2px solid {border}!important;
    margin:0!important;
    padding:0 1.5rem!important;
    gap:0!important;
    align-items:center!important;
    min-height:60px!important;
}}

/* Logo cell */
.nav-logo {{
    display:flex;align-items:center;gap:10px;
    padding:10px 20px 10px 0;
    border-right:1px solid {border};
    margin-right:4px;
    white-space:nowrap;
    flex-shrink:0;
}}
.nav-logo-icon{{
    width:34px;height:34px;background:{green};border-radius:8px;
    display:flex;align-items:center;justify-content:center;font-size:1rem;
    box-shadow:0 2px 6px rgba(26,127,55,0.3);flex-shrink:0;
}}
.nav-logo-name{{font-size:1.1rem;font-weight:800;letter-spacing:-0.4px;line-height:1;}}
.nav-logo-name span{{color:{green}!important;}}

/* Pills on far right */
.nav-pills{{
    margin-left:auto;display:flex;align-items:center;gap:6px;padding-left:12px;flex-shrink:0;
}}
.nav-pill{{
    padding:3px 9px;border-radius:20px;font-size:0.65rem;font-weight:600;
    letter-spacing:0.3px;white-space:nowrap;
}}
.np-blue{{background:rgba(9,105,218,0.1);color:{blue}!important;border:1px solid {blue};}}
.np-green{{background:rgba(26,127,55,0.1);color:{green}!important;border:1px solid {green};}}
.np-yellow{{background:rgba(154,103,0,0.1);color:{yellow}!important;border:1px solid {yellow};}}

/* All nav buttons default style */
div[data-testid="stHorizontalBlock"] .stButton>button {{
    background:transparent!important;
    color:{muted}!important;
    border:none!important;
    border-radius:0!important;
    border-bottom:3px solid transparent!important;
    font-size:0.84rem!important;
    font-weight:600!important;
    padding:0 14px!important;
    height:60px!important;
    white-space:nowrap!important;
    box-shadow:none!important;
    width:100%!important;
    transition:color 0.15s,border-bottom-color 0.15s!important;
}}
div[data-testid="stHorizontalBlock"] .stButton>button:hover{{
    color:{text}!important;background:rgba(0,0,0,0.03)!important;
    transform:none!important;opacity:1!important;
}}

/* ── GENERAL BUTTONS (non-nav, green) ── */
.stButton>button{{
    background:var(--green)!important;color:white!important;border:none!important;
    border-radius:8px!important;font-weight:600!important;padding:8px 20px!important;
    font-family:'Sora',sans-serif!important;
    transition:opacity 0.15s,transform 0.15s!important;
}}
.stButton>button:hover{{opacity:0.88!important;transform:translateY(-1px)!important;}}

/* ── CARDS ── */
.ipo-card{{background:var(--card);border:1.5px solid var(--border);border-radius:12px;padding:20px;margin-bottom:14px;transition:border-color 0.2s,box-shadow 0.2s;}}
.ipo-card:hover{{border-color:var(--green);box-shadow:0 4px 16px rgba(0,0,0,0.07);}}
.ipo-company{{font-size:1.05rem;font-weight:700;}}
.ipo-sector{{font-size:0.72rem;color:var(--muted)!important;text-transform:uppercase;letter-spacing:1.2px;margin:4px 0 12px;}}
.badge{{display:inline-block;padding:3px 10px;border-radius:20px;font-size:0.7rem;font-weight:600;}}
.badge-open{{background:rgba(63,185,80,0.15);color:var(--green)!important;border:1px solid var(--green);}}
.badge-upcoming{{background:rgba(88,166,255,0.15);color:var(--blue)!important;border:1px solid var(--blue);}}
.badge-bse{{background:rgba(210,153,34,0.15);color:var(--yellow)!important;border:1px solid var(--yellow);}}
.badge-nse{{background:rgba(88,166,255,0.15);color:var(--blue)!important;border:1px solid var(--blue);}}
.metric-row{{display:flex;gap:16px;margin-top:12px;flex-wrap:wrap;}}
.metric-item{{flex:1;min-width:80px;}}
.metric-label{{font-size:0.65rem;color:var(--muted)!important;text-transform:uppercase;letter-spacing:0.8px;}}
.metric-value{{font-size:0.9rem;font-weight:600;font-family:'JetBrains Mono',monospace;}}
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
.stTextInput>div>div>input{{background:var(--card)!important;border:1.5px solid var(--border)!important;color:var(--text)!important;border-radius:8px!important;}}
.stSelectbox>div>div{{background:var(--card)!important;border:1.5px solid var(--border)!important;}}
.stTabs [data-baseweb="tab-list"]{{background:var(--card2)!important;border-radius:10px!important;padding:4px!important;border:1px solid var(--border)!important;}}
.stTabs [data-baseweb="tab"]{{color:var(--muted)!important;border-radius:7px!important;font-family:'Sora',sans-serif!important;font-size:0.85rem!important;}}
.stTabs [aria-selected="true"]{{background:var(--card)!important;color:var(--green)!important;font-weight:700!important;}}
[data-testid="stMetric"]{{background:var(--card)!important;border:1.5px solid var(--border)!important;border-radius:10px!important;padding:16px!important;}}
[data-testid="stMetricValue"]{{color:var(--text)!important;font-family:'JetBrains Mono',monospace!important;}}
[data-testid="stMetricLabel"]{{color:var(--muted)!important;font-size:0.75rem!important;}}
hr{{border-color:var(--border)!important;}}
.section-header{{display:flex;align-items:center;gap:10px;margin-bottom:18px;padding-bottom:10px;border-bottom:1.5px solid var(--border);}}
.section-title{{font-size:1.05rem;font-weight:700;}}
.section-count{{background:var(--card2);color:var(--muted)!important;font-size:0.7rem;padding:2px 8px;border-radius:10px;border:1px solid var(--border);}}

/* ── COMING SOON CARDS — compact, equal height 3-col ── */
.coming-soon-section{{margin:2rem 0 0;padding:1.5rem;background:var(--card2);border-radius:16px;border:1.5px solid var(--border);}}
.coming-soon-header{{margin-bottom:1.2rem;}}
.coming-soon-label{{font-size:0.68rem;font-weight:700;color:var(--muted)!important;text-transform:uppercase;letter-spacing:2px;}}
.coming-soon-heading{{font-size:1.1rem;font-weight:800;letter-spacing:-0.3px;margin:2px 0;}}
.coming-soon-sub{{font-size:0.8rem;color:var(--muted)!important;}}
.cs-grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;}}
.cs-card{{
    background:var(--card);border:1.5px solid var(--border);border-radius:12px;
    padding:16px;position:relative;overflow:hidden;
    transition:border-color 0.2s,transform 0.2s,box-shadow 0.2s;
    display:flex;flex-direction:column;
}}
.cs-card::before{{content:'';position:absolute;top:0;left:0;right:0;height:3px;}}
.cs-card-fo::before{{background:linear-gradient(90deg,{yellow},{red});}}
.cs-card-mf::before{{background:linear-gradient(90deg,{blue},{green});}}
.cs-card-crypto::before{{background:linear-gradient(90deg,#f7931a,#9b59b6);}}
.cs-card:hover{{transform:translateY(-2px);box-shadow:0 6px 20px rgba(0,0,0,0.09);border-color:var(--green);}}
.cs-top{{display:flex;align-items:center;gap:10px;margin-bottom:8px;}}
.cs-icon{{font-size:1.4rem;}}
.cs-name{{font-size:0.95rem;font-weight:700;}}
.cs-desc{{font-size:0.78rem;color:var(--muted)!important;line-height:1.55;margin-bottom:10px;flex:1;}}
.cs-features{{font-size:0.75rem;color:var(--muted)!important;line-height:1.8;margin-bottom:12px;padding-left:0;list-style:none;}}
.cs-features li::before{{content:"→ ";color:var(--green)!important;font-weight:700;}}
.cs-pill{{display:inline-block;padding:3px 10px;border-radius:20px;font-size:0.65rem;font-weight:700;background:rgba(26,127,55,0.1);color:var(--green)!important;border:1px solid var(--green);}}
@media(max-width:768px){{.cs-grid{{grid-template-columns:1fr;}}}}
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

live_cls = "np-green" if DATA_SOURCE == "live" else "np-yellow"
live_txt = "🟢 LIVE" if DATA_SOURCE == "live" else "🟡 DEMO"
dark_icon = "☀️" if dark else "🌙"
pages     = ["Dashboard", "IPO Detail", "GMP Tracker", "Historical Data"]
nav_icons = ["🏠", "🔍", "📊", "📜"]

# ── SINGLE NAV ROW: logo HTML + st.columns for buttons ───────────────────────
# Logo injected as HTML inside a zero-height div before the columns
st.markdown(f"""
<style>
/* The first horizontal block IS the nav row */
div[data-testid="stHorizontalBlock"]:first-of-type {{
    background:{nav_bg}!important;
    border-bottom:2px solid {border}!important;
    margin:0 -1px!important;
    padding:0 1rem 0 0!important;
    gap:0!important;
    align-items:stretch!important;
    min-height:60px!important;
}}
/* First cell = logo */
div[data-testid="stHorizontalBlock"]:first-of-type > div:first-child {{
    flex:0 0 auto!important;width:auto!important;padding:0!important;
    border-right:1px solid {border}!important;
    display:flex!important;align-items:center!important;
}}
/* Nav button cells */
div[data-testid="stHorizontalBlock"]:first-of-type > div:not(:first-child):not(:last-child) {{
    flex:0 0 auto!important;width:auto!important;padding:0!important;
}}
/* Pills cell (last) */
div[data-testid="stHorizontalBlock"]:first-of-type > div:last-child {{
    flex:1 1 auto!important;padding:0!important;
    display:flex!important;align-items:center!important;justify-content:flex-end!important;
}}
/* Active page underline */
div[data-testid="stHorizontalBlock"]:first-of-type .stButton[data-active="true"]>button {{
    color:{green}!important;border-bottom:3px solid {green}!important;
    background:rgba(26,127,55,0.05)!important;
}}
</style>
""", unsafe_allow_html=True)

# Use columns: logo | D | I | G | H | theme+pills
nav_cols = st.columns([1.8, 1, 1, 1.1, 1.2, 2.5])

with nav_cols[0]:
    st.markdown(f"""
    <div class="nav-logo">
        <div class="nav-logo-icon">📈</div>
        <div class="nav-logo-name">Trade<span>Sage</span></div>
    </div>
    """, unsafe_allow_html=True)

for i, (p, icon) in enumerate(zip(pages, nav_icons)):
    with nav_cols[i + 1]:
        active_css = f"""
        <style>
        div[data-testid="stHorizontalBlock"]:first-of-type > div:nth-child({i+2}) .stButton>button {{
            color:{green}!important;border-bottom:3px solid {green}!important;
            background:rgba(26,127,55,0.05)!important;
        }}
        </style>""" if p == cur else ""
        if active_css: st.markdown(active_css, unsafe_allow_html=True)
        if st.button(f"{icon} {p}", key=f"nav_{p}"):
            st.session_state.current_page = p
            st.rerun()

with nav_cols[5]:
    st.markdown(f"""
    <div class="nav-pills">
        <span class="nav-pill np-blue">BSE SME</span>
        <span class="nav-pill np-blue">NSE Emerge</span>
        <span class="nav-pill {live_cls}">{live_txt}</span>
    </div>
    """, unsafe_allow_html=True)
    # dark mode toggle sits in this cell too
    if st.button(dark_icon, key="theme_btn"):
        st.session_state.dark_mode = not st.session_state.dark_mode
        st.rerun()

# ── PAGE CONTENT ──────────────────────────────────────────────────────────────
st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
cur = st.session_state.current_page
if   "Dashboard"  in cur:
    from pages.dashboard   import render; render(ACTIVE_IPOS, UPCOMING_IPOS)
elif "IPO Detail" in cur:
    from pages.ipo_detail  import render; render(ACTIVE_IPOS + UPCOMING_IPOS)
elif "GMP"        in cur:
    from pages.gmp_tracker import render; render(ACTIVE_IPOS + UPCOMING_IPOS, GMP_HISTORY)
elif "Historical" in cur:
    from pages.historical  import render; render(HISTORICAL_IPOS)
