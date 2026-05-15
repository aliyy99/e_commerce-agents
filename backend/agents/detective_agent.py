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

logger = logging.getLogger("technotrack.detective_agent")


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
        "Great product, the sound quality is amazing.",
        "Battery life is very short, I don't recommend it.",
        "Shipping was very late but the product is original and nice.",
        "Perfect in terms of comfort, I wear it for hours without pain.",
        "I think the product is not original, the box was damaged.",
        "Best device you can buy for this price.",
        "I have constant overheating issues, definitely chronic.",
        "The device shuts itself down due to overheating.",
        "There are constant connection drops, not stable at all.",
        "It drops connection while playing games and has serious overheating problems, I do not recommend it."
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
        await emit_status("Detective Agent searching: " + request.product_keywords)

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
            await emit_status(f"Not found, retrying with shortened keyword: {current_query}")

    if not stores:
        return DetectiveResponse(
            status=AgentStatus.ERROR,
            query_used=current_query,
            retries=retries,
            error_detail="No results found in the search engine."
        )

    if emit_status:
        await emit_status("Prices and reviews successfully extracted.")

    return DetectiveResponse(
        status=AgentStatus.SUCCESS if retries == 0 else AgentStatus.FALLBACK,
        query_used=current_query,
        retries=retries,
        found_prices=stores,
        reviews_found=reviews
    )
