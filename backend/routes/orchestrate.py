"""
Techno Track AI - Orchestrator Route
POST /orchestrate
"""
import logging
from fastapi import APIRouter, HTTPException, status, WebSocket, WebSocketDisconnect

from ..agents.orchestrator  import orchestrate, manager
from ..models.requests      import OrchestrateRequest
from ..models.responses     import OrchestrateResponse, AgentStatus

logger = logging.getLogger("technotrack.routes.orchestrate")
router = APIRouter(tags=["Orchestrator"])


@router.websocket("/orchestrate/ws/{session_id}")
async def orchestrate_websocket(websocket: WebSocket, session_id: str):
    """
    WebSocket endpoint for receiving real-time status updates from the orchestrator.
    Frontend connects here with a generated session_id, then posts to /orchestrate
    with the same session_id.
    """
    await manager.connect(websocket, session_id)
    try:
        while True:
            # Keep connection alive
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect(session_id)
        logger.info(f"WebSocket disconnected for session: {session_id}")


@router.post(
    "/orchestrate",
    response_model=OrchestrateResponse,
    summary="Run the full multi-agent pipeline",
    description=(
        "The **Orchestrator** inspects the request payload and automatically "
        "decides which agents to invoke:\n\n"
        "- **Vision Agent** → triggered when `vision` field is present\n"
        "- **Detective Agent** → triggered when `detective` field is present, or automatically from Vision output.\n"
        "- **Analyst Agent** → triggered when `analyst` field is present, or automatically from Detective output.\n"
        "- **Visualizer Agent** → triggered for `fashion`/`furniture` + `style` field\n\n"
        "Agents run sequentially: Vision -> Detective -> Analyst."
        "Results are persisted to Supabase if `save_to_db=true`."
    ),
    status_code=status.HTTP_200_OK,
)
async def run_orchestration(body: OrchestrateRequest) -> OrchestrateResponse:
    """
    ROUTE: /orchestrate  →  Orchestrator (all agents)
    """
    logger.info("POST /orchestrate (query=%r, session_id=%s)", body.query, body.session_id)
    result = await orchestrate(body)
    if result.status == AgentStatus.ERROR and not result.agents_invoked:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No agents were invoked. Provide at least one valid payload.",
        )
    return result
