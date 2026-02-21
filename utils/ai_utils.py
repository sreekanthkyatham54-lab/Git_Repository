"""
ai_utils.py — AI analysis powered by Claude API.
Option A: question-routed DRHP sections for accurate, section-specific answers.
"""
import anthropic, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


def get_client(api_key: str) -> anthropic.Anthropic:
    return anthropic.Anthropic(api_key=api_key)


def get_drhp_context(ipo_id: str, user_question: str = "") -> str:
    """Pull relevant DRHP sections via Option A question routing."""
    try:
        from db_reader import get_drhp_context as _get
        return _get(ipo_id, user_question)
    except Exception:
        return ""


def build_ipo_context(ipo: dict) -> str:
    rev   = ipo.get("revenue_cr") or []
    prof  = ipo.get("profit_cr") or []
    years = ipo.get("years") or []
    if rev and prof:
        fin_lines = "\n".join(
            f"  {years[i] if i < len(years) else f'Year {i+1}'}: Revenue ₹{rev[i]}Cr | Profit ₹{prof[i]}Cr"
            for i in range(min(len(rev), len(prof)))
        )
    else:
        fin_lines = "  Not yet extracted (run drhp_scraper.py)"

    peers     = ipo.get("peers") or []
    data_q    = ipo.get("data_quality", "limited")
    dq_note   = {"full_drhp":"✅ Full DRHP loaded","partial":"⚠ Partial DRHP","limited":"⚠ Summary only — DRHP not yet loaded"}.get(data_q,"")

    return f"""
=== IPO SUMMARY ({dq_note}) ===
Company:     {ipo.get('company','—')}
Type:        {ipo.get('ipo_type','SME')} | Exchange: {ipo.get('exchange','—')}
Sector:      {ipo.get('sector','—')}
Issue Price: ₹{ipo.get('issue_price','—')} | Size: ₹{ipo.get('issue_size_cr','—')}Cr | Lot: {ipo.get('lot_size','—')} shares
Open/Close:  {ipo.get('open_date','—')} to {ipo.get('close_date','—')}

=== MARKET SIGNALS ===
GMP:            ₹{ipo.get('gmp',0)} ({ipo.get('gmp_percent',0)}%)
Subscription:   {ipo.get('subscription_times',0)}x
Recommendation: {ipo.get('recommendation','—')}

=== FINANCIALS ===
{fin_lines}
P/E: {ipo.get('pe_ratio','—')}x | Industry P/E: {ipo.get('industry_pe','—')}x
Promoter Holding: {ipo.get('promoter_holding','—')}%

=== DETAILS ===
Lead Manager: {ipo.get('lead_manager','—')}
Registrar:    {ipo.get('registrar','—')}
Peers:        {', '.join(peers) if peers else '—'}
Business:     {str(ipo.get('summary','—'))[:400]}
Objects:      {str(ipo.get('objects','—'))[:300]}
Key Risks:    {str(ipo.get('risks_text','—'))[:300]}
"""


SYSTEM_PROMPT = """You are TradeSage — an expert IPO analyst for the Indian stock market, trusted by retail investors.

You have deep expertise in:
- Reading SEBI DRHPs (Draft Red Herring Prospectus) — you know the standard structure cold
- BSE SME, NSE Emerge, and Mainboard IPO regulations and norms
- Indian SME and Mainboard company valuations, GMP interpretation, subscription analysis
- Identifying red flags: promoter pledging, customer concentration, litigation, related party transactions

When DRHP sections are provided:
- Reference the ACTUAL text — quote specific numbers, names, clauses
- Cite which section the information came from (Risk Factors, Financials, etc.)
- Never fabricate details — if something isn't in the data, say so clearly

Always:
1. Lead with the most important insight for a retail investor
2. Quote specific numbers — revenue figures, GMP %, litigation amounts
3. Highlight RED FLAGS prominently — don't bury them
4. Use plain language — no financial jargon without explanation
5. Be honest — a neutral or negative view is more valuable than false positivity
6. End chat answers with one actionable takeaway

Format: Use bullet points for lists. Use ₹ for rupees. Keep responses focused and under 300 words unless deep analysis is requested."""


