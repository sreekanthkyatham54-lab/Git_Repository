"""
ai_utils.py — AI analysis using RAG (Retrieval-Augmented Generation)
=====================================================================
Architecture:
  1. rag_retriever finds the most relevant chunks from the DRHP
     using cosine similarity on sentence-transformer embeddings
  2. Retrieved chunks are passed to Claude with strict citation rules
  3. Claude answers ONLY from the retrieved text — no hallucination

Every answer includes page citations so users can verify in the original filing.
"""
import anthropic, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


def get_client(api_key: str) -> anthropic.Anthropic:
    return anthropic.Anthropic(api_key=api_key)


# ── RAG CONTEXT BUILDER ───────────────────────────────────────────────────────
def build_rag_context(ipo_id: str, question: str, for_scorecard: bool = False) -> tuple:
    """
    Retrieve relevant chunks from RAG index and format them for Claude.
    Returns: (context_string, rag_available)
    """
    try:
        from rag_retriever import retrieve_chunks, retrieve_for_scorecard, has_rag_index
    except ImportError:
        return "", False

    if not has_rag_index(ipo_id):
        return "", False

    chunks = retrieve_for_scorecard(ipo_id) if for_scorecard else retrieve_chunks(ipo_id, question, top_k=6)

    if not chunks:
        return "", True

    passages = []
    for chunk in chunks:
        section_label = chunk["section"].replace("_", " ").title()
        passage = (
            f"[Source: {section_label} section, Page {chunk['page_number']}]\n"
            f"{chunk['text']}"
        )
        passages.append(passage)

    divider = "\n" + "━" * 50 + "\n"
    context = (
        f"\n\n---\n"
        f"**DRHP PASSAGES (retrieved from actual filing)**\n"
        f"These are exact extracts from the DRHP. Answer ONLY from this text.\n\n"
        + divider.join(passages)
    )
    return context, True


def build_ipo_summary(ipo: dict) -> str:
    """
    Build IPO summary for Claude.
    IMPORTANT: Financial numbers (revenue, profit) are intentionally excluded.
    They came from broken regex extraction and were causing hallucinations.
    Claude gets correct financial figures from RAG passages only.
    """
    peers = ipo.get("peers") or []
    return f"""
=== IPO FACTS ===
Company:      {ipo.get('company','—')}
Type:         {ipo.get('ipo_type','SME')} | Exchange: {ipo.get('exchange','—')}
Sector:       {ipo.get('sector','—')}
Issue Price:  ₹{ipo.get('issue_price','—')} | Size: ₹{ipo.get('issue_size_cr','—')}Cr | Lot: {ipo.get('lot_size','—')} shares
Open/Close:   {ipo.get('open_date','—')} to {ipo.get('close_date','—')}

=== MARKET SIGNALS ===
GMP:            ₹{ipo.get('gmp',0)} ({ipo.get('gmp_percent',0)}% above issue price)
Subscription:   {ipo.get('subscription_times',0)}x
Recommendation: {ipo.get('recommendation','—')}

=== VALUATION CONTEXT ===
P/E: {ipo.get('pe_ratio','—')}x | Industry P/E: {ipo.get('industry_pe','—')}x
Promoter Holding: {ipo.get('promoter_holding','—')}%

=== OTHER DETAILS ===
Lead Manager: {ipo.get('lead_manager','—')}
Registrar:    {ipo.get('registrar','—')}
Peers:        {', '.join(peers) if peers else '—'}

=== FINANCIALS ===
Read ONLY from the DRHP passages below. Do not use any other figures.
"""


RAG_SYSTEM_PROMPT = """You are TradeSage — an expert IPO analyst for the Indian stock market.

STRICT RULES — non-negotiable:
1. Answer ONLY from the DRHP passages provided below. These are exact extracts from the actual SEBI filing.
2. Every factual claim MUST cite its source: write (Source: [Section], Page [N]) after the claim.
3. If the answer is NOT in the provided passages, say:
   "This specific information is not available in the DRHP sections I retrieved."
   Do NOT guess, estimate, or infer beyond what is written.
4. Only quote numbers that appear explicitly in the passages. Never calculate or estimate figures.
5. If passages contain contradictory information, flag it explicitly.

After DRHP citations, you may add one brief market context sentence using GMP/subscription data
from IPO Facts — but label it clearly as "Market context:" not as DRHP data.

Format:
- Lead with the most important finding for a retail investor
- Use bullet points for multiple findings, each with page citation
- End with one "Actionable takeaway:" line
- Keep under 300 words unless deep analysis is requested
- Use ₹ for rupees"""

NO_RAG_SYSTEM_PROMPT = """You are TradeSage — an expert IPO analyst for the Indian stock market.

IMPORTANT: The DRHP for this IPO has not been indexed yet. You are working from
summary data only — NOT from the actual SEBI filing.

Be transparent about this limitation. Do not present analysis as if it came from the DRHP.
Prefix uncertain statements with "Based on available summary data..."

For questions requiring DRHP data (risks, financials, litigation, promoters), tell the user:
"For accurate analysis, run rag_indexer.py to enable full DRHP Q&A for this IPO."

Use ₹ for rupees. Be honest about data limitations."""


