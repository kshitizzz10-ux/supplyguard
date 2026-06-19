# SupplyGuard 🛡️
**AI-powered Supplier Risk Monitoring for Indian Manufacturing SMEs**

Built for InnovateZ 2026 | Zentiti | VIT Bhopal

---

## The Problem

A garment factory owner in Bhopal has 14 suppliers. One morning his 
fabric supplier texts "bhai aaj nahi hoga." No warning. 60 workers 
sitting idle. ₹80,000/day going out with zero output.

The scary part? The warning signs were there for months — late 
deliveries, dropping quality, GST not filed. All sitting in his own 
data. Nobody connected the dots.

SupplyGuard connects the dots.

---

## What it does

Upload your supplier data (Tally export or a simple CSV). SupplyGuard 
scores every supplier from 0-100 based on delivery history, quality, 
financial health, and communication patterns. Red suppliers float to 
the top. One click drafts an email to your backup vendor.

No IT team needed. No expensive software. Just upload and go.

---

## Running it locally

```bash
git clone https://github.com/kshitizzz10-ux/supplyguard.git
cd supplyguard
python -m venv venv
venv\Scripts\activate
pip install streamlit pandas plotly groq python-dotenv
```

Create a `.env` file:
GROQ_API_KEY=your_key_here

Run:
```bash
streamlit run app.py
```

Upload `demo_data.csv` to see it work. Ram Textiles will go red.

---

## How the scoring works

Four dimensions, weighted by how much each typically matters to 
a manufacturing SME:

| Dimension | Weight | What it measures |
|-----------|--------|-----------------|
| Delivery | 35% | On-time rate, quantity fulfilled, late deliveries |
| Quality | 25% | Defect rate, complaints filed |
| Financial | 25% | GST filing regularity, advance payment requests |
| Communication | 15% | Response time, last-minute reschedules |

---

## Tech used

- Streamlit — frontend
- Pandas — data processing  
- Groq (Llama 3.3 70B) — email drafting
- Python — scoring engine
- WhatsApp .txt parser — keyword-based for now, NLP in v2

---

## What's real vs what's planned

**Working:**
- CSV upload and supplier scoring
- Risk flag detection
- AI email drafting for at-risk suppliers
- WhatsApp chat delay signal parser

**Mocked / Phase 2:**
- GST check uses CSV column, not live government API
- Trend chart uses illustrative data, not historical DB
- Voice input and challan scanning not yet built

---

*Made by Kshitiz Goyal | CSE AIML | VIT Bhopal*
