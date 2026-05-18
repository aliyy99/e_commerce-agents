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
║                                                              ║
║  This module delegates the actual model call + JSON parse to ║
║  ``services.gemini_grounded.call_gemini`` so the analyst     ║
║  shares the same async transport, repair stack and cascade   ║
║  logic as the Compare and Price-History agents — one place   ║
║  to fix when Gemini changes its output shape.                ║
╚══════════════════════════════════════════════════════════════╝
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
async def _call_pro_analyst(
    product_name: str,
    reviews: List[str],
    price_history: List[PricePoint],
    locale: str,
) -> tuple[dict, str]:
    """
    AGENT: Analyst Agent
    Sends all reviews + price history to Gemini (model from ``settings.PRO_MODEL``)
    in a single mega-prompt. The analyst request can contain 5,000+ reviews
    and the Flash model's long-context handling is sufficient for fake-review
    detection and buy/wait reasoning. The "PRO_MODEL" setting name is kept for
    backwards-compat — its value points to a free-tier Flash model.

    Implementation note
    ───────────────────
    We route through ``services.gemini_grounded.call_gemini`` rather than the
    sync google-generativeai SDK because:

    * the SDK is synchronous and would block the FastAPI event loop for the
      full duration of a multi-second Gemini call (everyone else freezes);
    * the shared helper already implements quota cascade, 503 same-model
      retry, auth-error short-circuit and — crucially — the JSON repair
      stack that recovers from unescaped embedded quotes, invalid
      ``\\<letter>`` escapes, bare control bytes and trailing commas. The
      analyst's previous ad-hoc parser handled none of these.

    Args:
        product_name:  Display name for the product.
        reviews:       List of raw scraped review strings.
        price_history: Chronological list of PricePoint entries.
        locale:        ISO-639 language code for the response.

    Returns:
        ``(parsed_json, model_used)`` — the analyst insights dict and the
        model name that actually produced it (useful for response metadata).
    """
    # Compact the inputs to fit comfortably inside the model's context window
    # even on free-tier Flash. The 500-review cap and 400-char-per-review
    # ceiling together keep us under ~200K tokens with plenty of headroom
    # for the system prompt and response.
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

    # Quota-survival cascade for free-tier keys. Each Flash variant has an
    # independent per-minute RPM counter, so 429 on Flash-preview rolls
    # forward to Flash 2.5, then the lite tiers. Lite tiers are safe here
    # because this call uses ``use_search=False`` — the grounding tool's
    # lite-variant misfire risk doesn't apply, so the deeper rungs are
    # actually usable as quota survival.
    extras = [
        "gemini-3-flash-lite-preview",
        "gemini-2.5-flash-lite",
    ]
    result = await call_gemini(
        primary_model=settings.PRO_MODEL,
        fallback_model=settings.PRO_FALLBACK_MODEL,
        extra_models=extras,
        system=_ANALYST_SYSTEM.format(locale=locale),
        user_prompt=prompt,
        use_search=False,            # analyst reasons over supplied data only
        response_json=True,
        max_output_tokens=2048,
        temperature=0.2,
        top_p=0.95,
        timeout_seconds=45.0,
    )
    if result.parsed is None:
        # Defensive — call_gemini raises on parse failure, so this branch
        # only fires if ``response_json`` was somehow flipped to False.
        raise RuntimeError("Analyst model returned a non-JSON payload.")
    return result.parsed, result.model_used


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

    # Single entrypoint — the cascade, retries, JSON repair and auth handling
    # all live inside ``call_gemini``. Auth errors bubble up as
    # GeminiAuthError so the route layer can return a meaningful status code;
    # everything else collapses to a graceful AnalystResponse(status=ERROR)
    # with the underlying message in ``error_detail``.
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
