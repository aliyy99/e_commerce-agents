"""Techno Track AI - DB package"""
from .supabase_client import (
    get_supabase,
    upsert_analysis_result,
    fetch_cached_analysis,
    save_generated_image,
    add_favorite,
    get_favorites,
    delete_favorite,
    add_price_alert,
    get_price_alerts,
    delete_price_alert,
)

__all__ = [
    "get_supabase",
    "upsert_analysis_result",
    "fetch_cached_analysis",
    "save_generated_image",
    "add_favorite",
    "get_favorites",
    "delete_favorite",
    "add_price_alert",
    "get_price_alerts",
    "delete_price_alert",
]
