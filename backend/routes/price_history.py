"""
Techno Track AI - Price History Route
POST /api/v1/price-history

Builds a 12-month monthly price curve for a product in Turkey and returns a
structured JSON payload the frontend renders as a chart.

  • With Google Search grounding (billed keys): the model researches real
    prices per month and the response carries the grounding sources.
  • Without grounding (free tier): the Detective Agent first fetches TODAY's
    real price from Turkish marketplaces. The current month is pinned to that
    live price and earlier months are explicitly marked as model estimates
    (``grounded=false``, notes "estimate"); the sources are the live listings.

Model ladder: PRICE_HISTORY_MODEL → PRICE_HISTORY_FALLBACK_MODEL → shared
extra rungs, via ``services.gemini_grounded.call_gemini``.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from ..agents.detective_agent import run_detective_agent
from ..config import settings
from ..models.requests import DetectiveRequest
from ..models.responses import AgentStatus
from ..services.gemini_client import GeminiAuthError
from ..services.gemini_grounded import call_gemini, search_available

logger = logging.getLogger("technotrack.routes.price_history")
router = APIRouter(prefix="/price-history", tags=["Price History"])


# ── Request / Response models ─────────────────────────────────────────────
class PriceHistoryRequest(BaseModel):
    product_name: str = Field(..., example="Samsung Galaxy S25 Ultra 512 GB")
    product_id: Optional[str] = None
    locale: str = Field(default="tr")
    currency: str = Field(default="TRY")


class MonthlyPricePoint(BaseModel):
    month: str = Field(..., example="2025-06")
    label: str = Field(..., example="Haziran 2025")
    price: float
    note: Optional[str] = None


class PriceHistorySource(BaseModel):
    title: Optional[str] = None
    uri: str


class PriceHistoryResponse(BaseModel):
    product_name: str
    currency: str = "TRY"
    points: List[MonthlyPricePoint]
    summary: str
    trend: str = Field(..., example="stable")
    lowest: Optional[float] = None
    highest: Optional[float] = None
    average: Optional[float] = None
    sources: List[PriceHistorySource] = Field(default_factory=list)
    model_used: str
    # True only when the model actually invoked Google Search and returned
    # grounding chunks. False means past months are model estimates (the
    # current month is then the live marketplace price when one was found).
    grounded: bool = False


# ── Month helpers ─────────────────────────────────────────────────────────
_MONTH_LABELS = [
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
]


def _last_12_months(now: Optional[datetime] = None) -> List[dict]:
    """Build the list of (YYYY-MM, 'Mon YYYY') pairs ending at the current month."""
    now = now or datetime.utcnow()
    year, month = now.year, now.month
    out: List[dict] = []
    # 11 months back + current = 12 entries.
    for offset in range(11, -1, -1):
        m = month - offset
        y = year
        while m <= 0:
            m += 12
            y -= 1
        out.append({"month": f"{y:04d}-{m:02d}", "label": f"{_MONTH_LABELS[m - 1]} {y}"})
    return out


# ── Prompting ─────────────────────────────────────────────────────────────
_PRICE_HISTORY_SYSTEM = """
You are a senior e-commerce price analyst agent for the Turkish market. The
Google Search tool is ALWAYS available to you and you MUST call it at least
once at the start of every request before writing your answer — Turkish retail
prices move with high inflation, and your training data is stale. Treat any
internal estimate without a corroborating search result as low confidence.

Return ONLY the requested JSON structure — no commentary, no markdown fence,
no extra text. All text fields must be written in English. The output MUST be
a single, syntactically valid JSON object.
""".strip()

_OFFLINE_SYSTEM = """
You are a senior e-commerce price analyst for the Turkish market. You have NO
web-search tool. You are given today's REAL marketplace prices; everything
before the current month is your estimate, and you must say so.

Return ONLY the requested JSON structure — no commentary, no markdown fence,
no extra text. All text fields must be written in English. The output MUST be
a single, syntactically valid JSON object.
""".strip()


def _schema(currency: str) -> dict:
    return {
        "currency": currency,
        "points": [
            {"month": "YYYY-MM", "label": "Mon YYYY", "price": 0, "note": ""}
        ],
        "summary": "2-3 sentence English price commentary",
        "trend": "downward|upward|stable|volatile",
        "lowest": 0,
        "highest": 0,
        "average": 0,
    }


def _build_prompt(product_name: str, currency: str, months: List[dict]) -> str:
    month_list = ", ".join(m["month"] for m in months)
    return f"""
