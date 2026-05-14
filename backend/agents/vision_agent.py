"""
╔══════════════════════════════════════════════════════════════╗
║            VISION AGENT  –  Gemini 3 Flash (Preview)         ║
╠══════════════════════════════════════════════════════════════╣
║  WHY FLASH 3?                                                ║
║  ▸ Faster + cheaper than Pro for structured JSON ID calls    ║
║  ▸ Native multimodal — no separate embedding step            ║
║  ▸ Strong brand/variant disambiguation at lower latency      ║
║  ▸ Pro 2.5 kept as fallback for ambiguous / low-confidence   ║
║    images where extra reasoning budget pays off.             ║
╚══════════════════════════════════════════════════════════════╝
"""
from __future__ import annotations

import base64
import json
import logging
import re
from typing import Optional

import google.generativeai as genai
from tenacity import retry, stop_after_attempt, wait_exponential

from ..config import settings
from ..models.requests import VisionRequest
from ..models.responses import VisionResponse, AgentStatus, DetectedSpec
from ..services.gemini_client import (
    GeminiAuthError,
    configure_gemini_client,
    raise_if_auth_error,
    retry_on_non_auth_error,
)

logger = logging.getLogger("shopsage.vision_agent")

# ─────────────────────────────────────────────────────────────
# Prompt template
# ─────────────────────────────────────────────────────────────
def _parse_vision_json(raw_text: str) -> dict:
    """Robust JSON extraction from a Gemini response.

    Handles markdown-fenced output (```json ... ```), leading prose, and
    trailing chatter that the model occasionally adds despite instructions.
    """
    if not raw_text:
        raise ValueError("Vision model returned empty text.")

    text = raw_text.strip()

    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL | re.IGNORECASE)
    if fenced:
        return json.loads(fenced.group(1))

    first = text.find("{")
    last = text.rfind("}")
    if first != -1 and last != -1 and last > first:
        return json.loads(text[first : last + 1])

    return json.loads(text)


# NOTE: this template uses a literal "{locale}" sentinel and is rendered with
# str.replace — not str.format — because the JSON example contains real { }
# braces that str.format would mis-parse as placeholders.
_VISION_PROMPT = """
You are a world-class product identification expert.
Analyze the provided image and return ONLY a JSON object (no markdown, no extra text)
with the following structure:

{
  "product_name": "Full product name with variant",
  "search_keywords": "Short, critical keywords for searching (e.g. 'Sony WH-1000XM5')",
  "brand": "Brand name",
  "category": "Electronics | Fashion | Furniture | Other",
  "specs": [
    {"key": "spec name", "value": "spec value"}
  ],
  "confidence": 0.0 to 1.0
}

Be precise. If the image quality is too low to identify the product, set confidence < 0.4
and use null for unknown fields.
Respond in the language corresponding to locale: {locale}.
""".strip()


def _render_vision_prompt(locale: str) -> str:
    return _VISION_PROMPT.replace("{locale}", locale)


# ─────────────────────────────────────────────────────────────
# Core function  (Pro model, with secondary Pro retry)
# ─────────────────────────────────────────────────────────────
@retry(
    stop=stop_after_attempt(2),
    wait=wait_exponential(multiplier=1, min=1, max=4),
    reraise=True,
    retry=retry_on_non_auth_error,
)
async def _call_primary_vision(image_part: dict, locale: str) -> dict:
    """
    AGENT: Vision Agent
    Calls Gemini 3 Flash with the image part and returns parsed JSON.
    Uses tenacity retry with exponential back-off (max 2 attempts).

    Args:
        image_part: Dict with 'mime_type' and 'data' (inline) or 'file_uri'.
        locale:     Language for the model response.

    Returns:
        Parsed JSON dict from the model.

    Raises:
        Exception: Any network or parsing error – caller will retry on Pro fallback.
    """
    configure_gemini_client()
    # Gemini 3 Flash: fast structured-JSON product ID at lower cost than Pro.
    primary = genai.GenerativeModel(model_name=settings.VISION_MODEL)
    prompt = _render_vision_prompt(locale)

    try:
        response = primary.generate_content(
            [prompt, image_part],
            generation_config=genai.GenerationConfig(
                temperature=0.1,       # Near-deterministic for factual extraction
                max_output_tokens=1024,
                response_mime_type="application/json",
            ),
        )
    except Exception as err:
        raise_if_auth_error(err)
        raise
    return _parse_vision_json(getattr(response, "text", "") or "")


