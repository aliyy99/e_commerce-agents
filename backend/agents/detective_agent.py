"""
╔══════════════════════════════════════════════════════════════╗
║             DETECTIVE AGENT  –  Search Logic                ║
╠══════════════════════════════════════════════════════════════╣
║  RESPONSIBILITIES:                                           ║
║  ▸ Take search_keywords from Vision Agent.                   ║
║  ▸ Search e-commerce sites for prices and reviews.           ║
║  ▸ If search fails (simulated), shorten the keyword and      ║
║    retry (Agentic behavior).                                 ║
╚══════════════════════════════════════════════════════════════╝
"""
from __future__ import annotations

import asyncio
import logging
import random
from typing import List

from ..models.requests import DetectiveRequest
from ..models.responses import DetectiveResponse, AgentStatus, StoreResult

logger = logging.getLogger("shopsage.detective_agent")


async def mock_search(query: str) -> tuple[List[StoreResult], List[str]]:
    """
    Simulates a search API call.
    If the query is too long (e.g., > 3 words), it artificially "fails" to
    demonstrate the agentic fallback behavior.
    """
    await asyncio.sleep(1.5)  # Simulate network latency

    words = query.split()
    if len(words) > 3:
        # Simulate a failure to find exact match
        return [], []

    # Simulate success
    base_price = random.uniform(500, 1500)
    
    stores = [
        StoreResult(store="Amazon", price=round(base_price * 0.95, 2), url="https://amazon.com/mock"),
        StoreResult(store="BestBuy", price=round(base_price * 1.05, 2), url="https://bestbuy.com/mock"),
        StoreResult(store="LocalShop", price=round(base_price, 2), url="https://localshop.com/mock"),
    ]

    reviews = [
        "Harika bir ürün, ses kalitesi muazzam.",
        "Bataryası çok hızlı bitiyor, tavsiye etmem.",
        "Kargolama çok gecikti ama ürün orijinal ve güzel.",
        "Konfor açısından mükemmel, saatlerce takıyorum ağrı yapmıyor.",
        "Ürün orijinal değil galiba, kutusu hasarlıydı.",
        "Bu fiyata alınabilecek en iyi cihaz.",
    ]

    return stores, reviews


async def run_detective_agent(request: DetectiveRequest, emit_status=None) -> DetectiveResponse:
    """
    AGENT: Detective Agent
    ──────────────────────────────────────
    Takes keywords, searches, and applies retry logic.
    """
    logger.info("DetectiveAgent → starting (keywords=%r)", request.product_keywords)
    
    if emit_status:
        await emit_status("Detective Agent aranıyor: " + request.product_keywords)

    current_query = request.product_keywords
    retries = 0
    stores, reviews = [], []

    while retries < 3:
        logger.debug("DetectiveAgent → searching %r (retry %d)", current_query, retries)
        stores, reviews = await mock_search(current_query)

        if stores:
            # Success
            break
        
        # Fallback: shorten the query
        words = current_query.split()
        if len(words) <= 1:
            break # Can't shorten anymore
        
        current_query = " ".join(words[:-1]) # Remove the last word
        retries += 1
        
        if emit_status:
            await emit_status(f"Bulunamadı, anahtar kelime kısaltılarak tekrar aranıyor: {current_query}")

    if not stores:
        return DetectiveResponse(
            status=AgentStatus.ERROR,
            query_used=current_query,
            retries=retries,
            error_detail="Arama motorunda sonuç bulunamadı."
        )

    if emit_status:
        await emit_status("Fiyatlar ve yorumlar başarıyla çekildi.")

    return DetectiveResponse(
        status=AgentStatus.SUCCESS if retries == 0 else AgentStatus.FALLBACK,
        query_used=current_query,
        retries=retries,
        found_prices=stores,
        reviews_found=reviews
    )