Research the monthly retail price of this product in the Turkish market over
the last 12 months.

Product: {product_name}
Market: Turkey
Currency: {currency}
Months (oldest → newest, output one entry per month): {month_list}

REQUIRED RESEARCH STEP — you MUST call the Google Search tool BEFORE writing
any JSON. Run AT LEAST these queries (run more if you have low confidence):
  1. "{product_name} fiyat" site:hepsiburada.com
  2. "{product_name} fiyat" site:trendyol.com
  3. "{product_name} Akakçe fiyat geçmişi"
  4. "{product_name} cimri fiyat geçmişi"
  5. "{product_name} price history Turkey"
Also try queries on mediamarkt.com.tr, vatanbilgisayar.com, amazon.com.tr.
Do NOT skip the search even if you think you already know the price — pricing
in Turkey moves with inflation and your training data may be stale.

After searching:
- For months with direct evidence in the search results, use the observed
  Turkish e-commerce price (preferably the lowest list price seen that month).
- For months WITHOUT direct evidence, interpolate from the nearest known
  prices. If the product had not launched yet, back-project from the launch
  price or the previous generation.
- You MUST output exactly one price per month listed above (12 entries).

Output rules:
- ONLY a single valid JSON object matching the schema below. No markdown
  fences, no commentary, no trailing text.
- All text fields in English. Keep ``note`` ≤ 6 words; omit if nothing useful
  to add. Do not repeat the same boilerplate note across months.
- For months where you used a real search result, set ``note`` to the source
  site name (e.g. "hepsiburada", "akakce"). For interpolated months, set
  ``note`` to "interpolated" or omit it.
- Prices as plain numbers (no currency symbols), integers or 2 decimals.
- Use the exact "month" / "label" values from the list above.

Schema:
{json.dumps(_schema(currency), ensure_ascii=False, indent=2)}
""".strip()


def _build_offline_prompt(
    product_name: str,
    currency: str,
    months: List[dict],
    live_listings: List[dict],
) -> str:
    month_list = ", ".join(m["month"] for m in months)
    current = months[-1]["month"]
    if live_listings:
        lines = "\n".join(
            f"  - {item['store']}: {item['price']:.0f} {currency} — {item['title']}"
            for item in live_listings
        )
        anchor = min(item["price"] for item in live_listings)
        live_block = (
            f"REAL prices fetched today from Turkish marketplaces:\n{lines}\n"
            f"The {current} entry MUST be exactly {anchor:.0f} (the lowest live price)."
        )
    else:
        live_block = (
            "No live marketplace price could be fetched today, so EVERY month "
            "is an estimate — say so in the summary."
        )
    return f"""
Estimate the monthly retail price of this product in the Turkish market over
the last 12 months.

Product: {product_name}
Currency: {currency}
Months (oldest → newest, output one entry per month): {month_list}

{live_block}

Rules:
- Output exactly one price per month listed above (12 entries).
- Work backwards from the current price using what you know about this
  product: Turkish launch price, successor launches, campaign periods and
  the lira's inflation trend. If the product had not launched yet in a
  month, back-project from its launch price or its predecessor.
- ``note``: "live price" for {current} when a live price was given above,
  otherwise "estimate".
- ``summary``: 2-3 sentences that explicitly say the earlier months are
  model estimates, not recorded prices.
- Prices as plain numbers (no currency symbols). Use the exact "month" /
  "label" values from the list above. All text in English.

