# v3.5 - simple working nav, no alignment hacks
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
    yellow="#d29922"; blue="#58a6ff"; nav_bg="#161b22"; btn="#2ea043"
else:
    bg="#f6f8fa"; card="#ffffff"; card2="#eef1f5"; text="#1a1a2e"
    muted="#57606a"; border="#d0d7de"; green="#1a7f37"; red="#cf222e"
    yellow="#9a6700"; blue="#0969da"; nav_bg="#ffffff"; btn="#2da44e"

cur = st.session_state.current_page
pages = ["Dashboard", "IPO Detail", "GMP Tracker", "Historical Data"]
icons = {"Dashboard":"🏠","IPO Detail":"🔍","GMP Tracker":"📊","Historical Data":"📜"}

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Sora:wght@400;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap');
:root{{--bg:{bg};--card:{card};--card2:{card2};--text:{text};--muted:{muted};--border:{border};--green:{green};--red:{red};--yellow:{yellow};--blue:{blue};--btn:{btn};}}
html,body,.stApp{{background:var(--bg)!important;font-family:'Sora',sans-serif!important;color:var(--text)!important;}}
p,span,div,label,h1,h2,h3,h4,h5,li,td,th{{color:var(--text)!important;}}
#MainMenu,footer,header,[data-testid="stSidebarNav"],[data-testid="stToolbar"],[data-testid="stSidebar"],[data-testid="collapsedControl"],.stDeployButton{{display:none!important;}}
.block-container{{padding:0 2rem 2rem!important;max-width:100%!important;}}
section[data-testid="stMain"]>div:first-child{{padding-top:0!important;}}

/* ── NAV ── */
.ts-nav{{background:{nav_bg};border-bottom:2px solid {border};margin:0 -2rem;padding:0 2rem;display:flex;align-items:center;height:60px;gap:0;}}
.ts-logo{{display:flex;align-items:center;gap:10px;padding-right:20px;border-right:1px solid {border};margin-right:4px;flex-shrink:0;}}
.ts-logo-icon{{width:34px;height:34px;background:{green};border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:1rem;box-shadow:0 2px 6px rgba(26,127,55,0.3);}}
.ts-logo-name{{font-size:1.1rem;font-weight:800;letter-spacing:-0.4px;}}
.ts-logo-name b{{color:{green}!important;}}
.ts-nav-links{{display:flex;align-items:stretch;flex:1;}}
.ts-nav-link{{
    display:flex;align-items:center;padding:0 16px;height:60px;
    font-size:0.85rem;font-weight:600;color:{muted}!important;
    cursor:pointer;border-bottom:3px solid transparent;
    text-decoration:none;white-space:nowrap;
    transition:color 0.15s,border-bottom-color 0.15s;
}}
.ts-nav-link:hover{{color:{text}!important;background:rgba(0,0,0,0.03);}}
.ts-nav-link.active{{color:{green}!important;border-bottom:3px solid {green};background:rgba(26,127,55,0.05);}}
.ts-pills{{margin-left:auto;display:flex;align-items:center;gap:6px;padding-left:12px;flex-shrink:0;}}
.ts-pill{{padding:3px 9px;border-radius:20px;font-size:0.65rem;font-weight:600;letter-spacing:0.3px;white-space:nowrap;}}
.np-blue{{background:rgba(9,105,218,0.1);color:{blue}!important;border:1px solid {blue};}}
.np-green{{background:rgba(26,127,55,0.1);color:{green}!important;border:1px solid {green};}}
.np-yellow{{background:rgba(154,103,0,0.1);color:{yellow}!important;border:1px solid {yellow};}}

/* ── BUTTONS ── */
.stButton>button{{background:var(--btn)!important;color:white!important;border:none!important;border-radius:8px!important;font-weight:600!important;padding:8px 20px!important;font-family:'Sora',sans-serif!important;transition:opacity 0.15s,transform 0.15s!important;}}
.stButton>button:hover{{opacity:0.88!important;transform:translateY(-1px)!important;}}

