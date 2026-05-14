"""Backend-for-Frontend Gemini wrappers."""
import json
import logging

import google.generativeai as genai

from ..config import settings
from ..models.requests import ChatRequest
from .gemini_client import (
    GeminiAuthError,
    configure_gemini_client,
    raise_if_auth_error,
)

logger = logging.getLogger("shopsage.services.gemini_proxy")

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
    messages = _build_chat_messages(request)
    candidate_models = list(dict.fromkeys([
        settings.CHAT_MODEL,
        settings.FLASH_MODEL,
        settings.PRO_MODEL,
    ]))

    last_error: Exception | None = None
    for model_name in candidate_models:
        try:
            model = genai.GenerativeModel(
                model_name=model_name,
                system_instruction=_CHAT_SYSTEM,
            )
            response = model.generate_content(messages)
            reply_text = (response.text or "").strip()
            if reply_text:
                return reply_text
            raise ValueError(f"Gemini boş yanıt döndü (model={model_name}).")
        except Exception as exc:
            # Auth errors won't recover by trying another model — fail fast.
            try:
                raise_if_auth_error(exc)
            except GeminiAuthError as auth_err:
                logger.error("Chat auth error: %s", auth_err)
                raise RuntimeError(str(auth_err)) from auth_err
            logger.warning("Chat model failed (model=%s): %s", model_name, exc)
            last_error = exc

    raise RuntimeError("Hiçbir chat modeli yanıt üretemedi.") from last_error
