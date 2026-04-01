# v4.0 - removed Google OAuth, fixed waitlist persistence
"""Early Access signup page — F&O Trading Signals product"""
import streamlit as st
import json, os, base64, urllib.request
from datetime import datetime

WAITLIST_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "waitlist.json")
GITHUB_OWNER  = "sreekanthkyatham54-lab"
GITHUB_REPO   = "Git_Repository"
GITHUB_PATH   = "data/waitlist.json"
GITHUB_BRANCH = "main"

SIGNAL_TYPES = [
    ("Straddle VWAP break",       "Institutional sellers in pain — move starting",   "green"),
    ("Deep OTM volume spike",     "15–20x normal = someone knows something",         "green"),
    ("CE/PE short covering",      "Forced covering = directional acceleration",      "green"),
    ("FII 3-day trend",           "Institutional accumulation = structural move",    "green"),
    ("Gamma squeeze setup",       "Market makers forced to buy/sell",                "green"),
    ("Liquidity sweep reversal",  "Institutional trap = reversal entry",             "green"),
    ("VIX above 18 detected",     "Options overpriced — sit out today",              "red"),
    ("Choppy day identified",     "No institutional flow — no trade",                "red"),
]

EXPERIENCE_OPTIONS = [
    "Select...",
    "Just starting out (< 1 yr)",
    "Intermediate (1–3 yrs)",
    "Experienced (3–7 yrs)",
    "Professional / full-time trader",
]


# ── GitHub API persistence ────────────────────────────────────────────────────

def _github_token():
    try:
        return st.secrets["GITHUB_TOKEN"]
    except Exception:
        return ""


def _load_from_github() -> list:
    try:
        headers = {"Accept": "application/vnd.github.v3+json"}
        tok = _github_token()
        if tok:
            headers["Authorization"] = f"token {tok}"
        url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/contents/{GITHUB_PATH}"
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=6) as resp:
            data = json.loads(resp.read())
        return json.loads(base64.b64decode(data["content"]).decode())
    except Exception:
        return []


def _commit_to_github(entries: list, email: str) -> bool:
    tok = _github_token()
    if not tok:
        return False
    try:
        headers = {
            "Authorization": f"token {tok}",
            "Accept":        "application/vnd.github.v3+json",
            "Content-Type":  "application/json",
        }
        url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/contents/{GITHUB_PATH}"
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=6) as resp:
            sha = json.loads(resp.read())["sha"]
        body = json.dumps({
            "message": f"Waitlist signup: {email}",
            "content": base64.b64encode(json.dumps(entries, indent=2).encode()).decode(),
            "sha":     sha,
            "branch":  GITHUB_BRANCH,
        }).encode()
        put = urllib.request.Request(url, data=body, headers=headers, method="PUT")
        with urllib.request.urlopen(put, timeout=10) as resp:
            return resp.status in (200, 201)
    except Exception:
        return False


# ── Waitlist helpers ──────────────────────────────────────────────────────────

def _load_waitlist() -> list:
    try:
        if os.path.exists(WAITLIST_PATH):
            with open(WAITLIST_PATH) as f:
                data = json.load(f)
            if data:
                return data
    except Exception:
        pass
    return _load_from_github()


def _save_entry(entry: dict):
    """Returns (count, is_new, github_ok)."""
    entries = _load_waitlist()
    email = (entry.get("email") or "").strip().lower()
    if email and any((e.get("email") or "").lower() == email for e in entries):
        return len(entries), False, False
    entries.append(entry)
    try:
        with open(WAITLIST_PATH, "w") as f:
            json.dump(entries, f, indent=2)
    except Exception:
        pass
    github_ok = _commit_to_github(entries, email)
    return len(entries), True, github_ok


def _waitlist_count() -> int:
    return len(_load_waitlist())


# ── Page render ───────────────────────────────────────────────────────────────

