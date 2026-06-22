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

st.set_page_config(
    page_title="SupplyGuard",
    page_icon="🛡️",
    layout="wide"
)

# dark mode toggle - stored in session so it persists across reruns
if 'dark_mode' not in st.session_state:
    st.session_state.dark_mode = True

dark = st.session_state.dark_mode

# just keeping colors in one place so i don't have to change 50 lines if i change theme
if dark:
    bg        = "#0d0f1a"
    card      = "#161827"
    border    = "#2a2d3e"
    txt       = "#e8eaf0"
    txt_soft  = "#8b8fa8"
    accent    = "#4f8ef7"
    header_bg = "linear-gradient(135deg, #0d0f1a 0%, #1a1f3a 100%)"
    score_bg  = "#1a1d2e"
    icon      = "☀️"
    mode_label = "Light mode"
else:
    bg        = "#f4f6fb"
    card      = "#ffffff"
    border    = "#e0e4ef"
    txt       = "#1a1d2e"
    txt_soft  = "#6b7280"
    accent    = "#2563eb"
    header_bg = "linear-gradient(135deg, #1a1f3a 0%, #2563eb 100%)"
    score_bg  = "#f0f4ff"
    icon      = "🌙"
    mode_label = "Dark mode"

st.markdown(f"""
<style>
    .stApp {{
        background-color: {bg};
        color: {txt};
    }}
    section[data-testid="stSidebar"] {{
        background-color: {card};
        border-right: 1px solid {border};
    }}
    .header-bar {{
        background: {header_bg};
        padding: 18px 24px;
        border-radius: 12px;
        margin-bottom: 24px;
    }}
    .metric-card {{
        background: {card};
        border: 1px solid {border};
        border-radius: 10px;
        padding: 16px 20px;
        text-align: center;
    }}
    .metric-num {{
        font-size: 32px;
        font-weight: 700;
        line-height: 1;
    }}
    .metric-label {{
        font-size: 12px;
        color: {txt_soft};
        margin-top: 4px;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }}
    .score-box {{
        background: {score_bg};
        border: 1px solid {border};
        border-radius: 12px;
        padding: 20px;
        text-align: center;
        margin-bottom: 16px;
    }}
    div[data-testid="stButton"] button {{
        background: {card};
        border: 1px solid {border};
        color: {txt};
        border-radius: 8px;
        transition: all 0.15s;
    }}
    div[data-testid="stButton"] button:hover {{
        border-color: {accent};
        color: {accent};
    }}
    .step-card {{
        background: {card};
        border: 1px solid {border};
        border-radius: 12px;
        padding: 24px 20px;
        text-align: center;
    }}
    .alert-box {{
        background: rgba(239, 68, 68, 0.08);
        border: 1px solid rgba(239, 68, 68, 0.25);
        border-left: 4px solid #ef4444;
        border-radius: 8px;
        padding: 12px 16px;
        margin-bottom: 16px;
        font-size: 14px;
        color: {txt};
    }}
    header[data-testid="stHeader"] {{
        background: transparent;
    }}
    .stCaption, .stCaption p {{
        color: {txt_soft} !important;
    }}
</style>
""", unsafe_allow_html=True)


# fake trend data - in production this would come from a DB with historical scores
# for now generating something that looks realistic around the actual score
def make_trend(score, weeks=6):
    trend = []
    current = score
    for _ in range(weeks):
        current = max(0, min(100, current + random.uniform(-8, 8)))
        trend.append(round(current, 1))
    trend[-1] = score  # last point is always the real current score
    return trend


def draft_email_with_ai(supplier_name, category, score, issues):
    prompt = f"""
You are helping an Indian manufacturing SME owner write an urgent email to a backup supplier.

Context:
- Current supplier "{supplier_name}" (provides {category}) has dropped to a health score of {score}/100
- Identified issues: {issues}
- Need to check if backup supplier can step in

Write a short, professional email asking the backup supplier for:
1. Availability of {category} materials
2. Current pricing
3. Earliest delivery they can commit to

Keep it direct and suitable for Indian B2B. Sign off as: Factory Management Team
Write only the email. No explanation.
"""
    resp = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}]
    )
    return resp.choices[0].message.content


