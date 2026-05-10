"""ShopSage AI - Chat Assistant Route"""
import logging
from fastapi import APIRouter, HTTPException, status
import google.generativeai as genai

from ..models.requests import ChatRequest
from ..models.responses import ChatResponse
from ..config import settings
from ..db.supabase_client import save_recent_search
import json

logger = logging.getLogger("shopsage.routes.chat")
router = APIRouter(tags=["Chat"])

genai.configure(api_key=settings.GOOGLE_API_KEY)

_CHAT_SYSTEM = """
You are ShopSage Assistant, a highly intelligent and helpful shopping guide.
Your goal is to help users make informed purchasing decisions based on the product analysis data provided to you.
Be concise, friendly, and data-driven. Always refer to the provided context data when answering.
If the context data shows that prices are dropping or an item is overpriced, warn the user.
If the analyst agent found bot reviews or chronic issues (Kronik Sorunlar), mention them.
If the user asks "Bu ürün fiyatına değer mi?" or similar, answer clearly (e.g., "Evet, çünkü..." or "Hayır, bekle...").
Respond in Turkish.
"""

@router.post("/chat", response_model=ChatResponse)
async def chat_with_assistant(request: ChatRequest) -> ChatResponse:
    try:
        model = genai.GenerativeModel(
            model_name=settings.PRO_MODEL,
            system_instruction=_CHAT_SYSTEM
        )
        
        # Build conversation history
        messages = []
        for msg in request.history:
            messages.append({"role": "user" if msg.role == "user" else "model", "parts": [msg.content]})
        
        # Add context to the latest user message secretly
        latest_message = request.user_message
        if request.context_data:
            context_str = json.dumps(request.context_data, ensure_ascii=False, indent=2)
            latest_message = f"Product Analysis Context Data:\n{context_str}\n\nUser Question:\n{request.user_message}"
        
        messages.append({"role": "user", "parts": [latest_message]})
        
        response = model.generate_content(messages)
        reply_text = response.text.strip()
        
        if request.context_data:
            product_name = request.context_data.get("product_name", "Unknown Product")
            try:
                await save_recent_search(
                    product_name=product_name,
                    assistant_advice=reply_text
                )
            except Exception as db_err:
                logger.warning(f"Failed to save recent search to DB: {db_err}")
        
        return ChatResponse(reply=reply_text)
        
    except Exception as e:
        logger.error(f"Chat route failed: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