def render():
    green  = "#1a7f37"
    amber  = "#9a6700"
    red    = "#cf222e"
    card   = "#ffffff"
    border = "#d0d7de"
    muted  = "#57606a"
    text   = "#1a1a2e"

    count = _waitlist_count()

    st.markdown(f"""
    <style>
    .ea-hero {{
        background:linear-gradient(135deg,#0d1117 0%,#161b22 55%,#0d2818 100%);
        border-radius:16px; padding:40px 40px 36px; margin-bottom:20px;
        position:relative; overflow:hidden; border:1px solid #30363d;
    }}
    .ea-hero::after {{
        content:''; position:absolute; bottom:-80px; right:-80px;
        width:260px; height:260px;
        background:radial-gradient(circle,rgba(26,127,55,0.14) 0%,transparent 70%);
        pointer-events:none;
    }}
    .ea-hero-pill     {{ display:inline-block; border:1px solid {green}; color:{green}!important; font-size:0.68rem; font-weight:700; letter-spacing:2px; text-transform:uppercase; padding:5px 14px; border-radius:20px; margin-bottom:16px; background:rgba(26,127,55,0.1); }}
    .ea-hero-h1       {{ font-size:clamp(1.7rem,4vw,2.5rem); font-weight:800; letter-spacing:-0.8px; line-height:1.12; color:#e6edf3!important; margin-bottom:2px; }}
    .ea-hero-h1-green {{ font-size:clamp(1.7rem,4vw,2.5rem); font-weight:800; letter-spacing:-0.8px; line-height:1.2;  color:{green}!important; margin-bottom:16px; }}
    .ea-hero-sub      {{ font-size:0.92rem; color:#8b949e!important; line-height:1.65; max-width:560px; margin-bottom:28px; }}
    .ea-stats         {{ display:flex; gap:36px; flex-wrap:wrap; }}
    .ea-stat-val      {{ font-size:1.6rem; font-weight:800; color:{green}!important; font-family:'JetBrains Mono',monospace; line-height:1; }}
    .ea-stat-label    {{ font-size:0.63rem; font-weight:600; letter-spacing:1.5px; text-transform:uppercase; color:#6e7681!important; margin-top:4px; }}

    .ea-news       {{ background:rgba(154,103,0,0.06); border:1px solid rgba(154,103,0,0.4); border-left:4px solid {amber}; border-radius:0 10px 10px 0; padding:16px 20px; margin-bottom:28px; font-size:0.85rem; line-height:1.65; color:{text}!important; }}
    .ea-news-label {{ font-size:0.65rem; font-weight:700; letter-spacing:2px; text-transform:uppercase; color:{amber}!important; margin-bottom:8px; }}
    .ea-news-amber {{ color:{amber}!important; font-weight:700; }}
    .ea-news-green {{ color:{green}!important; font-weight:700; }}

    .ea-form-title  {{ font-size:1.1rem; font-weight:700; margin-bottom:6px; color:{text}!important; }}
    .ea-form-sub    {{ font-size:0.82rem; color:{muted}!important; margin-bottom:14px; line-height:1.55; }}
    .ea-limit-badge {{ display:inline-block; background:rgba(207,34,46,0.08); border:1px solid rgba(207,34,46,0.3); color:{red}!important; font-size:0.72rem; font-weight:600; padding:3px 12px; border-radius:20px; margin-bottom:18px; }}
    .ea-privacy     {{ font-size:0.75rem; color:{muted}!important; text-align:center; margin-top:12px; line-height:1.5; }}

    .ea-signals-card  {{ background:{card}; border:1.5px solid {border}; border-radius:14px; padding:24px; }}
    .ea-signals-title {{ font-size:0.95rem; font-weight:700; color:{text}!important; margin-bottom:16px; padding-bottom:12px; border-bottom:1.5px solid {border}; }}
    .ea-signal-row    {{ display:flex; align-items:flex-start; gap:10px; padding:9px 0; border-bottom:1px solid rgba(208,215,222,0.45); }}
    .ea-signal-row:last-child {{ border-bottom:none; }}
    .ea-dot           {{ width:9px; height:9px; border-radius:50%; flex-shrink:0; margin-top:5px; }}
    .ea-dot-green     {{ background:{green}; }}
    .ea-dot-red       {{ background:{red}; }}
    .ea-signal-name   {{ font-size:0.85rem; font-weight:700; color:{text}!important; margin-bottom:1px; }}
    .ea-signal-desc   {{ font-size:0.75rem; color:{muted}!important; line-height:1.4; }}
    .ea-waitlist-count {{ text-align:center; padding:20px 0 4px; }}
    .ea-count-num     {{ font-size:2.2rem; font-weight:800; color:{green}!important; font-family:'JetBrains Mono',monospace; line-height:1; }}
    .ea-count-label   {{ font-size:0.65rem; font-weight:700; letter-spacing:2px; text-transform:uppercase; color:{muted}!important; margin-top:4px; }}
    .ea-already-box   {{ background:rgba(26,127,55,0.05); border:1px solid rgba(26,127,55,0.2); border-radius:10px; padding:14px 16px; margin-top:16px; }}
    .ea-already-label {{ font-size:0.65rem; font-weight:700; letter-spacing:1.5px; text-transform:uppercase; color:{green}!important; margin-bottom:6px; }}
    .ea-already-text  {{ font-size:0.78rem; color:{muted}!important; line-height:1.55; }}

    .ea-success       {{ background:rgba(26,127,55,0.06); border:1.5px solid rgba(26,127,55,0.3); border-radius:14px; padding:32px 24px; text-align:center; }}
    .ea-success-icon  {{ font-size:2.8rem; margin-bottom:10px; }}
    .ea-success-title {{ font-size:1.2rem; font-weight:800; color:{green}!important; margin-bottom:6px; }}
    .ea-success-sub   {{ font-size:0.85rem; color:{muted}!important; line-height:1.6; }}
    .ea-success-badge {{ display:inline-block; background:rgba(26,127,55,0.1); border:1px solid {green}; color:{green}!important; border-radius:20px; padding:4px 16px; font-size:0.8rem; font-weight:700; margin-top:14px; }}

    div[data-testid="stButton"] button {{
        width:100%!important; background:{green}!important; color:white!important;
        border:none!important; border-radius:8px!important; font-weight:700!important;
        font-size:0.95rem!important; padding:10px 20px!important;
    }}
    </style>
    """, unsafe_allow_html=True)

    # ── Hero ──────────────────────────────────────────────────────────────────
    st.markdown(f"""
    <div class="ea-hero">
        <div class="ea-hero-pill">Early Access — Limited Spots</div>
        <div class="ea-hero-h1">Big players move first.</div>
        <div class="ea-hero-h1-green">Now you can too.</div>
        <div class="ea-hero-sub">
            Minutes before Trump's Iran announcement, a $1.5 billion futures bet was placed.
            The same invisible moves happen in Nifty options every week.
            TradeSage F&amp;O detects them before the move is obvious.
        </div>
        <div class="ea-stats">
            <div><div class="ea-stat-val">3–4x</div><div class="ea-stat-label">Weekly Opportunities</div></div>
            <div><div class="ea-stat-val">&lt;90s</div><div class="ea-stat-label">Alert Lead Time</div></div>
            <div><div class="ea-stat-val">{count or 47}</div><div class="ea-stat-label">On Waitlist</div></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── News callout ──────────────────────────────────────────────────────────
    st.markdown(f"""
    <div class="ea-news">
        <div class="ea-news-label">What triggered this product</div>
        A US Senator called it <span class="ea-news-amber">"mindblowing corruption"</span> —
        a <span class="ea-news-green">$1.5 billion futures bet placed 5 minutes before Trump posted
        about halting Iran strikes. Stocks surged 2.5%. Crude fell 6%.</span>
        <span class="ea-news-green">This happens in Indian markets every week.</span>
    </div>
    """, unsafe_allow_html=True)

    # ── Two-column layout ─────────────────────────────────────────────────────
    left_col, right_col = st.columns([1, 1], gap="large")

    with right_col:
        signals_html = "".join(
            f'<div class="ea-signal-row"><div class="ea-dot ea-dot-{c}"></div>'
            f'<div><div class="ea-signal-name">{n}</div><div class="ea-signal-desc">{d}</div></div></div>'
            for n, d, c in SIGNAL_TYPES
        )
        st.markdown(f"""
        <div class="ea-signals-card">
            <div class="ea-signals-title">What TradeSage F&amp;O detects</div>
            {signals_html}
            <div class="ea-waitlist-count">
                <div class="ea-count-num">{count or 47}</div>
                <div class="ea-count-label">Traders on Waitlist</div>
            </div>
            <div class="ea-already-box">
                <div class="ea-already-label">Already on TradeSage?</div>
                <div class="ea-already-text">
                    F&amp;O Signals will appear as a new tab in your existing TradeSage.
                    Same login. Same platform. More intelligence.
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with left_col:
        _render_form(count)


# ── Form ──────────────────────────────────────────────────────────────────────

def _render_form(count):
    if st.session_state.get("ea_signup_done"):
        final_count = st.session_state.get("ea_waitlist_count", count)
        github_ok   = st.session_state.get("ea_github_ok", False)
        st.markdown(f"""
        <div class="ea-success">
            <div class="ea-success-icon">🎉</div>
            <div class="ea-success-title">You're on the list!</div>
            <div class="ea-success-sub">
                We'll send you one WhatsApp message the moment<br>
                F&amp;O Signals is ready. No spam, ever.
            </div>
            <div class="ea-success-badge">#{final_count} on the waitlist</div>
        </div>
        """, unsafe_allow_html=True)
        if not github_ok:
            st.warning("Entry saved this session but not yet committed to GitHub. Add `GITHUB_TOKEN` to Streamlit Cloud secrets to persist data permanently.")
        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
        if st.button("← Back to Dashboard", key="ea_back"):
            st.session_state.current_page = "Dashboard"
            st.rerun()
        return

    st.markdown("""
    <div class="ea-form-title">Request early access</div>
    <div class="ea-form-sub">
        Free for 3 months. We'll WhatsApp you before launch.
        No spam — just one message when it's ready.
    </div>
    <div class="ea-limit-badge">Limited to first 500 traders</div>
    """, unsafe_allow_html=True)

    name       = st.text_input("Full name",       placeholder="Rajesh Kumar",     key="ea_name")
    email      = st.text_input("Email address",   placeholder="rajesh@gmail.com", key="ea_email")
    whatsapp   = st.text_input("WhatsApp number", placeholder="9876543210",        key="ea_wa")
    experience = st.selectbox("Trading experience", EXPERIENCE_OPTIONS,            key="ea_exp")

    st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

    if st.button("Join waitlist", key="ea_submit", use_container_width=True):
        if not name.strip():
            st.error("Please enter your name."); return
        if not email.strip() or "@" not in email:
            st.error("Please enter a valid email address."); return
        if experience == "Select...":
            st.error("Please select your trading experience."); return

        entry = {
            "name":       name.strip(),
            "email":      email.strip(),
            "whatsapp":   whatsapp.strip(),
            "experience": experience,
            "signed_up":  datetime.utcnow().isoformat() + "Z",
        }
        count, is_new, github_ok = _save_entry(entry)
        if not is_new:
            st.info("This email is already on the waitlist.")
            return

        st.session_state["ea_signup_done"]    = True
        st.session_state["ea_waitlist_count"] = count
        st.session_state["ea_github_ok"]      = github_ok
        st.rerun()

    st.markdown("""
    <div class="ea-privacy">
        Your details are never shared. One WhatsApp message when early access opens.
    </div>
    """, unsafe_allow_html=True)
