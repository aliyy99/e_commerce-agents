"""
ShopSage AI - Orchestrator Route
POST /orchestrate
"""
import logging
from fastapi import APIRouter, HTTPException, status

from ..agents.orchestrator  import orchestrate
from ..models.requests      import OrchestrateRequest
from ..models.responses     import OrchestrateResponse, AgentStatus

logger = logging.getLogger("shopsage.routes.orchestrate")
router = APIRouter(tags=["Orchestrator"])


@router.post(
    "/orchestrate",
    response_model=OrchestrateResponse,
    summary="Run the full multi-agent pipeline",
    description=(
        "The **Orchestrator** inspects the request payload and automatically "
        "decides which agents to invoke:\n\n"
        "- **Vision Agent** → triggered when `vision` field is present\n"
        "- **Analyst Agent** → triggered when `analyst` field is present\n"
        "- **Visualizer Agent** → triggered for `fashion`/`furniture` + `style` field\n\n"
        "Vision and Analyst run **concurrently** via `asyncio.gather`. "
        "Results are persisted to Supabase if `save_to_db=true`."
    ),
    status_code=status.HTTP_200_OK,
)
async def run_orchestration(body: OrchestrateRequest) -> OrchestrateResponse:
    """
    ROUTE: /orchestrate  →  Orchestrator (all agents)
    """
    logger.info("POST /orchestrate (query=%r)", body.query)
    result = await orchestrate(body)
    if result.status == AgentStatus.ERROR and not result.agents_invoked:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No agents were invoked. Provide at least one of: vision, analyst, or style payload.",
        )
    return result
