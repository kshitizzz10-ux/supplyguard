# SupplyGuard 🛡️
**AI-Powered Supplier Risk Monitoring for Indian Manufacturing SMEs**  
*Built for InnovateZ 2026 | Zentiti | VIT Bhopal*

![Python](https://img.shields.io/badge/python-v3.10+-blue.svg)
![Streamlit](https://img.shields.io/badge/streamlit-1.32+-red.svg)
![Groq](https://img.shields.io/badge/Groq-Llama_3.3_70B-orange.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

---

## The SME Bottleneck

A garment factory owner in Bhopal manages 14 active suppliers. On Tuesday morning, his primary fabric vendor texts: *"Bhai, aaj delivery nahi hoga."* With zero buffer stock, the assembly line stalls. Sixty workers sit idle, burning **₹80,000/day** in overhead with zero unfulfilled output. 

The tragedy? The warning signs were sitting inside the owner's own systems for months—late challans in Tally, a dropping quality pass-rate, and missed quarterly GST filings. But because Tally doesn't talk to WhatsApp, the owner only discovers the supply chain failure at the exact moment the assembly line stops.

**SupplyGuard connects the dots automatically.**

---

## Architectural Philosophy: The "Boundary of Determinism"

We explicitly rejected the standard hackathon trend of passing raw tabular data to an autonomous LLM agent. Large Language Models are fundamentally unstable at multi-variable, clamped floating-point mathematics; handing an SME's raw financial ledger to an auto-regressive text generator introduces math hallucinations that can mask real stockout risks. 

SupplyGuard enforces a **hybrid intelligence pipeline**: strict, un-hallucinatable deterministic Python for the risk math, and zero-shot LLM orchestration strictly reserved for human communication synthesis.
