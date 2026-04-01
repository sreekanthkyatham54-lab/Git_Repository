# v2.0 - redesigned to match mockup
"""Early Access signup page — F&O Trading Signals product"""
import streamlit as st
import json, os
from datetime import datetime

WAITLIST_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "waitlist.json")

# signal name, description, color ("green" or "red")
SIGNAL_TYPES = [
    ("Straddle VWAP break",       "Institutional sellers in pain — move starting",          "green"),
    ("Deep OTM volume spike",     "15–20x normal = someone knows something",                "green"),
    ("CE/PE short covering",      "Forced covering = directional acceleration",             "green"),
    ("FII 3-day trend",           "Institutional accumulation = structural move",           "green"),
    ("Gamma squeeze setup",       "Market makers forced to buy/sell",                       "green"),
    ("Liquidity sweep reversal",  "Institutional trap = reversal entry",                    "green"),
    ("VIX above 18 detected",     "Options overpriced — sit out today",                     "red"),
    ("Choppy day identified",     "No institutional flow — no trade",                       "red"),
]

EXPERIENCE_OPTIONS = [
    "Select...",
    "Just starting out (< 1 yr)",
    "Intermediate (1–3 yrs)",
    "Experienced (3–7 yrs)",
    "Professional / full-time trader",
]


# ── Waitlist helpers ──────────────────────────────────────────────────────────

def _load_waitlist():
    try:
        if os.path.exists(WAITLIST_PATH):
            with open(WAITLIST_PATH) as f:
                return json.load(f)
    except Exception:
        pass
    return []


def _save_entry(entry: dict):
    """Append entry; returns (total_count, is_new)."""
    entries = _load_waitlist()
    email = (entry.get("email") or "").strip().lower()
    if email and any((e.get("email") or "").lower() == email for e in entries):
        return len(entries), False
    entries.append(entry)
    try:
        with open(WAITLIST_PATH, "w") as f:
            json.dump(entries, f, indent=2)
    except Exception:
        pass
    return len(entries), True


def _waitlist_count():
    return len(_load_waitlist())


# ── Main render ───────────────────────────────────────────────────────────────