# basic keyword scanner for WhatsApp chats
# not NLP - just looking for delay signals in Hindi and English
# good enough for the MVP, can upgrade to proper NLP later
def scan_whatsapp(text, supplier):
    hindi_signals  = ['nahi hoga', 'kal pakka', 'thoda late', 'der ho jayegi',
                      'aaj nahi', 'kal tak', 'parso', 'problem ho gaya']
    english_signals = ['delay', 'late', 'cannot deliver', 'not possible today',
                       'postpone', 'reschedule', 'issue with', 'problem with']

    lower = text.lower()
    h_count = sum(1 for kw in hindi_signals if kw in lower)
    e_count = sum(1 for kw in english_signals if kw in lower)
    total   = h_count + e_count

    if total == 0:
        risk, color = "Low", "green"
    elif total <= 3:
        risk, color = "Medium", "orange"
    else:
        risk, color = "High", "red"

    return {
        'total': total,
        'hindi': h_count,
        'english': e_count,
        'risk': risk,
        'color': color
    }


# top bar - logo left, theme toggle right
h_col, t_col = st.columns([5, 1])
with h_col:
    st.markdown(f"""
    <div class="header-bar">
        <div style="font-size:22px; font-weight:700; color:#fff; letter-spacing:-0.3px;">🛡️ SupplyGuard</div>
        <div style="font-size:13px; color:rgba(255,255,255,0.65); margin-top:3px;">
            AI-powered Supplier Risk Monitoring · Built for Indian Manufacturing SMEs
        </div>
    </div>
    """, unsafe_allow_html=True)
with t_col:
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button(f"{icon} {mode_label}", use_container_width=True):
        st.session_state.dark_mode = not st.session_state.dark_mode
        st.rerun()


# sidebar
with st.sidebar:
    st.markdown(f"<div style='font-size:17px; font-weight:700; padding:6px 0; color:{txt};'>🛡️ SupplyGuard</div>", unsafe_allow_html=True)
    st.divider()

    st.markdown(f"<div style='font-size:11px; font-weight:600; color:{txt_soft}; text-transform:uppercase; letter-spacing:0.06em; margin-bottom:6px;'>Upload Data</div>", unsafe_allow_html=True)
    uploaded_file = st.file_uploader(
        "Supplier CSV",
        type=['csv'],
        help="Tally export or any CSV with supplier data"
    )

    st.divider()

    st.markdown(f"<div style='font-size:11px; font-weight:600; color:{txt_soft}; text-transform:uppercase; letter-spacing:0.06em; margin-bottom:4px;'>Risk Weights</div>", unsafe_allow_html=True)
    st.caption("Drag to set what matters most to your factory")

    w_del  = st.slider("Delivery",        0, 100, 35)
    w_qual = st.slider("Quality",         0, 100, 25)
    w_fin  = st.slider("Financial / GST", 0, 100, 25)
    w_com  = st.slider("Communication",   0, 100, 15)

    weights = {
        'delivery':      w_del,
        'quality':       w_qual,
        'financial':     w_fin,
        'communication': w_com
    }

    st.divider()

    st.markdown(f"<div style='font-size:11px; font-weight:600; color:{txt_soft}; text-transform:uppercase; letter-spacing:0.06em; margin-bottom:4px;'>WhatsApp Parser</div>", unsafe_allow_html=True)
    st.caption("Paste a supplier name and upload their chat export")

    wa_supplier = st.text_input("Supplier name", placeholder="e.g. Ram Textiles")
    wa_file     = st.file_uploader("Chat export (.txt)", type=['txt'])

    if wa_file and wa_supplier:
        chat_text = wa_file.read().decode('utf-8', errors='ignore')
        result    = scan_whatsapp(chat_text, wa_supplier)
        st.divider()
        st.markdown(f"**{wa_supplier}**")
        st.metric("Delay signals found", result['total'])
        st.markdown(f"Risk level: :{result['color']}[**{result['risk']}**]")
        if result['hindi'] > 0:
            st.write(f"🔸 Hindi: {result['hindi']} signals")
        if result['english'] > 0:
            st.write(f"🔸 English: {result['english']} signals")

    st.divider()
    st.caption("v1.0 · InnovateZ 2026 · VIT Bhopal")


