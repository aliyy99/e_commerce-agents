"""ShopSage AI - Routes package"""
from .vision         import router as vision_router
from .analyze        import router as analyze_router
from .generate_style import router as style_router
from .orchestrate    import router as orchestrate_router
from .tracking       import router as tracking_router
from .user_data      import router as user_data_router
from .stream         import router as stream_router

__all__ = [
    "vision_router",
    "analyze_router",
    "style_router",
    "orchestrate_router",
    "tracking_router",
    "user_data_router",
    "stream_router",
]
