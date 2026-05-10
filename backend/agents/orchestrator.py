"""
╔══════════════════════════════════════════════════════════════╗
║               ORCHESTRATOR  –  Async Workflow Engine         ║
╠══════════════════════════════════════════════════════════════╣
║  RESPONSIBILITIES:                                           ║
║  ▸ Parse the user query to determine which agents to invoke  ║
║  ▸ Run Vision + Analyst concurrently with asyncio.gather     ║
║  ▸ Invoke Visualizer only for fashion/furniture categories   ║
║  ▸ Persist the aggregated result to Supabase                 ║
║  ▸ Return a unified OrchestrateResponse in < 5 s (P95)       ║
╚══════════════════════════════════════════════════════════════╝
"""
from __future__ import annotations

import asyncio
import logging
import time
import uuid
from datetime import datetime, timezone

from ..models.requests import OrchestrateRequest, ProductCategory
from ..models.responses import (
    AgentStatus, OrchestrateResponse,
    VisionResponse, AnalystResponse, StyleResponse,
)
from ..agents.vision_agent     import run_vision_agent
from ..agents.analyst_agent    import run_analyst_agent
from ..agents.visualizer_agent import run_visualizer_agent
from ..db import upsert_analysis_result

logger = logging.getLogger("shopsage.orchestrator")


# ─────────────────────────────────────────────────────────────
# Agent decision helpers
# ─────────────────────────────────────────────────────────────
def _needs_vision(req: OrchestrateRequest) -> bool:
    """ORCHESTRATOR: Returns True if the request contains image data."""
    return req.vision is not None


def _needs_analyst(req: OrchestrateRequest) -> bool:
    """ORCHESTRATOR: Returns True if reviews + price history are provided."""
    return req.analyst is not None


def _needs_visualizer(req: OrchestrateRequest) -> bool:
    """ORCHESTRATOR: Returns True for fashion/furniture queries with style payload."""
    return (
        req.style is not None
        and req.category in (ProductCategory.FASHION, ProductCategory.FURNITURE)
    )


# ─────────────────────────────────────────────────────────────
# Public entry-point
# ─────────────────────────────────────────────────────────────
async def orchestrate(request: OrchestrateRequest) -> OrchestrateResponse:
    """
    AGENT: Orchestrator
    ───────────────────
    Central workflow engine that:
      1. Determines which agents are needed for this request.
      2. Runs Vision & Analyst concurrently (asyncio.gather).
      3. Runs Visualizer independently (image generation is sequential).
      4. Merges all results into a single OrchestrateResponse.
      5. Persists to Supabase if save_to_db=True.

    Concurrency strategy:
      • Vision + Analyst → asyncio.gather (parallel I/O-bound calls)
      • Visualizer       → awaited after gather (avoids rate-limit spikes)

    Args:
        request: Validated OrchestrateRequest from the route handler.

    Returns:
        OrchestrateResponse aggregating all agent outputs.
    """
    t_start = time.monotonic()
    agents_invoked: list[str] = []
    vision_result:  VisionResponse  | None = None
    analyst_result: AnalystResponse | None = None
    style_result:   StyleResponse   | None = None
    db_record_id:   str | None = None

    logger.info("Orchestrator → query=%r  category=%s", request.query, request.category)

    # ── PHASE 1: Concurrent Vision + Analyst ──────────────────
    tasks = []

    if _needs_vision(request):
        tasks.append(_run_vision(request))
        agents_invoked.append("vision_agent")

    if _needs_analyst(request):
        tasks.append(_run_analyst(request))
        agents_invoked.append("analyst_agent")

    if tasks:
        results = await asyncio.gather(*tasks, return_exceptions=True)
        idx = 0
        if _needs_vision(request):
            vision_result = results[idx] if not isinstance(results[idx], Exception) else _vision_error(results[idx])
            idx += 1
        if _needs_analyst(request):
            analyst_result = results[idx] if not isinstance(results[idx], Exception) else _analyst_error(results[idx])

    # ── PHASE 2: Sequential Visualizer ────────────────────────
    if _needs_visualizer(request):
        agents_invoked.append("visualizer_agent")
        try:
            style_result = await run_visualizer_agent(request.style)
        except Exception as err:
            logger.error("Visualizer failed in orchestrator: %s", err)
            style_result = StyleResponse(status=AgentStatus.ERROR, error_detail=str(err))

    # ── PHASE 3: Persist to Supabase ──────────────────────────
    if request.save_to_db and (vision_result or analyst_result):
        try:
            db_record_id = await upsert_analysis_result({
                "id":            str(uuid.uuid4()),
                "product_id":    getattr(request.analyst, "product_id", None),
                "query":         request.query,
                "category":      request.category,
                "vision_result": vision_result.model_dump()  if vision_result  else None,
                "analyst_result":analyst_result.model_dump() if analyst_result else None,
                "style_result":  style_result.model_dump()   if style_result   else None,
                "created_at":    datetime.now(timezone.utc).isoformat(),
            })
        except Exception as db_err:
            logger.warning("DB upsert failed (non-fatal): %s", db_err)

    duration_ms = int((time.monotonic() - t_start) * 1000)
    logger.info("Orchestrator → done  agents=%s  duration=%dms", agents_invoked, duration_ms)

    # Determine overall status
    all_results = [r for r in [vision_result, analyst_result, style_result] if r]
    if any(r.status == AgentStatus.ERROR for r in all_results):
        overall = AgentStatus.ERROR
    elif any(r.status == AgentStatus.FALLBACK for r in all_results):
        overall = AgentStatus.FALLBACK
    else:
        overall = AgentStatus.SUCCESS

    return OrchestrateResponse(
        status=overall,
        query=request.query,
        agents_invoked=agents_invoked,
        vision_result=vision_result,
        analyst_result=analyst_result,
        style_result=style_result,
        db_record_id=db_record_id,
        duration_ms=duration_ms,
    )


# ─────────────────────────────────────────────────────────────
# Private wrappers (allow asyncio.gather to return typed results)
# ─────────────────────────────────────────────────────────────
async def _run_vision(req: OrchestrateRequest) -> VisionResponse:
    return await run_vision_agent(req.vision)


async def _run_analyst(req: OrchestrateRequest) -> AnalystResponse:
    return await run_analyst_agent(req.analyst)


def _vision_error(err: Exception) -> VisionResponse:
    return VisionResponse(status=AgentStatus.ERROR, error_detail=str(err))


def _analyst_error(err: Exception) -> AnalystResponse:
    from ..models.responses import BuyStrategy, ReviewInsight, PriceTrend
    return AnalystResponse(
        status=AgentStatus.ERROR,
        product_id="unknown",
        product_name="unknown",
        strategy=BuyStrategy.UNCERTAIN,
        confidence=0.0,
        review_insight=ReviewInsight(total_reviews=0, fake_review_pct=0, average_sentiment=0),
        price_trend=PriceTrend(current_price=0, lowest_30d=0, highest_30d=0, trend_direction="unknown"),
        ai_summary="",
        error_detail=str(err),
    )
