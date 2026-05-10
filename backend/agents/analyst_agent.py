"""
╔══════════════════════════════════════════════════════════════╗
║             ANALYST AGENT  –  Gemini 2.5 Pro                ║
╠══════════════════════════════════════════════════════════════╣
║  WHY PRO?                                                    ║
║  ▸ 1M-token context window: ingests thousands of reviews     ║
║    + full price history in a single request                  ║
║  ▸ Multi-step reasoning: detects fake reviews, identifies    ║
║    recurring hardware/software flaws, weighs contradictions  ║
║  ▸ Structured output mode for reliable JSON extraction       ║
╚══════════════════════════════════════════════════════════════╝
"""
from __future__ import annotations

import json
import logging
import statistics
from typing import List

import google.generativeai as genai
from tenacity import retry, stop_after_attempt, wait_exponential

from ..config import settings
from ..models.requests import AnalystRequest, PricePoint
from ..models.responses import (
    AnalystResponse, AgentStatus,
    BuyStrategy, ReviewInsight, PriceTrend,
)

logger = logging.getLogger("shopsage.analyst_agent")
genai.configure(api_key=settings.GOOGLE_API_KEY)


# ─────────────────────────────────────────────────────────────
# Prompt templates
# ─────────────────────────────────────────────────────────────
_ANALYST_SYSTEM = """
You are an elite product intelligence analyst with expertise in:
• Detecting fake / incentivized reviews using linguistic pattern analysis (Güven Kontrolü). Score generic reviews like "Harika ürün", "Çok iyi" as bot-like.
• Identifying chronic product defects from repeated complaint patterns (Kronik Sorunlar). Specifically warn if negative words like "Isınma" or "Kopma" appear more than 3 times.
• Evaluating pricing trends and predicting future price movements
• Generating clear buy/wait/avoid recommendations
• Creating Sentiment Maps (e.g., Comfort, Audio Quality, Battery)
• Catching Red Flags ("fake product", "arrived broken")

You MUST respond in strict JSON (no markdown, no prose outside JSON).
Response locale: {locale}
""".strip()

_ANALYST_PROMPT = """
Product: {product_name}

=== REVIEWS ({review_count} reviews) ===
{reviews_block}

=== PRICE HISTORY ===
{price_history_block}

Analyze the above data and return ONLY this JSON structure:

{{
  "strategy": "AL | BEKLE | KAÇIN | BELİRSİZ",
  "confidence": 0.0 to 1.0,
  "fake_review_pct": 0 to 100,
  "chronic_issues": ["issue 1", "issue 2"],
  "positive_themes": ["theme 1", "theme 2"],
  "average_sentiment": -1.0 to 1.0,
  "sentiment_map": {{"Konfor": 0.8, "Ses Kalitesi": 0.9, "Batarya": -0.5}},
  "red_flags": ["Critical warning 1", "Critical warning 2"],
  "trend_direction": "upward | downward | stable",
  "predicted_drop": "description or null",
  "ai_summary": "2-3 sentence plain-language summary",
  "final_recommendation": "Detailed strategic decision merging price, reviews, and trends (e.g. 'Şu an almanı öneririm çünkü...')"
}}
""".strip()


# ─────────────────────────────────────────────────────────────
# Price utilities
# ─────────────────────────────────────────────────────────────
def _compute_price_trend(price_history: List[PricePoint]) -> PriceTrend:
    """
    AGENT: Analyst Agent – Helper
    Computes descriptive price statistics from raw price history.
    Uses only stdlib (statistics module) — no pandas overhead.
    """
    prices = [p.price for p in price_history]
    current = price_history[-1].price  # most recent entry
    low_30  = min(prices)
    high_30 = max(prices)

    if len(prices) >= 2:
        slope = prices[-1] - prices[0]
        if slope < -10:
            direction = "downward"
        elif slope > 10:
            direction = "upward"
        else:
            direction = "stable"
    else:
        direction = "unknown"

    return PriceTrend(
        current_price=current,
        lowest_30d=low_30,
        highest_30d=high_30,
        trend_direction=direction,
        predicted_drop=None,  # Will be filled by Pro model
    )


