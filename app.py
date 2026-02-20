# v3.0 - top nav, no sidebar, coming soon teaser cards
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

# ── SESSION STATE ──────────────────────────────────────────────────────────────
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
    yellow="#d29922"; blue="#58a6ff"
    hero_bg="linear-gradient(135deg,#0d1117 0%,#0d2818 100%)"
    nav_bg="#161b22"; nav_border="#30363d"
else:
    bg="#f6f8fa"; card="#ffffff"; card2="#eef1f5"; text="#1a1a2e"
    muted="#57606a"; border="#d0d7de"; green="#1a7f37"; red="#cf222e"
    yellow="#9a6700"; blue="#0969da"
    hero_bg="linear-gradient(135deg,#f0fdf4 0%,#dcfce7 60%,#f0f9ff 100%)"
    nav_bg="#ffffff"; nav_border="#d0d7de"

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Sora:wght@400;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap');
:root{{
    --bg:{bg};--card:{card};--card2:{card2};--text:{text};--muted:{muted};
    --border:{border};--green:{green};--red:{red};--yellow:{yellow};--blue:{blue};
}}

/* ── RESET STREAMLIT DEFAULTS ── */
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
section[data-testid="stMain"]>div{{padding-top:0!important;}}

/* ── TOP NAV BAR ── */
.ts-navbar{{
    background:{nav_bg};
    border-bottom:2px solid {nav_border};
    padding:0 2rem;
    display:flex;
    align-items:center;
    justify-content:space-between;
    height:64px;
    position:sticky;
    top:0;
    z-index:9999;
    box-shadow:0 2px 8px rgba(0,0,0,0.06);
}}
.ts-navbar-left{{display:flex;align-items:center;gap:32px;}}
.ts-logo{{display:flex;align-items:center;gap:10px;text-decoration:none;}}
.ts-logo-icon{{
    width:36px;height:36px;background:{green};border-radius:9px;
    display:flex;align-items:center;justify-content:center;font-size:1.1rem;
    box-shadow:0 2px 8px rgba(26,127,55,0.3);flex-shrink:0;
}}
.ts-logo-name{{font-size:1.25rem;font-weight:800;color:{text}!important;letter-spacing:-0.5px;}}
.ts-logo-name span{{color:{green}!important;}}
.ts-nav-links{{display:flex;align-items:center;gap:4px;}}
.ts-nav-link{{
    padding:8px 16px;border-radius:8px;font-size:0.85rem;font-weight:600;
    color:{muted}!important;cursor:pointer;border:none;background:transparent;
    transition:all 0.15s;white-space:nowrap;
}}
.ts-nav-link:hover{{background:{card2};color:{text}!important;}}
.ts-nav-link.active{{background:rgba(26,127,55,0.12);color:{green}!important;}}
.ts-navbar-right{{display:flex;align-items:center;gap:12px;}}
.ts-badge-pill{{
    padding:4px 10px;border-radius:20px;font-size:0.68rem;font-weight:600;
    letter-spacing:0.3px;white-space:nowrap;
}}
.ts-pill-blue{{background:rgba(9,105,218,0.1);color:{blue}!important;border:1px solid {blue};}}
.ts-pill-green{{background:rgba(26,127,55,0.1);color:{green}!important;border:1px solid {green};}}
.ts-pill-yellow{{background:rgba(154,103,0,0.1);color:{yellow}!important;border:1px solid {yellow};}}

/* ── MAIN CONTENT PADDING ── */
.ts-content{{padding:1.5rem 2rem;}}

/* ── CARDS ── */
.ipo-card{{background:var(--card);border:1.5px solid var(--border);border-radius:12px;padding:20px;margin-bottom:14px;transition:border-color 0.2s,box-shadow 0.2s;}}
.ipo-card:hover{{border-color:var(--green);box-shadow:0 4px 16px rgba(0,0,0,0.07);}}
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
.stButton>button{{background:var(--green)!important;color:white!important;border:none!important;border-radius:8px!important;font-weight:600!important;padding:8px 20px!important;font-family:'Sora',sans-serif!important;transition:opacity 0.15s,transform 0.15s!important;}}
.stButton>button:hover{{opacity:0.88!important;transform:translateY(-1px)!important;}}
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

