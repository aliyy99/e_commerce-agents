"""
ShopSage AI - Favorites & Price Alerts Route
Provides CRUD endpoints for user favorites and price tracking.
Uses a mock_user_id header for auth simulation.
"""
import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Header, status
from pydantic import BaseModel, Field

from ..db import add_favorite, get_favorites, delete_favorite
from ..db import add_price_alert, get_price_alerts, delete_price_alert

logger = logging.getLogger("shopsage.routes.user_data")
router = APIRouter(prefix="/user", tags=["User Data"])

# Default mock user — simulates auth until Supabase Auth is wired up
MOCK_USER_ID = "mock-user-001"


# ── Request / Response Schemas ──────────────────────────────────

class AddFavoriteRequest(BaseModel):
    product_name: str = Field(..., example="Sony WH-1000XM5")
    price: float = Field(..., gt=0, example=348.00)
    url: str = Field(..., example="https://amazon.com/dp/B0C8QJ...")
    image_url: Optional[str] = Field(None, example="https://images.unsplash.com/...")

class AddAlertRequest(BaseModel):
    product_id: str = Field(..., example="prod-uuid-123")
    product_name: str = Field(..., example="MacBook Pro 14\"")
    target_price: float = Field(..., gt=0, example=1100.00)
    current_price: float = Field(..., gt=0, example=1245.50)

class DeleteResponse(BaseModel):
    success: bool
    message: str


# ── Favorites Endpoints ─────────────────────────────────────────

@router.get("/favorites", summary="Get user's favorite products")
async def list_favorites(x_user_id: str = Header(default=MOCK_USER_ID)):
    """Returns all favorited products for the authenticated (or mock) user."""
    try:
        data = await get_favorites(x_user_id)
        return {"favorites": data}
    except Exception as e:
        logger.error("Failed to fetch favorites: %s", e)
        raise HTTPException(status_code=500, detail="Could not retrieve favorites.")


@router.post("/favorites", status_code=status.HTTP_201_CREATED, summary="Add a product to favorites")
async def create_favorite(body: AddFavoriteRequest, x_user_id: str = Header(default=MOCK_USER_ID)):
    """Saves a product to the user's favorites list in Supabase."""
    try:
        record = await add_favorite(
            user_id=x_user_id,
            product_name=body.product_name,
            price=body.price,
            url=body.url,
            image_url=body.image_url,
        )
        return {"status": "created", "favorite": record}
    except Exception as e:
        logger.error("Failed to add favorite: %s", e)
        raise HTTPException(status_code=500, detail="Could not add favorite.")


@router.delete("/favorites/{favorite_id}", summary="Remove a product from favorites")
async def remove_favorite(favorite_id: str, x_user_id: str = Header(default=MOCK_USER_ID)):
    """Deletes a specific favorite by ID."""
    try:
        deleted = await delete_favorite(favorite_id, x_user_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Favorite not found.")
        return DeleteResponse(success=True, message="Favoriden kaldırıldı.")
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to delete favorite: %s", e)
        raise HTTPException(status_code=500, detail="Could not remove favorite.")


# ── Price Alerts Endpoints ──────────────────────────────────────

@router.get("/alerts", summary="Get user's active price alerts")
async def list_alerts(x_user_id: str = Header(default=MOCK_USER_ID)):
    """Returns all active price tracking alerts for the user."""
    try:
        data = await get_price_alerts(x_user_id)
        return {"alerts": data}
    except Exception as e:
        logger.error("Failed to fetch alerts: %s", e)
        raise HTTPException(status_code=500, detail="Could not retrieve alerts.")


@router.post("/alerts", status_code=status.HTTP_201_CREATED, summary="Create a price drop alert")
async def create_alert(body: AddAlertRequest, x_user_id: str = Header(default=MOCK_USER_ID)):
    """Sets up a price tracking alert — user will be notified when the price drops below target."""
    try:
        record = await add_price_alert(
            user_id=x_user_id,
            product_id=body.product_id,
            product_name=body.product_name,
            target_price=body.target_price,
            current_price=body.current_price,
        )
        return {"status": "created", "alert": record}
    except Exception as e:
        logger.error("Failed to create alert: %s", e)
        raise HTTPException(status_code=500, detail="Could not create alert.")


@router.delete("/alerts/{alert_id}", summary="Deactivate a price alert")
async def deactivate_alert(alert_id: str, x_user_id: str = Header(default=MOCK_USER_ID)):
    """Soft-deletes (deactivates) a price alert."""
    try:
        deleted = await delete_price_alert(alert_id, x_user_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Alert not found.")
        return DeleteResponse(success=True, message="Alarm devre dışı bırakıldı.")
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to delete alert: %s", e)
        raise HTTPException(status_code=500, detail="Could not deactivate alert.")
