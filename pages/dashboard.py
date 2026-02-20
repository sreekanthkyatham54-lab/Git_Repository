# v3.0 - top nav, coming soon teaser cards
"""Dashboard page — Active & Upcoming IPOs + Coming Soon teaser"""
import streamlit as st
from datetime import datetime as dt


def render(active_ipos, upcoming_ipos):
    # ── STATS BAR ─────────────────────────────────────────────────────────────
    total = len(active_ipos) + len(upcoming_ipos)
    avg_gmp = sum(round(float(i["gmp"] or 0) / float(i["issue_price"] or 1) * 100, 1) for i in active_ipos) / len(active_ipos) if active_ipos else 0
    subscribe_count = sum(1 for i in active_ipos + upcoming_ipos if i["recommendation"] == "SUBSCRIBE")

    col1, col2, col3, col4 = st.columns(4)
    with col1: st.metric("Active IPOs",      len(active_ipos),          "Open Now")
    with col2: st.metric("Upcoming IPOs",    len(upcoming_ipos),         "Opening Soon")
    with col3: st.metric("Avg GMP (Active)", f"{avg_gmp:.1f}%",          "Grey Market")
    with col4: st.metric("Subscribe Calls",  f"{subscribe_count}/{total}","AI Recommended")

    st.markdown("---")

    # ── FILTERS ───────────────────────────────────────────────────────────────
    col_f1, col_f2, col_f3 = st.columns([2, 2, 3])
    with col_f1: exchange_filter = st.selectbox("Exchange", ["All", "BSE SME", "NSE Emerge"])
    with col_f2: rec_filter      = st.selectbox("Recommendation", ["All", "SUBSCRIBE", "NEUTRAL", "AVOID"])
    with col_f3: search          = st.text_input("Search IPOs", placeholder="Company name or sector...")

    def filter_ipos(ipos):
        f = ipos
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
        <div class="coming-soon-title">🔮 Roadmap</div>
        <div class="coming-soon-heading">What's Coming to TradeSage</div>
        <div class="coming-soon-sub">We're building the most comprehensive investment research platform for Indian retail investors.</div>
    </div>
    """, unsafe_allow_html=True)

    cs_col1, cs_col2, cs_col3 = st.columns(3)

    with cs_col1:
        st.markdown("""
        <div class="cs-card cs-card-mf">
            <div class="cs-icon">📊</div>
            <div class="cs-name">MF Screener</div>
            <div class="cs-desc">AI-powered mutual fund analysis with portfolio overlap detection, factor scoring, and personalised fund recommendations.</div>
            <ul class="cs-features">
                <li>Fund vs benchmark analysis</li>
                <li>Portfolio overlap checker</li>
                <li>SIP return projections</li>
                <li>Tax efficiency scoring</li>
            </ul>
            <span class="cs-pill">Coming Q2 2026</span>
        </div>
        """, unsafe_allow_html=True)

    with cs_col2:
        st.markdown("""
        <div class="cs-card cs-card-fo">
            <div class="cs-icon">📈</div>
            <div class="cs-name">F&O Copilot</div>
            <div class="cs-desc">Real-time options chain analysis, strategy builder, and AI-generated trade setups for futures & options traders.</div>
            <ul class="cs-features">
                <li>Options chain heatmap</li>
                <li>Strategy P&L simulator</li>
                <li>IV percentile alerts</li>
                <li>Max pain calculator</li>
            </ul>
            <span class="cs-pill">Coming Q3 2026</span>
        </div>
        """, unsafe_allow_html=True)

    with cs_col3:
        st.markdown("""
        <div class="cs-card cs-card-crypto">
            <div class="cs-icon">₿</div>
            <div class="cs-name">Crypto Tracker</div>
            <div class="cs-desc">Indian crypto market intelligence — exchange rates, regulatory updates, on-chain signals, and AI sentiment analysis.</div>
            <ul class="cs-features">
                <li>INR-denominated pricing</li>
                <li>Regulatory news feed</li>
                <li>On-chain analytics</li>
                <li>Portfolio tracker</li>
            </ul>
            <span class="cs-pill">Coming Q4 2026</span>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)


def _render_ipo_card(ipo, is_active):
    with st.container():
        col1, col2 = st.columns([3, 1])
        with col1:
            exchange_badge = f"<span class='badge badge-bse'>{ipo['exchange']}</span>" if "BSE" in ipo["exchange"] else f"<span class='badge badge-nse'>{ipo['exchange']}</span>"
            status_badge   = "<span class='badge badge-open'>● OPEN</span>" if is_active else "<span class='badge badge-upcoming'>◎ UPCOMING</span>"
            rec = ipo["recommendation"]
            rec_html = {"SUBSCRIBE": "<span class='rec-subscribe'>✓ SUBSCRIBE</span>",
                        "AVOID":     "<span class='rec-avoid'>✗ AVOID</span>"}.get(rec, "<span class='rec-neutral'>~ NEUTRAL</span>")

            gmp_color   = "positive" if ipo["gmp"] > 0 else ("negative" if ipo["gmp"] < 0 else "neutral")
            gmp_sign    = "+" if ipo["gmp"] > 0 else ""
            issue_price = float(ipo.get("issue_price") or 0)
            gmp_val     = float(ipo.get("gmp") or 0)
            gmp_pct     = round((gmp_val / issue_price * 100), 1) if issue_price > 0 else 0
            sub_color   = "positive" if ipo["subscription_times"] > 5 else ("neutral" if ipo["subscription_times"] > 1 else "negative")
            sub_display = f"{ipo['subscription_times']}x" if ipo["subscription_times"] > 0 else "—"
            try:
                open_date_fmt = dt.strptime(str(ipo["open_date"]), "%Y-%m-%d").strftime("%d/%m/%y")
            except:
                open_date_fmt = str(ipo["open_date"])

            st.markdown(f"""
            <div class='ipo-card'>
                <div style='display:flex;align-items:center;gap:8px;margin-bottom:8px;'>
                    {exchange_badge} {status_badge}
                </div>
                <div class='ipo-company'>{ipo['company']}</div>
                <div class='ipo-sector'>{ipo['sector']}</div>
                <div class='metric-row'>
                    <div class='metric-item'><div class='metric-label'>Issue Price</div><div class='metric-value'>₹{ipo['issue_price']}</div></div>
                    <div class='metric-item'><div class='metric-label'>Size</div><div class='metric-value'>₹{ipo['issue_size_cr']}Cr</div></div>
                    <div class='metric-item'><div class='metric-label'>GMP</div><div class='metric-value {gmp_color}'>{gmp_sign}₹{ipo['gmp']} ({gmp_sign}{gmp_pct}%)</div></div>
                    <div class='metric-item'><div class='metric-label'>Subscribed</div><div class='metric-value {sub_color}'>{sub_display}</div></div>
                    <div class='metric-item'><div class='metric-label'>Opens</div><div class='metric-value' style='font-size:0.82rem;'>{open_date_fmt}</div></div>
                    <div class='metric-item'><div class='metric-label'>Recommendation</div><div style='margin-top:2px;'>{rec_html}</div></div>
                </div>
                <div style='margin-top:12px;font-size:0.83rem;color:var(--muted);line-height:1.5;'>{str(ipo.get('summary',''))[:160]}...</div>
            </div>
            """, unsafe_allow_html=True)

        with col2:
            st.markdown("<div style='height:30px'></div>", unsafe_allow_html=True)
            if st.button("Analyze →", key=f"analyze_{ipo['id']}"):
                st.session_state.selected_ipo_id = ipo["id"]
                st.session_state.current_page    = "IPO Detail"
                st.rerun()
