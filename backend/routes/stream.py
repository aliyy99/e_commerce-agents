"""
ShopSage AI - Server-Sent Events (SSE) Streaming Route
GET /api/v1/stream/pipeline/{session_id}

Provides a real-time "Agentic Logs" feed to the frontend.
Each agent (Visionary, Detective, Analyst) pushes structured log events
via an asyncio.Queue tied to the session_id.

Why SSE over WebSocket?
- Simpler client-side implementation (native EventSource API)
- Auto-reconnect built into the browser standard
- Unidirectional (server → client) which is exactly what we need
- No keep-alive handshake overhead
"""
import asyncio
import json
import logging
import time
from typing import AsyncGenerator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

logger = logging.getLogger("shopsage.routes.stream")
router = APIRouter(prefix="/stream", tags=["SSE Streaming"])


# ── Session-based event bus ─────────────────────────────────────
# Each pipeline run creates a queue; the SSE endpoint reads from it.
_event_queues: dict[str, asyncio.Queue] = {}


def get_or_create_queue(session_id: str) -> asyncio.Queue:
    """Returns the event queue for a session, creating it if necessary."""
    if session_id not in _event_queues:
        _event_queues[session_id] = asyncio.Queue()
    return _event_queues[session_id]


def cleanup_queue(session_id: str):
    """Removes the queue after the pipeline completes."""
    _event_queues.pop(session_id, None)


async def push_event(session_id: str, agent: str, message: str, event_type: str = "log"):
    """
    Pushes a structured event to the session queue.
    Called by the orchestrator and individual agents during execution.

    Args:
        session_id: The pipeline session identifier.
        agent: Agent name (e.g., "Visionary", "Detective", "Analyst", "Decision").
        message: Human-readable status message.
        event_type: SSE event type — "log", "result", "error", "done".
    """
    q = get_or_create_queue(session_id)
    event = {
        "agent": agent,
        "message": message,
        "type": event_type,
        "timestamp": time.time(),
    }
    await q.put(event)


async def _event_generator(session_id: str) -> AsyncGenerator[str, None]:
    """
    Async generator that yields SSE-formatted events from the session queue.
    Terminates when a "done" event is received or after 5 min timeout.
    """
    q = get_or_create_queue(session_id)
    timeout = 300  # 5 minutes max

    try:
        start = time.monotonic()
        while time.monotonic() - start < timeout:
            try:
                event = await asyncio.wait_for(q.get(), timeout=30)
                # Format as SSE. Use json.dumps so quotes/backslashes/newlines
                # in agent messages cannot corrupt the data payload.
                payload = json.dumps({
                    "agent": event["agent"],
                    "message": event["message"],
                    "ts": event["timestamp"],
                }, ensure_ascii=False)
                yield f"event: {event['type']}\n"
                yield f"data: {payload}\n\n"

                if event["type"] == "done":
                    break
            except asyncio.TimeoutError:
                # Send heartbeat to keep connection alive
                yield f": heartbeat\n\n"
    finally:
        cleanup_queue(session_id)


@router.get(
    "/pipeline/{session_id}",
    summary="Subscribe to real-time pipeline logs via SSE",
    description=(
        "Opens a Server-Sent Events stream for the given session. "
        "The frontend connects here before triggering /orchestrate. "
        "Events include agent status updates, progress messages, and final results."
    ),
)
async def stream_pipeline(session_id: str):
    """
    SSE endpoint: streams real-time agentic log events.

    Usage (Frontend):
      const eventSource = new EventSource('/api/v1/stream/pipeline/my-session-123');
      eventSource.addEventListener('log', (e) => console.log(JSON.parse(e.data)));
    """
    return StreamingResponse(
        _event_generator(session_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable Nginx buffering
        },
    )
