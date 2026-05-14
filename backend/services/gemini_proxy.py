"""Backend-for-Frontend Gemini wrappers."""
import json
import logging
import re

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
When the user asks about WHEN to buy (timing, deals, upcoming sales, new model releases), use Google Search
to gather fresh real-world data (current promos, expected next-gen launch dates, recent price trends) and
ground your timing advice on those findings. Cite the key facts you used inline (e.g. "Eylül 2025'te yeni
model çıkacağı için ...").
Respond in Turkish.
""".strip()


_TIMING_PATTERNS = re.compile(
    r"(ne zaman|şimdi mi al|şu an mı al|alay[ıi]m m[ıi]|bekleye?y?im mi|"
    r"erteleye?y?im|fiyat d[uü]ş[eü]r m[uü]|yeni model|yeni s[uü]r[uü]m|"
    r"kampanya ne zaman|bu fiyat[a]? de[gğ]er mi|when to buy|"
    r"should i (buy|wait)|right time|good time|upcoming (sale|release)|"
    r"next (model|version)|black friday|cyber monday|prime day|11\.11|sale)",
    re.IGNORECASE,
)


def _is_timing_question(user_message: str) -> bool:
    """Heuristic: does the user need fresh web data to answer 'when to buy?'."""
    if not user_message:
        return False
    return bool(_TIMING_PATTERNS.search(user_message))


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


def _extract_grounding_citations(response) -> str:
    """Pull out source URIs from a grounded response, if any.

    Returns a markdown-formatted 'Kaynaklar' block, or empty string.
    Tolerant to SDK shape changes (different attribute names across versions).
    """
    try:
        candidate = response.candidates[0]
        meta = getattr(candidate, "grounding_metadata", None)
        if not meta:
            return ""
        chunks = getattr(meta, "grounding_chunks", None) or []
        sources = []
        for ch in chunks[:5]:
            web = getattr(ch, "web", None)
            if web and getattr(web, "uri", None):
                title = getattr(web, "title", None) or web.uri
                sources.append(f"- [{title}]({web.uri})")
        if not sources:
            return ""
        return "\n\n**Kaynaklar:**\n" + "\n".join(sources)
    except Exception:
        return ""


_CHAT_GENERATION_CONFIG = genai.GenerationConfig(
    temperature=0.6,
    top_p=0.95,
    max_output_tokens=2048,
)

# Permissive safety filters — shopping advice should not be blocked as harmful.
_CHAT_SAFETY_SETTINGS = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_ONLY_HIGH"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_ONLY_HIGH"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_ONLY_HIGH"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_ONLY_HIGH"},
]


def _try_chat_model(model_name: str, tools, messages: list[dict]) -> tuple[str, object]:
    """Call a single Gemini chat model and return (reply_text, response)."""
    kwargs = {
        "model_name": model_name,
        "system_instruction": _CHAT_SYSTEM,
        "safety_settings": _CHAT_SAFETY_SETTINGS,
    }
    if tools is not None:
        kwargs["tools"] = tools

    model = genai.GenerativeModel(**kwargs)
    response = model.generate_content(
        messages,
        generation_config=_CHAT_GENERATION_CONFIG,
    )
    reply_text = (getattr(response, "text", None) or "").strip()
    if not reply_text:
        raise ValueError(f"Gemini boş yanıt döndü (model={model_name}).")
    return reply_text, response


def generate_chat_reply(request: ChatRequest) -> str:
    """Proxy frontend chat payload to Gemini and return plain reply text."""
    configure_gemini_client()
    messages = _build_chat_messages(request)
    candidate_models = list(dict.fromkeys([
        settings.CHAT_MODEL,
        settings.PRO_MODEL,
        settings.FLASH_MODEL,
    ]))

    use_search = _is_timing_question(request.user_message)
    search_tools = [{"google_search_retrieval": {}}] if use_search else None

    last_error: Exception | None = None
    for model_name in candidate_models:
        # When grounding is desired, try grounded first; on any error retry the
        # same model without tools so plain text answer still goes out.
        tool_attempts = [search_tools, None] if use_search else [None]
        for tools in tool_attempts:
            try:
                reply_text, response = _try_chat_model(model_name, tools, messages)
                if tools is not None:
                    reply_text += _extract_grounding_citations(response)
                return reply_text
            except Exception as exc:
                try:
                    raise_if_auth_error(exc)
                except GeminiAuthError as auth_err:
                    logger.error("Chat auth error: %s", auth_err)
                    raise RuntimeError(str(auth_err)) from auth_err
                logger.warning(
                    "Chat model failed (model=%s, grounded=%s): %s",
                    model_name,
                    tools is not None,
                    exc,
                )
                last_error = exc

    raise RuntimeError("Hiçbir chat modeli yanıt üretemedi.") from last_error
