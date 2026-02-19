"""GMP Tracker page — Grey Market Premium trends for all active/upcoming IPOs"""
import streamlit as st
import plotly.graph_objects as go


def render(all_ipos, gmp_history):
    st.markdown("<div class='app-title' style='margin-bottom:8px;'>📊 GMP <span style='color:#00d4aa;'>Tracker</span></div>", unsafe_allow_html=True)
    st.markdown("<div class='app-subtitle' style='margin-bottom:24px;'>GREY MARKET PREMIUM · REAL-TIME TRENDS · LISTING SIGNAL</div>", unsafe_allow_html=True)

    st.markdown("""
    <div class='alert-yellow' style='margin-bottom:24px;'>
        <strong>What is GMP?</strong> Grey Market Premium is the price at which IPO shares are traded unofficially before listing. 
        High GMP suggests strong demand, but it's speculative and not always accurate — check our Historical Data to see how often GMP predictions come true.
    </div>
    """, unsafe_allow_html=True)

    # Summary cards
    cols = st.columns(len(all_ipos))
    for idx, ipo in enumerate(all_ipos):
        with cols[idx]:
            gmp_color = "#00d4aa" if ipo["gmp"] > 0 else ("#ff4757" if ipo["gmp"] < 0 else "#ffd32a")
            sign = "+" if ipo["gmp"] > 0 else ""
            st.markdown(f"""
            <div style='background:var(--bg-card); border:1px solid var(--border); border-radius:10px; padding:14px; text-align:center;'>
                <div style='font-size:0.72rem; color:#8892a4; text-transform:uppercase; letter-spacing:0.8px; margin-bottom:6px;'>{ipo['company'].split()[0]}</div>
                <div style='font-size:1.6rem; font-weight:700; font-family:monospace; color:{gmp_color};'>{sign}₹{ipo['gmp']}</div>
                <div style='font-size:0.8rem; color:{gmp_color};'>{sign}{ipo['gmp_percent']:.1f}%</div>
                <div style='font-size:0.72rem; color:#8892a4; margin-top:6px;'>{ipo['subscription_status']}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # GMP Trend Charts
    st.markdown("### GMP Trend Charts")
    
    col1, col2 = st.columns(2)
    
    for idx, ipo in enumerate(all_ipos):
        history = gmp_history.get(ipo["id"], [])
        if not history:
            continue
        
        container = col1 if idx % 2 == 0 else col2
        
        with container:
            days = [h["label"] for h in history]
            gmps = [h["gmp"] for h in history]
            
            line_color = "#00d4aa" if gmps[-1] > 0 else "#ff4757"
            fill_color = "rgba(0,212,170,0.1)" if gmps[-1] > 0 else "rgba(255,71,87,0.1)"
            
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=days, y=gmps,
                mode="lines+markers+text",
                text=[f"₹{g}" for g in gmps],
                textposition="top center",
                line=dict(color=line_color, width=2.5),
                fill="tozeroy",
                fillcolor=fill_color,
                marker=dict(size=8, color=line_color),
            ))
            
            fig.add_hline(y=0, line_dash="dash", line_color="#8892a4", opacity=0.5)
            
            fig.update_layout(
                title=dict(text=f"{ipo['company'][:30]} — GMP Trend (₹{ipo['issue_price']} issue)", font=dict(color="#e8edf5", size=12)),
                paper_bgcolor="#111827",
                plot_bgcolor="#111827",
                font=dict(color="#8892a4", size=10),
                height=240,
                margin=dict(l=10, r=10, t=40, b=10),
                xaxis=dict(gridcolor="#1e2d45"),
                yaxis=dict(gridcolor="#1e2d45", title="GMP (₹)"),
                showlegend=False,
            )
            
            st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")
    
    # GMP Interpretation Guide
    st.markdown("### How to Interpret GMP")
    
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("""
        <div class='alert-green'>
            <strong style='color:#00d4aa;'>GMP > 20% 🔥</strong><br>
            <span style='font-size:0.85rem;'>Strong demand. Market expects significant listing gains. 
            But beware — oversubscription can lead to profit-booking on day 1.</span>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown("""
        <div class='alert-yellow'>
            <strong style='color:#ffd32a;'>GMP 5–20% ✓</strong><br>
            <span style='font-size:0.85rem;'>Healthy interest. Moderate listing gain expected. 
            More sustainable than very high GMP IPOs. Good signal for fundamentally strong cos.</span>
        </div>
        """, unsafe_allow_html=True)
    with c3:
        st.markdown("""
        <div class='alert-red'>
            <strong style='color:#ff4757;'>GMP < 0% ⚠</strong><br>
            <span style='font-size:0.85rem;'>Weak/negative sentiment. Market expects listing below issue price. 
            Strong signal to avoid unless fundamentals strongly support investment.</span>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("""
    <div style='margin-top:16px; padding:12px; background:var(--bg-card); border-radius:8px; font-size:0.82rem; color:#8892a4; line-height:1.6;'>
        ⚠️ <strong>GMP Disclaimer:</strong> Grey market data is unofficial and traded in unregulated markets. 
        GMP can be manipulated and doesn't always predict listing price. 
        Always check our <strong>Historical Data</strong> tab to see the actual GMP accuracy rate (currently ~62%).
    </div>
    """, unsafe_allow_html=True)
