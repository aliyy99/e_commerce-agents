"""
ShopSage AI - Supabase Client Singleton
Provides a shared, async-ready Supabase client for all DB operations.
"""
import logging
from functools import lru_cache
from supabase import create_client, Client
from ..config import settings

logger = logging.getLogger("shopsage.db")


@lru_cache(maxsize=1)
def get_supabase() -> Client:
    """
    Returns a cached Supabase client instance.
    Uses @lru_cache to ensure a single connection is reused across all agents.

    Returns:
        Client: Authenticated Supabase client ready for DB operations.
    """
    logger.info("Initializing Supabase client → %s", settings.SUPABASE_URL)
    client: Client = create_client(
        supabase_url=settings.SUPABASE_URL,
        supabase_key=settings.SUPABASE_SERVICE_KEY,  # Service key for backend writes
    )
    return client


# ──────────────────────────────────────────────────────────────
# Analysis Results (existing)
# ──────────────────────────────────────────────────────────────

async def upsert_analysis_result(record: dict) -> str:
    """
    Upserts a full orchestration result into the 'analysis_results' table.

    Args:
        record: Dict containing all agent outputs + metadata.

    Returns:
        str: UUID of the inserted/updated row.

    Raises:
        Exception: Propagates Supabase errors to the caller (Orchestrator handles).
    """
    db = get_supabase()
    response = (
        db.table("analysis_results")
        .upsert(record, on_conflict="product_id,created_at")
        .execute()
    )
    row_id: str = response.data[0]["id"]
    logger.info("DB upsert succeeded → row_id=%s", row_id)
    return row_id


async def fetch_cached_analysis(product_id: str, max_age_minutes: int = 30) -> dict | None:
    """
    Retrieves a recent analysis from DB to avoid redundant AI calls.

    Args:
        product_id:      The product's internal ID.
        max_age_minutes: Only return results newer than this threshold.

    Returns:
        dict | None: Cached row dict, or None if stale / not found.
    """
    db = get_supabase()
    response = (
        db.table("analysis_results")
        .select("*")
        .eq("product_id", product_id)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )

    if not response.data:
        return None

    row = response.data[0]

    # Check freshness via Supabase's timestamptz column
    from datetime import datetime, timezone, timedelta
    created_at = datetime.fromisoformat(row["created_at"].replace("Z", "+00:00"))
    if datetime.now(timezone.utc) - created_at > timedelta(minutes=max_age_minutes):
        logger.debug("Cache hit but stale for product_id=%s", product_id)
        return None

    logger.info("Cache hit for product_id=%s (age < %dm)", product_id, max_age_minutes)
    return row


async def save_generated_image(product_name: str, image_bytes: bytes) -> str:
    """
    Uploads a Visualizer Agent output to Supabase Storage.

    Args:
        product_name: Used to build the storage path.
        image_bytes:  Raw image bytes to upload.

    Returns:
        str: Public URL of the uploaded image.
    """
    import time, re
    db = get_supabase()
    safe_name = re.sub(r"[^a-z0-9_]", "_", product_name.lower())
    path = f"generated/{safe_name}_{int(time.time())}.png"

    db.storage.from_("shopsage-images").upload(
        path=path,
        file=image_bytes,
        file_options={"content-type": "image/png"},
    )
    public_url = db.storage.from_("shopsage-images").get_public_url(path)
    logger.info("Image uploaded to Supabase Storage → %s", public_url)
    return public_url


# ──────────────────────────────────────────────────────────────
# Favorites CRUD
# ──────────────────────────────────────────────────────────────

async def add_favorite(user_id: str, product_name: str, price: float, url: str, image_url: str | None = None) -> dict:
    """Inserts a new favorite product for the user."""
    db = get_supabase()
    record = {
        "user_id": user_id,
        "product_name": product_name,
        "price": price,
        "url": url,
        "image_url": image_url,
    }
    response = db.table("favorites").insert(record).execute()
    logger.info("Favorite added for user=%s product=%s", user_id, product_name)
    return response.data[0]


async def get_favorites(user_id: str) -> list[dict]:
    """Returns all favorites for a user, ordered newest-first."""
    db = get_supabase()
    response = (
        db.table("favorites")
        .select("*")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .execute()
    )
    return response.data


async def delete_favorite(favorite_id: str, user_id: str) -> bool:
    """Removes a favorite by its ID (scoped to user for safety)."""
    db = get_supabase()
    response = (
        db.table("favorites")
        .delete()
        .eq("id", favorite_id)
        .eq("user_id", user_id)
        .execute()
    )
    deleted = len(response.data) > 0
    if deleted:
        logger.info("Favorite %s deleted for user %s", favorite_id, user_id)
    return deleted


# ──────────────────────────────────────────────────────────────
# Price Alerts CRUD
# ──────────────────────────────────────────────────────────────

async def add_price_alert(user_id: str, product_id: str, product_name: str, target_price: float, current_price: float) -> dict:
    """Creates a new price alert/tracking entry."""
    db = get_supabase()
    record = {
        "user_id": user_id,
        "product_id": product_id,
        "product_name": product_name,
        "target_price": target_price,
        "current_price": current_price,
        "is_active": True,
    }
    response = db.table("price_alerts").insert(record).execute()
    logger.info("Price alert created for user=%s product=%s target=%.2f", user_id, product_name, target_price)
    return response.data[0]


async def get_price_alerts(user_id: str) -> list[dict]:
    """Returns all active price alerts for a user."""
    db = get_supabase()
    response = (
        db.table("price_alerts")
        .select("*")
        .eq("user_id", user_id)
        .eq("is_active", True)
        .order("created_at", desc=True)
        .execute()
    )
    return response.data


async def delete_price_alert(alert_id: str, user_id: str) -> bool:
    """Deactivates a price alert (soft-delete)."""
    db = get_supabase()
    response = (
        db.table("price_alerts")
        .update({"is_active": False})
        .eq("id", alert_id)
        .eq("user_id", user_id)
        .execute()
    )
    updated = len(response.data) > 0
    if updated:
        logger.info("Price alert %s deactivated for user %s", alert_id, user_id)
    return updated

# ──────────────────────────────────────────────────────────────
# Recent Searches (Chat & Analysis Persistence)
# ──────────────────────────────────────────────────────────────

async def save_recent_search(product_name: str, category: str = "other", analysis_summary: str | None = None, assistant_advice: str | None = None, user_id: str | None = None) -> dict:
    """Logs an analyzed product and the assistant's advice to the database."""
    db = get_supabase()
    record = {
        "product_name": product_name,
        "category": category,
        "analysis_summary": analysis_summary,
        "assistant_advice": assistant_advice,
    }
    if user_id:
        record["user_id"] = user_id

    response = db.table("recent_searches").insert(record).execute()
    logger.info("Recent search saved for product=%s", product_name)
    return response.data[0]
