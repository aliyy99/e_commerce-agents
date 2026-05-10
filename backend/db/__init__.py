"""ShopSage AI - DB package"""
from .supabase_client import (
    get_supabase,
    upsert_analysis_result,
    fetch_cached_analysis,
    save_generated_image,
)

__all__ = [
    "get_supabase",
    "upsert_analysis_result",
    "fetch_cached_analysis",
    "save_generated_image",
]
