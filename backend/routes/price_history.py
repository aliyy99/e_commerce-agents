"""
ShopSage AI - Price History Route
POST /api/v1/price-history

Uses Gemini 3 Pro (with 2.5 Pro fallback) grounded by Google Search to fetch
approximate last-12-month monthly prices for a given product in Turkey, then
returns a structured JSON payload the frontend can render as a chart.
"""
from __future__ import annotations

import json
import logging
import re
from datetime import datetime
from typing import List, Optional

import google.generativeai as genai
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from ..config import settings
from ..services.gemini_client import (
    GeminiAuthError,
    configure_gemini_client,
    raise_if_auth_error,
)

logger = logging.getLogger("shopsage.routes.price_history")
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
You are a senior e-commerce price analyst agent. When a search tool is
available, use it to gather approximate historical monthly prices for the
requested product. When no search tool is available, rely on your training
knowledge and produce best-effort plausible monthly estimates — do NOT refuse
or apologize about missing data.

Return ONLY the requested JSON structure — no commentary, no markdown fence,
no extra text. All text fields must be written in English. The output MUST be
a single, syntactically valid JSON object.
""".strip()


def _build_prompt(product_name: str, currency: str, months: List[dict]) -> str:
    month_lines = "\n".join(f"- {m['month']}  ({m['label']})" for m in months)
    schema_months = [
        {"month": m["month"], "label": m["label"], "price": 0, "note": "short english note"}
        for m in months
    ]
    schema = {
        "currency": currency,
        "points": schema_months,
        "summary": "2-3 sentence English price commentary",
        "trend": "downward|upward|stable|volatile",
        "lowest": 0,
        "highest": 0,
        "average": 0,
    }
    return f"""
Research the approximate monthly retail price of the following product in the
Turkish market for the past 12 months.

Product: {product_name}
Target market: Turkey
Currency: {currency}

Months to analyze (oldest → newest):
{month_lines}

Steps:
1. Search the major Turkish e-commerce sites — Hepsiburada, Trendyol,
   MediaMarkt, Vatan Bilgisayar, Amazon Turkey, Akakçe — with queries such as
   "{product_name} price", "{product_name} price history",
   "{product_name} Akakçe fiyat geçmişi".
2. For each month, decide the average list price in TRY during that month.
   For months without direct data, interpolate reasonably from the nearest
   months.
3. If the product had not launched yet for a given month, still produce a
   plausible estimate (back-projected from the launch price or the previous
   generation). You MUST output a price for every one of the 12 months.
4. Output prices as plain numbers only (integers or two decimal places). Do
   not include currency symbols.
5. All natural-language fields (summary, note) must be written in English.

Output: ONLY the filled JSON below. No markdown fences, no comments, no
trailing text.