def chat_with_ipo(api_key: str, ipo: dict, messages: list, user_message: str) -> str:
    """RAG-powered chat Q&A — answers grounded in actual DRHP text with page citations."""
    client      = get_client(api_key)
    ipo_id      = ipo.get("id", "")
    ipo_summary = build_ipo_summary(ipo)

    rag_context, rag_available = build_rag_context(ipo_id, user_message)

    if rag_available and rag_context:
        system = RAG_SYSTEM_PROMPT + f"\n\n{ipo_summary}{rag_context}"
    elif rag_available and not rag_context:
        system = (
            RAG_SYSTEM_PROMPT + f"\n\n{ipo_summary}"
            + "\n\n⚠ No relevant DRHP passages found for this question. "
            + "Answer from IPO Facts only and be explicit about this limitation."
        )
    else:
        system = NO_RAG_SYSTEM_PROMPT + f"\n\n{ipo_summary}"

    chat_messages = [{"role": m["role"], "content": m["content"]} for m in messages]
    chat_messages.append({"role": "user", "content": user_message})

    response = client.messages.create(
        model      = "claude-haiku-4-5-20251001",
        max_tokens = 1200,
        system     = system,
        messages   = chat_messages,
    )
    return response.content[0].text


def get_ai_recommendation(api_key: str, ipo: dict) -> dict:
    """Full AI scorecard using RAG — retrieves best chunk from each DRHP section."""
    ipo_id      = ipo.get("id", "")
    ipo_summary = build_ipo_summary(ipo)

    rag_context, rag_available = build_rag_context(ipo_id, question="", for_scorecard=True)

    drhp_note = (
        "Full DRHP passages provided above. Base analysis on actual DRHP text. Cite page numbers."
        if rag_available and rag_context else
        "DRHP not yet indexed. Base analysis on IPO Facts only. Note limitations clearly."
    )

    data_source = "DRHP passages — RAG indexed" if rag_available else "Summary data only — DRHP not indexed"

    prompt = f"""{ipo_summary}{rag_context}

{drhp_note}

Provide a structured IPO analysis. Respond ONLY with a valid JSON object (no markdown, no backticks):
{{
  "verdict":        "SUBSCRIBE" or "AVOID" or "NEUTRAL",
  "conviction":     "High" or "Medium" or "Low",
  "score":          <integer 1-10>,
  "one_liner":      "<25 word verdict summary>",
  "bull_case":      "<2-3 sentences — cite specific DRHP findings with page numbers>",
  "bear_case":      "<2-3 sentences — cite specific risks with page numbers>",
  "red_flags":      ["<specific flag from DRHP, page N>", "<flag2>"],
  "positives":      ["<specific positive from DRHP, page N>", "<positive2>"],
  "valuation_view": "<1 sentence on valuation — cite DRHP if available>",
  "gmp_view":       "<1 sentence interpreting GMP signal>",
  "suitable_for":   "<risk profile and investment horizon>",
  "data_source":    "{data_source}"
}}"""

    response = get_client(api_key).messages.create(
        model      = "claude-haiku-4-5-20251001",
        max_tokens = 1400,
        messages   = [{"role": "user", "content": prompt}],
    )
    text = response.content[0].text.strip()
    if "```" in text:
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    return json.loads(text.strip())


def compare_with_industry(api_key: str, ipo: dict) -> str:
    """Industry comparison using RAG."""
    ipo_id  = ipo.get("id", "")
    company = ipo.get("company", "this company")
    sector  = ipo.get("sector") or "—"
    peers   = ", ".join(ipo.get("peers") or []) or "not available"
    pe      = ipo.get("pe_ratio") or "not available"
    ind_pe  = ipo.get("industry_pe") or "not available"

    ipo_summary = build_ipo_summary(ipo)
    rag_context, _ = build_rag_context(
        ipo_id,
        question="revenue profit financial performance growth valuation peer comparison"
    )

    prompt = f"""{ipo_summary}{rag_context}

Analyse how {company} compares with its sector ({sector}) and listed peers ({peers}).

Write 3-4 focused paragraphs:
1. Revenue and profit growth — cite exact figures with page numbers from DRHP passages
2. Valuation — P/E {pe}x vs industry P/E {ind_pe}x — attractive or expensive?
3. Competitive positioning vs peers — advantages and disadvantages
4. Overall verdict — good entry point or wait-and-watch?

Be specific with numbers. Cite page numbers. Write for a retail investor."""

    response = get_client(api_key).messages.create(
        model      = "claude-haiku-4-5-20251001",
        max_tokens = 900,
        messages   = [{"role": "user", "content": prompt}],
    )
    return response.content[0].text
