# 📈 SME IPO Research Platform

An AI-powered research platform for Indian SME IPOs (BSE SME & NSE Emerge), 
built with Streamlit and Claude AI.

---

## 🚀 Quick Start

### 1. Install Dependencies
```bash
cd sme-ipo-research
pip install -r requirements.txt
```

### 2. Run the App
```bash
streamlit run app.py
```

### 3. Open in Browser
Navigate to `http://localhost:8501`

### 4. Add Claude API Key
- Get your key at https://console.anthropic.com
- Enter it in the sidebar when the app opens
- All AI features (Q&A, Scorecard, Industry Analysis) will activate

---

## ✨ Features

### 🏠 Dashboard
- Active and Upcoming IPO list (BSE SME + NSE Emerge)
- Filter by exchange, recommendation, and search
- Key metrics: issue price, GMP, subscription status, size
- AI-powered recommendation tags (SUBSCRIBE / NEUTRAL / AVOID)
- Click "Analyze →" to deep dive into any IPO

### 🔍 IPO Detail
**Tab 1: AI Q&A Chatbot**
- Ask anything about the IPO in plain language
- Pre-built suggested questions for quick analysis
- Full conversation history
- Powered by Claude claude-opus-4-6

**Tab 2: AI Scorecard**
- Score out of 10 with conviction level
- Bull case vs Bear case analysis
- Red flags and positives
- GMP signal interpretation
- Valuation view

**Tab 3: Industry & Peers**
- P/E comparison vs listed peers
- AI-generated peer comparison analysis
- Sector positioning

**Tab 4: Financials**
- 3-year Revenue & Profit charts
- CAGR calculations
- Net margin trends
- Promoter holding

**Tab 5: News**
- Latest news about the company and sector

### 📊 GMP Tracker
- GMP trend charts for all active/upcoming IPOs
- Day-by-day GMP movement
- GMP interpretation guide (bullish / neutral / bearish signals)

### 📜 Historical Data
- Full listing history with actual gains vs GMP predictions
- GMP accuracy analysis (Was GMP right?)
- Pie chart: 62% historical GMP accuracy
- Filter by GMP accuracy and performance

---

## 📁 Project Structure

```
sme-ipo-research/
├── app.py                    # Main Streamlit app + routing
├── requirements.txt
├── README.md
├── data/
│   └── ipo_data.py           # IPO seed data (replace with live APIs)
├── pages/
│   ├── dashboard.py          # Active & Upcoming IPO dashboard
│   ├── ipo_detail.py         # AI Q&A, Scorecard, Industry, Financials, News
│   ├── gmp_tracker.py        # GMP trend charts
│   └── historical.py         # Historical IPO performance
└── utils/
    └── ai_utils.py           # Claude API integration
```

---

## 🔌 Live Data Integration (Phase 2)

Replace the seed data in `data/ipo_data.py` with these live sources:

| Data | Source | Method |
|------|---------|--------|
| Active IPOs | BSE SME / NSE Emerge | Web scraping or API |
| DRHP Documents | SEBI EFILING portal | PDF download + OCR |
| GMP Data | investorgain.com / ipowatch.in | Web scraping |
| Company News | NewsAPI / Google News RSS | API |
| Subscription Data | Chittorgarh / BSE live | Web scraping |
| Peer Financials | Screener.in | Web scraping |

**For DRHP Q&A (RAG):**
1. Download DRHP PDF from SEBI
2. Parse with AWS Textract or PyMuPDF
3. Chunk + embed into Pinecone/Qdrant
4. Replace `build_ipo_context()` with vector retrieval

---

## 🔮 Roadmap

### Phase 2 (Next Sprint)
- [ ] Live data scraping from BSE/NSE
- [ ] DRHP PDF upload + RAG-based Q&A
- [ ] Real GMP data feed integration
- [ ] Email alerts for new IPO filings
- [ ] Allotment status checker

### Phase 3 (Coming Soon)
- [ ] **Mutual Fund Screener** — Filter MFs by category, returns, AUM, risk
- [ ] **F&O Trading Copilot** — Options strategy builder, Greeks calculator
- [ ] **Crypto Investment Tracker** — Portfolio tracking + AI insights

---

## ⚠️ Disclaimer

This platform provides research and analysis for educational purposes only.
It does not constitute financial advice. IPO investments carry market risks.
GMP is an unofficial, unregulated market signal. Always consult a SEBI-registered
advisor before making investment decisions.

---

## 🛠 Tech Stack

- **Frontend**: Streamlit
- **AI**: Anthropic Claude claude-opus-4-6
- **Charts**: Plotly
- **Data**: Curated seed data (replace with live APIs)
- **Fonts**: Space Grotesk + JetBrains Mono (via Google Fonts)

---

Built with ❤️ for Indian retail investors
