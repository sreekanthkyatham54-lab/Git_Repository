"""IPO Details page — AI Q&A, Recommendation Scorecard, Industry Analysis, News"""
import streamlit as st
import plotly.graph_objects as go
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from data.ipo_data import NEWS, GMP_HISTORY


def render(all_ipos):
    st.markdown("<div class='app-title' style='margin-bottom:8px;'>🔍 IPO <span style='color:#00d4aa;'>Deep Dive</span></div>", unsafe_allow_html=True)
    st.markdown("<div class='app-subtitle' style='margin-bottom:24px;'>AI-POWERED ANALYSIS · DRHP Q&A · PEER COMPARISON</div>", unsafe_allow_html=True)

    # IPO Selector
    ipo_names = [i["company"] for i in all_ipos]
    
    # Pre-select if coming from dashboard
    default_idx = 0
    if st.session_state.get("selected_ipo_id"):
        for idx, ipo in enumerate(all_ipos):
            if ipo["id"] == st.session_state.selected_ipo_id:
                default_idx = idx
                break

    selected_name = st.selectbox("Select IPO to analyze", ipo_names, index=default_idx)
    ipo = next(i for i in all_ipos if i["company"] == selected_name)

    st.markdown("---")

    # ── OVERVIEW ROW ──────────────────────────────────────────────────────────────
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("Issue Price", f"₹{ipo['issue_price']}")
    with col2:
        # FIX 3: GMP % = GMP / Issue Price * 100 (premium over issue price)
        issue_price = float(ipo.get('issue_price') or 0)
        gmp = float(ipo.get('gmp') or 0)
        gmp_pct = round((gmp / issue_price * 100), 1) if issue_price > 0 else 0
        gmp_delta = f"+{gmp_pct}% over issue" if gmp >= 0 else f"{gmp_pct}% over issue"
        st.metric("GMP", f"₹{gmp}", gmp_delta)
    with col3:
        st.metric("Issue Size", f"₹{ipo['issue_size_cr']}Cr")
    with col4:
        if ipo["subscription_times"] > 0:
            st.metric("Subscribed", f"{ipo['subscription_times']}x")
        else:
            # FIX 4: Format date as DD/MM/YY
            raw_date = ipo.get("open_date", "")
            try:
                from datetime import datetime
                d = datetime.strptime(raw_date, "%Y-%m-%d")
                display_date = d.strftime("%d/%m/%y")
            except Exception:
                display_date = raw_date
            st.metric("Opens", display_date)
    with col5:
        risk_delta = {"Low": "✓", "Low-Medium": "✓", "Medium": "~", "High": "⚠"}
        st.metric("Risk Level", ipo["risk"], risk_delta.get(ipo["risk"], ""))

    st.markdown("---")

    # ── TABS ─────────────────────────────────────────────────────────────────────
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🤖 AI Q&A", "📊 AI Scorecard", "🏭 Industry & Peers", "📈 Financials", "📰 News"
    ])

    # ── TAB 1: AI Q&A ────────────────────────────────────────────────────────────
    with tab1:
        st.markdown(f"""
        <div class='alert-green'>
            <strong>Ask anything about {ipo['company']}</strong> — financials, risks, promoters, valuation, 
            whether to subscribe, how it compares to peers, what the GMP signals, and more.
        </div>
        """, unsafe_allow_html=True)

        chat_key = f"chat_{ipo['id']}"
        if chat_key not in st.session_state.chat_histories:
            st.session_state.chat_histories[chat_key] = []

        # Suggested questions — store clicked question in session state to survive rerun
        pending_key = f"pending_q_{ipo['id']}"
        if pending_key not in st.session_state:
            st.session_state[pending_key] = None

        st.markdown("<div style='font-size:0.8rem; color:#8892a4; margin-bottom:8px;'>💡 Quick questions:</div>", unsafe_allow_html=True)
        q_cols = st.columns(3)
        suggested_qs = [
            "Should I subscribe to this IPO?",
            "What are the main red flags?",
            "Is the valuation reasonable?",
            "What does the GMP signal?",
            "Who are the promoters?",
            "How does revenue growth compare to peers?",
        ]
        for i, q in enumerate(suggested_qs):
            with q_cols[i % 3]:
                if st.button(q, key=f"sq_{ipo['id']}_{i}"):
                    st.session_state[pending_key] = q

        st.markdown("---")

        # Display chat history
        for msg in st.session_state.chat_histories[chat_key]:
            if msg["role"] == "user":
                st.markdown(f"<div class='chat-message-user'>👤 {msg['content']}</div>", unsafe_allow_html=True)
            else:
                st.markdown(f"<div class='chat-message-ai'>🤖 {msg['content']}</div>", unsafe_allow_html=True)

        # Input
        user_input = st.chat_input("Ask about this IPO...", key=f"chat_input_{ipo['id']}")

        # Resolve question — typed input takes priority, then pending suggested question
        question = user_input or st.session_state[pending_key]

        if question:
            st.session_state[pending_key] = None
            st.session_state.chat_histories[chat_key].append(
                {"role": "user", "content": question}
            )
            st.markdown(f"<div class='chat-message-user'>👤 {question}</div>", unsafe_allow_html=True)

            with st.spinner("🤖 Analyzing..."):
                try:
                    from utils.ai_utils import chat_with_ipo
                    response = chat_with_ipo(
                        st.session_state.api_key,
                        ipo,
                        st.session_state.chat_histories[chat_key][:-1],
                        question,
                    )
                    st.session_state.chat_histories[chat_key].append(
                        {"role": "assistant", "content": response}
                    )
                    st.markdown(f"<div class='chat-message-ai'>🤖 {response}</div>", unsafe_allow_html=True)
                except Exception as e:
                    st.session_state.chat_histories[chat_key].pop()
                    st.error(f"❌ AI Error: {str(e)}")

        if st.session_state.chat_histories.get(chat_key):
            if st.button("🗑 Clear Chat", key=f"clear_{ipo['id']}"):
                st.session_state.chat_histories[chat_key] = []
                st.rerun()

    # ── TAB 2: AI SCORECARD ──────────────────────────────────────────────────────
    with tab2:
        st.markdown("### AI Investment Scorecard")
        if st.button("🤖 Generate AI Scorecard", key=f"scorecard_{ipo['id']}"):
            with st.spinner("AI analyzing DRHP, financials, valuation..."):
                try:
                    from utils.ai_utils import get_ai_recommendation
                    result = get_ai_recommendation(st.session_state.api_key, ipo)
                    st.session_state[f"scorecard_result_{ipo['id']}"] = result
                except Exception as e:
                    st.error(f"Error: {e}")

        if f"scorecard_result_{ipo['id']}" in st.session_state:
            r = st.session_state[f"scorecard_result_{ipo['id']}"]
            _render_ai_scorecard(r, ipo)
        else:
            _render_static_scorecard(ipo)

    # ── TAB 3: INDUSTRY & PEERS ──────────────────────────────────────────────────
    with tab3:
        st.markdown("### Industry & Peer Comparison")
        
        # Peer comparison chart
        col_l, col_r = st.columns([1, 1])
        with col_l:
            st.markdown(f"""
            <div style='background:var(--bg-card); border:1px solid var(--border); border-radius:10px; padding:16px;'>
                <div style='font-size:0.75rem; color:#8892a4; text-transform:uppercase; letter-spacing:1px; margin-bottom:12px;'>Valuation vs Peers</div>
                <div style='font-size:2rem; font-weight:700; font-family: monospace; color:#4a9eff;'>{ipo['pe_ratio']}x</div>
                <div style='font-size:0.82rem; color:#8892a4;'>Company P/E</div>
                <div style='margin-top:12px; font-size:1.2rem; font-weight:600; font-family: monospace; color:#8892a4;'>{ipo['industry_pe']}x</div>
                <div style='font-size:0.82rem; color:#8892a4;'>Industry P/E</div>
                <div style='margin-top:12px; padding:8px 12px; background:rgba(0,212,170,0.1); border-radius:8px; font-size:0.85rem; color:#00d4aa;'>
                    Trading at {'discount' if ipo['pe_ratio'] < ipo['industry_pe'] else 'premium'} to industry: {abs(ipo['industry_pe'] - ipo['pe_ratio']):.1f}x
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        with col_r:
            st.markdown(f"""
            <div style='background:var(--bg-card); border:1px solid var(--border); border-radius:10px; padding:16px;'>
                <div style='font-size:0.75rem; color:#8892a4; text-transform:uppercase; letter-spacing:1px; margin-bottom:12px;'>Listed Peers</div>
                {''.join([f"<div style='padding:6px 0; border-bottom:1px solid #1e2d45; font-size:0.9rem; color:#e8edf5;'>🏢 {p}</div>" for p in ipo['peers']])}
                <div style='margin-top:12px; font-size:0.78rem; color:#8892a4;'>* Mainboard listed companies used for valuation benchmarking</div>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # AI Peer Analysis — always available (key loaded from secrets)
        if st.button("🤖 Get AI Industry Analysis", key=f"peer_{ipo['id']}"):
            with st.spinner("Comparing with industry and peers..."):
                try:
                    from utils.ai_utils import compare_with_industry
                    analysis = compare_with_industry(st.session_state.api_key, ipo)
                    st.session_state[f"peer_result_{ipo['id']}"] = analysis
                except Exception as e:
                    st.error(f"Error: {e}")

            result_text = st.session_state.get(f"peer_result_{ipo['id']}")
            if result_text:
                st.markdown(f"""
                <div class='chat-message-ai'>{result_text.replace(chr(10), '<br>')}</div>
                """, unsafe_allow_html=True)

    # ── TAB 4: FINANCIALS ────────────────────────────────────────────────────────
    with tab4:
        st.markdown("### Financial Performance")

        has_financials = (
            isinstance(ipo.get("revenue_cr"), list) and len(ipo["revenue_cr"]) >= 2 and
            isinstance(ipo.get("profit_cr"), list) and len(ipo["profit_cr"]) >= 2
        )

        if not has_financials:
            st.info(
                "📄 Financial data for this IPO is not yet available in our database. "
                "This is common for newly filed SME IPOs. "
                "Check the company's DRHP on the SEBI EFILING portal for audited financials."
            )
            c1, c2 = st.columns(2)
            with c1:
                st.metric("Issue Size", f"₹{ipo.get('issue_size_cr', '—')} Cr")
                st.metric("Issue Price", f"₹{ipo.get('issue_price', '—')}")
            with c2:
                st.metric("Exchange", ipo.get("exchange", "—"))
                st.metric("Promoter Holding", f"{ipo.get('promoter_holding', '—')}%" if ipo.get('promoter_holding') else "—")
        else:
            years = ipo.get("years") or [f"FY{22+i}" for i in range(len(ipo["revenue_cr"]))]

            col1, col2 = st.columns(2)
            with col1:
                fig = go.Figure()
                fig.add_trace(go.Bar(
                    x=years, y=ipo["revenue_cr"],
                    name="Revenue",
                    marker_color="#4a9eff",
                    text=[f"₹{v}Cr" for v in ipo["revenue_cr"]],
                    textposition="outside",
                ))
                fig.update_layout(
                    title="Revenue (₹ Cr)",
                    paper_bgcolor="#111827", plot_bgcolor="#111827",
                    font=dict(color="#8892a4", size=11),
                    title_font=dict(color="#e8edf5", size=13),
                    showlegend=False, height=280,
                    margin=dict(l=10, r=10, t=40, b=10),
                    xaxis=dict(gridcolor="#1e2d45"),
                    yaxis=dict(gridcolor="#1e2d45"),
                )
                st.plotly_chart(fig, use_container_width=True)

            with col2:
                fig2 = go.Figure()
                fig2.add_trace(go.Bar(
                    x=years, y=ipo["profit_cr"],
                    name="Net Profit",
                    marker_color="#00d4aa",
                    text=[f"₹{v}Cr" for v in ipo["profit_cr"]],
                    textposition="outside",
                ))
                fig2.update_layout(
                    title="Net Profit (₹ Cr)",
                    paper_bgcolor="#111827", plot_bgcolor="#111827",
                    font=dict(color="#8892a4", size=11),
                    title_font=dict(color="#e8edf5", size=13),
                    showlegend=False, height=280,
                    margin=dict(l=10, r=10, t=40, b=10),
                    xaxis=dict(gridcolor="#1e2d45"),
                    yaxis=dict(gridcolor="#1e2d45"),
                )
                st.plotly_chart(fig2, use_container_width=True)

            # Safe CAGR calculation
            try:
                n_years = max(len(ipo["revenue_cr"]) - 1, 1)
                rev_cagr = ((ipo["revenue_cr"][-1] / ipo["revenue_cr"][0]) ** (1/n_years) - 1) * 100
                profit_growth = ((ipo["profit_cr"][-1] / ipo["profit_cr"][0]) ** (1/n_years) - 1) * 100
                net_margin = (ipo["profit_cr"][-1] / ipo["revenue_cr"][-1]) * 100
                c1, c2, c3, c4 = st.columns(4)
                with c1:
                    st.metric("Revenue CAGR", f"{rev_cagr:.1f}%")
                with c2:
                    st.metric("Profit CAGR", f"{profit_growth:.1f}%")
                with c3:
                    st.metric("Net Margin", f"{net_margin:.1f}%")
                with c4:
                    st.metric("Promoter Holding", f"{ipo['promoter_holding']}%")
            except Exception:
                pass

    # ── TAB 5: NEWS ──────────────────────────────────────────────────────────────
    with tab5:
        st.markdown("### Latest News")
        news_items = NEWS.get(ipo["id"], [])
        if not news_items:
            st.info("No recent news found for this company.")
        else:
            for n in news_items:
                st.markdown(f"""
                <div style='background:var(--bg-card); border:1px solid var(--border); border-radius:10px; padding:16px; margin-bottom:12px;'>
                    <div style='font-size:0.75rem; color:#4a9eff; text-transform:uppercase; letter-spacing:0.8px; margin-bottom:6px;'>{n['source']} · {n['date']}</div>
                    <div style='font-size:0.95rem; font-weight:500; color:#e8edf5; line-height:1.5;'>{n['title']}</div>
                </div>
                """, unsafe_allow_html=True)


def _render_static_scorecard(ipo):
    rec = ipo["recommendation"]
    color = {"SUBSCRIBE": "#00d4aa", "AVOID": "#ff4757", "NEUTRAL": "#ffd32a"}.get(rec, "#8892a4")
    
    st.markdown(f"""
    <div style='text-align:center; padding:24px; background:var(--bg-card); border-radius:12px; margin-bottom:20px;'>
        <div style='font-size:3rem; font-weight:700; color:{color};'>{rec}</div>
        <div style='font-size:1rem; color:#8892a4; margin-top:8px;'>Risk Level: {ipo['risk']}</div>
        <div style='margin-top:16px; font-size:0.9rem; color:#e8edf5; max-width:500px; margin-left:auto; margin-right:auto; line-height:1.6;'>
            {ipo['summary']}
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("""<div style='font-size:0.85rem; color:#00d4aa; font-weight:600; margin-bottom:8px;'>✓ Key Positives</div>""", unsafe_allow_html=True)
        st.markdown(f"""<div class='alert-green' style='font-size:0.85rem; color:#e8edf5;'>{ipo['drhp_highlights']}</div>""", unsafe_allow_html=True)
    with col2:
        st.markdown("""<div style='font-size:0.85rem; color:#ff4757; font-weight:600; margin-bottom:8px;'>⚠ Key Risks</div>""", unsafe_allow_html=True)
        st.markdown(f"""<div class='alert-red' style='font-size:0.85rem; color:#e8edf5;'>{ipo['risks_text']}</div>""", unsafe_allow_html=True)
    
    st.markdown("""
    <div style='margin-top:16px; padding:12px; background:rgba(74,158,255,0.08); border-radius:8px; font-size:0.82rem; color:#8892a4; text-align:center;'>
        💡 Add your Claude API key to generate an AI-enhanced scorecard with deeper analysis
    </div>
    """, unsafe_allow_html=True)


def _render_ai_scorecard(r, ipo):
    verdict = r.get("verdict", "NEUTRAL")
    score = r.get("score", 5)
    color = {"SUBSCRIBE": "#00d4aa", "AVOID": "#ff4757", "NEUTRAL": "#ffd32a"}.get(verdict, "#8892a4")

    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.markdown(f"""
        <div style='text-align:center; padding:24px; background:var(--bg-card); border-radius:12px;'>
            <div style='font-size:2.5rem; font-weight:700; color:{color};'>{verdict}</div>
            <div style='font-size:1rem; color:#8892a4; margin-top:4px;'>Conviction: {r.get('conviction','')}</div>
            <div style='margin-top:16px; font-size:2.8rem; font-weight:700; font-family:monospace; color:{color};'>{score}<span style='font-size:1.2rem; color:#8892a4;'>/10</span></div>
            <div style='font-size:0.78rem; color:#8892a4; text-transform:uppercase; letter-spacing:1px;'>AI Score</div>
            <div style='margin-top:16px; font-size:0.82rem; color:#e8edf5; line-height:1.6; font-style:italic;'>"{r.get('one_liner','')}"</div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown("""<div style='font-size:0.85rem; color:#00d4aa; font-weight:600; margin-bottom:6px;'>📈 Bull Case</div>""", unsafe_allow_html=True)
        st.markdown(f"""<div class='alert-green' style='font-size:0.85rem;'>{r.get('bull_case','')}</div>""", unsafe_allow_html=True)
        
        st.markdown("""<div style='font-size:0.85rem; color:#ff4757; font-weight:600; margin-bottom:6px; margin-top:12px;'>📉 Bear Case</div>""", unsafe_allow_html=True)
        st.markdown(f"""<div class='alert-red' style='font-size:0.85rem;'>{r.get('bear_case','')}</div>""", unsafe_allow_html=True)

    st.markdown("---")
    
    col3, col4 = st.columns(2)
    with col3:
        st.markdown("**✅ Positives**")
        for p in r.get("positives", []):
            st.markdown(f"<div style='font-size:0.85rem; color:#00d4aa; padding:3px 0;'>+ {p}</div>", unsafe_allow_html=True)
        st.markdown(f"<br><div style='font-size:0.85rem; color:#8892a4;'><strong>Valuation:</strong> {r.get('valuation_view','')}</div>", unsafe_allow_html=True)
        st.markdown(f"<div style='font-size:0.85rem; color:#8892a4; margin-top:6px;'><strong>GMP Signal:</strong> {r.get('gmp_view','')}</div>", unsafe_allow_html=True)
    
    with col4:
        st.markdown("**🚩 Red Flags**")
        flags = r.get("red_flags", [])
        if flags:
            for f in flags:
                st.markdown(f"<div style='font-size:0.85rem; color:#ff4757; padding:3px 0;'>⚠ {f}</div>", unsafe_allow_html=True)
        else:
            st.markdown("<div style='font-size:0.85rem; color:#00d4aa;'>No major red flags identified</div>", unsafe_allow_html=True)
        
        st.markdown(f"<br><div style='font-size:0.85rem; color:#8892a4;'><strong>Suitable for:</strong> {r.get('suitable_for','')}</div>", unsafe_allow_html=True)
