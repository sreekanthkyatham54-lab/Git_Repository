"""
AI utility functions powered by Claude API.
Uses DRHP text from DB when available for deep analysis.
"""
import anthropic
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


def get_client(api_key: str) -> anthropic.Anthropic:
    return anthropic.Anthropic(api_key=api_key)


def get_drhp_context(ipo_id: str) -> str:
    """Load DRHP text from DB if available. Returns empty string if not."""
    try:
        from db_reader import get_drhp_text
        text = get_drhp_text(ipo_id)
        if text and len(text) > 200:
            # Send most relevant ~30K chars to Claude (fits in context well)
            return f"\n\n## DRHP / PROSPECTUS FULL TEXT (use this for detailed answers):\n{text[:30000]}"
    except Exception:
        pass
    return ""


def build_ipo_context(ipo: dict) -> str:
    rev   = ipo.get("revenue_cr") or []
    prof  = ipo.get("profit_cr") or []
    years = ipo.get("years") or []

    if rev and prof:
        fin_lines = "\n".join(
            f"  - {years[i] if i < len(years) else f'Year {i+1}'}: Revenue ₹{rev[i]}Cr | Profit ₹{prof[i]}Cr"
            for i in range(min(len(rev), len(prof)))
        )
    else:
        fin_lines = "  - Not yet extracted (DRHP pipeline not run)"

    peers     = ipo.get("peers") or []
    peers_str = ", ".join(peers) if peers else "Not available"
    promoters = ipo.get("promoters", "") or ""
    objects   = ipo.get("objects", "") or ""
    risks     = ipo.get("risks_text", "") or ""

    return f"""
=== IPO SUMMARY ===
Company:     {ipo.get('company', '—')}
Sector:      {ipo.get('sector', '—')}
Exchange:    {ipo.get('exchange', '—')}
Issue Price: ₹{ipo.get('issue_price', '—')} per share
Issue Size:  ₹{ipo.get('issue_size_cr', '—')} Cr
Lot Size:    {ipo.get('lot_size', '—')} shares
Open/Close:  {ipo.get('open_date', '—')} to {ipo.get('close_date', '—')}
Listing:     {ipo.get('listing_date', '—')}

=== MARKET SIGNALS ===
GMP (Grey Market Premium): ₹{ipo.get('gmp', 0)} ({ipo.get('gmp_percent', 0)}%)
Subscription:              {ipo.get('subscription_times', 0)}x subscribed
Recommendation (ipowatch): {ipo.get('recommendation', '—')}

=== FINANCIALS ===
{fin_lines}
P/E Ratio:       {ipo.get('pe_ratio', '—')}x
Industry P/E:    {ipo.get('industry_pe', '—')}x
Promoter Holding: {ipo.get('promoter_holding', '—')}%

=== COMPANY DETAILS ===
Lead Manager:  {ipo.get('lead_manager', '—')}
Registrar:     {ipo.get('registrar', '—')}
Listed Peers:  {peers_str}

Business:  {ipo.get('summary', '—')[:400]}
Promoters: {promoters[:400] if promoters else '—'}
Objects of Issue: {objects[:400] if objects else '—'}
Key Risks: {risks[:400] if risks else '—'}
"""


SYSTEM_PROMPT = """You are an expert SME IPO analyst for the Indian stock market. You have deep knowledge of:
- BSE SME and NSE Emerge listed companies and SEBI regulations
- Reading and interpreting DRHPs (Draft Red Herring Prospectus)
- Indian financial markets, SME valuations, GMP interpretation
- Retail investor risk assessment

When DRHP text is provided, always reference specific data from it — page numbers, exact figures, promoter names, actual risk factors listed.

You always:
1. Quote specific numbers from the data (revenue, profit, GMP, P/E)
2. Highlight both positives AND risks clearly
3. Use plain language a retail investor understands
4. Flag red flags prominently — litigation, pledging, concentration risk
5. Never give financial advice — give research to help informed decisions

Format responses cleanly with bullet points where helpful. Use ₹ for Indian Rupees."""


def chat_with_ipo(api_key: str, ipo: dict, messages: list, user_message: str) -> str:
    client = get_client(api_key)
    ipo_context  = build_ipo_context(ipo)
    drhp_context = get_drhp_context(ipo.get("id", ""))

    system = SYSTEM_PROMPT + f"\n\n{ipo_context}{drhp_context}"

    chat_messages = [{"role": m["role"], "content": m["content"]} for m in messages]
    chat_messages.append({"role": "user", "content": user_message})

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",   # 20x cheaper than Opus
        max_tokens=1200,
        system=system,
        messages=chat_messages,
    )
    return response.content[0].text


def get_ai_recommendation(api_key: str, ipo: dict) -> dict:
    client = get_client(api_key)
    ipo_context  = build_ipo_context(ipo)
    drhp_context = get_drhp_context(ipo.get("id", ""))

    has_drhp = bool(drhp_context)
    drhp_note = "Full DRHP text is provided above — use it for precise analysis." if has_drhp else \
                "DRHP not yet loaded. Run drhp_scraper.py to enable deep analysis."

    prompt = f"""{ipo_context}{drhp_context}

{drhp_note}

Provide a structured IPO analysis. Respond ONLY with a valid JSON object (no markdown, no backticks):
{{
  "verdict": "SUBSCRIBE" or "AVOID" or "NEUTRAL",
  "conviction": "High" or "Medium" or "Low",
  "score": <integer 1-10>,
  "one_liner": "<25 word max verdict summary>",
  "bull_case": "<2-3 sentences — specific positives from the data/DRHP>",
  "bear_case": "<2-3 sentences — specific risks from the data/DRHP>",
  "red_flags": ["<specific flag from DRHP or data>", "<flag2>"],
  "positives":  ["<specific positive>", "<positive2>"],
  "valuation_view": "<1 sentence on P/E and issue price vs peers>",
  "gmp_view": "<1 sentence interpreting the GMP signal>",
  "suitable_for": "<who should consider this — risk profile, investment horizon>",
  "data_quality": "full_drhp" or "partial" or "limited"
}}"""

    response = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=1000,
        messages=[{"role": "user", "content": prompt}],
    )
    text = response.content[0].text.strip()
    if "```" in text:
        text = text.split("```")[1]
        if text.startswith("json"): text = text[4:]
    return json.loads(text.strip())


def compare_with_industry(api_key: str, ipo: dict) -> str:
    client = get_client(api_key)
    ipo_context  = build_ipo_context(ipo)
    drhp_context = get_drhp_context(ipo.get("id", ""))

    company  = ipo.get("company", "this company")
    sector   = ipo.get("sector") or "—"
    peers    = ipo.get("peers") or []
    peers_str = ", ".join(peers) if peers else "not yet available"
    pe       = ipo.get("pe_ratio") or "not available"
    ind_pe   = ipo.get("industry_pe") or "not available"

    prompt = f"""{ipo_context}{drhp_context}

Analyze how {company} compares with its sector ({sector}) and listed peers ({peers_str}).

Write 3-4 focused paragraphs covering:
1. Revenue and profit growth trends (use exact figures if available from DRHP/data)
2. Valuation — P/E {pe}x vs industry P/E {ind_pe}x — is it attractive or expensive?
3. Competitive positioning vs listed peers — advantages and disadvantages
4. Overall verdict — good entry point or wait-and-watch?

Be specific with numbers. Write for a retail investor."""

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",   # 20x cheaper than Opus
        max_tokens=800,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text
