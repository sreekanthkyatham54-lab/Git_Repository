# v1.0 - F&O Early Access signup with Google OAuth
"""Early Access signup page — F&O Trading Signals product"""
import streamlit as st
import json, os
from datetime import datetime

WAITLIST_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "waitlist.json")

SIGNAL_TYPES = [
    ("🐋", "Big Block Trades",       "Detect when institutions accumulate quietly in futures before a move"),
    ("🌍", "FII Long Buildup",        "Foreign institutional longs surging on index futures — follow the smart flow"),
    ("📊", "Put/Call Ratio Spike",    "Unusual options activity that reliably signals short-term market direction"),
    ("🔥", "Open Interest Surge",     "Sudden OI buildup in specific strikes reveals where smart money is positioned"),
    ("🌑", "Dark Pool Prints",        "Off-exchange block trades that precede large directional moves by 24–48 hrs"),
    ("🇺🇸", "Macro Mirror Trades",   "Policy-driven positioning in US/global futures that flows into Indian markets"),
    ("😖", "Options Pain Point",      "Max pain analysis to predict weekly expiry direction with 70%+ accuracy"),
    ("⚡", "Volatility Crush Play",   "VIX spike signals: when to sell premium and when to buy directional options"),
]

EXPERIENCE_OPTIONS = [
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


# ── Main render ───────────────────────────────────────────────────────────────

def render():
    green  = "#1a7f37"
    bg     = "#f6f8fa"
    card   = "#ffffff"
    border = "#d0d7de"
    muted  = "#57606a"
    text   = "#1a1a2e"
    red    = "#cf222e"

    # ── Page-level styles ─────────────────────────────────────────────────────
    st.markdown(f"""
    <style>
    /* ── Hero ── */
    .ea-hero {{
        background: linear-gradient(135deg, #0d1117 0%, #161b22 50%, #0d2818 100%);
        border-radius: 16px;
        padding: 48px 40px 40px;
        margin-bottom: 32px;
        position: relative;
        overflow: hidden;
        border: 1px solid #30363d;
    }}
    .ea-hero::before {{
        content: '';
        position: absolute;
        top: -60px; right: -60px;
        width: 220px; height: 220px;
        background: radial-gradient(circle, rgba(26,127,55,0.18) 0%, transparent 70%);
        pointer-events: none;
    }}
    .ea-hero-label {{
        font-size: 0.68rem; font-weight: 700; letter-spacing: 2.5px;
        text-transform: uppercase; color: {green}!important;
        margin-bottom: 10px;
    }}
    .ea-hero-headline {{
        font-size: clamp(1.6rem, 4vw, 2.4rem);
        font-weight: 800; letter-spacing: -0.8px;
        line-height: 1.15; color: #e6edf3!important;
        margin-bottom: 14px;
    }}
    .ea-hero-headline span {{ color: {green}!important; }}
    .ea-hero-sub {{
        font-size: 1rem; color: #8b949e!important;
        line-height: 1.65; max-width: 580px; margin-bottom: 24px;
    }}
    /* ── News callout ── */
    .ea-news {{
        background: rgba(207,34,46,0.08);
        border: 1px solid rgba(207,34,46,0.35);
        border-radius: 10px;
        padding: 14px 18px;
        margin-bottom: 8px;
        display: flex; gap: 12px; align-items: flex-start;
    }}
    .ea-news-icon {{ font-size: 1.3rem; flex-shrink: 0; margin-top: 1px; }}
    .ea-news-body {{ font-size: 0.83rem; color: #cdd9e5!important; line-height: 1.6; }}
    .ea-news-body strong {{ color: #ffa198!important; }}
    /* ── Form card ── */
    .ea-form-card {{
        background: {card};
        border: 1.5px solid {border};
        border-radius: 14px;
        padding: 28px 24px;
    }}
    .ea-form-title {{
        font-size: 1.05rem; font-weight: 700;
        margin-bottom: 4px; color: {text}!important;
    }}
    .ea-form-sub {{
        font-size: 0.82rem; color: {muted}!important;
        margin-bottom: 20px; line-height: 1.5;
    }}
    .ea-divider {{
        display: flex; align-items: center; gap: 10px;
        margin: 18px 0;
    }}
    .ea-divider-line {{
        flex: 1; height: 1px; background: {border};
    }}
    .ea-divider-text {{
        font-size: 0.72rem; color: {muted}!important;
        font-weight: 600; text-transform: uppercase; letter-spacing: 1px;
        white-space: nowrap;
    }}
    /* ── Signal list ── */
    .ea-signal-card {{
        background: {card};
        border: 1.5px solid {border};
        border-radius: 12px;
        padding: 24px;
        height: 100%;
    }}
    .ea-signal-title {{
        font-size: 0.95rem; font-weight: 700; margin-bottom: 18px;
        padding-bottom: 12px; border-bottom: 1.5px solid {border};
        color: {text}!important;
    }}
    .ea-signal-item {{
        display: flex; gap: 12px; align-items: flex-start;
        padding: 10px 0; border-bottom: 1px solid rgba(208,215,222,0.5);
    }}
    .ea-signal-item:last-child {{ border-bottom: none; }}
    .ea-signal-icon {{
        font-size: 1.2rem; flex-shrink: 0;
        width: 34px; height: 34px;
        background: rgba(26,127,55,0.08);
        border: 1px solid rgba(26,127,55,0.2);
        border-radius: 8px;
        display: flex; align-items: center; justify-content: center;
    }}
    .ea-signal-name {{
        font-size: 0.85rem; font-weight: 700;
        color: {text}!important; margin-bottom: 2px;
    }}
    .ea-signal-desc {{
        font-size: 0.76rem; color: {muted}!important; line-height: 1.45;
    }}
    /* ── Success state ── */
    .ea-success {{
        background: rgba(26,127,55,0.06);
        border: 1.5px solid rgba(26,127,55,0.35);
        border-radius: 14px;
        padding: 28px 24px;
        text-align: center;
    }}
    .ea-success-icon {{ font-size: 2.8rem; margin-bottom: 12px; }}
    .ea-success-title {{
        font-size: 1.2rem; font-weight: 800;
        color: {green}!important; margin-bottom: 6px;
    }}
    .ea-success-sub {{
        font-size: 0.87rem; color: {muted}!important; line-height: 1.6;
    }}
    .ea-count-badge {{
        display: inline-block;
        background: rgba(26,127,55,0.1);
        border: 1px solid {green};
        color: {green}!important;
        border-radius: 20px;
        padding: 4px 14px;
        font-size: 0.8rem; font-weight: 700;
        margin-top: 14px;
    }}
    </style>
    """, unsafe_allow_html=True)

    # ── Hero ──────────────────────────────────────────────────────────────────
    st.markdown(f"""
    <div class="ea-hero">
        <div class="ea-hero-label">⚡ Coming Q3 2026 — Join the waitlist</div>
        <div class="ea-hero-headline">
            Big players move first.<br>
            <span>Now you can too.</span>
        </div>
        <div class="ea-hero-sub">
            Institutional traders see the order flow before price moves.
            TradeSage F&O Signals surfaces their positioning — block trades, FII buildup,
            OI surges — so you act on data, not news.
        </div>
        <div class="ea-news">
            <div class="ea-news-icon">🚨</div>
            <div class="ea-news-body">
                <strong>Bloomberg, Jan 2025:</strong>
                When Trump signalled Iran sanctions were back on the table, hedge funds
                loaded <strong>$1.5 billion in crude oil futures</strong> 48 hours before
                the official announcement. Retail investors read about it in the news —
                the move was already over. With F&O Signals, you'd see the positioning
                build in real time.
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Two-column layout ─────────────────────────────────────────────────────
    left_col, right_col = st.columns([1, 1], gap="large")

    with right_col:
        signals_html = "".join(
            f"""<div class="ea-signal-item">
                    <div class="ea-signal-icon">{icon}</div>
                    <div>
                        <div class="ea-signal-name">{name}</div>
                        <div class="ea-signal-desc">{desc}</div>
                    </div>
                </div>"""
            for icon, name, desc in SIGNAL_TYPES
        )
        st.markdown(f"""
        <div class="ea-signal-card">
            <div class="ea-signal-title">⚡ 8 Signal Types — Launching Q3 2026</div>
            {signals_html}
        </div>
        """, unsafe_allow_html=True)

    with left_col:
        _render_form()


# ── Form logic ────────────────────────────────────────────────────────────────

def _render_form():
    green  = "#1a7f37"
    muted  = "#57606a"
    text   = "#1a1a2e"

    # Check for already-submitted state
    if st.session_state.get("ea_signup_done"):
        count = st.session_state.get("ea_waitlist_count", 1)
        st.markdown(f"""
        <div class="ea-success">
            <div class="ea-success-icon">🎉</div>
            <div class="ea-success-title">You're on the list!</div>
            <div class="ea-success-sub">
                We'll notify you the moment F&O Signals launches.<br>
                Expect early access invites to go out in Q3 2026.
            </div>
            <div class="ea-count-badge">#{count} on the waitlist</div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("← Back to Dashboard", key="ea_back"):
            st.session_state.current_page = "Dashboard"
            st.rerun()
        return

    st.markdown("""
    <div class="ea-form-card">
        <div class="ea-form-title">Get early access</div>
        <div class="ea-form-sub">
            Be first in line. Early members get priority access and locked-in
            founding-member pricing.
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Google OAuth path ─────────────────────────────────────────────────────
    google_available = _check_google_auth_configured()

    if google_available:
        try:
            user = st.experimental_user
            logged_in = getattr(user, "is_logged_in", False)
        except Exception:
            logged_in = False
            user = None

        if not logged_in:
            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
            col_btn, _ = st.columns([2, 1])
            with col_btn:
                if st.button("🔑  Sign in with Google", key="ea_google_login", use_container_width=True):
                    st.login("google")

            st.markdown(f"""
            <div class="ea-divider">
                <div class="ea-divider-line"></div>
                <div class="ea-divider-text">or fill in manually</div>
                <div class="ea-divider-line"></div>
            </div>
            """, unsafe_allow_html=True)
            _manual_form(prefill_email=None, prefill_name=None)

        else:
            # Logged in via Google — just need WhatsApp + experience
            name  = getattr(user, "name",  None) or ""
            email = getattr(user, "email", None) or ""

            st.markdown(f"""
            <div style='background:rgba(26,127,55,0.06);border:1px solid rgba(26,127,55,0.25);
                        border-radius:10px;padding:12px 16px;margin-bottom:16px;
                        display:flex;align-items:center;gap:10px;'>
                <span style='font-size:1.3rem;'>✅</span>
                <div>
                    <div style='font-size:0.85rem;font-weight:700;color:{text};'>
                        Signed in as {name}</div>
                    <div style='font-size:0.75rem;color:{muted};'>{email}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            whatsapp = st.text_input(
                "WhatsApp number (for signal alerts)",
                placeholder="+91 98765 43210",
                key="ea_wa_google",
            )
            experience = st.selectbox(
                "Trading experience",
                EXPERIENCE_OPTIONS,
                key="ea_exp_google",
            )

            col_submit, col_logout = st.columns([2, 1])
            with col_submit:
                if st.button("Join Waitlist →", key="ea_submit_google", use_container_width=True):
                    _do_save(name=name, email=email, whatsapp=whatsapp, experience=experience, via="google")
            with col_logout:
                if st.button("Sign out", key="ea_logout"):
                    st.logout()
    else:
        # Google auth not configured — show manual form only
        _manual_form(prefill_email=None, prefill_name=None)


def _manual_form(prefill_email, prefill_name):
    """Render the manual signup form."""
    name = st.text_input(
        "Full name",
        value=prefill_name or "",
        placeholder="Rahul Sharma",
        key="ea_name_manual",
    )
    email = st.text_input(
        "Email address",
        value=prefill_email or "",
        placeholder="rahul@example.com",
        key="ea_email_manual",
    )
    whatsapp = st.text_input(
        "WhatsApp number (for signal alerts)",
        placeholder="+91 98765 43210",
        key="ea_wa_manual",
    )
    experience = st.selectbox(
        "Trading experience",
        EXPERIENCE_OPTIONS,
        key="ea_exp_manual",
    )

    st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
    if st.button("Join Waitlist →", key="ea_submit_manual", use_container_width=True):
        if not name.strip():
            st.error("Please enter your name.")
            return
        if not email.strip() or "@" not in email:
            st.error("Please enter a valid email address.")
            return
        _do_save(name=name.strip(), email=email.strip(), whatsapp=whatsapp.strip(), experience=experience, via="manual")


def _do_save(name, email, whatsapp, experience, via):
    entry = {
        "name":       name,
        "email":      email,
        "whatsapp":   whatsapp,
        "experience": experience,
        "via":        via,
        "signed_up":  datetime.utcnow().isoformat() + "Z",
    }
    count, is_new = _save_entry(entry)
    st.session_state["ea_signup_done"]     = True
    st.session_state["ea_waitlist_count"]  = count
    if not is_new:
        st.session_state["ea_already_signed"] = True
    st.rerun()


def _check_google_auth_configured() -> bool:
    """Return True if Google OAuth secrets are present."""
    try:
        _ = st.secrets["auth"]["google"]["client_id"]
        return True
    except Exception:
        return False
