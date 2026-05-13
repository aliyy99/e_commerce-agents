"""
ShopSage AI - Analyst Route
POST /analyze/reviews
"""
import logging
from fastapi import APIRouter, HTTPException, status

from ..agents.analyst_agent import run_analyst_agent
from ..agents.compare_agent import run_compare_agent
from ..models.requests      import AnalystRequest, CompareRequest
from ..models.responses     import AnalystResponse, AgentStatus, CompareResponse

logger = logging.getLogger("shopsage.routes.analyze")
router = APIRouter(prefix="/analyze", tags=["Analyst Agent"])

@router.post(
    "/compare",
    response_model=CompareResponse,
    summary="Multi-site product comparison and analysis",
    status_code=status.HTTP_200_OK,
)
async def analyze_compare(body: CompareRequest) -> CompareResponse:
    logger.info("POST /analyze/compare with %d products", len(body.products))
    try:
        report = await run_compare_agent(body)
        return CompareResponse(markdown_report=report)
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
        "The **Analyst Agent** (Gemini Pro) detects fake reviews, identifies "
        "chronic product issues, and produces a Buy / Wait / Avoid recommendation. "
        "Gemini Pro is used here for its 1M-token context window and "
        "multi-step reasoning capability."
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
