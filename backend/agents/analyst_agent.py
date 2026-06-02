"""Analyst Agent — non-grounded review + price-history intelligence.

Ingests scraped reviews and price history, then asks Gemini (``settings.PRO_MODEL``)
for a structured JSON verdict: fake-review estimate, chronic issues, sentiment
map, red flags and a buy/wait/avoid recommendation. The model call, JSON repair
and quota cascade live in ``services.gemini_grounded.call_gemini``.
"""
from __future__ import annotations

import logging
from typing import List

from ..config import settings
from ..models.requests import AnalystRequest, PricePoint
from ..models.responses import (
    AnalystResponse, AgentStatus,
    BuyStrategy, ReviewInsight, PriceTrend,
)
from ..services.gemini_client import GeminiAuthError
from ..services.gemini_grounded import call_gemini

logger = logging.getLogger("technotrack.analyst_agent")


_ANALYST_SYSTEM = """
You are an elite product intelligence analyst with expertise in:
• Detecting fake / incentivized reviews using linguistic pattern analysis (Trust Check). Score generic reviews like "Great product", "Very good" as bot-like.
• Identifying chronic product defects from repeated complaint patterns (Chronic Issues). Specifically warn if negative words like "Overheating" or "Disconnection" appear more than 3 times.
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
  "strategy": "BUY | WAIT | AVOID | UNCERTAIN",
  "confidence": 0.0 to 1.0,
  "fake_review_pct": 0 to 100,
  "chronic_issues": ["issue 1", "issue 2"],
  "positive_themes": ["theme 1", "theme 2"],
  "average_sentiment": -1.0 to 1.0,
  "sentiment_map": {{"Comfort": 0.8, "Audio Quality": 0.9, "Battery": -0.5}},
  "red_flags": ["Critical warning 1", "Critical warning 2"],
  "trend_direction": "upward | downward | stable",
  "predicted_drop": "description or null",
  "ai_summary": "2-3 sentence plain-language summary",
  "final_recommendation": "Detailed strategic decision merging price, reviews, and trends (e.g. 'I recommend buying now because...')"
}}
""".strip()


def _compute_price_trend(price_history: List[PricePoint]) -> PriceTrend:
    """Descriptive price statistics (current / 30d low / 30d high / direction)."""
    prices = [p.price for p in price_history]
    current = price_history[-1].price
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
        predicted_drop=None,
    )


async def _call_pro_analyst(
    product_name: str,
    reviews: List[str],
    price_history: List[PricePoint],
    locale: str,
) -> tuple[dict, str]:
    """Send all reviews + price history to ``settings.PRO_MODEL`` in one prompt
    and return ``(parsed_json, model_used)``.
    """
    # Cap at 500 reviews × 400 chars so the prompt stays well under the
    # context limit with headroom for the system prompt and response.
    reviews_block = "\n".join(
        f"[{i+1}] {r[:400]}" for i, r in enumerate(reviews[:500])
    )
    price_block = "\n".join(
        f"{p.date} | {p.store} | ${p.price:.2f}" for p in price_history
    )
    prompt = _ANALYST_PROMPT.format(
        product_name=product_name,
        review_count=len(reviews),
        reviews_block=reviews_block,
        price_history_block=price_block,
    )

    # Deep rung on an independent quota counter; this call is non-grounded so
    # the lite tier is safe to use.
    extras = ["gemini-2.5-flash-lite"]
    result = await call_gemini(
        primary_model=settings.PRO_MODEL,
        fallback_model=settings.PRO_FALLBACK_MODEL,
        extra_models=extras,
        system=_ANALYST_SYSTEM.format(locale=locale),
        user_prompt=prompt,
        use_search=False,
        response_json=True,
        # Headroom for Gemini 3's thinking tokens + the full JSON report.
        max_output_tokens=3072,
        temperature=0.2,
        top_p=0.95,
        timeout_seconds=45.0,
    )
    if result.parsed is None:
        raise RuntimeError("Analyst model returned a non-JSON payload.")
    return result.parsed, result.model_used


async def run_analyst_agent(request: AnalystRequest, emit_status=None) -> AnalystResponse:
    """Analyze scraped reviews + price history into an AnalystResponse:
    fake-review %, chronic issues, sentiment map, red flags and a
    buy/wait/avoid recommendation.
    """
    logger.info(
        "AnalystAgent → starting (product=%s, reviews=%d)",
        request.product_name, len(request.reviews),
    )

    if emit_status:
        await emit_status(f"Analyst Agent interpreting data ({settings.PRO_MODEL})...")

    price_trend = _compute_price_trend(request.price_history)

    # Auth errors bubble up for the route layer; everything else degrades to a
    # graceful AnalystResponse(status=ERROR) instead of a 500.
    try:
        data, used_model = await _call_pro_analyst(
            product_name=request.product_name,
            reviews=request.reviews,
            price_history=request.price_history,
            locale=request.locale,
        )
    except GeminiAuthError:
        raise
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
            ai_summary="An error occurred during analysis.",
            final_recommendation="Analysis could not be performed.",
            error_detail=str(err),
        )

    if emit_status:
        await emit_status("Analysis complete, final strategy created.")

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
        "BUY":       BuyStrategy.BUY,
        "WAIT":    BuyStrategy.WAIT,
        "AVOID":    BuyStrategy.AVOID,
        "UNCERTAIN": BuyStrategy.UNCERTAIN,
    }
    strategy = strategy_map.get(data.get("strategy", "UNCERTAIN"), BuyStrategy.UNCERTAIN)

    return AnalystResponse(
        status=AgentStatus.SUCCESS,
        agent=f"analyst_agent ({used_model})",
        model_used=used_model,
        product_id=request.product_id,
        product_name=request.product_name,
        strategy=strategy,
        confidence=float(data.get("confidence", 0.5)),
        review_insight=review_insight,
        price_trend=price_trend,
        ai_summary=data.get("ai_summary", ""),
        final_recommendation=data.get("final_recommendation", "Uncertain."),
    )
