"""Backend-for-Frontend Gemini wrappers."""
import json
import logging
import re

import google.generativeai as genai
import httpx

from ..config import get_gemini_api_key, settings
from ..models.requests import ChatRequest
from .gemini_client import (
    GeminiAuthError,
    configure_gemini_client,
    raise_if_auth_error,
)

logger = logging.getLogger("technotrack.services.gemini_proxy")

_CHAT_SYSTEM = """
You are Techno Track Assistant, a highly intelligent and helpful shopping guide.
Your goal is to help users make informed purchasing decisions based on the product analysis data provided to you.
Be concise, friendly, and data-driven. Always refer to the provided context data when answering.

PRICE GROUNDING RULES — read carefully:
1. If the context contains a ``price_history`` block (12-month grounded chart
   data produced by the Price Graphic), it is the AUTHORITATIVE source for ANY
   price-related answer. Quote its ``lowest`` / ``highest`` / ``average`` /
   latest-month value verbatim. Do NOT invent or contradict these figures.
2. If the context contains a ``stores`` array (per-retailer prices), you may
   cite those alongside the chart but the chart still wins on disputes.
3. If no ``price_history`` is present AND the user asks about price, you MUST
   call the Google Search tool to look up current Turkish e-commerce prices
   (hepsiburada, trendyol, akakce, cimri, vatanbilgisayar, mediamarkt) before
   giving any number. Never quote a price from training data alone.
4. Other non-price topics (specs, features, comparisons, advice) — answer
   normally from the context and your own knowledge.

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

# Plain "what is the price / how much" style asks — distinct from timing.
# Triggers Google Search only when no price_history is in the context.
_PRICE_PATTERNS = re.compile(
    r"(fiyat[ıi]?|kaç (tl|lira|para)|ne kadar|kaça|"
    r"ucuz|pahal[ıi]|indirim|kampanya|en d[uü]ş[uü]k|en y[uü]ksek|ortalama|"
    r"price|cost|how much|cheapest|most expensive|average price|deal)",
    re.IGNORECASE,
)


def _is_timing_question(user_message: str) -> bool:
    """Heuristic: does the user need fresh web data to answer 'when to buy?'."""
    if not user_message:
        return False
    return bool(_TIMING_PATTERNS.search(user_message))


def _is_price_question(user_message: str) -> bool:
    """Heuristic: is the user asking about a price/cost figure?"""
    if not user_message:
        return False
    return bool(_PRICE_PATTERNS.search(user_message))


def _has_price_history(context_data) -> bool:
    """True when the frontend handed us a populated price_history block."""
    if not isinstance(context_data, dict):
        return False
    ph = context_data.get("price_history")
    if not isinstance(ph, dict):
        return False
    points = ph.get("points")
    return isinstance(points, list) and len(points) > 0


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


_GEMINI_REST_BASE = "https://generativelanguage.googleapis.com/v1beta/models"


def _extract_rest_grounding_citations(data: dict) -> str:
    """Pull Kaynaklar block from a REST generateContent response."""
    try:
        candidates = data.get("candidates") or []
        if not candidates:
            return ""
        meta = candidates[0].get("groundingMetadata") or {}
        chunks = meta.get("groundingChunks") or []
        sources: list[str] = []
        seen: set[str] = set()
        for ch in chunks[:5]:
            web = ch.get("web") or {}
            uri = web.get("uri")
            if not uri or uri in seen:
                continue
            seen.add(uri)
            title = web.get("title") or uri
            sources.append(f"- [{title}]({uri})")
        if not sources:
            return ""
        return "\n\n**Kaynaklar:**\n" + "\n".join(sources)
    except Exception:
        return ""


def _try_chat_model_rest_grounded(model_name: str, messages: list[dict]) -> tuple[str, dict]:
    """Call Gemini via REST with the modern ``google_search`` tool.

    The SDK (google-generativeai 0.8.x) only exposes ``google_search_retrieval``
    which Gemini 2.5+/3 reject — so for grounded chat we go direct to REST,
    same as price_history. Returns (reply_with_citations, raw_response).
    """
    api_key = get_gemini_api_key()
    url = f"{_GEMINI_REST_BASE}/{model_name}:generateContent?key={api_key}"
    body = {
        "systemInstruction": {"parts": [{"text": _CHAT_SYSTEM}]},
        "contents": [
            {"role": m["role"], "parts": [{"text": p} for p in m["parts"]]}
            for m in messages
        ],
        "tools": [{"google_search": {}}],
        "safetySettings": _CHAT_SAFETY_SETTINGS,
        "generationConfig": {
            "temperature": 0.6,
            "topP": 0.95,
            "maxOutputTokens": 2048,
        },
    }
    try:
        resp = httpx.post(url, json=body, timeout=60.0)
    except httpx.HTTPError as exc:
        raise RuntimeError(f"Gemini REST chat failed (model={model_name}): {exc}") from exc

    if resp.status_code != 200:
        raise RuntimeError(
            f"Gemini REST {resp.status_code} (model={model_name}): {resp.text[:300]}"
        )

    data = resp.json()
    candidates = data.get("candidates") or []
    if not candidates:
        raise ValueError(f"Gemini returned no candidates (model={model_name}).")
    parts = (candidates[0].get("content") or {}).get("parts") or []
    text = "".join(p.get("text", "") for p in parts if isinstance(p, dict)).strip()
    if not text:
        raise ValueError(f"Gemini returned empty text (model={model_name}).")
    return text + _extract_rest_grounding_citations(data), data


def _try_chat_model(model_name: str, tools, messages: list[dict]) -> tuple[str, object]:
    """Call a single Gemini chat model via SDK (no Google Search tool here).

    Grounded calls go through ``_try_chat_model_rest_grounded`` instead because
    the SDK doesn't expose the ``google_search`` tool form 2.5+ models require.
    """
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
    # Order matters: primary chat model first, then a distinct Flash fallback
    # (so we don't re-hit the same model on a 429), then Pro as last resort.
    candidate_models = list(dict.fromkeys([
        settings.CHAT_MODEL,
        settings.CHAT_FALLBACK_MODEL,
        settings.FLASH_MODEL,
        settings.PRO_MODEL,
    ]))

    # Ground with Google Search when:
    #   - user asks WHEN to buy (timing), OR
    #   - user asks about price AND no price_history was supplied by the
    #     frontend (i.e. no chart has been generated yet, so we need a live
    #     lookup rather than relying on training data).
    has_chart = _has_price_history(request.context_data)
    use_search = _is_timing_question(request.user_message) or (
        _is_price_question(request.user_message) and not has_chart
    )

    last_error: Exception | None = None
    for model_name in candidate_models:
        # When grounding is desired, try the REST grounded path first; on any
        # error fall back to the plain SDK path so the user still gets text.
        if use_search:
            try:
                reply_text, _ = _try_chat_model_rest_grounded(model_name, messages)
                return reply_text
            except Exception as exc:
                try:
                    raise_if_auth_error(exc)
                except GeminiAuthError as auth_err:
                    logger.error("Chat auth error: %s", auth_err)
                    raise RuntimeError(str(auth_err)) from auth_err
                logger.warning(
                    "Chat grounded (REST) failed (model=%s): %s", model_name, exc
                )
                last_error = exc

        try:
            reply_text, _ = _try_chat_model(model_name, None, messages)
            return reply_text
        except Exception as exc:
            try:
                raise_if_auth_error(exc)
            except GeminiAuthError as auth_err:
                logger.error("Chat auth error: %s", auth_err)
                raise RuntimeError(str(auth_err)) from auth_err
            logger.warning("Chat model failed (model=%s): %s", model_name, exc)
            last_error = exc

    raise RuntimeError("Hiçbir chat modeli yanıt üretemedi.") from last_error
