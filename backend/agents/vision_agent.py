"""
╔══════════════════════════════════════════════════════════════╗
║              VISION AGENT  –  Gemini 2.5 Flash              ║
╠══════════════════════════════════════════════════════════════╣
║  WHY FLASH?                                                  ║
║  ▸ Sub-second multimodal inference (target < 800 ms)         ║
║  ▸ Native vision tokens – no separate embedding step         ║
║  ▸ Efficient for high-throughput image-identification tasks  ║
╚══════════════════════════════════════════════════════════════╝
"""
from __future__ import annotations

import base64
import json
import logging
import re
from typing import Optional

import httpx
import google.generativeai as genai
from tenacity import retry, stop_after_attempt, wait_exponential

from ..config import settings
from ..models.requests import VisionRequest, ImageInputType
from ..models.responses import VisionResponse, AgentStatus, DetectedSpec
from ..services.gemini_client import (
    GeminiAuthError,
    configure_gemini_client,
    raise_if_auth_error,
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


# ─────────────────────────────────────────────────────────────
# Core function  (Flash model, with Pro fallback)
# ─────────────────────────────────────────────────────────────
@retry(
    stop=stop_after_attempt(2),
    wait=wait_exponential(multiplier=1, min=1, max=4),
    reraise=True,
    retry=lambda retry_state: not isinstance(
        retry_state.outcome.exception(), GeminiAuthError
    ),
)
async def _call_flash_vision(image_part: dict, locale: str) -> dict:
    """
    AGENT: Vision Agent
    Calls Gemini Flash with the image part and returns parsed JSON.
    Uses tenacity retry with exponential back-off (max 2 attempts).

    Args:
        image_part: Dict with 'mime_type' and 'data' (inline) or 'file_uri'.
        locale:     Language for the model response.

    Returns:
        Parsed JSON dict from the model.

    Raises:
        Exception: Any network or parsing error – caller will fallback to Pro.
    """
    configure_gemini_client()
    # WHY FLASH: Low-latency multimodal model, ideal for real-time image
    # identification. Processes vision tokens natively without extra embedding step.
    flash = genai.GenerativeModel(model_name=settings.FLASH_MODEL)
    prompt = _VISION_PROMPT.format(locale=locale)

    try:
        response = flash.generate_content(
            [prompt, image_part],
            generation_config=genai.GenerationConfig(
                temperature=0.1,       # Near-deterministic for factual extraction
                max_output_tokens=512,
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
    Called when Flash fails (timeout, parsing error, low confidence).
    Gemini Pro is slower but more accurate on ambiguous images.

    Args:
        image_part: Same image dict passed to Flash.
        locale:     Language for the model response.

    Returns:
        Parsed JSON dict from the model.
    """
    logger.warning("Vision fallback triggered → switching to %s", settings.PRO_MODEL)
    configure_gemini_client()
    # WHY PRO FALLBACK: Deeper image reasoning when Flash confidence < 0.4
    # or when Flash returns malformed JSON.
    pro = genai.GenerativeModel(model_name=settings.PRO_MODEL)
    prompt = _VISION_PROMPT.format(locale=locale)

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


async def _fetch_image_bytes(url: str) -> bytes:
    """
    AGENT: Vision Agent – Helper
    Downloads image bytes from a remote URL asynchronously.
    """
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(str(url))
        resp.raise_for_status()
        return resp.content


# ─────────────────────────────────────────────────────────────
# Public entry-point
# ─────────────────────────────────────────────────────────────
async def run_vision_agent(request: VisionRequest) -> VisionResponse:
    """
    AGENT: Vision Agent  (Gemini 2.5 Flash)
    ─────────────────────────────────────
    Main entry-point. Accepts a VisionRequest (Base64 or URL),
    prepares the image part, calls Flash, falls back to Pro if needed,
    and returns a fully validated VisionResponse.

    Fallback logic:
      Flash fails / returns confidence < 0.4  →  Pro is tried once.
      Pro also fails                           →  Returns ERROR status.

    Args:
        request: Validated VisionRequest from the route handler.

    Returns:
        VisionResponse with product details or error information.
    """
    logger.info("VisionAgent → starting (input_type=%s)", request.input_type)

    # ── 1. Prepare image bytes ─────────────────────────────
    if request.input_type == ImageInputType.BASE64:
        image_bytes = base64.b64decode(request.image_data)
    else:
        image_bytes = await _fetch_image_bytes(str(request.image_url))

    image_part = {
        "mime_type": "image/jpeg",
        "data": base64.b64encode(image_bytes).decode("utf-8"),
    }

    # ── 2. Try Flash first ─────────────────────────────────
    model_used = settings.FLASH_MODEL
    status     = AgentStatus.SUCCESS
    raw_text: Optional[str] = None

    try:
        data = await _call_flash_vision(image_part, request.locale)

        # Trigger fallback if Flash is not confident enough
        if (data.get("confidence") or 1.0) < 0.4:
            raise ValueError(f"Flash confidence too low: {data.get('confidence')}")

    except GeminiAuthError as auth_err:
        # Auth errors won't recover by retrying Pro — both use the same key.
        logger.error("VisionAgent auth error: %s", auth_err)
        return VisionResponse(
            status=AgentStatus.ERROR,
            error_detail=str(auth_err),
        )
    except Exception as flash_err:
        logger.warning("Flash vision failed (%s) → trying Pro fallback", flash_err)
        try:
            data       = await _call_pro_vision_fallback(image_part, request.locale)
            model_used = settings.PRO_MODEL
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
                error_detail=f"Flash: {flash_err} | Pro: {pro_err}",
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
