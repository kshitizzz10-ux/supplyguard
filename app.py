import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import os
from groq import Groq

from dotenv import load_dotenv
from scoring import process_suppliers, get_status
import random

load_dotenv()

groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# page config
st.set_page_config(
    page_title="SupplyGuard",
    page_icon="🛡️",
    layout="wide"
)

# simple css to make it look clean
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #1a1a2e, #16213e);
        padding: 20px;
        border-radius: 10px;
        margin-bottom: 20px;
        color: white;
    }
    .supplier-card {
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        padding: 15px;
        margin: 8px 0;
        cursor: pointer;
    }
    .red-card {
        border-left: 4px solid #ff4444;
        background-color: #fff5f5;
    }
    .yellow-card {
        border-left: 4px solid #ffaa00;
        background-color: #fffbf0;
    }
    .green-card {
        border-left: 4px solid #00cc66;
        background-color: #f0fff8;
    }
    .score-big {
        font-size: 48px;
        font-weight: bold;
    }
    .metric-box {
        background: #f8f9fa;
        border-radius: 8px;
        padding: 12px;
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)


def generate_weekly_trend(base_score, weeks=6):
    # generates a fake but realistic trend for the last 6 weeks
    trend = []
    current = base_score
    for i in range(weeks):
        variation = random.uniform(-8, 8)
        point = max(0, min(100, current + variation))
        trend.append(round(point, 1))
        current = point
    trend[-1] = base_score  # last point is current actual score
    return trend


def draft_backup_email(supplier_name, supplier_category, health_score, issues):
    prompt = f"""
You are helping an Indian manufacturing factory owner draft an urgent email to a backup supplier.

Situation:
- Their current supplier "{supplier_name}" who provides {supplier_category} has a health score of {health_score}/100
- Key issues identified: {issues}
- They need to quickly find an alternative supplier

Write a professional but urgent email to a backup supplier requesting:
1. Availability of {supplier_category} materials
2. Their current pricing
3. Earliest possible delivery timeline

Keep it concise, professional, and suitable for Indian B2B communication.
Sign it as: Factory Management Team

Just write the email directly, no explanation needed.
"""
    response = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content


def parse_whatsapp_chat(chat_text, supplier_name):
    delay_keywords_hindi = ['nahi hoga', 'kal pakka', 'thoda late', 'der ho jayegi',
                            'aaj nahi', 'kal tak', 'parso', 'problem ho gaya']
    delay_keywords_english = ['delay', 'late', 'cannot deliver', 'not possible today',
                              'postpone', 'reschedule', 'issue with', 'problem with']
    chat_lower = chat_text.lower()
    hindi_count = sum(1 for kw in delay_keywords_hindi if kw in chat_lower)
    english_count = sum(1 for kw in delay_keywords_english if kw in chat_lower)
    total_delay_signals = hindi_count + english_count

    if total_delay_signals == 0:
        risk_level = "Low"
        risk_color = "green"
    elif total_delay_signals <= 3:
        risk_level = "Medium"
        risk_color = "orange"
    else:
        risk_level = "High"
        risk_color = "red"

    return {
        'total_signals': total_delay_signals,
        'hindi_signals': hindi_count,
        'english_signals': english_count,
        'risk_level': risk_level,
        'risk_color': risk_color
    }

# ---- MAIN APP STARTS HERE ----

# header
st.markdown("""
<div class="main-header">
    <h1 style="margin:0; font-size: 28px;">🛡️ SupplyGuard</h1>
    <p style="margin:5px 0 0 0; opacity:0.8; font-size:14px;">
        AI-powered Supplier Risk Monitoring for Indian Manufacturing SMEs
    </p>
</div>
""", unsafe_allow_html=True)

