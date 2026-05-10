"""ShopSage AI - Routes package"""
from .vision         import router as vision_router
from .analyze        import router as analyze_router
from .generate_style import router as style_router
from .orchestrate    import router as orchestrate_router

__all__ = ["vision_router", "analyze_router", "style_router", "orchestrate_router"]
