"""
Techno Track AI - Price History Route
POST /api/v1/price-history

Uses Gemini 2.5 Flash (with 2.0 Flash fallback) grounded by Google Search to
fetch approximate last-12-month monthly prices for a given product in Turkey,
then returns a structured JSON payload the frontend can render as a chart.

Implementation note: calls the Gemini REST API directly via ``httpx`` instead
of the google-generativeai SDK, because SDK 0.8.x's Tool proto exposes only
``google_search_retrieval`` — but Gemini 2.5+ models reject that field and
require the modern ``google_search`` tool form.
"""
from __future__ import annotations

import json
import logging
import re
from datetime import datetime
from typing import List, Optional

import httpx
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from ..config import get_gemini_api_key, settings
from ..services.gemini_client import (
    GeminiAuthError,
    configure_gemini_client,
    raise_if_auth_error,
)

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
    # grounding chunks. False means the chart values are AI-extrapolated rather
    # than fetched from live e-commerce data — frontend should warn the user.
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


def _build_prompt(product_name: str, currency: str, months: List[dict]) -> str:
    month_list = ", ".join(m["month"] for m in months)
    schema = {
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
{json.dumps(schema, ensure_ascii=False, indent=2)}
""".strip()


# ── Gemini call ───────────────────────────────────────────────────────────
# Direct REST is used (instead of the google-generativeai SDK) because SDK
# 0.8.x's Tool proto exposes only ``google_search_retrieval``, while Gemini
# 2.5+ models require the newer ``google_search`` tool — passing it via the SDK
# raises "Unknown field for FunctionDeclaration: google_search".
_GENERATION_CONFIG = {
    "temperature": 0.4,
    "topP": 0.95,
    # 8192 leaves headroom after the model spends tokens on grounded search +
    # 12 monthly entries — 4096 was getting truncated mid-JSON.
    "maxOutputTokens": 8192,
}

_SAFETY_SETTINGS = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_ONLY_HIGH"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_ONLY_HIGH"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_ONLY_HIGH"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_ONLY_HIGH"},
]

_GEMINI_REST_BASE = "https://generativelanguage.googleapis.com/v1beta/models"


def _extract_grounding_sources(response: dict | None) -> List[dict]:
    if not response:
        return []
    try:
        candidates = response.get("candidates") or []
        if not candidates:
            return []
        meta = candidates[0].get("groundingMetadata") or {}
        chunks = meta.get("groundingChunks") or []
        out: List[dict] = []
        seen = set()
        for ch in chunks[:8]:
            web = ch.get("web") or {}
            uri = web.get("uri")
            if not uri or uri in seen:
                continue
            seen.add(uri)
            title = web.get("title") or uri
            out.append({"title": title, "uri": uri})
        return out
    except Exception:
        return []


_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL | re.IGNORECASE)


def _parse_json_payload(text: str) -> dict:
    """Tolerant JSON extraction: handles ```json fences, surrounding prose, etc.

    Uses ``strict=False`` so raw newlines/tabs inside string literals (a common
    Gemini quirk in long ``summary``/``note`` fields) don't blow up parsing.
    """
    if not text:
        raise ValueError("Empty response.")
    text = text.strip()

    def _loads(s: str) -> dict:
        return json.loads(s, strict=False)

    # Direct parse first.
    try:
        return _loads(text)
    except json.JSONDecodeError:
        pass

    # Fenced block.
    fence_match = _JSON_FENCE_RE.search(text)
    if fence_match:
        try:
            return _loads(fence_match.group(1))
        except json.JSONDecodeError:
            pass

    # First { ... last } heuristic.
    first = text.find("{")
    last = text.rfind("}")
    if first != -1 and last > first:
        candidate = text[first : last + 1]
        try:
            return _loads(candidate)
        except json.JSONDecodeError as err:
            raise ValueError(f"JSON parse failed: {err}") from err

    raise ValueError("Could not extract JSON from response.")


def _try_model(model_name: str, prompt: str, tool_spec: dict, api_key: str):
    """Call Gemini REST generateContent with the given Google Search tool spec.

    Bypasses the SDK because google-generativeai 0.8.x doesn't expose the
    ``google_search`` Tool field required by Gemini 2.5+ models.
    """
    url = f"{_GEMINI_REST_BASE}/{model_name}:generateContent?key={api_key}"
    body = {
        "systemInstruction": {"parts": [{"text": _PRICE_HISTORY_SYSTEM}]},
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "tools": [tool_spec],
        "safetySettings": _SAFETY_SETTINGS,
        "generationConfig": _GENERATION_CONFIG,
    }
    try:
        resp = httpx.post(url, json=body, timeout=90.0)
    except httpx.HTTPError as exc:
        raise RuntimeError(f"Gemini REST call failed (model={model_name}): {exc}") from exc

    if resp.status_code != 200:
        # Surface the API's own message so auth/quota errors are diagnosable.
        raise RuntimeError(
            f"Gemini REST {resp.status_code} (model={model_name}): {resp.text[:400]}"
        )

    data = resp.json()
    candidates = data.get("candidates") or []
    if not candidates:
        raise ValueError(f"Gemini returned no candidates (model={model_name}).")
    parts = (candidates[0].get("content") or {}).get("parts") or []
    text = "".join(p.get("text", "") for p in parts if isinstance(p, dict)).strip()
    if not text:
        raise ValueError(f"Gemini returned empty text (model={model_name}).")
    return text, data


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
    # Refresh .env so a freshly rotated key takes effect, then resolve it for
    # the REST call (we bypass the SDK to use the modern ``google_search`` tool).
    configure_gemini_client()
    api_key = get_gemini_api_key()

    months = _last_12_months()
    prompt = _build_prompt(body.product_name, body.currency, months)

    # Highest non-Pro Flash first cascade. Lite tiers stay in reserve as
    # quota-survival rungs because ``google_search`` grounding can flake
    # on them — when that happens we roll forward to the next rung.
    # ``google_search`` is the only tool form these models accept; older
    # ``google_search_retrieval`` returns 400. Worst case is 4 API calls
    # but the happy path is 1.
    candidate_models = list(dict.fromkeys([
        getattr(settings, "PRICE_HISTORY_MODEL", None) or "gemini-3-flash-preview",
        getattr(settings, "PRICE_HISTORY_FALLBACK_MODEL", None) or "gemini-2.5-flash",
        "gemini-3-flash-lite-preview",
        "gemini-2.5-flash-lite",
    ]))
    candidate_models = [m for m in candidate_models if m]

    last_error: Exception | None = None
    last_response = None
    last_model = None
    parsed_payload: Optional[dict] = None

    tool_spec = {"google_search": {}}

    for model_name in candidate_models:
        try:
            text, response = _try_model(model_name, prompt, tool_spec, api_key)
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
            logger.warning("Price-history model failed (model=%s): %s", model_name, exc)
            last_error = exc

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
        grounded=bool(sources),
    )
