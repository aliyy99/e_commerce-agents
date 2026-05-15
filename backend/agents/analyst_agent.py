"""
╔══════════════════════════════════════════════════════════════╗
║             ANALYST AGENT  –  Gemini Flash                  ║
╠══════════════════════════════════════════════════════════════╣
║  Model: ``settings.PRO_MODEL`` (free-tier-safe Flash variant) ║
║  ▸ Large context window: ingests thousands of reviews        ║
║    + full price history in a single request                  ║
║  ▸ Detects fake reviews, identifies recurring hardware /     ║
║    software flaws, weighs contradictions                     ║
║  ▸ Structured output mode for reliable JSON extraction       ║
║  NOTE: Pro-family models are paid-tier only on this key      ║
║  (limit=0 on free tier), so the default routes to Flash.     ║
╚══════════════════════════════════════════════════════════════╝
"""
from __future__ import annotations

import json
import logging
import re
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
from ..services.gemini_client import (
    is_rate_limit_error,
    GeminiAuthError,
    configure_gemini_client,
    raise_if_auth_error,
    retry_on_non_auth_error,
)

logger = logging.getLogger("shopsage.analyst_agent")


# ─────────────────────────────────────────────────────────────
# Prompt templates
# ─────────────────────────────────────────────────────────────
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
    retry=retry_on_non_auth_error,
)
async def _call_pro_analyst(
    product_name: str,
    reviews: List[str],
    price_history: List[PricePoint],
    locale: str,
    model_name: str | None = None,
) -> dict:
    """
    AGENT: Analyst Agent
    Sends all reviews + price history to Gemini (model from ``settings.PRO_MODEL``)
    in a single mega-prompt. The analyst request can contain 5,000+ reviews
    and the Flash model's long-context handling is sufficient for fake-review
    detection and buy/wait reasoning. The "PRO_MODEL" setting name is kept for
    backwards-compat — its value points to a free-tier Flash model.

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

    configure_gemini_client()
    resolved_model = model_name or settings.PRO_MODEL
    pro = genai.GenerativeModel(
        model_name=resolved_model,
        system_instruction=_ANALYST_SYSTEM.format(locale=locale),
    )
    prompt = _ANALYST_PROMPT.format(
        product_name=product_name,
        review_count=len(reviews),
        reviews_block=reviews_block,
        price_history_block=price_block,
    )
    try:
        response = pro.generate_content(
            prompt,
            generation_config=genai.GenerationConfig(
                temperature=0.2,        # Low temp for deterministic analysis
                max_output_tokens=2048, # Enough for detailed JSON output
                # Strict JSON mode — Flash sometimes emits trailing commas or
                # unescaped newlines that break a plain ``json.loads``.
                response_mime_type="application/json",
            ),
        )
    except Exception as err:
        raise_if_auth_error(err)
        raise
    raw_text = (getattr(response, "text", "") or "").strip()
    if not raw_text:
        raise ValueError("Analyst model returned empty text.")
    # strict=False allows raw newlines/tabs inside JSON string values, which
    # Gemini occasionally produces even in JSON-mime mode.
    try:
        return json.loads(raw_text, strict=False)
    except json.JSONDecodeError:
        pass
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw_text, re.DOTALL | re.IGNORECASE)
    if fenced:
        return json.loads(fenced.group(1), strict=False)
    first = raw_text.find("{")
    last = raw_text.rfind("}")
    if first != -1 and last != -1 and last > first:
        return json.loads(raw_text[first : last + 1], strict=False)
    return json.loads(raw_text, strict=False)


# ─────────────────────────────────────────────────────────────
# Public entry-point
# ─────────────────────────────────────────────────────────────
async def run_analyst_agent(request: AnalystRequest, emit_status=None) -> AnalystResponse:
    """
    AGENT: Analyst Agent  (Gemini Flash via ``settings.PRO_MODEL``)
    ──────────────────────────────────────────────────────────────
    Analyzes scraped reviews and price history to produce:
      • Fake review percentage estimate
      • Chronic product issue list
      • Sentiment score and Sentiment Map
      • Red Flag detection
      • Buy / Wait / Avoid recommendation
      • Plain-language AI summary and Final Strategy

    Model is resolved from ``settings.PRO_MODEL``; defaults to a free-tier
    Flash variant because Pro models have zero free quota on the active key.

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
        await emit_status(f"Analyst Agent interpreting data ({settings.PRO_MODEL})...")

    # Pre-compute price trend (synchronous, cheap)
    price_trend = _compute_price_trend(request.price_history)

    # Cascade: primary model first, then fallback (different model family so
    # daily-quota counters are independent). At most 2 successful API calls.
    candidate_models = list(dict.fromkeys([
        settings.PRO_MODEL,
        settings.PRO_FALLBACK_MODEL,
    ]))
    data: dict | None = None
    used_model: str | None = None
    last_err: Exception | None = None
    for model_name in candidate_models:
        try:
            data = await _call_pro_analyst(
                product_name=request.product_name,
                reviews=request.reviews,
                price_history=request.price_history,
                locale=request.locale,
                model_name=model_name,
            )
            used_model = model_name
            break
        except Exception as err:
            last_err = err
            # Auth errors are terminal — no point trying the fallback model.
            try:
                raise_if_auth_error(err)
            except GeminiAuthError:
                raise
            if is_rate_limit_error(err):
                logger.warning("AnalystAgent: %s rate-limited, trying fallback.", model_name)
                continue
            logger.warning("AnalystAgent: %s failed (%s), trying fallback.", model_name, err)
            continue

    if data is None:
        logger.error("AnalystAgent failed on all candidates: %s", last_err)
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
            error_detail=str(last_err),
        )

    if emit_status:
        await emit_status("Analysis complete, final strategy created.")

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
