"""
ShopSage AI - Analyst Route
POST /analyze/reviews
"""
import logging
from fastapi import APIRouter, HTTPException, status

from ..agents.analyst_agent import run_analyst_agent
from ..models.requests      import AnalystRequest
from ..models.responses     import AnalystResponse, AgentStatus

logger = logging.getLogger("shopsage.routes.analyze")
router = APIRouter(prefix="/analyze", tags=["Analyst Agent"])


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
