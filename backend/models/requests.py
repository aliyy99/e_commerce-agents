"""
ShopSage AI - Pydantic Request Models
Validates all incoming data before it reaches any agent.
"""
from __future__ import annotations
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field, model_validator


class ImageInputType(str, Enum):
    BASE64 = "base64"


class ProductCategory(str, Enum):
    ELECTRONICS = "electronics"
    FASHION     = "fashion"
    FURNITURE   = "furniture"
    OTHER       = "other"


# ──────────────────────────────────────────────────────────────
# Vision Agent  →  POST /vision/analyze-image
# ──────────────────────────────────────────────────────────────
class VisionRequest(BaseModel):
    """
    Payload for the Vision Agent.
    Accepts a raw Base64-encoded image string from uploaded/captured images.
    """
    input_type: ImageInputType = Field(
        ...,
        description="Must be 'base64' for uploaded/captured images."
    )
    image_data: Optional[str] = Field(
        None,
        description="Base64-encoded image string (without data-URI prefix)."
    )
    locale: str = Field(default="tr", description="ISO-639 language code for the response.")

    @model_validator(mode="after")
    def check_image_source(self) -> "VisionRequest":
        if self.input_type == ImageInputType.BASE64 and not self.image_data:
            raise ValueError("image_data is required when input_type is 'base64'.")
        return self


# ──────────────────────────────────────────────────────────────
# Detective Agent
# ──────────────────────────────────────────────────────────────
class DetectiveRequest(BaseModel):
    """Payload for Detective Agent."""
    product_keywords: str = Field(..., description="Keywords extracted by Vision Agent.")
    locale: str = Field(default="tr")


# ──────────────────────────────────────────────────────────────
# Analyst Agent  →  POST /analyze/reviews
# ──────────────────────────────────────────────────────────────
class PricePoint(BaseModel):
    """Single entry in a price-history timeline."""
    date:  str   = Field(..., example="2025-04-01")
    price: float = Field(..., gt=0, example=1299.99)
    store: str   = Field(..., example="Amazon")


class AnalystRequest(BaseModel):
    """
    Payload for the Analyst Agent.
    Accepts scraped review texts and a price-history list from Detective Agent.
    """
    product_id:    str             = Field(..., description="Internal product identifier.")
    product_name:  str             = Field(..., example="MacBook Pro 14\" M3 Pro")
    reviews:       List[str]       = Field(..., min_length=1, description="Raw scraped review strings.")
    price_history: List[PricePoint] = Field(..., min_length=1)
    locale:        str             = Field(default="tr")


# ──────────────────────────────────────────────────────────────
# Visualizer Agent  →  POST /generate-style
# ──────────────────────────────────────────────────────────────
class StyleRequest(BaseModel):
    """
    Payload for the Visualizer Agent.
    Triggers image generation only for fashion or furniture queries.
    """
    product_name:  str             = Field(..., example="Beige Linen Sofa")
    category:      ProductCategory = Field(..., description="Must be 'fashion' or 'furniture' to trigger generation.")
    style_context: Optional[str]   = Field(
        None,
        example="Scandinavian interior with warm lighting and white oak floors."
    )

    @model_validator(mode="after")
    def validate_category(self) -> "StyleRequest":
        if self.category not in (ProductCategory.FASHION, ProductCategory.FURNITURE):
            raise ValueError(
                f"Visualizer Agent only supports 'fashion' and 'furniture' categories, got '{self.category}'."
            )
        return self


# ──────────────────────────────────────────────────────────────
# Tracking System
# ──────────────────────────────────────────────────────────────
class TrackProductRequest(BaseModel):
    user_id: str
    product_id: str
    target_price: float


# ──────────────────────────────────────────────────────────────
# Orchestrator  →  POST /orchestrate
# ──────────────────────────────────────────────────────────────
class OrchestrateRequest(BaseModel):
    """
    Master payload consumed by the Orchestrator.
    It decides which agents to invoke based on the provided fields.
    """
    query:         str                   = Field(..., example="Find me the best MacBook Pro deal")
    category:      ProductCategory       = Field(default=ProductCategory.OTHER)
    vision:        Optional[VisionRequest]   = None
    detective:     Optional[DetectiveRequest]= None
    analyst:       Optional[AnalystRequest]  = None
    style:         Optional[StyleRequest]    = None
    save_to_db:    bool                  = Field(default=True, description="Persist results to Supabase.")
    session_id:    Optional[str]         = Field(None, description="WebSocket session ID for real-time updates.")

# ──────────────────────────────────────────────────────────────
# Chat Assistant
# ──────────────────────────────────────────────────────────────
class ChatMessage(BaseModel):
    role: str = Field(..., description="'user' or 'assistant'")
    content: str

class ChatRequest(BaseModel):
    history: List[ChatMessage] = Field(default_factory=list)
    user_message: str
    context_data: Optional[dict] = Field(None, description="Current product analysis data")

# ──────────────────────────────────────────────────────────────
# Compare Agent
# ──────────────────────────────────────────────────────────────
class CompareSiteData(BaseModel):
    site: Optional[str] = None
    url: str = Field(..., description="Direct product page URL.")
    product_name: Optional[str] = None
    price: Optional[str] = None
    currency: str = "TRY"
    rating: Optional[str] = None
    rating_scale: str = "5"
    review_count: Optional[str] = None
    specs: dict = Field(default_factory=dict)
    reviews: List[str] = Field(default_factory=list)

class CompareRequest(BaseModel):
    products: List[CompareSiteData]
    locale: str = Field(default="tr", description="Output locale for the comparison report.")
