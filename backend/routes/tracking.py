"""
Techno Track AI - Tracking System
POST /track
"""
import logging
import uuid
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from ..models.requests import TrackProductRequest

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
