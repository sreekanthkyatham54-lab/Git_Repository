# TradeSage — AI-Powered Investment Research Platform

## Product Vision
TradeSage gives every Indian retail investor access to professional-grade research.
The structural disadvantage between institutional investors (Bloomberg terminals, analyst teams)
and retail investors (Google and hope) is the problem we're solving.

**Current capability:** IPO Research & Analysis
**Roadmap:** Long-Term Investing Co-Pilot → F&O Intelligence → MF Screener → Crypto Markets

Live app: tradesage.streamlit.app

---

## Tech Stack
- **Frontend:** Streamlit (Python)
- **AI:** Anthropic Claude API (claude-sonnet-4-6)
- **Vector DB:** Pinecone (cloud) — index: `tradesage-drhp`, dimension 384
- **Embeddings:** sentence-transformers `all-MiniLM-L6-v2` (384 dimensions)
- **Local DB:** SQLite (`data/drhp.db`) — local fallback when Pinecone unavailable
- **Hosting:** Streamlit Cloud (auto-deploys from GitHub `main` branch)
- **Scraping:** ipowatch.in (BeautifulSoup)

---

## Repository Structure

```
Git_Repository/
├── app.py                    # Main Streamlit app — routing, session state, API key handling
├── scraper.py                # Scrapes ipowatch.in — IPO list, GMP, subscription data
├── rag_indexer.py            # Semantic chunking of DRHP PDFs → SQLite embeddings
├── rag_retriever.py          # Pinecone (primary) + SQLite (fallback) retrieval
├── pinecone_migrate.py       # One-time migration: SQLite → Pinecone
├── ai_cache.py               # Pre-computes AI scorecards, caches to ai_cache.json
├── drhp_scraper.py           # Downloads DRHP PDFs for indexed IPOs
├── data_loader.py            # Loads live_ipo_data.json, merges with ai_cache
├── db_reader.py              # SQLite inspection utilities
├── inspect_db.py             # Debug tool — prints chunk stats per IPO
│
├── pages/
│   ├── dashboard.py          # IPO listing cards, filters, founder vision + roadmap
│   ├── ipo_detail.py         # AI Q&A, Scorecard, Industry & Peers, Financials, News
│   ├── gmp_tracker.py        # GMP history and trends
│   └── historical.py         # Past IPO performance tracker
│
├── utils/
│   └── ai_utils.py           # All Claude API calls — chat_with_ipo(), get_ai_recommendation(),
│                             #   compare_with_industry(), build_ipo_summary()
│
├── data/
│   ├── live_ipo_data.json    # Written by scraper.py — NEVER commit this
│   ├── drhp.db               # SQLite with chunks + embeddings — NEVER commit (>100MB)
│   ├── ai_cache.json         # Pre-computed scorecards — NEVER commit
│   ├── drhp_pdfs/            # Downloaded PDFs — NEVER commit
│   └── ipo_data.py           # Static seed data — safe to commit
│
├── .env                      # Local secrets — NEVER commit
├── .gitignore                # Excludes drhp.db, live_ipo_data.json, ai_cache.json, .env
│
└── .github/workflows/
    └── refresh_data.yml      # GitHub Actions — runs scraper.py twice daily
```

---

## Key Architecture Decisions

### RAG Pipeline
1. **Indexing** (`rag_indexer.py`) — semantic chunking, NOT fixed-size chunks
   - Embeds sentences, measures cosine similarity between consecutive sentences
   - Splits where similarity drops below threshold (topic change)
   - Min chunk: 300 chars, Max chunk: 4000 chars
   - No section labels stored — labels caused wrong retrieval due to PDF footer contamination

2. **Retrieval** (`rag_retriever.py`) — pure cosine similarity, no section filters
   - Pinecone queried first (Streamlit Cloud has no local DB)
   - SQLite fallback for local development
   - `retrieve_chunks()` — for Q&A chat, returns top 12 chunks
   - `retrieve_for_scorecard()` — 7 targeted queries (risks, financials, valuation, peers, promoters, litigation, objects), top 2 chunks each
   - Keyword boost: questions containing "valuation", "P/E", "peer" etc. trigger a second
     targeted query using exact DRHP section language to find critical pages

3. **Pinecone index** — `tradesage-drhp`
   - Dimension: 384 (all-MiniLM-L6-v2)
   - Metric: cosine
   - Region: AWS us-east-1 (Starter plan)
   - Each vector metadata contains: ipo_id, company, page_number, chunk_index, text