def chat_with_ipo(api_key: str, ipo: dict, messages: list, user_message: str) -> str:
    """Chat Q&A — routes DRHP context based on the user's actual question."""
    client       = get_client(api_key)
    ipo_context  = build_ipo_context(ipo)
    # KEY Option A change: pass user_message so we fetch the RIGHT section
    drhp_context = get_drhp_context(ipo.get("id",""), user_question=user_message)

    data_quality = ipo.get("data_quality","limited")
    if not drhp_context:
        drhp_note = "\n\n⚠ DRHP not yet loaded for this IPO. Answering from summary data only — run drhp_scraper.py for full analysis."
    else:
        drhp_note = ""

    system = SYSTEM_PROMPT + f"\n\n{ipo_context}{drhp_context}{drhp_note}"

    chat_messages = [{"role": m["role"], "content": m["content"]} for m in messages]
    chat_messages.append({"role": "user", "content": user_message})

    response = get_client(api_key).messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1200,
        system=system,
        messages=chat_messages,
    )
    return response.content[0].text


def get_ai_recommendation(api_key: str, ipo: dict) -> dict:
    """Full AI scorecard — uses all DRHP sections for comprehensive analysis."""
    ipo_context  = build_ipo_context(ipo)
    # For scorecard: no specific question — get all sections in default order
    drhp_context = get_drhp_context(ipo.get("id",""), user_question="")

    has_drhp  = bool(drhp_context)
    drhp_note = (
        "Full DRHP sections provided above — base your analysis on actual DRHP text, cite specific findings."
        if has_drhp else
        "DRHP not yet loaded. Base analysis on summary data. Note data limitations in your response."
    )

    prompt = f"""{ipo_context}{drhp_context}

{drhp_note}

Provide a structured IPO analysis. Respond ONLY with a valid JSON object (no markdown, no backticks):
{{
  "verdict": "SUBSCRIBE" or "AVOID" or "NEUTRAL",
  "conviction": "High" or "Medium" or "Low",
  "score": <integer 1-10>,
  "one_liner": "<25 word verdict summary>",
  "bull_case": "<2-3 sentences — specific positives from DRHP/data>",
  "bear_case": "<2-3 sentences — specific risks from DRHP/data>",
  "red_flags": ["<specific flag from DRHP or data>", "<flag2>"],
  "positives":  ["<specific positive>", "<positive2>"],
  "valuation_view": "<1 sentence on P/E vs peers and issue price fairness>",
  "gmp_view": "<1 sentence interpreting the GMP signal>",
  "suitable_for": "<risk profile and investment horizon this suits>",
  "data_quality": "{ipo.get('data_quality','limited')}"
}}"""

    response = get_client(api_key).messages.create(
        model="claude-opus-4-6",
        max_tokens=1200,
        messages=[{"role":"user","content":prompt}],
    )
    text = response.content[0].text.strip()
    if "```" in text:
        text = text.split("```")[1]
        if text.startswith("json"): text = text[4:]
    return json.loads(text.strip())


def compare_with_industry(api_key: str, ipo: dict) -> str:
    """Industry comparison — uses financials section specifically."""
    ipo_context  = build_ipo_context(ipo)
    # Route to financials + overview sections
    drhp_context = get_drhp_context(ipo.get("id",""), user_question="revenue profit financial valuation peer comparison")

    company  = ipo.get("company","this company")
    sector   = ipo.get("sector") or "—"
    peers    = ", ".join(ipo.get("peers") or []) or "not available"
    pe       = ipo.get("pe_ratio") or "not available"
    ind_pe   = ipo.get("industry_pe") or "not available"

    prompt = f"""{ipo_context}{drhp_context}

Analyse how {company} compares with its sector ({sector}) and listed peers ({peers}).

Write 3-4 focused paragraphs:
1. Revenue and profit growth trends — use exact figures from DRHP if available
2. Valuation — P/E {pe}x vs industry P/E {ind_pe}x — attractive or expensive?
3. Competitive positioning vs peers — advantages and disadvantages
4. Overall verdict — good entry point or wait-and-watch?

Be specific with numbers. Write for a retail investor making a decision today."""

    response = get_client(api_key).messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=900,
        messages=[{"role":"user","content":prompt}],
    )
    return response.content[0].text
