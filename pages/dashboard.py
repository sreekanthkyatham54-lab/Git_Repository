"""Dashboard page — Active & Upcoming IPO list"""
import streamlit as st


def render(active_ipos, upcoming_ipos):
    # Header
    st.markdown("""
    <div class='app-header'>
        <div class='app-title'>SME <span>IPO Research</span></div>
        <div class='app-subtitle'>INDIA · BSE SME · NSE EMERGE · AI-POWERED ANALYSIS</div>
    </div>
    """, unsafe_allow_html=True)

    # Stats bar
    total = len(active_ipos) + len(upcoming_ipos)
    avg_gmp = sum(i["gmp_percent"] for i in active_ipos) / len(active_ipos) if active_ipos else 0
    subscribe_count = sum(1 for i in active_ipos + upcoming_ipos if i["recommendation"] == "SUBSCRIBE")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Active IPOs", len(active_ipos), "Open Now")
    with col2:
        st.metric("Upcoming IPOs", len(upcoming_ipos), "Opening Soon")
    with col3:
        st.metric("Avg GMP (Active)", f"{avg_gmp:.1f}%", "Grey Market")
    with col4:
        st.metric("Subscribe Calls", f"{subscribe_count}/{total}", "AI Recommended")

    st.markdown("---")

    # Filters
    col_f1, col_f2, col_f3 = st.columns([2, 2, 3])
    with col_f1:
        exchange_filter = st.selectbox("Exchange", ["All", "BSE SME", "NSE Emerge"])
    with col_f2:
        rec_filter = st.selectbox("Recommendation", ["All", "SUBSCRIBE", "NEUTRAL", "AVOID"])
    with col_f3:
        search = st.text_input("Search IPOs", placeholder="Company name or sector...")

    def filter_ipos(ipos):
        filtered = ipos
        if exchange_filter != "All":
            filtered = [i for i in filtered if i["exchange"] == exchange_filter]
        if rec_filter != "All":
            filtered = [i for i in filtered if i["recommendation"] == rec_filter]
        if search:
            s = search.lower()
            filtered = [i for i in filtered if s in i["company"].lower() or s in i["sector"].lower()]
        return filtered

    filtered_active = filter_ipos(active_ipos)
    filtered_upcoming = filter_ipos(upcoming_ipos)

    # Active IPOs
    st.markdown(f"""
    <div class='section-header'>
        <div class='section-title'>🟢 Active IPOs</div>
        <div class='section-count'>{len(filtered_active)} IPOs Open</div>
    </div>
    """, unsafe_allow_html=True)

    if not filtered_active:
        st.markdown('<div style="color:#8892a4; padding:20px; text-align:center;">No IPOs match your filters</div>', unsafe_allow_html=True)
    else:
        for ipo in filtered_active:
            _render_ipo_card(ipo, is_active=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Upcoming IPOs
    st.markdown(f"""
    <div class='section-header'>
        <div class='section-title'>🔵 Upcoming IPOs</div>
        <div class='section-count'>{len(filtered_upcoming)} Coming Soon</div>
    </div>
    """, unsafe_allow_html=True)

    if not filtered_upcoming:
        st.markdown('<div style="color:#8892a4; padding:20px; text-align:center;">No upcoming IPOs match your filters</div>', unsafe_allow_html=True)
    else:
        for ipo in filtered_upcoming:
            _render_ipo_card(ipo, is_active=False)


def _render_ipo_card(ipo, is_active):
    with st.container():
        col1, col2 = st.columns([3, 1])
        with col1:
            exchange_badge = f"<span class='badge badge-bse'>{ipo['exchange']}</span>" if "BSE" in ipo["exchange"] else f"<span class='badge badge-nse'>{ipo['exchange']}</span>"
            status_badge = "<span class='badge badge-open'>● OPEN</span>" if is_active else "<span class='badge badge-upcoming'>◎ UPCOMING</span>"
            
            rec = ipo["recommendation"]
            if rec == "SUBSCRIBE":
                rec_html = "<span class='rec-subscribe'>✓ SUBSCRIBE</span>"
            elif rec == "AVOID":
                rec_html = "<span class='rec-avoid'>✗ AVOID</span>"
            else:
                rec_html = "<span class='rec-neutral'>~ NEUTRAL</span>"

            gmp_color = "positive" if ipo["gmp"] > 0 else ("negative" if ipo["gmp"] < 0 else "neutral")
            gmp_sign = "+" if ipo["gmp"] > 0 else ""
            sub_color = "positive" if ipo["subscription_times"] > 5 else ("neutral" if ipo["subscription_times"] > 1 else "negative")

            sub_display = f"{ipo['subscription_times']}x" if ipo["subscription_times"] > 0 else "—"

            st.markdown(f"""
            <div class='ipo-card'>
                <div style='display:flex; align-items:center; gap:8px; margin-bottom:8px;'>
                    {exchange_badge} {status_badge}
                </div>
                <div class='ipo-company'>{ipo['company']}</div>
                <div class='ipo-sector'>{ipo['sector']}</div>
                <div class='metric-row'>
                    <div class='metric-item'>
                        <div class='metric-label'>Issue Price</div>
                        <div class='metric-value'>₹{ipo['issue_price']}</div>
                    </div>
                    <div class='metric-item'>
                        <div class='metric-label'>Size</div>
                        <div class='metric-value'>₹{ipo['issue_size_cr']}Cr</div>
                    </div>
                    <div class='metric-item'>
                        <div class='metric-label'>GMP</div>
                        <div class='metric-value {gmp_color}'>{gmp_sign}₹{ipo['gmp']} ({gmp_sign}{ipo['gmp_percent']:.1f}%)</div>
                    </div>
                    <div class='metric-item'>
                        <div class='metric-label'>Subscribed</div>
                        <div class='metric-value {sub_color}'>{sub_display}</div>
                    </div>
                    <div class='metric-item'>
                        <div class='metric-label'>Opens</div>
                        <div class='metric-value' style='font-size:0.82rem;'>{ipo['open_date']}</div>
                    </div>
                    <div class='metric-item'>
                        <div class='metric-label'>Recommendation</div>
                        <div style='margin-top:2px;'>{rec_html}</div>
                    </div>
                </div>
                <div style='margin-top:12px; font-size:0.83rem; color:#8892a4; line-height:1.5;'>{ipo['summary'][:160]}...</div>
            </div>
            """, unsafe_allow_html=True)

        with col2:
            st.markdown("<div style='height:30px'></div>", unsafe_allow_html=True)
            if st.button(f"Analyze →", key=f"analyze_{ipo['id']}"):
                st.session_state.selected_ipo_id = ipo["id"]
                st.session_state.current_page = "🔍 IPO Detail"
                st.rerun()
