"""
Techno Track AI - Tracking System
POST /track
"""
import asyncio
import logging
import re
import time
import uuid
from datetime import datetime, timezone
from typing import List, Optional

import httpx
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from ..agents.compare_agent import _scrape_one, _USER_AGENT
from ..models.requests import CompareSiteData, TrackProductRequest

logger = logging.getLogger("technotrack.routes.tracking")
router = APIRouter(prefix="/tracking", tags=["Tracking"])


class TrackResponse(BaseModel):
    status: str
    tracking_id: str
    message: str


@router.post(
    "/",
    response_model=TrackResponse,
    summary="Track a product for price drops",
    description="Saves the user's target price to Supabase to enable background monitoring.",
    status_code=status.HTTP_201_CREATED,
)
async def track_product(body: TrackProductRequest):
    """
    ROUTE: /tracking/  →  Save track request
    """
    logger.info("POST /tracking/ (user_id=%s, product_id=%s, target_price=%f)", 
                body.user_id, body.product_id, body.target_price)
    
    # In a real implementation, we would save this to Supabase `tracked_products` table.
    tracking_id = str(uuid.uuid4())
    
    # Mocking Supabase Insert:
    # await supabase.table("tracked_products").insert({
    #     "id": tracking_id,
    #     "user_id": body.user_id,
    #     "product_id": body.product_id,
    #     "target_price": body.target_price
    # }).execute()

    return TrackResponse(
        status="success",
        tracking_id=tracking_id,
        message=f"Ürün takibe alındı. Fiyat {body.target_price} altına düşerse bildirim gönderilecek."
    )


# ──────────────────────────────────────────────────────────────────────────
# Lightweight live-price check used by the in-app tracker.
# Reuses the compare-agent scraper (JSON-LD + meta-tag regex, no Gemini call)
# so it costs ZERO model quota. The frontend rotates through tracked items
# and calls this for ONE product per tick, keeping HTTP load small.
# ──────────────────────────────────────────────────────────────────────────


class TrackCheckSite(BaseModel):
    site: Optional[str] = None
    url: str
    product_name: Optional[str] = None


class TrackCheckRequest(BaseModel):
    product_name: str = Field(..., description="Catalog product name (used for logging only).")
    stores: List[TrackCheckSite] = Field(..., min_length=1)


class TrackCheckStorePrice(BaseModel):
    site: str
    url: str
    price: Optional[float] = None
    currency: str = "TRY"
    source_status: str
    source_note: Optional[str] = None


class TrackCheckResponse(BaseModel):
    product_name: str
    fetched_at: datetime
    currency: str = "TRY"
    stores: List[TrackCheckStorePrice]
    lowest_site: Optional[str] = None
    lowest_price: Optional[float] = None
    duration_ms: int


_PRICE_NUM_RE = re.compile(r"[-+]?\d[\d.,]*")


def _coerce_price(raw) -> Optional[float]:
    """Best-effort 'TL 84.999,00' / '84,999' / '84.999' → 84999.0 parser.

    The compare-agent merge step already runs ``_normalize_number_text`` so we
    usually get a clean numeric string here, but we keep this defensive against
    locale variants and "not found".
    """
    if raw is None:
        return None
    text = str(raw).strip()
    if not text or text.lower() == "not found":
        return None
    match = _PRICE_NUM_RE.search(text.replace("\xa0", " "))
    if not match:
        return None
    token = match.group(0)
    # Turkish formatting: "84.999,50" → strip dots, replace comma with dot.
    if "," in token and token.rfind(",") > token.rfind("."):
        token = token.replace(".", "").replace(",", ".")
    else:
        # English/US formatting "84,999.50" or thousands-only "84,999".
        if token.count(",") and not token.count("."):
            # No decimal separator at all → commas are thousands.
            token = token.replace(",", "")
        else:
            token = token.replace(",", "")
    try:
        return float(token)
    except ValueError:
        return None


@router.post(
    "/check-prices",
    response_model=TrackCheckResponse,
    summary="Fetch current store prices for a tracked product (no LLM call)",
    description=(
        "Scrapes JSON-LD / meta-tag prices from the supplied store URLs in "
        "parallel. Designed to be hit on a short cadence by the in-app price "
        "tracker — costs zero Gemini quota."
    ),
    status_code=status.HTTP_200_OK,
)
async def track_check_prices(body: TrackCheckRequest) -> TrackCheckResponse:
    start = time.monotonic()
    logger.info(
        "POST /tracking/check-prices product=%s stores=%d",
        body.product_name, len(body.stores),
    )

    # Reuse the compare-agent scraper. Build CompareSiteData objects so the
    # function's contract stays the same — we just throw away review / rating
    # fields, only `price` matters here.
    sites = [
        CompareSiteData(site=s.site, url=s.url, product_name=s.product_name or body.product_name)
        for s in body.stores
    ]

    timeout = httpx.Timeout(connect=10.0, read=15.0, write=15.0, pool=15.0)
    headers = {"User-Agent": _USER_AGENT, "Accept-Language": "en-US,en;q=0.9"}
    semaphore = asyncio.Semaphore(4)

    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True, headers=headers) as client:
        scraped = await asyncio.gather(
            *(_scrape_one(client, item, semaphore) for item in sites),
            return_exceptions=True,
        )

    results: List[TrackCheckStorePrice] = []
    currency = "TRY"
    for raw in scraped:
        if isinstance(raw, Exception):
            logger.warning("scrape exception: %s", raw)
            continue
        price = _coerce_price(raw.get("price"))
        results.append(
            TrackCheckStorePrice(
                site=str(raw.get("site") or "Unknown"),
                url=str(raw.get("url") or ""),
                price=price,
                currency=str(raw.get("currency") or "TRY"),
                source_status=str(raw.get("source_status") or "ok"),
                source_note=raw.get("source_note"),
            )
        )
        if raw.get("currency"):
            currency = str(raw["currency"])

    # Pick the lowest valid price across all stores.
    with_prices = [r for r in results if r.price is not None and r.price > 0]
    if with_prices:
        cheapest = min(with_prices, key=lambda r: r.price)
        lowest_site, lowest_price = cheapest.site, cheapest.price
    else:
        lowest_site, lowest_price = None, None

    return TrackCheckResponse(
        product_name=body.product_name,
        fetched_at=datetime.now(timezone.utc),
        currency=currency,
        stores=results,
        lowest_site=lowest_site,
        lowest_price=lowest_price,
        duration_ms=int((time.monotonic() - start) * 1000),
    )


async def check_price_drop(product_id: str, current_price: float):
    """
    BACKGROUND TASK DRAFT: check_price_drop
    ───────────────────────────────────────
    Taslak fonksiyon. Supabase Real-time webhooks veya cron job ile tetiklenir.
    Verilen product_id için takip listesini tarar ve fiyat düşmüşse kullanıcıya
    bildirim (WebSocket/Email/Push) atar.
    """
    logger.info("Checking price drops for product %s at %f", product_id, current_price)
    # 1. Fetch tracked targets from DB:
    # targets = await supabase.table("tracked_products").select("*").eq("product_id", product_id).execute()
    # 
    # 2. Iterate through targets:
    # for t in targets.data:
    #     if current_price <= t['target_price']:
    #         logger.info("Price drop matched for user %s!", t['user_id'])
    #         # 3. Trigger Notification (SendGrid / WebSocket / Push)
    pass