async def _call_pro_vision_fallback(image_part: dict, locale: str) -> dict:
    """
    AGENT: Vision Agent – Pro Fallback
    Called when the primary call fails (timeout, parsing error, low confidence).
    Retries on the Pro model with a higher token budget for ambiguous images.

    Args:
        image_part: Same image dict passed to the primary call.
        locale:     Language for the model response.

    Returns:
        Parsed JSON dict from the model.
    """
    logger.warning("Vision fallback triggered → retrying on %s", settings.VISION_FALLBACK_MODEL)
    configure_gemini_client()
    # WHY PRO FALLBACK: Larger output budget and a fresh request when the
    # Flash 3 primary returns low confidence or malformed JSON.
    pro = genai.GenerativeModel(model_name=settings.VISION_FALLBACK_MODEL)
    prompt = _render_vision_prompt(locale)

    try:
        response = pro.generate_content(
            [prompt, image_part],
            generation_config=genai.GenerationConfig(
                temperature=0.1,
                max_output_tokens=1024,
                response_mime_type="application/json",
            ),
        )
    except Exception as err:
        raise_if_auth_error(err)
        raise
    return _parse_vision_json(getattr(response, "text", "") or "")


# ─────────────────────────────────────────────────────────────
# Public entry-point
# ─────────────────────────────────────────────────────────────
async def run_vision_agent(request: VisionRequest) -> VisionResponse:
    """
    AGENT: Vision Agent  (Gemini 3 Flash → Gemini 2.5 Pro fallback)
    ───────────────────────────────────────────────────────────────
    Main entry-point. Accepts a VisionRequest (Base64),
    prepares the image part, calls Gemini 3 Flash as the primary identifier,
    and falls back to Gemini 2.5 Pro when needed.

    Fallback logic:
      Primary call fails / confidence < 0.4    →  Pro fallback is tried once.
      Pro fallback also fails                  →  Returns ERROR status.

    Args:
        request: Validated VisionRequest from the route handler.

    Returns:
        VisionResponse with product details or error information.
    """
    logger.info("VisionAgent → starting (input_type=%s)", request.input_type)

    # ── 1. Prepare image bytes ─────────────────────────────
    image_bytes = base64.b64decode(request.image_data)

    image_part = {
        "mime_type": "image/jpeg",
        "data": base64.b64encode(image_bytes).decode("utf-8"),
    }

    # ── 2. Try primary Gemini 3 Flash call first ──────────
    model_used = settings.VISION_MODEL
    status     = AgentStatus.SUCCESS
    raw_text: Optional[str] = None

    try:
        data = await _call_primary_vision(image_part, request.locale)

        # Trigger fallback if the model is not confident enough
        if (data.get("confidence") or 1.0) < 0.4:
            raise ValueError(f"Primary confidence too low: {data.get('confidence')}")

    except GeminiAuthError as auth_err:
        # Auth errors won't recover by retrying — same API key.
        logger.error("VisionAgent auth error: %s", auth_err)
        return VisionResponse(
            status=AgentStatus.ERROR,
            error_detail=str(auth_err),
        )
    except Exception as primary_err:
        logger.warning("Primary vision failed (%s) → trying Pro fallback", primary_err)
        try:
            data       = await _call_pro_vision_fallback(image_part, request.locale)
            model_used = settings.VISION_FALLBACK_MODEL
            status     = AgentStatus.FALLBACK
        except GeminiAuthError as auth_err:
            logger.error("VisionAgent auth error during Pro fallback: %s", auth_err)
            return VisionResponse(
                status=AgentStatus.ERROR,
                error_detail=str(auth_err),
            )
        except Exception as pro_err:
            logger.error("Pro fallback also failed: %s", pro_err)
            return VisionResponse(
                status=AgentStatus.ERROR,
                error_detail=f"Primary: {primary_err} | Pro fallback: {pro_err}",
            )

    # ── 3. Parse & return ──────────────────────────────────
    specs = [
        DetectedSpec(key=s["key"], value=s["value"])
        for s in (data.get("specs") or [])
    ]

    return VisionResponse(
        status=status,
        product_name=data.get("product_name"),
        search_keywords=data.get("search_keywords"),
        brand=data.get("brand"),
        category=data.get("category"),
        specs=specs,
        confidence=data.get("confidence"),
        raw_text=raw_text,
        model_used=model_used,
    )
