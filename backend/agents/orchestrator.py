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

from fastapi import WebSocket

from ..models.requests import OrchestrateRequest, ProductCategory, DetectiveRequest, AnalystRequest, PricePoint
from ..models.responses import (
    AgentStatus, OrchestrateResponse,
    VisionResponse, AnalystResponse, StyleResponse, DetectiveResponse
)
from ..agents.vision_agent     import run_vision_agent
from ..agents.detective_agent  import run_detective_agent
from ..agents.analyst_agent    import run_analyst_agent
from ..agents.visualizer_agent import run_visualizer_agent
from ..db import upsert_analysis_result

logger = logging.getLogger("shopsage.orchestrator")

# Basic WebSocket Manager (in a real app, this would be more robust)
class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, session_id: str):
        await websocket.accept()
        self.active_connections[session_id] = websocket

    def disconnect(self, session_id: str):
        if session_id in self.active_connections:
            del self.active_connections[session_id]

    async def send_status(self, session_id: str, message: str):
        if session_id in self.active_connections:
            try:
                await self.active_connections[session_id].send_json({"type": "status", "message": message})
            except Exception as e:
                logger.error("WebSocket send error: %s", e)

manager = ConnectionManager()

async def emit_status(session_id: str | None, message: str):
    if session_id:
        await manager.send_status(session_id, message)


# ─────────────────────────────────────────────────────────────
# Public entry-point
# ─────────────────────────────────────────────────────────────
async def orchestrate(request: OrchestrateRequest) -> OrchestrateResponse:
    """
    AGENT: Orchestrator (Chain of Thought Workflow)
    ───────────────────────────────────────────────
    1. Vision Agent (if image): Identifies product & extracts keywords.
    2. Detective Agent: Takes keywords, searches for prices and reviews.
    3. Analyst Agent: Takes reviews/prices, performs deep analysis.
    4. Visualizer Agent (parallel if applicable): Generates style image.
    """
    t_start = time.monotonic()
    agents_invoked: list[str] = []
    
    vision_result:  VisionResponse | None = None
    detective_result: DetectiveResponse | None = None
    analyst_result: AnalystResponse | None = None
    style_result:   StyleResponse | None = None
    db_record_id:   str | None = None
    
    sid = request.session_id

    await emit_status(sid, "Orkestrasyon başlatıldı...")

    # ── 1. Vision Agent ─────────────────────────────
    if request.vision is not None:
        agents_invoked.append("vision_agent")
        await emit_status(sid, "Görsel işleniyor (Gemini 2.0 Flash)...")
        try:
            vision_result = await run_vision_agent(request.vision)
            if vision_result.status != AgentStatus.ERROR:
                await emit_status(sid, f"Ürün tespit edildi: {vision_result.product_name}")
        except Exception as e:
            vision_result = _vision_error(e)

    # Determine keywords for search
    keywords = None
    if request.detective:
        keywords = request.detective.product_keywords
    elif vision_result and vision_result.search_keywords:
        keywords = vision_result.search_keywords
    elif request.query and len(request.query) > 3:
        keywords = request.query

    # ── 2. Detective Agent ──────────────────────────
    if keywords:
        agents_invoked.append("detective_agent")
        req = DetectiveRequest(product_keywords=keywords)
        
        async def emit_det(msg): await emit_status(sid, msg)
        
        try:
            detective_result = await run_detective_agent(req, emit_status=emit_det)
        except Exception as e:
            detective_result = DetectiveResponse(
                status=AgentStatus.ERROR, query_used=keywords, retries=0, error_detail=str(e)
            )

    # ── 3. Analyst Agent ────────────────────────────
    # If we have scraped data, or if user explicitly provided analyst payload
    analyst_req = None
    if detective_result and detective_result.status != AgentStatus.ERROR and detective_result.found_prices:
        prices = [
            PricePoint(date=datetime.now().strftime("%Y-%m-%d"), price=p.price, store=p.store)
            for p in detective_result.found_prices
        ]
        analyst_req = AnalystRequest(
            product_id=str(uuid.uuid4()),
            product_name=vision_result.product_name if vision_result else keywords,
            reviews=detective_result.reviews_found,
            price_history=prices
        )
    elif request.analyst:
        analyst_req = request.analyst

    if analyst_req:
        agents_invoked.append("analyst_agent")
        async def emit_ana(msg): await emit_status(sid, msg)
        try:
            analyst_result = await run_analyst_agent(analyst_req, emit_status=emit_ana)
        except Exception as e:
            analyst_result = _analyst_error(e)

    # ── 4. Visualizer Agent ─────────────────────────
    if request.style and request.category in (ProductCategory.FASHION, ProductCategory.FURNITURE):
        agents_invoked.append("visualizer_agent")
        await emit_status(sid, "Görsel (stil) üretiliyor (Imagen 3)...")
        try:
            style_result = await run_visualizer_agent(request.style)
        except Exception as err:
            style_result = StyleResponse(status=AgentStatus.ERROR, error_detail=str(err))


    # ── PHASE 5: Persist to Supabase ──────────────────────────
    if request.save_to_db and (vision_result or analyst_result):
        try:
            await emit_status(sid, "Sonuçlar Supabase'e kaydediliyor...")
            db_record_id = await upsert_analysis_result({
                "id":            str(uuid.uuid4()),
                "product_id":    analyst_result.product_id if analyst_result else None,
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

    await emit_status(sid, f"Orkestrasyon tamamlandı. ({duration_ms}ms)")

    all_results = [r for r in [vision_result, detective_result, analyst_result, style_result] if r]
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
        detective_result=detective_result,
        analyst_result=analyst_result,
        style_result=style_result,
        db_record_id=db_record_id,
        duration_ms=duration_ms,
    )

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
        review_insight=ReviewInsight(total_reviews=0, fake_review_pct=0, average_sentiment=0, sentiment_map={}, red_flags=[]),
        price_trend=PriceTrend(current_price=0, lowest_30d=0, highest_30d=0, trend_direction="unknown"),
        ai_summary="",
        final_recommendation="",
        error_detail=str(err),
    )
