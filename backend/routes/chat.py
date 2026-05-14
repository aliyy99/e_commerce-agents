"""ShopSage AI - Chat Assistant Route"""
import logging

from fastapi import APIRouter, HTTPException, status

from ..db.supabase_client import save_recent_search
from ..models.requests import ChatRequest
from ..models.responses import ChatResponse
from ..services.gemini_proxy import generate_chat_reply

logger = logging.getLogger("shopsage.routes.chat")
router = APIRouter(tags=["Chat"])


@router.post("/chat", response_model=ChatResponse)
async def chat_with_assistant(request: ChatRequest) -> ChatResponse:
    try:
        reply_text = generate_chat_reply(request)

        if request.context_data:
            product_name = request.context_data.get("product_name", "Unknown Product")
            try:
                await save_recent_search(
                    product_name=product_name,
                    assistant_advice=reply_text,
                )
            except Exception as db_err:
                logger.warning("Failed to save recent search to DB: %s", db_err)

        return ChatResponse(reply=reply_text)
    except Exception as e:
        logger.error("Chat route failed: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Chat assistant failed: {e}",
        )
