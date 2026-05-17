"""
Techno Track AI - Analyst Route
POST /analyze/reviews
"""
import logging
from fastapi import APIRouter, HTTPException, status

from ..agents.analyst_agent import run_analyst_agent
from ..agents.compare_agent import run_compare_agent
from ..models.requests      import AnalystRequest, CompareRequest
from ..models.responses     import AnalystResponse, AgentStatus, CompareResponse

logger = logging.getLogger("technotrack.routes.analyze")
router = APIRouter(prefix="/analyze", tags=["Analyst Agent"])

@router.post(
    "/compare",
    response_model=CompareResponse,
    summary="Deep multi-site analyst report (blind spots, chronic issues, trust)",
    status_code=status.HTTP_200_OK,
)
async def analyze_compare(body: CompareRequest) -> CompareResponse:
    logger.info("POST /analyze/compare with %d products", len(body.products))
    try:
        result = await run_compare_agent(body)
        return CompareResponse(
            deep_analysis=result.get("deep_analysis"),
            lowest_price=result.get("lowest_price"),
            lowest_price_site=result.get("lowest_price_site"),
            store_prices=result.get("store_prices") or [],
            model_used=result.get("model_used"),
        )
    except Exception as err:
        logger.error("Compare agent failed: %s", err)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(err),
        )



@router.post(
    "/reviews",
    response_model=AnalystResponse,
    summary="Deep analysis of product reviews and price history",
    description=(
        "Accepts scraped reviews and price history. "
        "The **Analyst Agent** (Gemini Flash) detects fake reviews, identifies "
        "chronic product issues, and produces a Buy / Wait / Avoid recommendation. "
        "Flash is used here for its long-context handling on the free tier "
        "(Pro models are paid-only on the active key)."
    ),
    status_code=status.HTTP_200_OK,
)
async def analyze_reviews(body: AnalystRequest) -> AnalystResponse:
    """
    ROUTE: /analyze/reviews  →  Analyst Agent
    """
    logger.info(
        "POST /analyze/reviews (product=%s, reviews=%d)",
        body.product_name, len(body.reviews),
    )
    result = await run_analyst_agent(body)
    if result.status == AgentStatus.ERROR:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=result.error_detail or "Analyst agent failed.",
        )
    return result
