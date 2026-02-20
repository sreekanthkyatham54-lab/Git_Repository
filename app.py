# v3.6 - pure HTML nav using query_params, no duplicate button row
"""TradeSage — SME IPO Research Platform"""
import streamlit as st
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from data_loader import load_ipo_data

st.set_page_config(
    page_title="TradeSage | India IPO Research",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── SESSION STATE ──────────────────────────────────────────────────────────────
if "selected_ipo_id" not in st.session_state: st.session_state.selected_ipo_id = None
if "chat_histories"  not in st.session_state: st.session_state.chat_histories  = {}
if "current_page"    not in st.session_state: st.session_state.current_page    = "Dashboard"
if "api_key"         not in st.session_state:
    try:    st.session_state.api_key = st.secrets["ANTHROPIC_API_KEY"]
    except: st.session_state.api_key = os.environ.get("ANTHROPIC_API_KEY", "")

# Handle query param navigation (from HTML nav link clicks)
qp = st.query_params.get("page", None)
if qp and qp != st.session_state.current_page:
    st.session_state.current_page = qp
    st.query_params.clear()

cur = st.session_state.current_page
pages = ["Dashboard", "IPO Detail", "GMP Tracker", "Historical Data"]
icons = {"Dashboard":"🏠","IPO Detail":"🔍","GMP Tracker":"📊","Historical Data":"📜"}

# ── THEME (light only — dark toggle removed per user request) ──────────────────
bg="#f6f8fa"; card="#ffffff"; card2="#eef1f5"; text="#1a1a2e"
muted="#57606a"; border="#d0d7de"; green="#1a7f37"; red="#cf222e"
yellow="#9a6700"; blue="#0969da"; nav_bg="#ffffff"; btn="#2da44e"

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
.ts-nav{{background:{nav_bg};border-bottom:2px solid {border};margin:0 -2rem;padding:0 2rem;display:flex;align-items:center;height:60px;gap:0;position:relative;z-index:100;}}
.ts-logo{{display:flex;align-items:center;gap:10px;padding-right:20px;border-right:1px solid {border};margin-right:4px;flex-shrink:0;text-decoration:none;}}
.ts-logo-icon{{width:34px;height:34px;background:{green};border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:1rem;box-shadow:0 2px 6px rgba(26,127,55,0.3);}}
.ts-logo-name{{font-size:1.1rem;font-weight:800;letter-spacing:-0.4px;color:{text}!important;}}
.ts-logo-name b{{color:{green}!important;}}
.ts-nav-links{{display:flex;align-items:stretch;flex:1;}}
.ts-nav-link{{display:flex;align-items:center;padding:0 16px;height:60px;font-size:0.85rem;font-weight:600;color:{muted}!important;cursor:pointer;border-bottom:3px solid transparent;text-decoration:none!important;white-space:nowrap;transition:color 0.15s,border-bottom-color 0.15s;}}
.ts-nav-link:hover{{color:{text}!important;background:rgba(0,0,0,0.03);text-decoration:none!important;}}
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

/* ── IPO CARDS ── */
.ipo-card{{background:var(--card);border:1.5px solid var(--border);border-radius:12px;padding:20px;margin-bottom:0;transition:border-color 0.2s,box-shadow 0.2s;}}
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
.ipo-summary{{margin-top:12px;font-size:0.83rem;color:var(--muted)!important;line-height:1.5;}}
.alert-green{{background:rgba(63,185,80,0.08);border-left:3px solid var(--green);padding:12px 16px;border-radius:0 8px 8px 0;margin:8px 0;}}
.alert-red{{background:rgba(248,81,73,0.08);border-left:3px solid var(--red);padding:12px 16px;border-radius:0 8px 8px 0;margin:8px 0;}}
.alert-yellow{{background:rgba(210,153,34,0.08);border-left:3px solid var(--yellow);padding:12px 16px;border-radius:0 8px 8px 0;margin:8px 0;}}
.chat-message-user{{background:rgba(88,166,255,0.08);border:1px solid rgba(88,166,255,0.2);border-radius:12px 12px 2px 12px;padding:12px 16px;margin:8px 0;font-size:0.9rem;}}
.chat-message-ai{{background:var(--card);border:1px solid var(--border);border-radius:12px 12px 12px 2px;padding:12px 16px;margin:8px 0;font-size:0.9rem;line-height:1.6;}}
.section-header{{display:flex;align-items:center;gap:10px;margin-bottom:18px;padding-bottom:10px;border-bottom:1.5px solid var(--border);}}
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

/* ── MOBILE RESPONSIVE ── */
/* Hamburger button - hidden on desktop */
.ts-hamburger {{
    display:none;
    flex-direction:column;justify-content:center;align-items:center;
    width:36px;height:36px;cursor:pointer;gap:5px;margin-left:auto;flex-shrink:0;
    background:transparent;border:none;padding:4px;
}}
.ts-hamburger span {{
    display:block;width:22px;height:2px;background:{text};
    border-radius:2px;transition:all 0.25s;
}}
/* Mobile nav drawer */
.ts-mobile-nav {{
    display:none;
    position:fixed;top:0;right:-100%;width:75%;max-width:280px;height:100vh;
    background:{card};border-left:1px solid {border};
    z-index:99999;transition:right 0.3s ease;
    flex-direction:column;padding:20px;box-shadow:-4px 0 20px rgba(0,0,0,0.15);
}}
.ts-mobile-nav.open {{ right:0; }}
.ts-mobile-overlay {{
    display:none;position:fixed;inset:0;background:rgba(0,0,0,0.4);
    z-index:99998;
}}
.ts-mobile-overlay.open {{ display:block; }}
.ts-mobile-nav-header {{
    display:flex;align-items:center;justify-content:space-between;
    margin-bottom:28px;padding-bottom:16px;border-bottom:1px solid {border};
}}
.ts-mobile-nav-close {{
    font-size:1.4rem;cursor:pointer;color:{muted};background:none;border:none;
    line-height:1;padding:4px;
}}
.ts-mobile-nav-link {{
    display:flex;align-items:center;gap:12px;padding:14px 8px;
    font-size:1rem;font-weight:600;color:{muted}!important;
    text-decoration:none!important;border-radius:8px;
    border-left:3px solid transparent;margin-bottom:4px;
    transition:all 0.15s;
}}
.ts-mobile-nav-link:hover {{ background:{card2};color:{text}!important; }}
.ts-mobile-nav-link.active {{
    color:{green}!important;border-left:3px solid {green};
    background:rgba(26,127,55,0.08);
}}
.ts-mobile-pills {{
    margin-top:auto;padding-top:20px;border-top:1px solid {border};
    display:flex;flex-wrap:wrap;gap:6px;
}}

@media (max-width:768px) {{
    /* Show hamburger, hide desktop nav links and pills */
    .ts-hamburger {{ display:flex!important; }}
    .ts-nav-links {{ display:none!important; }}
    .ts-pills {{ display:none!important; }}
    .ts-mobile-nav {{ display:flex!important; }}
    
    /* Nav bar height on mobile */
    .ts-nav {{ height:54px!important; }}
    .ts-logo {{ padding-right:12px!important; }}
    .ts-logo-name {{ font-size:1rem!important; }}
    
    /* 2x2 grid for metric cards on mobile */
    [data-testid="stMetric"] {{
        min-width:0!important;
    }}
    /* Force the 4-col metric row to wrap 2x2 */
    div[data-testid="stHorizontalBlock"]:has([data-testid="stMetric"]) {{
        flex-wrap:wrap!important;gap:10px!important;
    }}
    div[data-testid="stHorizontalBlock"]:has([data-testid="stMetric"]) > div {{
        flex:1 1 calc(50% - 5px)!important;min-width:calc(50% - 5px)!important;max-width:calc(50% - 5px)!important;
    }}
    
    /* IPO card full width on mobile */
    .block-container {{ padding:0 1rem 1.5rem!important; }}
    
    /* Analyze button col - stack on mobile */
    div[data-testid="stHorizontalBlock"]:has(>.stButton) {{
        flex-wrap:wrap!important;
    }}
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

live_cls = "np-green" if DATA_SOURCE == "live" else "np-yellow"
live_txt = "🟢 LIVE" if DATA_SOURCE == "live" else "🟡 DEMO"

# ── PURE HTML NAV BAR ─────────────────────────────────────────────────────────
# Navigation uses ?page=X query params — no Streamlit buttons in nav at all
def nav_link(page):
    active = "active" if page == cur else ""
    return f'<a class="ts-nav-link {active}" href="?page={page}" target="_self">{icons[page]} {page}</a>'

st.markdown(f"""
<!-- Overlay for closing drawer -->
<div class="ts-mobile-overlay" id="ts-overlay" onclick="closeMenu()"></div>

<!-- Mobile slide-in nav drawer -->
<div class="ts-mobile-nav" id="ts-mobile-nav">
    <div class="ts-mobile-nav-header">
        <div class="ts-logo" style="border:none;padding:0;">
            <div class="ts-logo-icon" style="width:28px;height:28px;font-size:0.85rem;">📈</div>
            <div class="ts-logo-name" style="font-size:1rem;">Trade<b>Sage</b></div>
        </div>
        <button class="ts-mobile-nav-close" onclick="closeMenu()">✕</button>
    </div>
    <a class="ts-mobile-nav-link {"active" if cur=="Dashboard" else ""}" href="?page=Dashboard" target="_self">🏠 Dashboard</a>
    <a class="ts-mobile-nav-link {"active" if cur=="IPO Detail" else ""}" href="?page=IPO Detail" target="_self">🔍 IPO Detail</a>
    <a class="ts-mobile-nav-link {"active" if cur=="GMP Tracker" else ""}" href="?page=GMP Tracker" target="_self">📊 GMP Tracker</a>
    <a class="ts-mobile-nav-link {"active" if cur=="Historical Data" else ""}" href="?page=Historical Data" target="_self">📜 Historical Data</a>
    <div class="ts-mobile-pills">
        <span class="ts-pill np-blue">Mainboard</span>
        <span class="ts-pill np-blue">BSE SME</span>
        <span class="ts-pill np-blue">NSE Emerge</span>
        <span class="ts-pill {live_cls}">{live_txt}</span>
    </div>
</div>

<!-- Top nav bar -->
<div class="ts-nav">
    <a class="ts-logo" href="?page=Dashboard" target="_self" style="text-decoration:none;">
        <div class="ts-logo-icon">📈</div>
        <div class="ts-logo-name">Trade<b>Sage</b></div>
    </a>
    <div class="ts-nav-links">
        {nav_link("Dashboard")}
        {nav_link("IPO Detail")}
        {nav_link("GMP Tracker")}
        {nav_link("Historical Data")}
    </div>
    <div class="ts-pills">
        <span class="ts-pill np-blue">Mainboard</span>
        <span class="ts-pill np-blue">BSE SME</span>
        <span class="ts-pill np-blue">NSE Emerge</span>
        <span class="ts-pill {live_cls}">{live_txt}</span>
    </div>
    <!-- Hamburger: only visible on mobile via CSS -->
    <button class="ts-hamburger" onclick="openMenu()" aria-label="Open menu">
        <span></span><span></span><span></span>
    </button>
</div>
<div style="height:16px"></div>

<script>
function openMenu() {{
    document.getElementById('ts-mobile-nav').classList.add('open');
    document.getElementById('ts-overlay').classList.add('open');
    document.body.style.overflow = 'hidden';
}}
function closeMenu() {{
    document.getElementById('ts-mobile-nav').classList.remove('open');
    document.getElementById('ts-overlay').classList.remove('open');
    document.body.style.overflow = '';
}}
</script>
""", unsafe_allow_html=True)

# ── PAGE CONTENT ──────────────────────────────────────────────────────────────
if   "Dashboard"  in cur:
    from pages.dashboard   import render; render(ACTIVE_IPOS, UPCOMING_IPOS)
elif "IPO Detail" in cur:
    from pages.ipo_detail  import render; render(ACTIVE_IPOS + UPCOMING_IPOS)
elif "GMP"        in cur:
    from pages.gmp_tracker import render; render(ACTIVE_IPOS + UPCOMING_IPOS, GMP_HISTORY)
elif "Historical" in cur:
    from pages.historical  import render; render(HISTORICAL_IPOS)