/* ── COMING SOON CARDS ── */
.coming-soon-section{{
    margin:2rem 0 0 0;
    padding:2rem;
    background:{card2};
    border-radius:16px;
    border:1.5px solid {border};
}}
.coming-soon-title{{
    font-size:0.72rem;font-weight:700;color:{muted}!important;
    text-transform:uppercase;letter-spacing:2px;margin-bottom:6px;
}}
.coming-soon-heading{{
    font-size:1.2rem;font-weight:800;color:{text}!important;
    margin-bottom:4px;letter-spacing:-0.3px;
}}
.coming-soon-sub{{font-size:0.83rem;color:{muted}!important;margin-bottom:1.5rem;}}
.cs-card{{
    background:{card};
    border:1.5px solid {border};
    border-radius:12px;
    padding:20px;
    height:100%;
    transition:border-color 0.2s,transform 0.2s,box-shadow 0.2s;
    position:relative;
    overflow:hidden;
}}
.cs-card::before{{
    content:'';position:absolute;top:0;left:0;right:0;height:3px;
}}
.cs-card-mf::before{{background:linear-gradient(90deg,{blue},{green});}}
.cs-card-fo::before{{background:linear-gradient(90deg,{yellow},{red});}}
.cs-card-crypto::before{{background:linear-gradient(90deg,#f7931a,#9b59b6);}}
.cs-card:hover{{transform:translateY(-3px);box-shadow:0 8px 24px rgba(0,0,0,0.1);border-color:{green};}}
.cs-icon{{font-size:2rem;margin-bottom:10px;}}
.cs-name{{font-size:1rem;font-weight:700;color:{text}!important;margin-bottom:6px;}}
.cs-desc{{font-size:0.82rem;color:{muted}!important;line-height:1.6;margin-bottom:14px;}}
.cs-features{{list-style:none;padding:0;margin:0 0 16px 0;}}
.cs-features li{{font-size:0.78rem;color:{muted}!important;padding:3px 0;}}
.cs-features li::before{{content:"→ ";color:{green}!important;font-weight:700;}}
.cs-pill{{
    display:inline-block;padding:4px 12px;border-radius:20px;
    font-size:0.68rem;font-weight:700;letter-spacing:0.5px;
    background:rgba(26,127,55,0.1);color:{green}!important;border:1px solid {green};
}}

/* ── MOBILE RESPONSIVE ── */
@media (max-width:768px){{
    .ts-navbar{{padding:0 1rem;height:56px;}}
    .ts-nav-links{{display:none;}}
    .ts-logo-name{{font-size:1.1rem;}}
    .ts-badge-pill{{display:none;}}
    .ts-mobile-nav{{
        display:flex;background:{nav_bg};border-bottom:1px solid {nav_border};
        overflow-x:auto;padding:0 1rem;gap:4px;
        scrollbar-width:none;-ms-overflow-style:none;
    }}
    .ts-mobile-nav::-webkit-scrollbar{{display:none;}}
    .ts-mobile-link{{
        padding:10px 14px;font-size:0.8rem;font-weight:600;
        color:{muted}!important;white-space:nowrap;border-bottom:2px solid transparent;
        cursor:pointer;flex-shrink:0;
    }}
    .ts-mobile-link.active{{color:{green}!important;border-bottom-color:{green};}}
    .ts-content{{padding:1rem;}}
}}
@media (min-width:769px){{
    .ts-mobile-nav{{display:none;}}
}}
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

# ── NAV STATE ─────────────────────────────────────────────────────────────────
pages     = ["Dashboard", "IPO Detail", "GMP Tracker", "Historical Data"]
nav_icons = ["🏠", "🔍", "📊", "📜"]
cur       = st.session_state.current_page
if cur not in pages: cur = "Dashboard"

live_pill = f'<span class="ts-badge-pill ts-pill-green">🟢 LIVE</span>' if DATA_SOURCE == "live" else f'<span class="ts-badge-pill ts-pill-yellow">🟡 DEMO</span>'
dark_label = "☀️" if dark else "🌙"

# ── TOP NAV BAR (HTML) ────────────────────────────────────────────────────────
nav_links_html = "".join([
    f'<span class="ts-nav-link {"active" if p == cur else ""}" '
    f'onclick="window.location.href=\'?page={p.replace(" ","_")}\'">{icon} {p}</span>'
    for p, icon in zip(pages, nav_icons)
])

st.markdown(f"""
<div class="ts-navbar">
    <div class="ts-navbar-left">
        <div class="ts-logo">
            <div class="ts-logo-icon">📈</div>
            <div class="ts-logo-name">Trade<span>Sage</span></div>
        </div>
        <div class="ts-nav-links">
            {nav_links_html}
        </div>
    </div>
    <div class="ts-navbar-right">
        <span class="ts-badge-pill ts-pill-blue">BSE SME</span>
        <span class="ts-badge-pill ts-pill-blue">NSE Emerge</span>
        {live_pill}
    </div>
</div>
<!-- Mobile tab bar -->
<div class="ts-mobile-nav">
    {"".join([f'<span class="ts-mobile-link {"active" if p == cur else ""}">{icon} {p}</span>' for p, icon in zip(pages, nav_icons)])}
</div>
""", unsafe_allow_html=True)

# ── NAV via Streamlit buttons (invisible, positioned over HTML links) ──────────
# Use st.columns to render real Streamlit buttons for navigation
nav_cols = st.columns([1, 1, 1, 1, 2])
for i, (p, icon) in enumerate(zip(pages, nav_icons)):
    with nav_cols[i]:
        btn_style = f"background:{'rgba(26,127,55,0.15)' if p == cur else 'transparent'}!important;color:{'var(--green)' if p == cur else 'var(--muted)'}!important;border:none!important;width:100%!important;font-size:0.8rem!important;padding:4px 8px!important;"
        if st.button(f"{icon} {p}", key=f"nav_{p}", help=p):
            st.session_state.current_page = p
            st.rerun()
with nav_cols[4]:
    if st.button(dark_label, key="theme_btn"):
        st.session_state.dark_mode = not st.session_state.dark_mode
        st.rerun()

st.markdown("<div style='border-bottom:1.5px solid var(--border);margin:-8px 0 16px 0;'></div>", unsafe_allow_html=True)

# ── PAGE ROUTING ──────────────────────────────────────────────────────────────
cur = st.session_state.current_page
if   "Dashboard"  in cur:
    from pages.dashboard  import render; render(ACTIVE_IPOS, UPCOMING_IPOS)
elif "IPO Detail" in cur:
    from pages.ipo_detail import render; render(ACTIVE_IPOS + UPCOMING_IPOS)
elif "GMP"        in cur:
    from pages.gmp_tracker import render; render(ACTIVE_IPOS + UPCOMING_IPOS, GMP_HISTORY)
elif "Historical" in cur:
    from pages.historical  import render; render(HISTORICAL_IPOS)