# main dashboard - shows when CSV is uploaded
if uploaded_file is not None:
    df        = pd.read_csv(uploaded_file)
    suppliers = process_suppliers(df, weights)

    total   = len(suppliers)
    at_risk = sum(1 for s in suppliers if s['status'] == 'At Risk')
    watch   = sum(1 for s in suppliers if s['status'] == 'Watch')
    healthy = sum(1 for s in suppliers if s['status'] == 'Healthy')

    # top metrics
    c1, c2, c3, c4 = st.columns(4)
    for col, val, label, color in [
        (c1, total,   "Total Suppliers", txt),
        (c2, at_risk, "At Risk 🔴",      "#ef4444"),
        (c3, watch,   "Watch 🟡",        "#f59e0b"),
        (c4, healthy, "Healthy 🟢",      "#10b981"),
    ]:
        with col:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-num" style="color:{color};">{val}</div>
                <div class="metric-label">{label}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    if at_risk > 0:
        names = [s['supplier_name'] for s in suppliers if s['status'] == 'At Risk']
        st.markdown(f"""
        <div class="alert-box">
            ⚠️ <strong>Weekly Alert —</strong> {', '.join(names)} {'is' if len(names) == 1 else 'are'} at high risk of disruption. Take action now.
        </div>
        """, unsafe_allow_html=True)

    left, right = st.columns([1, 2])

    with left:
        st.markdown(f"<div style='font-size:14px; font-weight:600; color:{txt}; margin-bottom:4px;'>All Suppliers</div>", unsafe_allow_html=True)
        st.caption("Click any to see breakdown")

        for s in suppliers:
            if st.button(f"{s['emoji']} {s['supplier_name']}  ·  {s['health_score']}/100",
                         key=f"btn_{s['supplier_name']}", use_container_width=True):
                st.session_state['selected'] = s['supplier_name']

        if 'selected' not in st.session_state:
            st.session_state['selected'] = suppliers[0]['supplier_name']

    with right:
        sel_name = st.session_state.get('selected', suppliers[0]['supplier_name'])
        s        = next((x for x in suppliers if x['supplier_name'] == sel_name), suppliers[0])

        score  = s['health_score']
        status = s['status']
        sc     = "#ef4444" if status == "At Risk" else "#f59e0b" if status == "Watch" else "#10b981"

        st.markdown(f"<div style='font-size:18px; font-weight:700; color:{txt};'>{s['emoji']} {s['supplier_name']}</div>", unsafe_allow_html=True)
        st.caption(f"{s['category']} · {s['location']}")

        # the big score number
        st.markdown(f"""
        <div class="score-box">
            <div style="font-size:62px; font-weight:800; color:{sc}; line-height:1;">{score}</div>
            <div style="font-size:13px; color:{txt_soft}; margin-top:6px;">Health Score / 100</div>
            <div style="font-size:13px; font-weight:600; margin-top:4px; color:{sc};">{s['emoji']} {status}</div>
        </div>
        """, unsafe_allow_html=True)

        # score breakdown bar chart
        scores_list = [s['delivery_score'], s['quality_score'], s['financial_score'], s['communication_score']]
        fig = go.Figure(go.Bar(
            x=scores_list,
            y=['Delivery (35%)', 'Quality (25%)', 'Financial (25%)', 'Communication (15%)'],
            orientation='h',
            marker_color=['#ef4444' if v < 40 else '#f59e0b' if v < 70 else '#10b981' for v in scores_list]
        ))
        fig.update_layout(
            title="Score Breakdown",
            xaxis_range=[0, 100],
            height=220,
            margin=dict(l=0, r=0, t=36, b=0),
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color=txt),
            title_font=dict(color=txt, size=13)
        )
        st.plotly_chart(fig, use_container_width=True)

        # trend - illustrative for now
        trend = make_trend(score)
        fig2  = go.Figure(go.Scatter(
            x=['6w ago', '5w ago', '4w ago', '3w ago', 'Last week', 'Now'],
            y=trend,
            mode='lines+markers',
            line=dict(color=sc, width=2),
            marker=dict(size=5),
            fill='tozeroy',
            fillcolor=f"rgba({int(sc[1:3],16)},{int(sc[3:5],16)},{int(sc[5:7],16)},0.07)"
        ))
        fig2.update_layout(
            title="Score Trend",
            yaxis_range=[0, 100],
            height=180,
            margin=dict(l=0, r=0, t=36, b=0),
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color=txt),
            title_font=dict(color=txt, size=13)
        )
        st.plotly_chart(fig2, use_container_width=True)
        st.caption("📌 Illustrative — real trend tracking needs a persistent DB (Phase 2)")

        # risk flags
        st.markdown(f"<div style='font-size:14px; font-weight:600; color:{txt}; margin: 10px 0 6px;'>⚠️ Risk Flags</div>", unsafe_allow_html=True)

        flags = []
        if s['late_deliveries'] >= 3:
            flags.append(f"🔴 {s['late_deliveries']} late deliveries in last 6 months")
        if s['defect_rate'] >= 5:
            flags.append(f"🔴 Defect rate: {s['defect_rate']}% — above acceptable threshold")
        gst_no = sum(1 for q in [s['gst_q1'], s['gst_q2'], s['gst_q3'], s['gst_q4']]
                     if str(q).strip().lower() == 'no')
        if gst_no >= 2:
            flags.append(f"🔴 GST not filed for {gst_no} quarters — possible financial stress")
        if s['advance_requests'] >= 2:
            flags.append(f"🟡 {s['advance_requests']} advance payment requests — cash flow concern")

        if flags:
            for f in flags:
                st.write(f)
        else:
            st.write("✅ No major flags — supplier looks stable")

        # AI email drafting - only show for red suppliers
        if status == 'At Risk':
            st.divider()
            st.markdown(f"<div style='font-size:14px; font-weight:600; color:{txt}; margin-bottom:4px;'>🤖 AI Action</div>", unsafe_allow_html=True)
            st.caption("Clicks the risk data above and drafts a backup supplier email for you to review.")

            if st.button("📧 Draft Backup Supplier Email", type="primary", use_container_width=True):
                with st.spinner("Writing email..."):
                    issues = ", ".join(flags) if flags else "consistent underperformance"
                    email  = draft_email_with_ai(s['supplier_name'], s['category'], score, issues)
                    st.success("✅ Done — review before sending")
                    st.text_area("Your email draft:", value=email, height=280)
                    st.caption("SupplyGuard drafts. You send.")

