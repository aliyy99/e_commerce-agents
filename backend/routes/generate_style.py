"""
ShopSage AI - Generate Style Route
POST /generate-style
"""
import logging
from fastapi import APIRouter, HTTPException, status

from ..agents.visualizer_agent import run_visualizer_agent
from ..models.requests          import StyleRequest
from ..models.responses         import StyleResponse, AgentStatus

logger = logging.getLogger("shopsage.routes.generate_style")
router = APIRouter(tags=["Visualizer Agent"])


@router.post(
    "/generate-style",
    response_model=StyleResponse,
    summary="Generate an outfit combo or room layout image",
    description=(
        "Only available for **fashion** and **furniture** categories. "
        "The **Visualizer Agent** (Imagen 3) generates a photorealistic "
        "contextual image: an outfit combination for fashion products, "
        "or a room placement shot for furniture. "
        "The image is stored in Supabase Storage and a public URL is returned."
    ),
    status_code=status.HTTP_200_OK,
)
async def generate_style(body: StyleRequest) -> StyleResponse:
    """
    ROUTE: /generate-style  →  Visualizer Agent
    """
    logger.info(
        "POST /generate-style (product=%s, category=%s)",
        body.product_name, body.category,
    )
    result = await run_visualizer_agent(body)
    if result.status == AgentStatus.ERROR:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=result.error_detail or "Visualizer agent failed.",
        )
    return result