### IPO ID Convention
- Format: `ipo_001`, `ipo_002` ... `ipo_017`
- Assigned at scrape time, persists across runs
- Used as Pinecone filter: `{"ipo_id": {"$eq": "ipo_005"}}`
- PDF filenames follow same convention: `ipo_005.pdf` = Gaudium IVF

### AI Scorecard Output Schema
```python
{
  "verdict":      "SUBSCRIBE" | "NEUTRAL" | "AVOID",
  "score":        int (1-10),
  "conviction":   "High" | "Medium" | "Low",
  "one_liner":    str,
  "bull_case":    str,
  "bear_case":    str,
  "positives":    [str, ...],   # List of positives with page citations
  "red_flags":    [str, ...],   # List of red flags with page citations
  "valuation_view": str,
  "gmp_view":     str,
  "suitable_for": str,
}
```

### Dashboard Recommendation Source
- AI verdict (from ai_cache.json) takes priority over ipowatch recommendation
- Shows "AI" badge next to verdict when sourced from our analysis
- Falls back to ipowatch recommendation if no AI cache exists

### Subscription Data
- Scraped from: `ipowatch.in/ipo-subscription-status-today/`
- Fields: `subscription_times` (total), `subscription_qib`, `subscription_nii`, `subscription_retail`
- Dashboard shows breakdown: `0.9x (Q:0x N:0.91x R:1.42x)`

---

## Environment Variables

### Local (.env file)
```
PINECONE_API_KEY=your_key_here
```

### Streamlit Cloud (Secrets)
```toml
PINECONE_API_KEY = "your_key_here"
```

### In-app (entered by user)
- `ANTHROPIC_API_KEY` — entered in sidebar at runtime, stored in `st.session_state.api_key`
- Not stored in secrets — users bring their own key

---

## Data Flow

```
ipowatch.in
    ↓ scraper.py (twice daily via GitHub Actions)
live_ipo_data.json
    ↓ data_loader.py
Streamlit app (active + upcoming + historical IPOs)

DRHP PDFs (local only)
    ↓ rag_indexer.py --force (run locally after new IPOs)
drhp.db (SQLite, local only)
    ↓ pinecone_migrate.py (run once after re-indexing)
Pinecone cloud index
    ↓ rag_retriever.py (queries at runtime)
Claude API (ai_utils.py)
    ↓
AI Q&A responses + Scorecard JSON
```

---

## Development Workflow

### Adding a new IPO
1. Download DRHP PDF → `data/drhp_pdfs/ipo_XXX.pdf`
2. Run `rag_indexer.py` (indexes new PDFs only, skips existing)
3. Run `pinecone_migrate.py` (uploads new chunks to Pinecone)
4. Run `scraper.py` (picks up new IPO from ipowatch)

### Re-indexing everything (after chunking changes)
```
run_rag_indexer.bat --force
python pinecone_migrate.py
```

### Deploying code changes
```
sync_to_git.bat   # copies code files to Git_Repository, commits, pushes Dev branch
```
Then merge Dev → main on GitHub for Streamlit auto-deploy.

**Never commit:** `drhp.db`, `live_ipo_data.json`, `ai_cache.json`, `.env`, `drhp_pdfs/`

---

## Current IPO Coverage
- 16–17 IPOs indexed in Pinecone
- Mix of Mainboard and SME (BSE SME, NSE Emerge)
- 6,943 semantic chunks total (~68MB in Pinecone)

---

## Known Issues / Technical Debt
- Lot size parsing fails for some IPOs (shows 0) — scraper regex needs improvement
- P/E ratio from scraper often 0.0 — ipowatch doesn't always surface this
- Pinecone Starter plan: index pauses after 3 weeks inactivity (cold start ~10s)
- Pinecone Starter: locked to AWS us-east-1 (~200ms latency from India)
- Upgrade to Standard plan when first paying users onboard (Asia-Pacific region)

---

## Roadmap
| Feature | Target | Status |
|---|---|---|
| IPO Research & Analysis | Q1 2026 | ✅ Live |
| Long-Term Investing Co-Pilot | Q2 2026 | 🔵 Planning |
| F&O Trading Intelligence | Q3 2026 | 🔵 Planning |
| Mutual Fund Screener | Q3 2026 | 🔵 Planning |
| Crypto Markets Intelligence | Q4 2026 | 🔵 Planning |

---

## Key Files to Understand First
If you're new to this codebase, read in this order:
1. `app.py` — understand routing and session state
2. `data_loader.py` — understand how IPO data flows in
3. `rag_retriever.py` — understand Pinecone + SQLite retrieval
4. `utils/ai_utils.py` — understand how Claude is prompted
5. `pages/ipo_detail.py` — understand the main user-facing feature
