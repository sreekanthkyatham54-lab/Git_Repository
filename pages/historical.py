# v3.0 - top nav
"""Historical IPO page — Did GMP predictions come true?"""
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px


def render(historical_ipos):
    st.markdown("### 📜 Historical IPO Data")
    st.markdown("<div style='font-size:0.75rem;color:var(--muted);text-transform:uppercase;letter-spacing:1.5px;margin-bottom:20px;'>DID GMP COME TRUE? · LISTING PERFORMANCE · TRACK RECORD</div>", unsafe_allow_html=True)

    # Only count IPOs that have GMP accuracy data
    ipos_with_gmp = [i for i in historical_ipos if i.get("gmp_accurate") is not None]
    total = len(historical_ipos)
    total_with_gmp = len(ipos_with_gmp)
    gmp_accurate = sum(1 for i in ipos_with_gmp if i["gmp_accurate"])
    positive_listings = sum(1 for i in historical_ipos if (i.get("actual_listing_gain") or 0) > 0)
    avg_listing_gain = sum((i.get("actual_listing_gain") or 0) for i in historical_ipos) / total if total else 0
    big_winners = sum(1 for i in historical_ipos if (i.get("actual_listing_gain") or 0) > 30)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        acc_pct = f"{(gmp_accurate/total_with_gmp)*100:.0f}%" if total_with_gmp else "N/A"
        st.metric("GMP Accuracy Rate", acc_pct, f"{gmp_accurate}/{total_with_gmp} with GMP data")
    with col2:
        st.metric("Positive Listings", f"{(positive_listings/total)*100:.0f}%", f"{positive_listings}/{total} profitable")
    with col3:
        st.metric("Avg Listing Gain", f"{avg_listing_gain:.1f}%")
    with col4:
        st.metric("Big Winners (>30%)", big_winners, f"out of {total}")

    st.markdown("---")

    # GMP Predicted vs Actual Listing Chart
    st.markdown("### GMP Prediction vs Actual Listing Gain")
    
    companies = [i["company"].split()[0] + " " + i["company"].split()[1] if len(i["company"].split()) > 1 else i["company"] for i in historical_ipos]
    gmp_predictions = [i["gmp_predicted_gain"] for i in historical_ipos]
    actual_gains = [i["actual_listing_gain"] for i in historical_ipos]
    accurate_colors = ["#00d4aa" if i["gmp_accurate"] else "#ff4757" for i in historical_ipos]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="GMP Predicted Gain",
        x=companies,
        y=gmp_predictions,
        marker_color="#4a9eff",
        opacity=0.7,
    ))
    fig.add_trace(go.Bar(
        name="Actual Listing Gain",
        x=companies,
        y=actual_gains,
        marker_color=accurate_colors,
        opacity=0.9,
    ))
    fig.add_hline(y=0, line_dash="solid", line_color="#8892a4", opacity=0.3)
    
    fig.update_layout(
        barmode="group",
        paper_bgcolor="#111827",
        plot_bgcolor="#111827",
        font=dict(color="#8892a4", size=10),
        legend=dict(font=dict(color="#e8edf5"), bgcolor="#111827"),
        height=320,
        margin=dict(l=10, r=10, t=20, b=10),
        xaxis=dict(gridcolor="#1e2d45", tickangle=-20),
        yaxis=dict(gridcolor="#1e2d45", title="Gain %"),
    )
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    # IPO Cards Table
    st.markdown("### IPO Listing Performance History")
    
    # Filter
    col_f1, col_f2 = st.columns([2, 2])
    with col_f1:
        accuracy_filter = st.selectbox("GMP Accuracy", ["All", "GMP Accurate", "GMP Missed"])
    with col_f2:
        performance_filter = st.selectbox("Listing Performance", ["All", "Profitable", "Loss"])

    filtered = historical_ipos.copy()
    if accuracy_filter == "GMP Accurate":
        filtered = [i for i in filtered if i["gmp_accurate"]]
    elif accuracy_filter == "GMP Missed":
        filtered = [i for i in filtered if not i["gmp_accurate"]]
    if performance_filter == "Profitable":
        filtered = [i for i in filtered if i["actual_listing_gain"] > 0]
    elif performance_filter == "Loss":
        filtered = [i for i in filtered if i["actual_listing_gain"] < 0]

    for ipo in filtered:
        listing_gain = ipo.get("actual_listing_gain") or 0
        listing_color = "#00d4aa" if listing_gain > 0 else "#ff4757"
        listing_sign = "+" if listing_gain > 0 else ""
        
        gmp_val = ipo.get("gmp_before_listing")
        gmp_pred = ipo.get("gmp_predicted_gain")
        if gmp_val is not None and gmp_val != 0:
            gmp_sign = "+" if gmp_val > 0 else ""
            gmp_display = f"{gmp_sign}₹{gmp_val} ({gmp_sign}{gmp_pred:.1f}%)" if gmp_pred else f"{gmp_sign}₹{gmp_val}"
            gmp_color = "#4a9eff"
        else:
            gmp_display = "N/A"
            gmp_color = "#8892a4"

        gmp_acc = ipo.get("gmp_accurate")
        if gmp_acc is True:
            accuracy_badge = "<span style='background:rgba(0,212,170,0.15);color:#00d4aa;border:1px solid rgba(0,212,170,0.3);padding:2px 10px;border-radius:10px;font-size:0.72rem;'>✓ GMP Accurate</span>"
        elif gmp_acc is False:
            accuracy_badge = "<span style='background:rgba(255,71,87,0.15);color:#ff4757;border:1px solid rgba(255,71,87,0.3);padding:2px 10px;border-radius:10px;font-size:0.72rem;'>✗ GMP Missed</span>"
        else:
            accuracy_badge = "<span style='background:rgba(136,146,164,0.15);color:#8892a4;border:1px solid rgba(136,146,164,0.3);padding:2px 10px;border-radius:10px;font-size:0.72rem;'>— No GMP Data</span>"

        listing_p = ipo.get("listing_price", 0)
        current_p = ipo.get("current_price", listing_p)
        current_vs_listing = ((current_p - listing_p) / listing_p) * 100 if listing_p else 0
        current_sign = "+" if current_vs_listing >= 0 else ""
        
        st.markdown(f"""
        <div style='background:var(--card); border:1px solid var(--border); border-radius:12px; padding:18px; margin-bottom:14px;'>
            <div style='display:flex; justify-content:space-between; align-items:flex-start;'>
                <div>
                    <div style='font-size:1rem; font-weight:600; margin-bottom:4px;'>{ipo['company']}</div>
                    <div style='font-size:0.75rem; color:var(--muted); text-transform:uppercase; letter-spacing:0.8px; margin-bottom:10px;'>{ipo.get('sector','—')} · {ipo.get('exchange','—')} · Listed {ipo.get('listing_date','—')}</div>
                </div>
                <div>{accuracy_badge}</div>
            </div>
            <div style='display:flex; gap:20px; flex-wrap:wrap;'>
                <div>
                    <div style='font-size:0.7rem; color:var(--muted); text-transform:uppercase; letter-spacing:0.8px; margin-bottom:2px;'>Issue Price</div>
                    <div style='font-size:0.95rem; font-weight:600; font-family:monospace;'>₹{ipo.get('issue_price','—')}</div>
                </div>
                <div>
                    <div style='font-size:0.7rem; color:var(--muted); text-transform:uppercase; letter-spacing:0.8px; margin-bottom:2px;'>GMP Before Listing</div>
                    <div style='font-size:0.95rem; font-weight:600; font-family:monospace; color:{gmp_color};'>{gmp_display}</div>
                </div>
                <div>
                    <div style='font-size:0.7rem; color:var(--muted); text-transform:uppercase; letter-spacing:0.8px; margin-bottom:2px;'>Listing Price</div>
                    <div style='font-size:0.95rem; font-weight:600; font-family:monospace;'>₹{listing_p}</div>
                </div>
                <div>
                    <div style='font-size:0.7rem; color:var(--muted); text-transform:uppercase; letter-spacing:0.8px; margin-bottom:2px;'>Listing Gain</div>
                    <div style='font-size:0.95rem; font-weight:700; font-family:monospace; color:{listing_color};'>{listing_sign}{listing_gain:.1f}%</div>
                </div>
                <div>
                    <div style='font-size:0.7rem; color:var(--muted); text-transform:uppercase; letter-spacing:0.8px; margin-bottom:2px;'>Current Price</div>
                    <div style='font-size:0.95rem; font-weight:600; font-family:monospace;'>₹{current_p} <span style='font-size:0.8rem; color:{"#00d4aa" if current_vs_listing >= 0 else "#ff4757"};'>({current_sign}{current_vs_listing:.1f}% from listing)</span></div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")
    
    # GMP accuracy summary
    st.markdown("### GMP Accuracy Analysis")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        # Pie chart
        fig_pie = go.Figure(go.Pie(
            labels=["GMP Accurate", "GMP Missed"],
            values=[gmp_accurate, total - gmp_accurate],
            marker=dict(colors=["#00d4aa", "#ff4757"]),
            hole=0.6,
            textfont=dict(color="#e8edf5"),
        ))
        fig_pie.update_layout(
            paper_bgcolor="#111827",
            font=dict(color="#8892a4"),
            legend=dict(font=dict(color="#e8edf5"), bgcolor="#111827"),
            height=260,
            margin=dict(l=10, r=10, t=20, b=10),
            annotations=[dict(text=f"{(gmp_accurate/total)*100:.0f}%", x=0.5, y=0.5, font_size=22, font_color="#00d4aa", showarrow=False)],
        )
        st.plotly_chart(fig_pie, use_container_width=True)
    
    with col2:
        st.markdown("""
        <div style='padding:16px;'>
            <div style='font-size:0.9rem; color:#e8edf5; line-height:1.8;'>
                <strong style='color:#00d4aa;'>Key Takeaways from GMP History:</strong><br><br>
                ✓ GMP correctly predicted listing direction in <strong>~62%</strong> of cases<br><br>
                ✓ GMP is more reliable when <strong>subscription > 5x</strong> AND GMP > 15%<br><br>
                ⚠ GMP can be <strong>manipulated</strong> — Mangal Compusolution listed +86% vs GMP of +25%<br><br>
                ⚠ Negative GMP was accurate in all cases (100%) — strong avoid signal<br><br>
                📊 Best strategy: Use GMP as <strong>one signal</strong>, not the only signal
            </div>
        </div>
        """, unsafe_allow_html=True)
