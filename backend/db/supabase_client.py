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
# Table-level helpers
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