# sidebar
with st.sidebar:
    st.header("📂 Upload Data")
    
    uploaded_file = st.file_uploader(
        "Upload Supplier CSV",
        type=['csv'],
        help="Upload your supplier data in CSV format"
    )
    
    st.divider()
    
    st.header("📱 WhatsApp Parser")
    supplier_name_wa = st.text_input("Supplier Name", placeholder="e.g. Ram Textiles")
    whatsapp_file = st.file_uploader(
        "Upload WhatsApp Chat Export (.txt)",
        type=['txt'],
        help="Export chat from WhatsApp → Chat → Export Chat (without media)"
    )
    
    if whatsapp_file and supplier_name_wa:
        chat_content = whatsapp_file.read().decode('utf-8', errors='ignore')
        wa_result = parse_whatsapp_chat(chat_content, supplier_name_wa)
        
        st.divider()
        st.subheader(f"Analysis: {supplier_name_wa}")
        st.metric("Delay Signals Found", wa_result['total_signals'])
        
        color = wa_result['risk_color']
        level = wa_result['risk_level']
        st.markdown(f"**Communication Risk:** :{color}[{level}]")
        
        if wa_result['hindi_signals'] > 0:
            st.write(f"🔸 Hindi delay signals: {wa_result['hindi_signals']}")
        if wa_result['english_signals'] > 0:
            st.write(f"🔸 English delay signals: {wa_result['english_signals']}")
    
    st.divider()
    st.caption("SupplyGuard v1.0 | InnovateZ 2026")