def render():
    green  = "#1a7f37"
    amber  = "#9a6700"
    red    = "#cf222e"
    bg     = "#f6f8fa"
    card   = "#ffffff"
    card2  = "#eef1f5"
    border = "#d0d7de"
    muted  = "#57606a"
    text   = "#1a1a2e"

    count = _waitlist_count()

    st.markdown(f"""
    <style>
    /* ── Hero ── */
    .ea-hero {{
        background: linear-gradient(135deg, #0d1117 0%, #161b22 55%, #0d2818 100%);
        border-radius: 16px;
        padding: 40px 40px 36px;
        margin-bottom: 20px;
        position: relative;
        overflow: hidden;
        border: 1px solid #30363d;
    }}
    .ea-hero::after {{
        content: '';
        position: absolute;
        bottom: -80px; right: -80px;
        width: 260px; height: 260px;
        background: radial-gradient(circle, rgba(26,127,55,0.14) 0%, transparent 70%);
        pointer-events: none;
    }}
    .ea-hero-pill {{
        display: inline-block;
        border: 1px solid {green};
        color: {green}!important;
        font-size: 0.68rem; font-weight: 700;
        letter-spacing: 2px; text-transform: uppercase;
        padding: 5px 14px; border-radius: 20px;
        margin-bottom: 16px;
        background: rgba(26,127,55,0.1);
    }}
    .ea-hero-h1 {{
        font-size: clamp(1.7rem, 4vw, 2.5rem);
        font-weight: 800; letter-spacing: -0.8px;
        line-height: 1.12; color: #e6edf3!important;
        margin-bottom: 2px;
    }}
    .ea-hero-h1-green {{
        font-size: clamp(1.7rem, 4vw, 2.5rem);
        font-weight: 800; letter-spacing: -0.8px;
        line-height: 1.2; color: {green}!important;
        margin-bottom: 16px;
    }}
    .ea-hero-sub {{
        font-size: 0.92rem; color: #8b949e!important;
        line-height: 1.65; max-width: 560px; margin-bottom: 28px;
    }}
    .ea-stats {{
        display: flex; gap: 36px; align-items: flex-start;
        flex-wrap: wrap;
    }}
    .ea-stat-val {{
        font-size: 1.6rem; font-weight: 800;
        color: {green}!important;
        font-family: 'JetBrains Mono', monospace;
        line-height: 1;
    }}
    .ea-stat-label {{
        font-size: 0.63rem; font-weight: 600;
        letter-spacing: 1.5px; text-transform: uppercase;
        color: #6e7681!important; margin-top: 4px;
    }}

    /* ── News callout ── */
    .ea-news {{
        background: rgba(154,103,0,0.06);
        border: 1px solid rgba(154,103,0,0.4);
        border-left: 4px solid {amber};
        border-radius: 0 10px 10px 0;
        padding: 16px 20px;
        margin-bottom: 28px;
        font-size: 0.85rem;
        line-height: 1.65;
        color: {text}!important;
    }}
    .ea-news-label {{
        font-size: 0.65rem; font-weight: 700;
        letter-spacing: 2px; text-transform: uppercase;
        color: {amber}!important; margin-bottom: 8px;
    }}
    .ea-news-amber {{ color: {amber}!important; font-weight: 700; }}
    .ea-news-green {{ color: {green}!important; font-weight: 700; }}

    /* ── Form card ── */
    .ea-form-card {{
        background: {card};
        border: 1.5px solid {border};
        border-radius: 14px;
        padding: 28px 24px 20px;
    }}
    .ea-form-title {{
        font-size: 1.1rem; font-weight: 700;
        margin-bottom: 6px; color: {text}!important;
    }}
    .ea-form-sub {{
        font-size: 0.82rem; color: {muted}!important;
        margin-bottom: 14px; line-height: 1.55;
    }}
    .ea-limit-badge {{
        display: inline-block;
        background: rgba(207,34,46,0.08);
        border: 1px solid rgba(207,34,46,0.3);
        color: {red}!important;
        font-size: 0.72rem; font-weight: 600;
        padding: 3px 12px; border-radius: 20px;
        margin-bottom: 18px;
    }}
    .ea-google-btn {{
        width: 100%; padding: 11px;
        background: {card}; color: {text}!important;
        border: 1.5px solid {border}; border-radius: 8px;
        font-size: 0.9rem; font-weight: 600;
        cursor: pointer; display: flex; align-items: center;
        justify-content: center; gap: 10px;
        font-family: 'Sora', sans-serif;
        transition: border-color 0.15s, box-shadow 0.15s;
    }}
    .ea-google-btn:hover {{
        border-color: #aaa;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    }}
    .ea-divider {{
        display: flex; align-items: center; gap: 10px;
        margin: 16px 0;
    }}
    .ea-divider-line {{ flex: 1; height: 1px; background: {border}; }}
    .ea-divider-text {{
        font-size: 0.72rem; color: {muted}!important;
        font-weight: 600; white-space: nowrap;
    }}
    .ea-privacy {{
        font-size: 0.75rem; color: {muted}!important;
        text-align: center; margin-top: 12px; line-height: 1.5;
    }}

    /* ── Right column ── */
    .ea-signals-card {{
        background: {card};
        border: 1.5px solid {border};
        border-radius: 14px;
        padding: 24px;
    }}
    .ea-signals-title {{
        font-size: 0.95rem; font-weight: 700;
        color: {text}!important;
        margin-bottom: 16px;
        padding-bottom: 12px;
        border-bottom: 1.5px solid {border};
    }}
    .ea-signal-row {{
        display: flex; align-items: flex-start; gap: 10px;
        padding: 9px 0;
        border-bottom: 1px solid rgba(208,215,222,0.45);
    }}
    .ea-signal-row:last-child {{ border-bottom: none; }}
    .ea-dot {{
        width: 9px; height: 9px; border-radius: 50%;
        flex-shrink: 0; margin-top: 5px;
    }}
    .ea-dot-green {{ background: {green}; }}
    .ea-dot-red   {{ background: {red}; }}
    .ea-signal-name {{
        font-size: 0.85rem; font-weight: 700;
        color: {text}!important; margin-bottom: 1px;
    }}
    .ea-signal-desc {{
        font-size: 0.75rem; color: {muted}!important; line-height: 1.4;
    }}
    .ea-waitlist-count {{
        text-align: center; padding: 20px 0 4px;
    }}
    .ea-count-num {{
        font-size: 2.2rem; font-weight: 800;
        color: {green}!important;
        font-family: 'JetBrains Mono', monospace;
        line-height: 1;
    }}
    .ea-count-label {{
        font-size: 0.65rem; font-weight: 700;
        letter-spacing: 2px; text-transform: uppercase;
        color: {muted}!important; margin-top: 4px;
    }}
    .ea-already-box {{
        background: rgba(26,127,55,0.05);
        border: 1px solid rgba(26,127,55,0.2);
        border-radius: 10px;
        padding: 14px 16px;
        margin-top: 16px;
    }}
    .ea-already-label {{
        font-size: 0.65rem; font-weight: 700;
        letter-spacing: 1.5px; text-transform: uppercase;
        color: {green}!important; margin-bottom: 6px;
    }}
    .ea-already-text {{
        font-size: 0.78rem; color: {muted}!important; line-height: 1.55;
    }}

    /* ── Success state ── */
    .ea-success {{
        background: rgba(26,127,55,0.06);
        border: 1.5px solid rgba(26,127,55,0.3);
        border-radius: 14px;
        padding: 32px 24px;
        text-align: center;
    }}
    .ea-success-icon {{ font-size: 2.8rem; margin-bottom: 10px; }}
    .ea-success-title {{
        font-size: 1.2rem; font-weight: 800;
        color: {green}!important; margin-bottom: 6px;
    }}
    .ea-success-sub {{
        font-size: 0.85rem; color: {muted}!important; line-height: 1.6;
    }}
    .ea-success-badge {{
        display: inline-block;
        background: rgba(26,127,55,0.1);
        border: 1px solid {green};
        color: {green}!important;
        border-radius: 20px; padding: 4px 16px;
        font-size: 0.8rem; font-weight: 700; margin-top: 14px;
    }}

    /* ── Google sign-in button ── */
    .google-btn-marker + div[data-testid="stButton"] > button {{
        background: white!important;
        color: #3c4043!important;
        border: 1.5px solid #dadce0!important;
        font-weight: 500!important;
        font-size: 0.9rem!important;
        display: flex!important;
        align-items: center!important;
        justify-content: center!important;
        gap: 10px!important;
        padding: 10px 16px!important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.08)!important;
        transition: box-shadow 0.2s, border-color 0.2s!important;
    }}
    .google-btn-marker + div[data-testid="stButton"] > button:hover {{
        box-shadow: 0 2px 8px rgba(0,0,0,0.15)!important;
        border-color: #aaa!important;
        opacity: 1!important;
        transform: none!important;
    }}
    .google-btn-marker + div[data-testid="stButton"] > button::before {{
        content: '';
        display: inline-block;
        width: 18px; height: 18px; flex-shrink: 0;
        background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 48 48'%3E%3Cpath fill='%23EA4335' d='M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z'/%3E%3Cpath fill='%234285F4' d='M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z'/%3E%3Cpath fill='%23FBBC05' d='M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z'/%3E%3Cpath fill='%2334A853' d='M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.18 1.48-4.97 2.31-8.16 2.31-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z'/%3E%3C/svg%3E");
        background-size: contain;
        background-repeat: no-repeat;
        background-position: center;
    }}

    /* override Streamlit button for Join waitlist */
    div[data-testid="stButton"] button {{
        width: 100%!important;
        background: {green}!important;
        color: white!important;
        border: none!important;
        border-radius: 8px!important;
        font-weight: 700!important;
        font-size: 0.95rem!important;
        padding: 10px 20px!important;
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
            <div>
                <div class="ea-stat-val">3–4x</div>
                <div class="ea-stat-label">Weekly Opportunities</div>
            </div>
            <div>
                <div class="ea-stat-val">&lt;90s</div>
                <div class="ea-stat-label">Alert Lead Time</div>
            </div>
            <div>
                <div class="ea-stat-val">{count if count else 47}</div>
                <div class="ea-stat-label">On Waitlist</div>
            </div>
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
            f"""<div class="ea-signal-row">
                    <div class="ea-dot ea-dot-{color}"></div>
                    <div>
                        <div class="ea-signal-name">{name}</div>
                        <div class="ea-signal-desc">{desc}</div>
                    </div>
                </div>"""
            for name, desc, color in SIGNAL_TYPES
        )
        st.markdown(f"""
        <div class="ea-signals-card">
            <div class="ea-signals-title">What TradeSage F&amp;O detects</div>
            {signals_html}
            <div class="ea-waitlist-count">
                <div class="ea-count-num">{count if count else 47}</div>
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


# ── Form logic ────────────────────────────────────────────────────────────────

def _render_form(count):
    green = "#1a7f37"
    muted = "#57606a"
    text  = "#1a1a2e"

    # Already submitted
    if st.session_state.get("ea_signup_done"):
        final_count = st.session_state.get("ea_waitlist_count", count)
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
        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
        if st.button("← Back to Dashboard", key="ea_back"):
            st.session_state.current_page = "Dashboard"
            st.rerun()
        return

    google_available = _check_google_auth_configured()

    # Check Google login state
    logged_in = False
    google_name  = ""
    google_email = ""
    if google_available:
        try:
            user = st.experimental_user
            logged_in    = getattr(user, "is_logged_in", False)
            google_name  = getattr(user, "name",  "") or ""
            google_email = getattr(user, "email", "") or ""
        except Exception:
            pass

    # ── Form card header ──────────────────────────────────────────────────────
    st.markdown("""
    <div style="margin-bottom:0">
        <div class="ea-form-title">Request early access</div>
        <div class="ea-form-sub">
            Free for 3 months. We'll WhatsApp you before launch.
            No spam — just one message when it's ready.
        </div>
        <div class="ea-limit-badge">Limited to first 500 traders</div>
    </div>
    """, unsafe_allow_html=True)

    if logged_in:
        # Already signed in via Google — show name + collect remaining fields
        st.markdown(f"""
        <div style='background:rgba(26,127,55,0.06);border:1px solid rgba(26,127,55,0.25);
                    border-radius:10px;padding:11px 16px;margin-bottom:14px;
                    display:flex;align-items:center;gap:10px;'>
            <span style='font-size:1.2rem;'>✅</span>
            <div>
                <div style='font-size:0.85rem;font-weight:700;color:{text};'>
                    Signed in as {google_name}</div>
                <div style='font-size:0.75rem;color:{muted};'>{google_email}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        whatsapp   = st.text_input("WhatsApp number", placeholder="9876543210", key="ea_wa_g")
        experience = st.selectbox("Trading experience", EXPERIENCE_OPTIONS, key="ea_exp_g")

        col_submit, col_logout = st.columns([3, 1])
        with col_submit:
            if st.button("Join waitlist", key="ea_submit_g", use_container_width=True):
                if experience == "Select...":
                    st.error("Please select your trading experience.")
                else:
                    _do_save(name=google_name, email=google_email,
                             whatsapp=whatsapp, experience=experience, via="google")
        with col_logout:
            if st.button("Sign out", key="ea_logout"):
                st.logout()

    else:
        # Not logged in — show Google button + manual form
        if google_available:
            st.markdown('<div class="google-btn-marker"></div>', unsafe_allow_html=True)
            if st.button("Continue with Google", key="ea_google_login", use_container_width=True):
                st.login("google")

            st.markdown("""
            <div class="ea-divider">
                <div class="ea-divider-line"></div>
                <div class="ea-divider-text">or fill in manually</div>
                <div class="ea-divider-line"></div>
            </div>
            """, unsafe_allow_html=True)

        _manual_form()

    st.markdown("""
    <div class="ea-privacy">
        Your details are never shared. One WhatsApp message when early access opens.
    </div>
    """, unsafe_allow_html=True)


def _manual_form():
    name       = st.text_input("Full name",       placeholder="Rajesh Kumar",      key="ea_name")
    email      = st.text_input("Email address",   placeholder="rajesh@gmail.com",  key="ea_email")
    whatsapp   = st.text_input("WhatsApp number", placeholder="9876543210",         key="ea_wa")
    experience = st.selectbox("Trading experience", EXPERIENCE_OPTIONS,             key="ea_exp")

    st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
    if st.button("Join waitlist", key="ea_submit_manual", use_container_width=True):
        if not name.strip():
            st.error("Please enter your name.")
            return
        if not email.strip() or "@" not in email:
            st.error("Please enter a valid email address.")
            return
        if experience == "Select...":
            st.error("Please select your trading experience.")
            return
        _do_save(name=name.strip(), email=email.strip(),
                 whatsapp=whatsapp.strip(), experience=experience, via="manual")


def _do_save(name, email, whatsapp, experience, via):
    entry = {
        "name":       name,
        "email":      email,
        "whatsapp":   whatsapp,
        "experience": experience,
        "via":        via,
        "signed_up":  datetime.utcnow().isoformat() + "Z",
    }
    count, _ = _save_entry(entry)
    st.session_state["ea_signup_done"]    = True
    st.session_state["ea_waitlist_count"] = count
    st.rerun()


def _check_google_auth_configured() -> bool:
    try:
        _ = st.secrets["auth"]["google"]["client_id"]
        return True
    except Exception:
        return False