/* ── INPUTS / WIDGETS ── */
.stTextInput>div>div>input{{background:var(--card)!important;border:1.5px solid var(--border)!important;color:var(--text)!important;border-radius:8px!important;}}
.stSelectbox>div>div{{background:var(--card)!important;border:1.5px solid var(--border)!important;}}
.stTabs [data-baseweb="tab-list"]{{background:var(--card2)!important;border-radius:10px!important;padding:4px!important;border:1px solid var(--border)!important;}}
.stTabs [data-baseweb="tab"]{{color:var(--muted)!important;border-radius:7px!important;font-family:'Sora',sans-serif!important;font-size:0.85rem!important;}}
.stTabs [aria-selected="true"]{{background:var(--card)!important;color:var(--green)!important;font-weight:700!important;}}
[data-testid="stMetric"]{{background:var(--card)!important;border:1.5px solid var(--border)!important;border-radius:10px!important;padding:16px!important;}}
[data-testid="stMetricValue"]{{color:var(--text)!important;font-family:'JetBrains Mono',monospace!important;}}
[data-testid="stMetricLabel"]{{color:var(--muted)!important;font-size:0.75rem!important;}}
hr{{border-color:var(--border)!important;}}
.stChat .stChatMessage{{background:var(--card)!important;border:1px solid var(--border)!important;}}

/* ── IPO CARDS ── */
.ipo-card{{background:var(--card);border:1.5px solid var(--border);border-radius:12px;padding:20px;margin-bottom:14px;display:flex;justify-content:space-between;align-items:flex-start;gap:16px;transition:border-color 0.2s,box-shadow 0.2s;}}
.ipo-card:hover{{border-color:var(--green);box-shadow:0 4px 16px rgba(0,0,0,0.07);}}
.ipo-card-body{{flex:1;min-width:0;}}
.ipo-card-action{{flex-shrink:0;display:flex;align-items:center;padding-top:4px;}}
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
.ipo-summary{{margin-top:12px;font-size:0.83rem;color:var(--muted)!important;line-height:1.5;}}
.analyze-btn{{
    display:inline-flex;align-items:center;gap:6px;
    background:{btn};color:white!important;
    border:none;border-radius:8px;padding:10px 20px;
    font-size:0.88rem;font-weight:600;font-family:'Sora',sans-serif;
    cursor:pointer;white-space:nowrap;
    transition:opacity 0.15s,transform 0.15s;text-decoration:none;
}}
.analyze-btn:hover{{opacity:0.88;transform:translateY(-1px);}}
.alert-green{{background:rgba(63,185,80,0.08);border-left:3px solid var(--green);padding:12px 16px;border-radius:0 8px 8px 0;margin:8px 0;}}
.alert-red{{background:rgba(248,81,73,0.08);border-left:3px solid var(--red);padding:12px 16px;border-radius:0 8px 8px 0;margin:8px 0;}}
.alert-yellow{{background:rgba(210,153,34,0.08);border-left:3px solid var(--yellow);padding:12px 16px;border-radius:0 8px 8px 0;margin:8px 0;}}
.chat-message-user{{background:rgba(88,166,255,0.08);border:1px solid rgba(88,166,255,0.2);border-radius:12px 12px 2px 12px;padding:12px 16px;margin:8px 0;font-size:0.9rem;}}
.chat-message-ai{{background:var(--card);border:1px solid var(--border);border-radius:12px 12px 12px 2px;padding:12px 16px;margin:8px 0;font-size:0.9rem;line-height:1.6;}}
.section-header{{display:flex;align-items:center;gap:10px;margin-bottom:18px;padding-bottom:10px;border-bottom:1.5px solid var(--border);}}
.section-title{{font-size:1.05rem;font-weight:700;}}
.section-count{{background:var(--card2);color:var(--muted)!important;font-size:0.7rem;padding:2px 8px;border-radius:10px;border:1px solid var(--border);}}

/* ── COMING SOON ── */
.coming-soon-section{{margin:2rem 0 0;padding:1.5rem;background:var(--card2);border-radius:16px;border:1.5px solid var(--border);}}
.coming-soon-label{{font-size:0.68rem;font-weight:700;color:var(--muted)!important;text-transform:uppercase;letter-spacing:2px;}}
.coming-soon-heading{{font-size:1.1rem;font-weight:800;letter-spacing:-0.3px;margin:2px 0;}}
.coming-soon-sub{{font-size:0.8rem;color:var(--muted)!important;margin-bottom:1.2rem;}}
.cs-grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;}}
.cs-card{{background:var(--card);border:1.5px solid var(--border);border-radius:12px;padding:16px;position:relative;overflow:hidden;transition:border-color 0.2s,transform 0.2s,box-shadow 0.2s;display:flex;flex-direction:column;}}
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