Schema:
{json.dumps(_schema(currency), ensure_ascii=False, indent=2)}
""".strip()


def _coerce_float(value) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _normalize_points(
    raw_points,
    template: List[dict],
) -> List[MonthlyPricePoint]:
    """Align model output to the canonical 12-month timeline."""
    by_month: dict[str, dict] = {}
    if isinstance(raw_points, list):
        for entry in raw_points:
            if not isinstance(entry, dict):
                continue
            month = str(entry.get("month") or "").strip()
            if not month:
                continue
            by_month[month] = entry

    out: List[MonthlyPricePoint] = []
    for tmpl in template:
        entry = by_month.get(tmpl["month"]) or {}
        price = _coerce_float(entry.get("price"))
        if price is None or price <= 0:
            # Skip months with no usable price — chart will simply have fewer
            # points rather than misleading zeros.
            continue
        out.append(
            MonthlyPricePoint(
                month=tmpl["month"],
                label=tmpl["label"],
                price=round(price, 2),
                note=(str(entry.get("note")).strip() or None) if entry.get("note") else None,
            )
        )
    return out


async def _live_listings(product_name: str) -> List[dict]:
    """Today's real marketplace prices for the product via the Detective Agent."""
    try:
        result = await run_detective_agent(
            DetectiveRequest(product_keywords=product_name), collect_reviews=False,
        )
    except GeminiAuthError:
        raise
    except Exception as err:
        logger.warning("Price-history live price lookup failed: %s", err)
        return []
    if result.status == AgentStatus.ERROR:
        logger.info("Price-history: no live listing for %r (%s)", product_name, result.error_detail)
        return []
    return [
        {"store": p.store, "price": p.price, "url": p.url, "title": p.title or product_name}
        for p in result.found_prices
    ]


async def _ask_model(product_name: str, currency: str, months: List[dict], live: List[dict]):
    return await call_gemini(
        settings.PRICE_HISTORY_MODEL,
        settings.PRICE_HISTORY_FALLBACK_MODEL,
        system=_PRICE_HISTORY_SYSTEM,
        user_prompt=_build_prompt(product_name, currency, months),
        offline_system=_OFFLINE_SYSTEM,
        offline_prompt=_build_offline_prompt(product_name, currency, months, live),
        use_search=True,
        response_json=True,
        max_output_tokens=8192,
        temperature=0.3,
        thinking_level="low",
        timeout_seconds=120.0,
    )


# ── Endpoint ──────────────────────────────────────────────────────────────
@router.post(
    "",
    response_model=PriceHistoryResponse,
    summary="12-month price history for a product (grounded, or anchored to today's live price)",
    status_code=status.HTTP_200_OK,
)
async def get_price_history(body: PriceHistoryRequest) -> PriceHistoryResponse:
    logger.info("POST /price-history product=%s", body.product_name)
    months = _last_12_months()
    currency = body.currency or "TRY"

    # Live prices are only needed when the model can't search the web itself.
    live_fetched = not search_available()
    live: List[dict] = await _live_listings(body.product_name) if live_fetched else []

    try:
        result = await _ask_model(body.product_name, currency, months, live)
        if not result.search_used and not live_fetched:
            # Grounding was refused during this very call, so the offline
            # prompt ran without live prices. Fetch them and ask again.
            live = await _live_listings(body.product_name)
            result = await _ask_model(body.product_name, currency, months, live)
    except GeminiAuthError as auth_err:
        logger.error("Price-history auth error: %s", auth_err)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(auth_err)) from auth_err
    except Exception as err:
        logger.warning("Price-history generation failed: %s", err)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to produce price history: {err}",
        ) from err

    parsed_payload = result.parsed or {}
    points = _normalize_points(parsed_payload.get("points"), months)
    if not points:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Model returned no valid monthly price data.",
        )

    current = months[-1]
    if result.search_used:
        sources = result.sources
    else:
        sources = [{"title": f"{item['store']} — {item['title']}", "uri": item["url"]} for item in live]
        if live:
            # Pin the current month to the real lowest price, whatever the model wrote.
            cheapest = min(live, key=lambda item: item["price"])
            points = [p for p in points if p.month != current["month"]]
            points.append(MonthlyPricePoint(
                month=current["month"], label=current["label"],
                price=round(cheapest["price"], 2), note=f"live: {cheapest['store']}",
            ))
        for p in points:
            if p.month != current["month"] or not live:
                p.note = "estimate"

    # Recompute stats from the final points so they always match the chart.
    prices = [p.price for p in points]
    trend_raw = str(parsed_payload.get("trend") or "stable").lower()
    trend = trend_raw if trend_raw in {"downward", "upward", "stable", "volatile"} else "stable"

    return PriceHistoryResponse(
        product_name=body.product_name,
        currency=str(parsed_payload.get("currency") or currency),
        points=points,
        summary=str(parsed_payload.get("summary") or "").strip()
            or "Estimated price curve for the last 12 months.",
        trend=trend,
        lowest=round(min(prices), 2),
        highest=round(max(prices), 2),
        average=round(sum(prices) / len(prices), 2),
        sources=[PriceHistorySource(**s) for s in sources],
        model_used=result.model_used or "unknown",
        grounded=bool(result.search_used and result.sources),
    )