# landing page - shown before any file is uploaded
else:
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(f"""
    <div style="text-align:center; padding: 28px 0 20px;">
        <div style="font-size:50px; margin-bottom:10px;">🛡️</div>
        <div style="font-size:24px; font-weight:700; color:{txt}; margin-bottom:8px;">
            Know before your supplier fails.
        </div>
        <div style="font-size:15px; color:{txt_soft}; max-width:420px; margin:0 auto; line-height:1.6;">
            Upload your supplier data. SupplyGuard scores every vendor,
            flags who's about to disrupt you, and drafts the email to your backup — automatically.
        </div>
    </div>
    """, unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    for col, icon_s, title, desc in [
        (c1, "📂", "Upload", "Drop your supplier CSV or Tally export. No setup needed."),
        (c2, "📊", "Score",  "Every supplier gets a 0–100 health score across 4 dimensions."),
        (c3, "⚡", "Act",    "One click and the AI drafts your backup supplier email."),
    ]:
        with col:
            st.markdown(f"""
            <div class="step-card">
                <div style="font-size:34px; margin-bottom:10px;">{icon_s}</div>
                <div style="font-size:15px; font-weight:600; color:{txt}; margin-bottom:6px;">{title}</div>
                <div style="font-size:13px; color:{txt_soft}; line-height:1.5;">{desc}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(f"""
    <div style="text-align:center; padding:18px 24px; background:{card}; border:1px solid {border};
                border-radius:12px; max-width:460px; margin:0 auto;">
        <div style="font-size:13px; color:{txt_soft}; margin-bottom:6px;">Try it right now</div>
        <div style="font-size:14px; color:{txt}; font-weight:500;">
            Upload <code>demo_data.csv</code> from the sidebar
        </div>
        <div style="font-size:12px; color:{txt_soft}; margin-top:6px;">
            Ram Textiles will go 🔴 red. Click it. Watch the AI act.
        </div>
    </div>
    """, unsafe_allow_html=True)