live_cls = "np-green" if DATA_SOURCE == "live" else "np-yellow"
live_txt = "🟢 LIVE" if DATA_SOURCE == "live" else "🟡 DEMO"

# ── NAV BAR — pure HTML with JS for clicks ────────────────────────────────────
nav_links = "".join([
    f'<a class="ts-nav-link{"  active" if p == cur else ""}" '
    f'onclick="window.parent.document.querySelector(\'[data-testid=\"stApp\"]\').dispatchEvent(new CustomEvent(\'nav\',{{detail:\'{p}\'}})); return false;" '
    f'href="#">{icons[p]} {p}</a>'
    for p in pages
])

st.markdown(f"""
<div class="ts-nav">
    <div class="ts-logo">
        <div class="ts-logo-icon">📈</div>
        <div class="ts-logo-name">Trade<b>Sage</b></div>
    </div>
    <div class="ts-nav-links">
        {nav_links}
    </div>
    <div class="ts-pills">
        <span class="ts-pill np-blue">BSE SME</span>
        <span class="ts-pill np-blue">NSE Emerge</span>
        <span class="ts-pill {live_cls}">{live_txt}</span>
    </div>
</div>
""", unsafe_allow_html=True)

# Nav buttons: real st.buttons styled to look like the HTML nav links above
# Hide them visually but keep pointer-events ON so clicks work
st.markdown(f"""
<style>
/* Nav button row — zero height, buttons overlap with HTML nav above */
div[data-testid="stHorizontalBlock"].ts-nav-btns {{
    position:relative;
    margin-top:-60px!important;
    height:60px!important;
    background:transparent!important;
    border:none!important;
    z-index:10;
    padding:0 2rem 0 204px!important;
    gap:0!important;
}}
div[data-testid="stHorizontalBlock"].ts-nav-btns > div {{
    padding:0!important;
    flex:0 0 auto!important;
    width:auto!important;
}}
/* Make nav buttons transparent but clickable */
div[data-testid="stHorizontalBlock"].ts-nav-btns .stButton>button {{
    background:transparent!important;color:transparent!important;
    border:none!important;border-radius:0!important;box-shadow:none!important;
    height:60px!important;padding:0 18px!important;min-width:80px!important;
    font-size:0!important;opacity:0!important;
    cursor:pointer!important;
    transition:none!important;transform:none!important;
}}
div[data-testid="stHorizontalBlock"].ts-nav-btns .stButton>button:hover{{
    opacity:0!important;transform:none!important;
}}
/* Dark toggle: last col, visible */
div[data-testid="stHorizontalBlock"].ts-nav-btns > div:last-child .stButton>button {{
    background:transparent!important;color:{muted}!important;border:none!important;
    border-radius:6px!important;box-shadow:none!important;font-size:1rem!important;
    padding:4px 10px!important;height:36px!important;opacity:1!important;
    position:relative;
}}
div[data-testid="stHorizontalBlock"].ts-nav-btns > div:last-child .stButton>button:hover{{
    background:var(--card2)!important;opacity:1!important;transform:none!important;
}}
</style>
""", unsafe_allow_html=True)

dark_icon = "☀️" if dark else "🌙"
with st.container():
    nav_cols = st.columns([1]*len(pages) + [0.4])
    for i, p in enumerate(pages):
        with nav_cols[i]:
            if st.button(f"{icons[p]} {p}", key=f"nav_{p}"):
                st.session_state.current_page = p
                st.rerun()
    with nav_cols[len(pages)]:
        if st.button(dark_icon, key="theme_btn"):
            st.session_state.dark_mode = not st.session_state.dark_mode
            st.rerun()

# ── PAGE CONTENT ──────────────────────────────────────────────────────────────
st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
cur = st.session_state.current_page
if   "Dashboard"  in cur:
    from pages.dashboard   import render; render(ACTIVE_IPOS, UPCOMING_IPOS)
elif "IPO Detail" in cur:
    from pages.ipo_detail  import render; render(ACTIVE_IPOS + UPCOMING_IPOS)
elif "GMP"        in cur:
    from pages.gmp_tracker import render; render(ACTIVE_IPOS + UPCOMING_IPOS, GMP_HISTORY)
elif "Historical" in cur:
    from pages.historical  import render; render(HISTORICAL_IPOS)