# ─────────────────────────────────────────────────────────────
# Model call
# ─────────────────────────────────────────────────────────────
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True,
)
async def _call_pro_analyst(
    product_name: str,
    reviews: List[str],
    price_history: List[PricePoint],
    locale: str,
) -> dict:
    """
    AGENT: Analyst Agent
    Sends all reviews + price history to Gemini Pro in a single mega-prompt.

    WHY PRO: The analyst request can contain 5,000+ reviews. Gemini Pro's
    1M-token context window and multi-step chain-of-thought reasoning ensure
    accurate fake detection and nuanced buy/wait recommendations.

    Args:
        product_name:  Display name for the product.
        reviews:       List of raw scraped review strings.
        price_history: Chronological list of PricePoint entries.
        locale:        ISO-639 language code for the response.

    Returns:
        Parsed JSON dict with all analyst insights.
    """
    # Build compacted blocks to stay within token budget
    reviews_block = "\n".join(
        f"[{i+1}] {r[:400]}" for i, r in enumerate(reviews[:500])  # cap at 500 reviews
    )
    price_block = "\n".join(
        f"{p.date} | {p.store} | ${p.price:.2f}" for p in price_history
    )

    # WHY PRO: Complex reasoning over long-context inputs (reviews + price trend)
    pro = genai.GenerativeModel(
        model_name=settings.PRO_MODEL,
        system_instruction=_ANALYST_SYSTEM.format(locale=locale),
    )
    prompt = _ANALYST_PROMPT.format(
        product_name=product_name,
        review_count=len(reviews),
        reviews_block=reviews_block,
        price_history_block=price_block,
    )
    response = pro.generate_content(
        prompt,
        generation_config=genai.GenerationConfig(
            temperature=0.2,        # Low temp for deterministic analysis
            max_output_tokens=2048, # Enough for detailed JSON output
        ),
    )
    return json.loads(response.text.strip())


# ─────────────────────────────────────────────────────────────
# Public entry-point
# ─────────────────────────────────────────────────────────────
async def run_analyst_agent(request: AnalystRequest, emit_status=None) -> AnalystResponse:
    """
    AGENT: Analyst Agent  (Gemini 2.5 Pro)
    ──────────────────────────────────────
    Analyzes scraped reviews and price history to produce:
      • Fake review percentage estimate
      • Chronic product issue list
      • Sentiment score and Sentiment Map
      • Red Flag detection
      • Buy / Wait / Avoid recommendation
      • Plain-language AI summary and Final Strategy

    This agent always uses Gemini Pro — there is no Flash equivalent
    for deep multi-step analysis over thousands of review tokens.

    Args:
        request: Validated AnalystRequest.

    Returns:
        AnalystResponse with full product intelligence report.
    """
    logger.info(
        "AnalystAgent → starting (product=%s, reviews=%d)",
        request.product_name, len(request.reviews),
    )

    if emit_status:
        await emit_status("Analyst Agent verileri yorumluyor (Gemini 2.5 Pro)...")

    # Pre-compute price trend (synchronous, cheap)
    price_trend = _compute_price_trend(request.price_history)

    try:
        data = await _call_pro_analyst(
            product_name=request.product_name,
            reviews=request.reviews,
            price_history=request.price_history,
            locale=request.locale,
        )
    except Exception as err:
        logger.error("AnalystAgent failed: %s", err)
        return AnalystResponse(
            status=AgentStatus.ERROR,
            product_id=request.product_id,
            product_name=request.product_name,
            strategy=BuyStrategy.UNCERTAIN,
            confidence=0.0,
            review_insight=ReviewInsight(
                total_reviews=len(request.reviews),
                fake_review_pct=0.0,
                average_sentiment=0.0,
            ),
            price_trend=price_trend,
            ai_summary="Analiz sırasında bir hata oluştu.",
            final_recommendation="Analiz yapılamadı.",
            error_detail=str(err),
        )

    if emit_status:
        await emit_status("Analiz tamamlandı, final strateji oluşturuldu.")

    # Merge predicted_drop from model into pre-computed trend
    price_trend.predicted_drop  = data.get("predicted_drop")
    price_trend.trend_direction = data.get("trend_direction", price_trend.trend_direction)

    review_insight = ReviewInsight(
        total_reviews=len(request.reviews),
        fake_review_pct=float(data.get("fake_review_pct", 0)),
        chronic_issues=data.get("chronic_issues", []),
        positive_themes=data.get("positive_themes", []),
        average_sentiment=float(data.get("average_sentiment", 0)),
        sentiment_map=data.get("sentiment_map", {}),
        red_flags=data.get("red_flags", []),
    )

    strategy_map = {
        "AL":       BuyStrategy.BUY,
        "BEKLE":    BuyStrategy.WAIT,
        "KAÇIN":    BuyStrategy.AVOID,
        "BELİRSİZ": BuyStrategy.UNCERTAIN,
    }
    strategy = strategy_map.get(data.get("strategy", "BELİRSİZ"), BuyStrategy.UNCERTAIN)

    return AnalystResponse(
        status=AgentStatus.SUCCESS,
        product_id=request.product_id,
        product_name=request.product_name,
        strategy=strategy,
        confidence=float(data.get("confidence", 0.5)),
        review_insight=review_insight,
        price_trend=price_trend,
        ai_summary=data.get("ai_summary", ""),
        final_recommendation=data.get("final_recommendation", "Belirsiz."),
    )
