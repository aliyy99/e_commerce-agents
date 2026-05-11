"""Backend-for-Frontend Gemini wrappers."""
import json

import google.generativeai as genai

from ..config import settings
from ..models.requests import ChatRequest
from .gemini_client import configure_gemini_client

_CHAT_SYSTEM = """
You are ShopSage Assistant, a highly intelligent and helpful shopping guide.
Your goal is to help users make informed purchasing decisions based on the product analysis data provided to you.
Be concise, friendly, and data-driven. Always refer to the provided context data when answering.
If the context data shows that prices are dropping or an item is overpriced, warn the user.
If the analyst agent found bot reviews or chronic issues (Kronik Sorunlar), mention them.
If the user asks "Bu ürün fiyatına değer mi?" or similar, answer clearly (e.g., "Evet, çünkü..." or "Hayır, bekle...").
Respond in Turkish.
""".strip()


def _build_chat_messages(request: ChatRequest) -> list[dict]:
    messages = []
    for msg in request.history:
        messages.append({"role": "user" if msg.role == "user" else "model", "parts": [msg.content]})

    latest_message = request.user_message
    if request.context_data:
        context_str = json.dumps(request.context_data, ensure_ascii=False, indent=2)
        latest_message = f"Product Analysis Context Data:\n{context_str}\n\nUser Question:\n{request.user_message}"

    messages.append({"role": "user", "parts": [latest_message]})
    return messages


def generate_chat_reply(request: ChatRequest) -> str:
    """Proxy frontend chat payload to Gemini and return plain reply text."""
    configure_gemini_client()
    model = genai.GenerativeModel(
        model_name=settings.PRO_MODEL,
        system_instruction=_CHAT_SYSTEM,
    )
    response = model.generate_content(_build_chat_messages(request))
    reply_text = (response.text or "").strip()
    if not reply_text:
        raise ValueError("Gemini boş yanıt döndü.")
    return reply_text
