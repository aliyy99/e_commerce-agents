"""
Techno Track AI - Pydantic Response Models
All agent outputs are typed here before being returned to the client.
"""
from __future__ import annotations
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class AgentStatus(str, Enum):
    SUCCESS  = "success"
    FALLBACK = "fallback"   # Primary → secondary Pro model fallback was triggered
    ERROR    = "error"


# ──────────────────────────────────────────────────────────────
# Vision Agent Response
# ──────────────────────────────────────────────────────────────
class DetectedSpec(BaseModel):
    key:   str = Field(..., example="RAM")
    value: str = Field(..., example="18 GB Unified Memory")


class VisionResponse(BaseModel):
    """
    Structured output from the Vision Agent (Gemini 3 Flash primary,
    cascading down to non-lite 2.5 Flash, then lite tiers, and Pro
    variants as a paid-plan last resort). Identifies product details
    from an image.
    """
    status:       AgentStatus
    agent:        str              = "vision_agent (gemini-3-flash)"
    product_name: Optional[str]   = None
    search_keywords: Optional[str] = Field(None, description="Keywords for Detective Agent.")
    brand:        Optional[str]   = None
    category:     Optional[str]   = None
    color:        Optional[str]   = Field(
        None,
        description="Primary colour of the product (English token, e.g. 'Black', 'White', 'Blue'). Used to auto-select the matching colour variant in the catalog.",
    )
    specs:        List[DetectedSpec] = Field(default_factory=list)
    confidence:   Optional[float] = Field(None, ge=0.0, le=1.0)
    raw_text:     Optional[str]   = None   # Full model output for debugging
    model_used:   str             = "gemini-3-flash-preview"
    error_detail: Optional[str]   = None


# ──────────────────────────────────────────────────────────────
# Detective Agent Response
# ──────────────────────────────────────────────────────────────
class StoreResult(BaseModel):
    store: str
    price: float
    url: str

class DetectiveResponse(BaseModel):
    """
    Structured output from Detective Agent (Search Logic).
    """
    status:       AgentStatus
    agent:        str = "detective_agent (search)"
    query_used:   str
    retries:      int
    found_prices: List[StoreResult] = Field(default_factory=list)
    reviews_found:List[str] = Field(default_factory=list)
    error_detail: Optional[str] = None


# ──────────────────────────────────────────────────────────────
# Analyst Agent Response
# ──────────────────────────────────────────────────────────────
class BuyStrategy(str, Enum):
    BUY       = "AL"
    WAIT      = "BEKLE"
    AVOID     = "KAÇIN"
    UNCERTAIN = "BELİRSİZ"


class ReviewInsight(BaseModel):
    total_reviews:    int
    fake_review_pct:  float = Field(..., description="Estimated percentage of fake reviews (0-100).")
    chronic_issues:   List[str] = Field(default_factory=list, example=["Fan noise under load", "Poor battery life"])
    positive_themes:  List[str] = Field(default_factory=list)
    average_sentiment: float    = Field(..., ge=-1.0, le=1.0)
    sentiment_map:    Dict[str, float] = Field(default_factory=dict, description="e.g., {'Konfor': 0.8, 'Ses Kalitesi': 0.9}")
    red_flags:        List[str] = Field(default_factory=list, description="Critical warnings from users.")


class PriceTrend(BaseModel):
    current_price:   float
    lowest_30d:      float
    highest_30d:     float
    trend_direction: str   = Field(..., example="downward")
    predicted_drop:  Optional[str] = Field(None, example="~10% drop expected within 2 weeks")


class AnalystResponse(BaseModel):
    """
    Structured output from the Analyst Agent. The default ``model_used`` /
    ``agent`` strings are overwritten by the caller with the actually-invoked
    model name; the defaults exist only for back-compat with consumers that
    didn't pass one.
    """
    status:        AgentStatus
    agent:         str           = "analyst_agent (gemini-3-flash)"
    product_id:    str
    product_name:  str
    strategy:      BuyStrategy
    confidence:    float         = Field(..., ge=0.0, le=1.0)
    review_insight: ReviewInsight
    price_trend:   PriceTrend
    ai_summary:    str           = Field(..., description="Plain-language buying recommendation.")
    final_recommendation: str    = Field(..., description="Detailed Buy/Wait reasoning.")
    model_used:    str           = "gemini-3-flash-preview"
    error_detail:  Optional[str] = None


# ──────────────────────────────────────────────────────────────
# Visualizer Agent Response
# ──────────────────────────────────────────────────────────────
class StyleResponse(BaseModel):
    """
    Structured output from the Visualizer Agent.
    Contains the generated style/room-placement image.
    """
    status:       AgentStatus
    agent:        str           = "visualizer_agent (imagen-3)"
    image_url:    Optional[str] = Field(None, description="Public URL of the generated image (stored in Supabase Storage).")
    image_base64: Optional[str] = Field(None, description="Base64-encoded fallback if storage upload fails.")
    prompt_used:  Optional[str] = None
    model_used:   str           = "imagen-3.0-generate-002"
    error_detail: Optional[str] = None


# ──────────────────────────────────────────────────────────────
# Orchestrator Response (wraps all agent outputs)
# ──────────────────────────────────────────────────────────────
class OrchestrateResponse(BaseModel):
    """
    Master response returned by the Orchestrator.
    Aggregates outputs from all invoked agents.
    """
    status:         AgentStatus
    query:          str
    agents_invoked: List[str]
    vision_result:  Optional[VisionResponse]  = None
    detective_result: Optional[DetectiveResponse] = None
    analyst_result: Optional[AnalystResponse] = None
    style_result:   Optional[StyleResponse]   = None
    db_record_id:   Optional[str]             = Field(None, description="Supabase row UUID if save_to_db=True.")
    duration_ms:    Optional[int]             = Field(None, description="Total orchestration time in milliseconds.")
    error_detail:   Optional[str]            = None

