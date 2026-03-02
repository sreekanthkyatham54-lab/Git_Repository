# TradeSage — AI Investment Research Platform

An AI-powered investment research platform for Indian retail investors. Built to level the playing field — giving individual investors the same depth of research that institutional desks have, without the Bloomberg terminal.

Live at: [tradesage.streamlit.app](https://tradesage.streamlit.app)

---

## What TradeSage Does

Most retail investors rely on YouTube, WhatsApp tips, and broker recommendations that are riddled with conflicts of interest. TradeSage reads primary source documents — DRHPs, annual reports, BSE filings — and answers questions in plain English.

**Current modules:**
- **IPO Research** — AI reads the full DRHP and answers any question about the IPO
- **Market Pulse** — Daily bullish/bearish signals based on technical indicators
- **Stock Research** — Multi-agent analysis of any NSE stock
- **Portfolio AI** — Upload your broker screenshot, get honest observations

---

## Features

### ⚡ Market Pulse
- Live Nifty 50 and Sensex prices with % change
- Stocks turning bullish or bearish today — based on DMA crossovers and MACD signals
- Sector momentum heatmap for 8 major Indian sectors
- High-impact news events that moved prices

### 📄 IPO Hub
- Active and upcoming IPOs (BSE SME, NSE Emerge, Mainboard)
- Key metrics: issue price, GMP, subscription status, lot size, listing date
- AI-generated recommendation tags: SUBSCRIBE / NEUTRAL / AVOID
- Subscription breakdown: QIB / NII / Retail

### 🔍 IPO Deep Dive (per IPO)
**AI Q&A** — Ask anything about the IPO in plain language. Claude reads the full DRHP and answers with page citations. Pre-built suggested questions included.

**AI Scorecard** — Score out of 10, conviction level, bull case vs bear case, red flags, GMP signal interpretation, valuation view.

**Industry & Peers** — P/E comparison vs listed peers, AI-generated sector positioning.

**Financials** — 3-year revenue and profit charts, CAGR, net margin trends, promoter holding.

### 📈 Stock Research
- Search any NSE stock by symbol
- Quick-pick buttons for popular stocks
- 4 AI agent cards running in parallel:
  - **Technical Agent** — RSI, MACD, 50/200 DMA crossovers, volume analysis
  - **Trend Agent** — Sector momentum, 52-week range, relative strength vs Nifty
  - **News Agent** — Recent headlines from Yahoo Finance
  - **Fundamentals Agent** — Revenue, profit, P/E, market cap from public filings
- Synthesis card with overall signal score and key observations

### 💼 Portfolio AI
- Upload a screenshot from any Indian broker app (Zerodha, Groww, Angel One, Upstox)
- Claude vision extracts your holdings automatically
- AI observations: concentration risk, underperformers, sector gaps, vs Nifty benchmark
- Sample portfolio available to preview without uploading

### 📊 GMP Tracker
- GMP trend charts for all active and upcoming IPOs
- Day-by-day GMP movement
- GMP accuracy guide and signal interpretation

### 📜 Historical Data
- Full listing history with actual gains vs GMP predictions
- GMP accuracy analysis
- Filter by performance and accuracy

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Streamlit + custom HTML/CSS via `st.markdown` |
| Language | Python 3.10+ |
| AI Model | Anthropic Claude (claude-sonnet-4-6) |
| Vector Database | Pinecone (6,943 vectors) |
| Embeddings | sentence-transformers (local) |
| Market Data | yfinance (Yahoo Finance) |
| IPO Scraping | requests + BeautifulSoup4 |
| PDF Parsing | pdfplumber |
| Local Database | SQLite |
| Charts | Plotly |
| Fonts | Sora + JetBrains Mono (Google Fonts) |
| Hosting | Streamlit Cloud |
| CI/CD | GitHub Actions (3x daily pipeline) |

---

## Project Structure

```
tradesage/
├── app.py                      # Main app, routing, nav bar, theme
├── requirements.txt
├── README.md
│
├── data/
│   ├── ipo_data.py             # Seed IPO data
│   ├── live_ipo_data.json      # Written by GitHub Actions scraper
│   ├── ai_cache.json           # Cached AI scorecards
│   └── drhp_pdfs/              # Downloaded DRHP PDFs (gitignored)
│
├── pages/
│   ├── market_pulse.py         # Market Pulse homepage
│   ├── stock_research.py       # Single stock multi-agent analysis
│   ├── portfolio_ai.py         # Portfolio screenshot → AI feedback
│   ├── dashboard.py            # IPO Hub (active + upcoming)
│   ├── ipo_detail.py           # IPO deep dive (Q&A, scorecard, charts)
│   ├── gmp_tracker.py          # GMP trend charts
│   └── historical.py           # Historical listing performance
│
├── utils/
│   ├── market_data.py          # Yahoo Finance data engine + technicals
│   └── ai_utils.py             # Claude API integration + RAG retrieval
│
├── scraper.py                  # Scrapes live IPO data from ipowatch.in
├── drhp_scraper.py             # Downloads and parses DRHP PDFs
├── rag_indexer.py              # Chunks DRHP text + creates embeddings
├── pinecone_push_new.py        # Incremental sync to Pinecone
├── ai_cache.py                 # Generates AI scorecards for new IPOs
├── data_loader.py              # Loads live or seed IPO data
│
└── .github/
    └── workflows/
        └── refresh_data.yml    # 3-job automation pipeline
```

---

## How the RAG Pipeline Works

TradeSage reads the full DRHP (Draft Red Herring Prospectus) for each IPO — typically 300-500 pages — and makes it searchable via AI.

```
DRHP PDF
    ↓
drhp_scraper.py         Downloads PDF, extracts text, identifies sections
    ↓
rag_indexer.py          Semantic chunking (512 tokens) + sentence-transformer embeddings
    ↓
pinecone_push_new.py    Upserts new vectors to Pinecone cloud index
    ↓
rag_retriever.py        On user query: embed query → cosine similarity → top-K chunks
    ↓
Claude API              Chunks + question → cited answer with page references
```

Keyword boosting is applied to prioritise chunks containing financial terms (revenue, profit, EBITDA, risk, etc.) over generic text matches.

---

## How the GitHub Actions Pipeline Works

Three jobs run automatically at 6:30 AM, 12:30 PM, and 6:30 PM IST daily:

**Job 1 — scrape_live_data** (~1 min)
Runs `scraper.py` → scrapes ipowatch.in → writes `data/live_ipo_data.json` → commits and pushes to main. Streamlit Cloud picks up fresh data on next load.

**Job 2 — drhp_pipeline** (runs after Job 1)
Runs `drhp_scraper.py` for new IPOs → `rag_indexer.py` → `pinecone_push_new.py`. Only processes IPOs not already in Pinecone. No commit needed — Pinecone is the source of truth.

**Job 3 — ai_cache** (runs after Job 2)
Runs `ai_cache.py` → generates scorecards for uncached IPOs → writes `data/ai_cache.json` → commits and pushes.

Each job is idempotent — safe to re-run without duplicating data.

---

## Local Setup

### 1. Clone and install

```bash
git clone https://github.com/your-username/Git_Repository.git
cd Git_Repository
pip install -r requirements.txt
```

### 2. Environment variables

Create a `.env` file in the root:

```
ANTHROPIC_API_KEY=your_key_here
PINECONE_API_KEY=your_key_here
```

Or enter your Anthropic API key directly in the app UI when it loads.

### 3. Run locally

```bash
streamlit run app.py
```

Open `http://localhost:8501`

### 4. Run the data pipeline locally (optional)

```bash
# Scrape live IPO data
python scraper.py

# Download DRHPs and index to Pinecone
python drhp_scraper.py
python rag_indexer.py
python pinecone_push_new.py

# Generate AI scorecards
python ai_cache.py
```

---

## Deployment (Streamlit Cloud)

1. Push repo to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect repo, set main file as `app.py`
4. Add secrets in Streamlit Cloud dashboard:
   ```
   ANTHROPIC_API_KEY = "your_key"
   PINECONE_API_KEY = "your_key"
   ```
5. Add `ANTHROPIC_API_KEY` and `PINECONE_API_KEY` to GitHub Secrets for Actions pipeline

---

## Roadmap

### Q2 2026 — Long-Term Investing Co-Pilot
- AI reads annual reports and concall transcripts
- Business quality scorecard: moat, management, financials
- Multi-year trend analysis with red flag detection
- Management guidance tracker (promised vs delivered)

### Q3 2026 — F&O Trading Intelligence
- Options chain heatmap with OI build-up signals
- IV percentile alerts and strategy suggestions
- AI-generated trade setups with defined risk/reward

### Q3 2026 — Mutual Fund Screener
- Factor-based scoring beyond star ratings
- Portfolio overlap detection across your MF holdings
- SIP optimizer for goal-based investing

### Q4 2026 — Crypto Markets Intelligence
- INR-denominated pricing and portfolio tracking
- Indian regulatory and tax update feed
- On-chain signals and whale movement alerts

---

## Known Limitations (MVP)

- Yahoo Finance is unofficial — may break if Yahoo changes their site. Production version will use TrueData or Global DataFeeds.
- No user authentication — all users see the same data, no personalisation
- SQLite resets on each GitHub Actions run — drhp.db is rebuilt from scratch each pipeline execution (acceptable at MVP scale)
- Streamlit Cloud free tier has memory limits — large DRHP files may cause timeouts
- News Agent in Stock Research uses Yahoo Finance news only — BSE announcement integration coming in next release

---

## Disclaimer

TradeSage is not a SEBI registered investment adviser. All content is automated analysis of publicly available data for informational and educational purposes only. Nothing on this platform constitutes personalised investment advice. IPO and equity investments carry market risks. GMP is an unofficial, unregulated signal. Please consult a SEBI-registered investment adviser before making any investment decisions.

---

Built for Indian retail investors who deserve better research tools.
