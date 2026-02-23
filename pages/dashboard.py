# v3.1 - F&O Q1, MF+Crypto Q2
"""Dashboard page — Active & Upcoming IPOs + Coming Soon teaser"""
import streamlit as st
from datetime import datetime as dt


def _load_ai_cache():
    try:
        import json, os
        cache_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "ai_cache.json")
        if os.path.exists(cache_file):
            return json.load(open(cache_file))
    except Exception:
        pass
    return {}


def _get_ai_verdict(ipo_id, ai_cache):
    """Get AI verdict from cache, fall back to ipowatch recommendation."""
    cached = ai_cache.get(ipo_id, {})
    scorecard = cached.get("scorecard", {})
    return scorecard.get("verdict", None)


def render(active_ipos, upcoming_ipos):
    # Load AI cache once for the whole dashboard
    ai_cache = _load_ai_cache()

    # Inject AI verdicts into IPO dicts
    for ipo in active_ipos + upcoming_ipos:
        ai_verdict = _get_ai_verdict(ipo["id"], ai_cache)
        if ai_verdict:
            ipo["recommendation"] = ai_verdict
            ipo["rec_source"]     = "AI"
        else:
            ipo["rec_source"]     = "ipowatch"

    # ── STATS BAR ─────────────────────────────────────────────────────────────
    total = len(active_ipos) + len(upcoming_ipos)
    avg_gmp = sum(round(float(i["gmp"] or 0) / float(i["issue_price"] or 1) * 100, 1) for i in active_ipos) / len(active_ipos) if active_ipos else 0
    subscribe_count = sum(1 for i in active_ipos + upcoming_ipos if i["recommendation"] == "SUBSCRIBE")

    st.markdown(f"""
    <div style='display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:20px;'>
        <div style='background:var(--card);border:1.5px solid var(--border);border-radius:10px;padding:16px 20px;'>
            <div style='font-size:0.75rem;color:var(--muted);font-weight:600;letter-spacing:0.3px;margin-bottom:4px;'>Active IPOs</div>
            <div style='font-size:2rem;font-weight:700;font-family:monospace;'>{len(active_ipos)}</div>
            <div style='font-size:0.78rem;color:var(--green);font-weight:600;margin-top:4px;'>↑ Open Now</div>
        </div>
        <div style='background:var(--card);border:1.5px solid var(--border);border-radius:10px;padding:16px 20px;'>
            <div style='font-size:0.75rem;color:var(--muted);font-weight:600;letter-spacing:0.3px;margin-bottom:4px;'>Upcoming IPOs</div>
            <div style='font-size:2rem;font-weight:700;font-family:monospace;'>{len(upcoming_ipos)}</div>
            <div style='font-size:0.78rem;color:var(--green);font-weight:600;margin-top:4px;'>↑ Opening Soon</div>
        </div>
        <div style='background:var(--card);border:1.5px solid var(--border);border-radius:10px;padding:16px 20px;'>
            <div style='font-size:0.75rem;color:var(--muted);font-weight:600;letter-spacing:0.3px;margin-bottom:4px;'>Avg GMP (Active)</div>
            <div style='font-size:2rem;font-weight:700;font-family:monospace;'>{avg_gmp:.1f}%</div>
            <div style='font-size:0.78rem;color:var(--green);font-weight:600;margin-top:4px;'>↑ Grey Market</div>
        </div>
        <div style='background:var(--card);border:1.5px solid var(--border);border-radius:10px;padding:16px 20px;'>
            <div style='font-size:0.75rem;color:var(--muted);font-weight:600;letter-spacing:0.3px;margin-bottom:4px;'>Subscribe Calls</div>
            <div style='font-size:2rem;font-weight:700;font-family:monospace;'>{subscribe_count}/{total}</div>
            <div style='font-size:0.78rem;color:var(--green);font-weight:600;margin-top:4px;'>↑ AI Recommended</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    # ── FILTERS ───────────────────────────────────────────────────────────────
    col_f1, col_f2, col_f3, col_f4 = st.columns([1.5, 1.8, 1.8, 2.5])
    with col_f1: type_filter     = st.selectbox("Type", ["All", "Mainboard", "SME"])
    with col_f2: exchange_filter = st.selectbox("Exchange", ["All", "BSE SME", "NSE Emerge", "BSE / NSE"])
    with col_f3: rec_filter      = st.selectbox("Recommendation", ["All", "SUBSCRIBE", "NEUTRAL", "AVOID"])
    with col_f4: search          = st.text_input("Search IPOs", placeholder="Company name or sector...")

    def filter_ipos(ipos):
        f = ipos
        if type_filter     != "All": f = [i for i in f if i.get("ipo_type","SME") == type_filter]
        if exchange_filter != "All": f = [i for i in f if i["exchange"] == exchange_filter]
        if rec_filter      != "All": f = [i for i in f if i["recommendation"] == rec_filter]
        if search:
            s = search.lower()
            f = [i for i in f if s in i["company"].lower() or s in i.get("sector","").lower()]
        return f

    filtered_active   = filter_ipos(active_ipos)
    filtered_upcoming = filter_ipos(upcoming_ipos)

    # ── ACTIVE IPOs ───────────────────────────────────────────────────────────
    st.markdown(f"""
    <div class='section-header'>
        <div class='section-title'>🟢 Active IPOs</div>
        <div class='section-count'>{len(filtered_active)} IPOs Open</div>
    </div>""", unsafe_allow_html=True)

    if not filtered_active:
        st.markdown('<div style="color:var(--muted);padding:20px;text-align:center;">No active IPOs match your filters</div>', unsafe_allow_html=True)
    else:
        for ipo in filtered_active:
            _render_ipo_card(ipo, is_active=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── UPCOMING IPOs ─────────────────────────────────────────────────────────
    st.markdown(f"""
    <div class='section-header'>
        <div class='section-title'>🔵 Upcoming IPOs</div>
        <div class='section-count'>{len(filtered_upcoming)} Coming Soon</div>
    </div>""", unsafe_allow_html=True)

    if not filtered_upcoming:
        st.markdown('<div style="color:var(--muted);padding:20px;text-align:center;">No upcoming IPOs match your filters</div>', unsafe_allow_html=True)
    else:
        for ipo in filtered_upcoming:
            _render_ipo_card(ipo, is_active=False)

    # ── COMING SOON TEASER ────────────────────────────────────────────────────
    st.markdown("""
    <div class="coming-soon-section">
        <div class="coming-soon-header">
            <div class="coming-soon-label">🔮 Roadmap</div>
            <div class="coming-soon-heading">What's Coming to TradeSage</div>
            <div class="coming-soon-sub">Building the most comprehensive investment research platform for Indian retail investors.</div>
        </div>
        <div class="cs-grid">
            <div class="cs-card cs-card-fo">
                <div class="cs-top"><div class="cs-icon">📈</div><div class="cs-name">F&amp;O Copilot</div></div>
                <div class="cs-desc">Real-time options chain analysis, strategy builder, and AI-generated trade setups for F&amp;O traders.</div>
                <ul class="cs-features">
                    <li>Options chain heatmap</li>
                    <li>Strategy P&amp;L simulator</li>
                    <li>IV percentile alerts</li>
                    <li>Max pain calculator</li>
                </ul>
                <span class="cs-pill">Coming Q1 2026</span>
            </div>
            <div class="cs-card cs-card-mf">
                <div class="cs-top"><div class="cs-icon">📊</div><div class="cs-name">MF Screener</div></div>
                <div class="cs-desc">AI-powered mutual fund analysis with portfolio overlap detection, factor scoring, and personalised recommendations.</div>
                <ul class="cs-features">
                    <li>Fund vs benchmark analysis</li>
                    <li>Portfolio overlap checker</li>
                    <li>SIP return projections</li>
                    <li>Tax efficiency scoring</li>
                </ul>
                <span class="cs-pill">Coming Q2 2026</span>
            </div>
            <div class="cs-card cs-card-crypto">
                <div class="cs-top"><div class="cs-icon">₿</div><div class="cs-name">Crypto Tracker</div></div>
                <div class="cs-desc">Indian crypto market intelligence — INR pricing, regulatory updates, on-chain signals, and AI sentiment.</div>
                <ul class="cs-features">
                    <li>INR-denominated pricing</li>
                    <li>Regulatory news feed</li>
                    <li>On-chain analytics</li>
                    <li>Portfolio tracker</li>
                </ul>
                <span class="cs-pill">Coming Q2 2026</span>
            </div>
        </div>
    </div>
    <br>
    """, unsafe_allow_html=True)


def _render_ipo_card(ipo, is_active):
    exchange_badge = f"<span class='badge badge-bse'>{ipo['exchange']}</span>" if "BSE" in ipo["exchange"] else f"<span class='badge badge-nse'>{ipo['exchange']}</span>"
    status_badge   = "<span class='badge badge-open'>● OPEN</span>" if is_active else "<span class='badge badge-upcoming'>◎ UPCOMING</span>"
    type_badge = "<span style='display:inline-block;padding:3px 8px;border-radius:20px;font-size:0.65rem;font-weight:700;background:rgba(139,92,246,0.1);color:#7c3aed;border:1px solid #7c3aed;'>MAINBOARD</span>" if ipo.get("ipo_type") == "Mainboard" else ""
    rec        = ipo.get("recommendation", "NEUTRAL")
    rec_source = ipo.get("rec_source", "ipowatch")
    ai_badge   = " <span style='font-size:0.55rem;background:rgba(99,102,241,0.15);color:#6366f1;padding:1px 5px;border-radius:4px;font-weight:700;'>AI</span>" if rec_source == "AI" else ""
    rec_html   = {"SUBSCRIBE": f"<span class='rec-subscribe'>✓ SUBSCRIBE{ai_badge}</span>",
                  "AVOID":     f"<span class='rec-avoid'>✗ AVOID{ai_badge}</span>"}.get(rec, f"<span class='rec-neutral'>~ NEUTRAL{ai_badge}</span>")
    gmp_color   = "positive" if ipo["gmp"] > 0 else ("negative" if ipo["gmp"] < 0 else "neutral")
    gmp_sign    = "+" if ipo["gmp"] > 0 else ""
    issue_price = float(ipo.get("issue_price") or 0)
    gmp_val     = float(ipo.get("gmp") or 0)
    gmp_pct     = round((gmp_val / issue_price * 100), 1) if issue_price > 0 else 0
    sub_times   = float(ipo.get("subscription_times") or 0)
    sub_color   = "positive" if sub_times > 5 else ("neutral" if sub_times > 1 else "negative")
    if sub_times > 0:
        qib    = ipo.get("subscription_qib", 0) or 0
        nii    = ipo.get("subscription_nii", 0) or 0
        retail = ipo.get("subscription_retail", 0) or 0
        if qib or nii or retail:
            sub_display = f"{sub_times}x <span style='font-size:0.65rem;color:var(--muted);'>(Q:{qib}x N:{nii}x R:{retail}x)</span>"
        else:
            sub_display = f"{sub_times}x"
    else:
        sub_display = "—"
    try:
        open_date_fmt = dt.strptime(str(ipo["open_date"]), "%Y-%m-%d").strftime("%d/%m/%y")
    except:
        open_date_fmt = str(ipo["open_date"])

    # Wrap in a styled container div, Analyze button is real st.button in col2
    with st.container():
        c1, c2 = st.columns([11, 2])
        with c1:
            st.markdown(f"""
            <div style='background:var(--card);border:1.5px solid var(--border);border-radius:12px;
                        padding:20px;transition:border-color 0.2s,box-shadow 0.2s;'>
                <div style='display:flex;align-items:center;gap:8px;margin-bottom:8px;'>
                    {exchange_badge} {status_badge} {type_badge}
                </div>
                <div style='font-size:1.05rem;font-weight:700;'>{ipo['company']}</div>
                <div style='font-size:0.72rem;color:var(--muted);text-transform:uppercase;letter-spacing:1.2px;margin:4px 0 12px;'>{ipo['sector']}</div>
                <div style='display:flex;gap:16px;flex-wrap:wrap;margin-top:4px;'>
                    <div><div style='font-size:0.65rem;color:var(--muted);text-transform:uppercase;letter-spacing:0.8px;'>Issue Price</div><div style='font-size:0.9rem;font-weight:600;font-family:monospace;'>₹{ipo['issue_price']}</div></div>
                    <div><div style='font-size:0.65rem;color:var(--muted);text-transform:uppercase;letter-spacing:0.8px;'>Size</div><div style='font-size:0.9rem;font-weight:600;font-family:monospace;'>₹{ipo['issue_size_cr']}Cr</div></div>
                    <div><div style='font-size:0.65rem;color:var(--muted);text-transform:uppercase;letter-spacing:0.8px;'>GMP</div><div class='metric-value {gmp_color}' style='font-size:0.9rem;font-weight:600;font-family:monospace;'>{gmp_sign}₹{ipo['gmp']} ({gmp_sign}{gmp_pct}%)</div></div>
                    <div><div style='font-size:0.65rem;color:var(--muted);text-transform:uppercase;letter-spacing:0.8px;'>Subscribed</div><div class='metric-value {sub_color}' style='font-size:0.9rem;font-weight:600;font-family:monospace;'>{sub_display}</div></div>
                    <div><div style='font-size:0.65rem;color:var(--muted);text-transform:uppercase;letter-spacing:0.8px;'>Opens</div><div style='font-size:0.85rem;font-weight:600;font-family:monospace;'>{open_date_fmt}</div></div>
                    <div><div style='font-size:0.65rem;color:var(--muted);text-transform:uppercase;letter-spacing:0.8px;'>Recommendation</div><div style='margin-top:2px;'>{rec_html}</div></div>
                </div>
                <div style='margin-top:12px;font-size:0.83rem;color:var(--muted);line-height:1.5;'>{str(ipo.get("summary",""))[:160]}...</div>
            </div>
            """, unsafe_allow_html=True)
        with c2:
            st.markdown("<div style='height:40px'></div>", unsafe_allow_html=True)
            if st.button("Analyze →", key=f"analyze_{ipo['id']}"):
                st.session_state.selected_ipo_id = ipo["id"]
                st.session_state.current_page    = "IPO Detail"
                st.rerun()
    st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)