# ──────────────────────────────────────────────────────────────
# Chat Assistant Response
# ──────────────────────────────────────────────────────────────
class ChatResponse(BaseModel):
    reply: str

class StorePrice(BaseModel):
    site: str
    url: str
    price: Optional[float] = None
    currency: str = "TRY"


# ──────────────────────────────────────────────────────────────
# DEEP ANALYSIS – Blind Spots / Chronic Issues / Trust Score
# ──────────────────────────────────────────────────────────────
class ChronicIssue(BaseModel):
    """A complaint pattern that recurs across many user reviews."""
    issue: str = Field(..., description="Concise label, e.g. 'Battery dies after 6 months'.")
    frequency: int = Field(..., ge=1, description="How many reviews mention this issue.")
    severity: str = Field(
        ...,
        description="'low' | 'medium' | 'high' — impact on the buying decision.",
    )
    evidence: List[str] = Field(
        default_factory=list,
        description="Up to 3 short verbatim quotes from real reviews.",
    )


class BlindSpot(BaseModel):
    """A technical limitation the seller/manufacturer does not advertise openly."""
    claim: str = Field(..., description="What the marketing/spec sheet implies.")
    reality: str = Field(..., description="What actually happens in everyday use.")
    source: str = Field(
        ...,
        description="'reviews' | 'spec_sheet' | 'expert_consensus' — where this was inferred from.",
    )


class TrustReport(BaseModel):
    """Estimates how trustworthy the visible review pool is."""
    total_reviews_seen: int
    organic_pct: float = Field(..., ge=0, le=100, description="Estimated genuine reviews %.")
    suspicious_pct: float = Field(..., ge=0, le=100, description="Estimated fake/bot reviews %.")
    trust_score: int = Field(
        ...,
        ge=0, le=100,
        description="0-100 confidence in the visible review pool (100 = fully trustworthy).",
    )
    suspicious_signals: List[str] = Field(
        default_factory=list,
        description="Patterns flagging fake reviews: 'all 5-star', 'generic praise', 'identical phrasing'.",
    )
    suspicious_examples: List[str] = Field(
        default_factory=list,
        description="Up to 3 sample suspicious review snippets.",
    )


class HonestPoint(BaseModel):
    """A genuinely strong or genuinely weak aspect of the product."""
    label: str = Field(..., description="One-line label, e.g. 'Camera in daylight'.")
    explanation: str = Field(..., description="Why this is genuinely good/bad.")
    evidence: Optional[str] = Field(None, description="Short supporting quote from a review, if any.")


class SiteSummary(BaseModel):
    """Compact per-site snapshot for the comparison strip."""
    site: str
    url: Optional[str] = None
    price: Optional[float] = None
    currency: str = "TRY"
    rating: Optional[float] = None
    review_count: Optional[int] = None
    pros: List[str] = Field(default_factory=list)
    cons: List[str] = Field(default_factory=list)


class GroundingSource(BaseModel):
    """A web source the grounded model cited via Google Search."""
    title: Optional[str] = None
    uri: str


class DeepAnalysis(BaseModel):
    """
    The structured intelligence report produced by the Analyst Agent. The
    frontend renders this directly — no markdown rehydration needed.
    """
    verdict: str = Field(..., description="'BUY' | 'WAIT' | 'AVOID'.")
    confidence: float = Field(..., ge=0.0, le=1.0)
    headline: str = Field(..., description="One-sentence punchy verdict.")
    final_recommendation: str = Field(
        ...,
        description="2-3 paragraph plain-language buying advice that names concrete reasons.",
    )
    blind_spots: List[BlindSpot] = Field(default_factory=list)
    chronic_issues: List[ChronicIssue] = Field(default_factory=list)
    trust_report: TrustReport
    honest_pros: List[HonestPoint] = Field(
        default_factory=list,
        description="Exactly 3 genuinely good aspects.",
    )
    honest_cons: List[HonestPoint] = Field(
        default_factory=list,
        description="Exactly 3 must-tolerate aspects.",
    )
    red_flags: List[str] = Field(
        default_factory=list,
        description="Critical warnings (fake product reports, arrived broken, etc.).",
    )
    site_summaries: List[SiteSummary] = Field(default_factory=list)
    cheapest_site: Optional[str] = None
    cheapest_price: Optional[float] = None
    grounding_sources: List[GroundingSource] = Field(
        default_factory=list,
        description="External web sources cited by the model via Google Search.",
    )
    grounded: bool = Field(
        default=False,
        description="True when the model actually invoked Google Search to corroborate facts.",
    )


class CompareResponse(BaseModel):
    """
    Response from /api/v1/analyze/compare.

    The page consumes ``deep_analysis`` directly; ``markdown_report`` is kept
    optional for backwards compatibility but the analyst agent no longer
    produces free-form prose by default.
    """
    deep_analysis: Optional[DeepAnalysis] = None
    markdown_report: Optional[str] = None
    lowest_price: Optional[float] = Field(
        None,
        description="Cheapest numeric price found across scraped sites (in store currency).",
    )
    lowest_price_site: Optional[str] = None
    store_prices: List[StorePrice] = Field(default_factory=list)
    model_used: Optional[str] = None