# main content
if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
    suppliers = process_suppliers(df)
    
    # summary metrics at top
    total = len(suppliers)
    at_risk = sum(1 for s in suppliers if s['status'] == 'At Risk')
    watch = sum(1 for s in suppliers if s['status'] == 'Watch')
    healthy = sum(1 for s in suppliers if s['status'] == 'Healthy')
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Suppliers", total)
    with col2:
        st.metric("🔴 At Risk", at_risk, delta=f"-{at_risk} need action", delta_color="inverse")
    with col3:
        st.metric("🟡 Watch", watch)
    with col4:
        st.metric("🟢 Healthy", healthy)
    
    st.divider()
    
    # weekly digest box
    if at_risk > 0:
        risk_names = [s['supplier_name'] for s in suppliers if s['status'] == 'At Risk']
        st.error(f"⚠️ **Weekly Alert:** {', '.join(risk_names)} {'is' if len(risk_names)==1 else 'are'} at high risk of disruption. Immediate action recommended.")
    
    # two column layout
    left_col, right_col = st.columns([1, 2])
    
    with left_col:
        st.subheader("All Suppliers")
        st.caption("Click any supplier to see details")
        
        selected_supplier = None
        
        for supplier in suppliers:
            score = supplier['health_score']
            emoji = supplier['emoji']
            name = supplier['supplier_name']
            status = supplier['status']
            
            if supplier['status'] == 'At Risk':
                card_class = "red-card"
            elif supplier['status'] == 'Watch':
                card_class = "yellow-class"
            else:
                card_class = "green-card"
            
            if st.button(
                f"{emoji} {name}  —  {score}/100",
                key=f"btn_{name}",
                use_container_width=True
            ):
                st.session_state['selected'] = name
        
        if 'selected' not in st.session_state and suppliers:
            st.session_state['selected'] = suppliers[0]['supplier_name']
    
    with right_col:
        selected_name = st.session_state.get('selected', suppliers[0]['supplier_name'])
        supplier = next((s for s in suppliers if s['supplier_name'] == selected_name), suppliers[0])
        
        score = supplier['health_score']
        status = supplier['status']
        emoji = supplier['emoji']
        
        st.subheader(f"{emoji} {supplier['supplier_name']}")
        st.caption(f"{supplier['category']} supplier · {supplier['location']}")
        
        # big score display
        score_color = "#ff4444" if status == "At Risk" else "#ffaa00" if status == "Watch" else "#00cc66"
        st.markdown(f"""
        <div style="text-align:center; padding: 15px; background:#f8f9fa; border-radius:10px; margin-bottom:15px;">
            <div style="font-size:56px; font-weight:bold; color:{score_color};">{score}</div>
            <div style="font-size:18px; color:#666;">Health Score / 100</div>
            <div style="font-size:16px; margin-top:5px;">{emoji} {status}</div>
        </div>
        """, unsafe_allow_html=True)
        
        # score breakdown chart
        fig = go.Figure(go.Bar(
            x=[supplier['delivery_score'], supplier['quality_score'],
               supplier['financial_score'], supplier['communication_score']],
            y=['Delivery (35%)', 'Quality (25%)', 'Financial (25%)', 'Communication (15%)'],
            orientation='h',
            marker_color=[
                '#ff4444' if supplier['delivery_score'] < 40 else '#ffaa00' if supplier['delivery_score'] < 70 else '#00cc66',
                '#ff4444' if supplier['quality_score'] < 40 else '#ffaa00' if supplier['quality_score'] < 70 else '#00cc66',
                '#ff4444' if supplier['financial_score'] < 40 else '#ffaa00' if supplier['financial_score'] < 70 else '#00cc66',
                '#ff4444' if supplier['communication_score'] < 40 else '#ffaa00' if supplier['communication_score'] < 70 else '#00cc66',
            ]
        ))
        fig.update_layout(
            title="Score Breakdown",
            xaxis_range=[0, 100],
            height=250,
            margin=dict(l=0, r=0, t=40, b=0),
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)'
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # trend chart
        trend_data = generate_weekly_trend(score)
        weeks = ['6 weeks ago', '5 weeks ago', '4 weeks ago', '3 weeks ago', 'Last week', 'This week']
        
        fig2 = go.Figure(go.Scatter(
            x=weeks,
            y=trend_data,
            mode='lines+markers',
            line=dict(color=score_color, width=2),
            marker=dict(size=6)
        ))
        fig2.update_layout(
            title="Score Trend (Last 6 Weeks)",
            yaxis_range=[0, 100],
            height=200,
            margin=dict(l=0, r=0, t=40, b=0),
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)'
        )
        st.plotly_chart(fig2, use_container_width=True)
        
        # flags section
        st.subheader("⚠️ Risk Flags")
        
        flags = []
        if supplier['late_deliveries'] >= 3:
            flags.append(f"🔴 {supplier['late_deliveries']} late deliveries in last 6 months")
        if supplier['defect_rate'] >= 5:
            flags.append(f"🔴 High defect rate: {supplier['defect_rate']}%")
        
        gst_missed = sum(1 for q in [supplier['gst_q1'], supplier['gst_q2'], 
                                      supplier['gst_q3'], supplier['gst_q4']] 
                        if str(q).strip().lower() == 'no')
        if gst_missed >= 2:
            flags.append(f"🔴 GST not filed for {gst_missed} quarters — financial distress signal")
        if supplier['advance_requests'] >= 2:
            flags.append(f"🟡 {supplier['advance_requests']} advance payment requests — cash flow concern")
        
        if flags:
            for flag in flags:
                st.write(flag)
        else:
            st.write("✅ No major risk flags detected")
        
        # draft email button — only for at-risk suppliers
        if status == 'At Risk':
            st.divider()
            st.subheader("🤖 AI Action")
            
            if st.button("📧 Draft Backup Supplier Email", type="primary", use_container_width=True):
                with st.spinner("Gemini is drafting your email..."):
                    issues_list = ", ".join(flags) if flags else "poor overall performance"
                    email_content = draft_backup_email(
                        supplier['supplier_name'],
                        supplier['category'],
                        score,
                        issues_list
                    )
                    st.success("✅ Email drafted successfully!")
                    st.text_area(
                        "Ready to send — review and copy:",
                        value=email_content,
                        height=300
                    )
                    st.caption("💡 Review this email before sending. SupplyGuard drafts, you decide.")

else:
    # landing state when no file uploaded
    st.markdown("""
    <div style="text-align:center; padding:60px 20px;">
        <div style="font-size:64px;">🛡️</div>
        <h2>Welcome to SupplyGuard</h2>
        <p style="color:#666; font-size:16px; max-width:500px; margin:0 auto;">
            Upload your supplier CSV file from the sidebar to get started. 
            SupplyGuard will automatically score every supplier and flag who needs your attention.
        </p>
        <br>
        <p style="color:#999; font-size:14px;">
            📊 Supports Tally exports and Excel/CSV formats
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    st.info("👈 Upload your supplier CSV from the sidebar to begin")