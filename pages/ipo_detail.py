"""IPO Detail page — AI Q&A, Scorecard, Industry Analysis, Financials, News"""
import streamlit as st
import plotly.graph_objects as go
import sys, os
from datetime import datetime
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from data.ipo_data import NEWS, GMP_HISTORY


def _fmt_date(raw):
    try:
        return datetime.strptime(str(raw), "%Y-%m-%d").strftime("%d/%m/%y")
    except:
        return str(raw)


def _gmp_pct(ipo):
    try:
        return round(float(ipo.get("gmp") or 0) / float(ipo.get("issue_price") or 1) * 100, 1)
    except:
        return 0.0


def render(all_ipos):
    # ── BACK BUTTON ──────────────────────────────────────────────────────────
    if st.button("← Back to Dashboard", key="back_btn"):
        st.session_state.current_page = "🏠 Dashboard"
        st.rerun()

    st.markdown("<div style='font-size:1.5rem;font-weight:700;margin:8px 0 2px;'>🔍 IPO Deep Dive</div>", unsafe_allow_html=True)
    st.markdown("<div style='font-size:0.78rem;color:#8892a4;margin-bottom:20px;letter-spacing:1px;'>AI-POWERED ANALYSIS · DRHP Q&A · PEER COMPARISON</div>", unsafe_allow_html=True)

    # IPO Selector
    ipo_names = [i["company"] for i in all_ipos]
    default_idx = 0
    if st.session_state.get("selected_ipo_id"):
        for idx, ipo in enumerate(all_ipos):
            if ipo["id"] == st.session_state.selected_ipo_id:
                default_idx = idx
                break

    selected_name = st.selectbox("Select IPO to analyze", ipo_names, index=default_idx)
    ipo = next(i for i in all_ipos if i["company"] == selected_name)

    st.markdown("---")

    # ── OVERVIEW METRICS ─────────────────────────────────────────────────────
    gmp_pct = _gmp_pct(ipo)
    gmp     = float(ipo.get("gmp") or 0)
    gmp_sign = "+" if gmp >= 0 else ""

    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("Issue Price", f"₹{ipo.get('issue_price', '—')}")
    with col2:
        st.metric("GMP", f"₹{gmp}", f"{gmp_sign}{gmp_pct}% vs issue price")
    with col3:
        st.metric("Issue Size", f"₹{ipo.get('issue_size_cr','—')}Cr")
    with col4:
        if ipo.get("subscription_times", 0) > 0:
            st.metric("Subscribed", f"{ipo['subscription_times']}x")
        else:
            st.metric("Opens", _fmt_date(ipo.get("open_date", "")))
    with col5:
        risk = ipo.get("risk", "—")
        risk_delta = {"Low": "✓ Low Risk", "Low-Medium": "✓", "Medium": "~ Medium", "High": "⚠ High"}
        st.metric("Risk Level", risk, risk_delta.get(risk, ""))

    st.markdown("---")

    # ── TABS ─────────────────────────────────────────────────────────────────
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🤖 AI Q&A", "📊 AI Scorecard", "🏭 Industry & Peers", "📈 Financials", "📰 News"
    ])

    # ── TAB 1: AI Q&A ────────────────────────────────────────────────────────
    with tab1:
        st.markdown(f"""
        <div class='alert-green'>
            <strong>Ask anything about {ipo['company']}</strong> — financials, risks, promoters, 
            valuation, whether to subscribe, GMP signals, and more.
        </div>
        """, unsafe_allow_html=True)

        chat_key  = f"chat_{ipo['id']}"
        pending_key = f"pending_q_{ipo['id']}"
        if chat_key not in st.session_state.chat_histories:
            st.session_state.chat_histories[chat_key] = []
        if pending_key not in st.session_state:
            st.session_state[pending_key] = None

        st.markdown("<div style='font-size:0.8rem;color:#8892a4;margin-bottom:8px;'>💡 Quick questions:</div>", unsafe_allow_html=True)
        suggested_qs = [
            "Should I subscribe to this IPO?",
            "What are the main red flags?",
            "Is the valuation reasonable?",
            "What does the GMP signal?",
            "Who are the promoters?",
            "How does revenue growth compare to peers?",
        ]
        q_cols = st.columns(3)
        for i, q in enumerate(suggested_qs):
            with q_cols[i % 3]:
                if st.button(q, key=f"sq_{ipo['id']}_{i}"):
                    st.session_state[pending_key] = q

        st.markdown("---")

        for msg in st.session_state.chat_histories[chat_key]:
            css = "chat-message-user" if msg["role"] == "user" else "chat-message-ai"
            icon = "👤" if msg["role"] == "user" else "🤖"
            st.markdown(f"<div class='{css}'>{icon} {msg['content']}</div>", unsafe_allow_html=True)

        user_input = st.chat_input("Ask about this IPO...", key=f"chat_input_{ipo['id']}")
        question = user_input or st.session_state[pending_key]

        if question:
            st.session_state[pending_key] = None
            st.session_state.chat_histories[chat_key].append({"role": "user", "content": question})
            st.markdown(f"<div class='chat-message-user'>👤 {question}</div>", unsafe_allow_html=True)
            with st.spinner("🤖 Analyzing..."):
                try:
                    from utils.ai_utils import chat_with_ipo
                    response = chat_with_ipo(st.session_state.api_key, ipo,
                                            st.session_state.chat_histories[chat_key][:-1], question)
                    st.session_state.chat_histories[chat_key].append({"role": "assistant", "content": response})
                    st.markdown(f"<div class='chat-message-ai'>🤖 {response}</div>", unsafe_allow_html=True)
                except Exception as e:
                    st.session_state.chat_histories[chat_key].pop()
                    st.error(f"❌ Error: {e}")

        if st.session_state.chat_histories.get(chat_key):
            if st.button("🗑 Clear Chat", key=f"clear_{ipo['id']}"):
                st.session_state.chat_histories[chat_key] = []
                st.rerun()

    # ── TAB 2: AI SCORECARD ──────────────────────────────────────────────────
    with tab2:
        st.markdown("### 📊 AI Investment Scorecard")

        # Auto-generate scorecard on first view (cached in session state)
        scorecard_key = f"scorecard_result_{ipo['id']}"
        if scorecard_key not in st.session_state:
            with st.spinner("🤖 Generating AI scorecard..."):
                try:
                    from utils.ai_utils import get_ai_recommendation
                    result = get_ai_recommendation(st.session_state.api_key, ipo)
                    st.session_state[scorecard_key] = result
                except Exception as e:
                    st.session_state[scorecard_key] = None
                    st.error(f"Error generating scorecard: {e}")

        if st.session_state.get(scorecard_key):
            _render_ai_scorecard(st.session_state[scorecard_key], ipo)
        else:
            _render_static_scorecard(ipo)

        if st.button("🔄 Regenerate Scorecard", key=f"regen_{ipo['id']}"):
            if scorecard_key in st.session_state:
                del st.session_state[scorecard_key]
            st.rerun()

    # ── TAB 3: INDUSTRY & PEERS ──────────────────────────────────────────────
    with tab3:
        st.markdown("### 🏭 Industry & Peer Comparison")

        col_l, col_r = st.columns(2)
        pe = ipo.get('pe_ratio') or 0
        ind_pe = ipo.get('industry_pe') or 0
        with col_l:
            disc_prem = 'discount' if (pe and ind_pe and pe < ind_pe) else 'premium'
            diff = abs((ind_pe or 0) - (pe or 0))
            st.markdown(f"""
            <div style='background:var(--bg-card);border:1px solid var(--border);border-radius:10px;padding:16px;'>
                <div style='font-size:0.75rem;color:var(--text-muted);text-transform:uppercase;letter-spacing:1px;margin-bottom:12px;'>Valuation vs Peers</div>
                <div style='font-size:2rem;font-weight:700;font-family:monospace;color:var(--blue);'>{pe or '—'}x</div>
                <div style='font-size:0.82rem;color:var(--text-muted);'>Company P/E</div>
                <div style='margin-top:12px;font-size:1.2rem;font-weight:600;font-family:monospace;color:var(--text-muted);'>{ind_pe or '—'}x</div>
                <div style='font-size:0.82rem;color:var(--text-muted);'>Industry P/E</div>
                {f"<div style='margin-top:12px;padding:8px 12px;background:rgba(0,180,148,0.1);border-radius:8px;font-size:0.85rem;color:var(--green);'>Trading at {disc_prem} to industry: {diff:.1f}x</div>" if pe and ind_pe else ""}
            </div>
            """, unsafe_allow_html=True)

        peers = ipo.get('peers') or []
        with col_r:
            peers_html = ''.join([f"<div style='padding:6px 0;border-bottom:1px solid var(--border);font-size:0.9rem;'>🏢 {p}</div>" for p in peers]) if peers else "<div style='color:var(--text-muted);font-size:0.85rem;'>Peer data available after DRHP scrape</div>"
            st.markdown(f"""
            <div style='background:var(--bg-card);border:1px solid var(--border);border-radius:10px;padding:16px;'>
                <div style='font-size:0.75rem;color:var(--text-muted);text-transform:uppercase;letter-spacing:1px;margin-bottom:12px;'>Listed Peers</div>
                {peers_html}
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # Auto-generate industry analysis (cached)
        peer_key = f"peer_result_{ipo['id']}"
        if peer_key not in st.session_state:
            with st.spinner("🤖 Analysing industry & peers..."):
                try:
                    from utils.ai_utils import compare_with_industry
                    analysis = compare_with_industry(st.session_state.api_key, ipo)
                    st.session_state[peer_key] = analysis
                except Exception as e:
                    st.session_state[peer_key] = f"Could not generate analysis: {e}"

        if st.session_state.get(peer_key):
            st.markdown(f"<div class='chat-message-ai'>{st.session_state[peer_key].replace(chr(10), '<br>')}</div>", unsafe_allow_html=True)

        if st.button("🔄 Refresh Analysis", key=f"refresh_peer_{ipo['id']}"):
            if peer_key in st.session_state:
                del st.session_state[peer_key]
            st.rerun()

    # ── TAB 4: FINANCIALS ────────────────────────────────────────────────────
    with tab4:
        st.markdown("### 📈 Financial Performance")
        has_financials = (
            isinstance(ipo.get("revenue_cr"), list) and len(ipo["revenue_cr"]) >= 2 and
            isinstance(ipo.get("profit_cr"), list) and len(ipo["profit_cr"]) >= 2
        )
        if not has_financials:
            st.info("📄 Financial data not yet extracted. Run `drhp_scraper.py` to pull financials from the DRHP PDF.")
            c1, c2 = st.columns(2)
            with c1:
                st.metric("Issue Size", f"₹{ipo.get('issue_size_cr','—')} Cr")
                st.metric("Issue Price", f"₹{ipo.get('issue_price','—')}")
            with c2:
                st.metric("Exchange", ipo.get("exchange","—"))
                ph = ipo.get('promoter_holding')
                st.metric("Promoter Holding", f"{ph}%" if ph else "—")
        else:
            years = ipo.get("years") or [f"FY{22+i}" for i in range(len(ipo["revenue_cr"]))]
            col1, col2 = st.columns(2)
            with col1:
                fig = go.Figure()
                fig.add_trace(go.Bar(x=years, y=ipo["revenue_cr"], name="Revenue",
                    marker_color="#4a9eff", text=[f"₹{v}Cr" for v in ipo["revenue_cr"]], textposition="outside"))
                fig.update_layout(title="Revenue (₹ Cr)", paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)", showlegend=False, height=280,
                    margin=dict(l=10,r=10,t=40,b=10))
                st.plotly_chart(fig, use_container_width=True)
            with col2:
                fig2 = go.Figure()
                colors = ["#00d4aa" if v >= 0 else "#ff4757" for v in ipo["profit_cr"]]
                fig2.add_trace(go.Bar(x=years, y=ipo["profit_cr"], name="Profit",
                    marker_color=colors, text=[f"₹{v}Cr" for v in ipo["profit_cr"]], textposition="outside"))
                fig2.update_layout(title="Net Profit (₹ Cr)", paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)", showlegend=False, height=280,
                    margin=dict(l=10,r=10,t=40,b=10))
                st.plotly_chart(fig2, use_container_width=True)

            try:
                rev = ipo["revenue_cr"]
                prof = ipo["profit_cr"]
                if len(rev) >= 2 and rev[0] > 0:
                    n = len(rev) - 1
                    rev_cagr = round(((rev[-1]/rev[0])**(1/n) - 1)*100, 1)
                    c1,c2,c3,c4 = st.columns(4)
                    with c1: st.metric("Revenue CAGR", f"{rev_cagr}%")
                    with c2: st.metric("Latest Revenue", f"₹{rev[-1]}Cr")
                    with c3: st.metric("Latest Profit", f"₹{prof[-1]}Cr")
                    with c4:
                        nm = round(prof[-1]/rev[-1]*100,1) if rev[-1] else 0
                        st.metric("Net Margin", f"{nm}%")
            except Exception:
                pass

    # ── TAB 5: NEWS ──────────────────────────────────────────────────────────
    with tab5:
        st.markdown("### 📰 Latest News & Updates")
        news_items = NEWS.get(ipo["id"], [])
        if not news_items:
            # Auto-generate news summary via AI
            news_key = f"news_{ipo['id']}"
            if news_key not in st.session_state:
                with st.spinner("🤖 Fetching latest news summary..."):
                    try:
                        from utils.ai_utils import chat_with_ipo
                        news_prompt = f"Summarise what is publicly known about {ipo['company']} IPO — any news, analyst views, subscription trends, GMP movement, or market sentiment. Keep it concise and factual."
                        news_resp = chat_with_ipo(st.session_state.api_key, ipo, [], news_prompt)
                        st.session_state[news_key] = news_resp
                    except Exception as e:
                        st.session_state[news_key] = None

            if st.session_state.get(news_key):
                st.markdown(f"<div class='chat-message-ai'>🤖 {st.session_state[news_key].replace(chr(10),'<br>')}</div>", unsafe_allow_html=True)
                if st.button("🔄 Refresh News", key=f"refresh_news_{ipo['id']}"):
                    del st.session_state[news_key]
                    st.rerun()
            else:
                st.info("No news found for this IPO yet.")
        else:
            for n in news_items:
                st.markdown(f"""
                <div style='background:var(--bg-card);border:1px solid var(--border);border-radius:10px;padding:16px;margin-bottom:12px;'>
                    <div style='font-size:0.75rem;color:var(--blue);text-transform:uppercase;letter-spacing:0.8px;margin-bottom:6px;'>{n['source']} · {n['date']}</div>
                    <div style='font-size:0.95rem;font-weight:500;line-height:1.5;'>{n['title']}</div>
                </div>
                """, unsafe_allow_html=True)


def _render_static_scorecard(ipo):
    rec   = ipo.get("recommendation", "NEUTRAL")
    color = {"SUBSCRIBE": "#00d4aa", "AVOID": "#ff4757", "NEUTRAL": "#ffd32a"}.get(rec, "#8892a4")
    st.markdown(f"""
    <div style='text-align:center;padding:24px;background:var(--bg-card);border-radius:12px;margin-bottom:20px;'>
        <div style='font-size:3rem;font-weight:700;color:{color};'>{rec}</div>
        <div style='font-size:1rem;color:var(--text-muted);margin-top:8px;'>Risk Level: {ipo.get('risk','—')}</div>
        <div style='margin-top:16px;font-size:0.9rem;max-width:500px;margin-left:auto;margin-right:auto;line-height:1.6;'>
            {ipo.get('summary','No summary available.')}
        </div>
    </div>
    """, unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("<div style='font-size:0.85rem;color:var(--green);font-weight:600;margin-bottom:8px;'>✓ Key Positives</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='alert-green' style='font-size:0.85rem;'>{ipo.get('drhp_highlights','Run DRHP scraper to get detailed analysis.')}</div>", unsafe_allow_html=True)
    with col2:
        st.markdown("<div style='font-size:0.85rem;color:var(--red);font-weight:600;margin-bottom:8px;'>⚠ Key Risks</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='alert-red' style='font-size:0.85rem;'>{ipo.get('risks_text','Run DRHP scraper to get risk factors.')}</div>", unsafe_allow_html=True)


def _render_ai_scorecard(r, ipo):
    verdict = r.get("verdict", "NEUTRAL")
    score   = r.get("score", 5)
    color   = {"SUBSCRIBE": "#00d4aa", "AVOID": "#ff4757", "NEUTRAL": "#ffd32a"}.get(verdict, "#8892a4")

    col1, col2 = st.columns([1, 2])
    with col1:
        st.markdown(f"""
        <div style='text-align:center;padding:24px;background:var(--bg-card);border-radius:12px;'>
            <div style='font-size:2.5rem;font-weight:700;color:{color};'>{verdict}</div>
            <div style='font-size:1rem;color:var(--text-muted);margin-top:4px;'>Conviction: {r.get('conviction','')}</div>
            <div style='margin-top:16px;font-size:2.8rem;font-weight:700;font-family:monospace;color:{color};'>{score}<span style='font-size:1.2rem;color:var(--text-muted);'>/10</span></div>
            <div style='font-size:0.78rem;color:var(--text-muted);text-transform:uppercase;letter-spacing:1px;'>AI Score</div>
            <div style='margin-top:16px;font-size:0.82rem;line-height:1.6;font-style:italic;'>"{r.get('one_liner','')}"</div>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown("<div style='font-size:0.85rem;color:var(--green);font-weight:600;margin-bottom:6px;'>📈 Bull Case</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='alert-green' style='font-size:0.85rem;'>{r.get('bull_case','')}</div>", unsafe_allow_html=True)
        st.markdown("<div style='font-size:0.85rem;color:var(--red);font-weight:600;margin-bottom:6px;margin-top:12px;'>📉 Bear Case</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='alert-red' style='font-size:0.85rem;'>{r.get('bear_case','')}</div>", unsafe_allow_html=True)

    st.markdown("---")
    col3, col4 = st.columns(2)
    with col3:
        st.markdown("**✅ Positives**")
        for p in r.get("positives", []):
            st.markdown(f"<div style='font-size:0.85rem;color:var(--green);padding:3px 0;'>+ {p}</div>", unsafe_allow_html=True)
        st.markdown(f"<br><div style='font-size:0.85rem;color:var(--text-muted);'><strong>Valuation:</strong> {r.get('valuation_view','')}</div>", unsafe_allow_html=True)
        st.markdown(f"<div style='font-size:0.85rem;color:var(--text-muted);margin-top:6px;'><strong>GMP Signal:</strong> {r.get('gmp_view','')}</div>", unsafe_allow_html=True)
    with col4:
        st.markdown("**🚩 Red Flags**")
        for f in r.get("red_flags", []) or ["No major red flags identified"]:
            color_f = "var(--red)" if r.get("red_flags") else "var(--green)"
            st.markdown(f"<div style='font-size:0.85rem;color:{color_f};padding:3px 0;'>⚠ {f}</div>", unsafe_allow_html=True)
        st.markdown(f"<br><div style='font-size:0.85rem;color:var(--text-muted);'><strong>Suitable for:</strong> {r.get('suitable_for','')}</div>", unsafe_allow_html=True)
