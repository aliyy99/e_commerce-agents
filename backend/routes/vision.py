"""
ShopSage AI - Vision Route
POST /vision/analyze-image
"""
import logging
from fastapi import APIRouter, HTTPException, status

from ..agents.vision_agent import run_vision_agent
from ..models.requests     import VisionRequest
from ..models.responses    import VisionResponse, AgentStatus

logger = logging.getLogger("shopsage.routes.vision")
router = APIRouter(prefix="/vision", tags=["Vision Agent"])


@router.post(
    "/analyze-image",
    response_model=VisionResponse,
    summary="Identify a product from an image",
    description=(
        "Accepts a Base64-encoded image from upload/camera input. "
        "The **Vision Agent** (Gemini 3 Flash) identifies the product, brand, "
        "and technical specifications. Falls back to Gemini 2.5 Pro with an "
        "expanded token budget if the initial confidence is below 0.4."
    ),
    status_code=status.HTTP_200_OK,
)
async def analyze_image(body: VisionRequest) -> VisionResponse:
    """
    ROUTE: /vision/analyze-image  →  Vision Agent
    """
    logger.info("POST /vision/analyze-image (input_type=%s)", body.input_type)
    result = await run_vision_agent(body)
    if result.status == AgentStatus.ERROR:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=result.error_detail or "Vision agent failed.",
        )
    return result