{json.dumps(schema, ensure_ascii=False, indent=2)}
""".strip()


# ── Gemini call ───────────────────────────────────────────────────────────
_GENERATION_CONFIG = genai.GenerationConfig(
    temperature=0.4,
    top_p=0.95,
    max_output_tokens=4096,
)

_SAFETY_SETTINGS = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_ONLY_HIGH"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_ONLY_HIGH"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_ONLY_HIGH"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_ONLY_HIGH"},
]


def _extract_grounding_sources(response) -> List[dict]:
    try:
        candidate = response.candidates[0]
        meta = getattr(candidate, "grounding_metadata", None)
        if not meta:
            return []
        chunks = getattr(meta, "grounding_chunks", None) or []
        out: List[dict] = []
        seen = set()
        for ch in chunks[:8]:
            web = getattr(ch, "web", None)
            if not web:
                continue
            uri = getattr(web, "uri", None)
            if not uri or uri in seen:
                continue
            seen.add(uri)
            title = getattr(web, "title", None) or uri
            out.append({"title": title, "uri": uri})
        return out
    except Exception:
        return []


_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL | re.IGNORECASE)


def _parse_json_payload(text: str) -> dict:
    """Tolerant JSON extraction: handles ```json fences, surrounding prose, etc."""
    if not text:
        raise ValueError("Empty response.")
    text = text.strip()

    # Direct parse first.
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Fenced block.
    fence_match = _JSON_FENCE_RE.search(text)
    if fence_match:
        try:
            return json.loads(fence_match.group(1))
        except json.JSONDecodeError:
            pass

    # First { ... last } heuristic.
    first = text.find("{")
    last = text.rfind("}")
    if first != -1 and last > first:
        candidate = text[first : last + 1]
        try:
            return json.loads(candidate)
        except json.JSONDecodeError as err:
            raise ValueError(f"JSON parse failed: {err}") from err

    raise ValueError("Could not extract JSON from response.")


def _try_model(model_name: str, prompt: str, tool_spec):
    """Run one (model, tool_spec) combo. tool_spec=None for ungrounded."""
    kwargs = {
        "model_name": model_name,
        "system_instruction": _PRICE_HISTORY_SYSTEM,
        "safety_settings": _SAFETY_SETTINGS,
    }
    if tool_spec is not None:
        kwargs["tools"] = [tool_spec]
    model = genai.GenerativeModel(**kwargs)

    # Force JSON mime type when ungrounded — tools and response_mime_type are
    # incompatible on the Gemini API, so we only constrain output when we've
    # already fallen back to a non-search attempt.
    if tool_spec is None:
        generation_config = genai.GenerationConfig(
            temperature=_GENERATION_CONFIG.temperature,
            top_p=_GENERATION_CONFIG.top_p,
            max_output_tokens=_GENERATION_CONFIG.max_output_tokens,
            response_mime_type="application/json",
        )
    else:
        generation_config = _GENERATION_CONFIG

    response = model.generate_content(prompt, generation_config=generation_config)
    text = (getattr(response, "text", None) or "").strip()
    if not text:
        raise ValueError(f"Gemini returned empty response (model={model_name}).")
    return text, response


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


# ── Endpoint ──────────────────────────────────────────────────────────────
@router.post(
    "",
    response_model=PriceHistoryResponse,
    summary="12-month grounded price history for a product",
    status_code=status.HTTP_200_OK,
)
async def get_price_history(body: PriceHistoryRequest) -> PriceHistoryResponse:
    logger.info("POST /price-history product=%s", body.product_name)
    configure_gemini_client()

    months = _last_12_months()
    prompt = _build_prompt(body.product_name, body.currency, months)

    # Pro tier shares one heavily rate-limited daily quota across all *-pro
    # models on the free tier, so we cascade Pro → Flash variants that have
    # independent quota and still produce solid grounded results.
    candidate_models = list(dict.fromkeys([
        getattr(settings, "PRICE_HISTORY_MODEL", None) or "gemini-3-pro-preview",
        settings.PRO_MODEL,
        settings.VISION_MODEL,          # gemini-3-flash-preview (independent quota)
        settings.CHAT_MODEL,            # gemini-3-flash-preview (same family, kept for clarity)
        settings.CHAT_FALLBACK_MODEL,   # gemini-2.5-flash-lite
        settings.FLASH_MODEL,
    ]))
    candidate_models = [m for m in candidate_models if m]

    last_error: Exception | None = None
    last_response = None
    last_model = None
    parsed_payload: Optional[dict] = None

    # Tool spec attempts, in order:
    #  - {"google_search_retrieval": {}} works on Gemini 1.5 / 3 family
    #  - {"google_search": {}} works on Gemini 2.0+ (newer SDK contract)
    #  - None: ungrounded (final fallback so we still return JSON)
    tool_attempts = [
        {"google_search_retrieval": {}},
        {"google_search": {}},
        None,
    ]

    for model_name in candidate_models:
        for tool_spec in tool_attempts:
            try:
                text, response = _try_model(model_name, prompt, tool_spec)
                parsed_payload = _parse_json_payload(text)
                last_response = response
                last_model = model_name
                break
            except Exception as exc:
                try:
                    raise_if_auth_error(exc)
                except GeminiAuthError as auth_err:
                    logger.error("Price-history auth error: %s", auth_err)
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail=str(auth_err),
                    ) from auth_err
                logger.warning(
                    "Price-history model failed (model=%s, tool=%s): %s",
                    model_name,
                    "none" if tool_spec is None else next(iter(tool_spec.keys())),
                    exc,
                )
                last_error = exc
        if parsed_payload is not None:
            break

    if parsed_payload is None:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to produce price history: {last_error}",
        )

    points = _normalize_points(parsed_payload.get("points"), months)
    if not points:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Model returned no valid monthly price data.",
        )

    prices = [p.price for p in points]
    lowest = _coerce_float(parsed_payload.get("lowest")) or min(prices)
    highest = _coerce_float(parsed_payload.get("highest")) or max(prices)
    average = _coerce_float(parsed_payload.get("average")) or round(sum(prices) / len(prices), 2)
    trend_raw = str(parsed_payload.get("trend") or "stable").lower()
    trend = trend_raw if trend_raw in {"downward", "upward", "stable", "volatile"} else "stable"

    sources = _extract_grounding_sources(last_response) if last_response is not None else []

    return PriceHistoryResponse(
        product_name=body.product_name,
        currency=str(parsed_payload.get("currency") or body.currency or "TRY"),
        points=points,
        summary=str(parsed_payload.get("summary") or "").strip()
            or "Estimated price curve for the last 12 months.",
        trend=trend,
        lowest=round(lowest, 2) if lowest is not None else None,
        highest=round(highest, 2) if highest is not None else None,
        average=round(average, 2) if average is not None else None,
        sources=[PriceHistorySource(**s) for s in sources],
        model_used=last_model or "unknown",
    )
