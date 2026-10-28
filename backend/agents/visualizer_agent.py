"""
╔══════════════════════════════════════════════════════════════╗
║   VISUALIZER AGENT  –  Gemini native image generation        ║
╠══════════════════════════════════════════════════════════════╣
║  MODEL: IMAGE_MODEL ("Nano Banana" family) with              ║
║  IMAGE_FALLBACK_MODEL. Image models have NO free-tier quota  ║
║  — this agent needs a billed Gemini key and otherwise        ║
║  returns a clear ERROR response.                             ║
║                                                              ║
║  TRIGGER CONDITIONS:                                         ║
║  ▸ Category == "fashion"   → outfit combination image        ║
║  ▸ Category == "furniture" → room placement / interior shot  ║
╚══════════════════════════════════════════════════════════════╝
"""
from __future__ import annotations

import base64
import logging

import httpx

from ..config import get_gemini_api_key, settings
from ..db import save_generated_image
from ..models.requests import StyleRequest, ProductCategory
from ..models.responses import StyleResponse, AgentStatus
from ..services.gemini_client import (
    GeminiAuthError,
    raise_if_auth_error,
)

logger = logging.getLogger("technotrack.visualizer_agent")

_REST_BASE = "https://generativelanguage.googleapis.com/v1beta/models"


async def _generate_image(prompt: str) -> tuple[bytes, str, str]:
    """Return (image_bytes, mime_type, model_used), trying IMAGE_MODEL first."""
    api_key = get_gemini_api_key(reload=True)
    body = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"responseModalities": ["TEXT", "IMAGE"]},
    }
    errors: list[str] = []
    models = list(dict.fromkeys(m for m in (settings.IMAGE_MODEL, settings.IMAGE_FALLBACK_MODEL) if m))
    async with httpx.AsyncClient(timeout=httpx.Timeout(120.0, connect=10.0)) as client:
        for model in models:
            resp = await client.post(
                f"{_REST_BASE}/{model}:generateContent",
                json=body,
                headers={"x-goog-api-key": api_key},
            )
            if resp.status_code != 200:
                snippet = resp.text[:300]
                raise_if_auth_error(RuntimeError(snippet))
                if resp.status_code == 429 and "FreeTier" in resp.text:
                    errors.append(f"{model}: image generation has no free-tier quota (billing required)")
                else:
                    errors.append(f"{model}: HTTP {resp.status_code} {snippet[:120]}")
                continue
            parts = ((resp.json().get("candidates") or [{}])[0].get("content") or {}).get("parts") or []
            for part in parts:
                inline = part.get("inlineData")
                if inline and inline.get("data"):
                    return base64.b64decode(inline["data"]), inline.get("mimeType") or "image/png", model
            errors.append(f"{model}: response contained no image")
    raise RuntimeError("Image generation failed. " + " | ".join(errors))

# ─────────────────────────────────────────────────────────────
# Prompt templates per category
# ─────────────────────────────────────────────────────────────
_FASHION_PROMPT = (
    "A high-fashion editorial photograph showing a complete outfit combination "
    "featuring {product_name}. "
    "{style_context} "
    "Professional studio lighting, white background, Vogue magazine style. "
    "No text, no watermarks, photorealistic."
)

_FURNITURE_PROMPT = (
    "A professional interior design photograph of a modern living room featuring "
    "{product_name} as the focal piece. "
    "{style_context} "
    "Natural lighting, award-winning interior photography, 4K detail. "
    "No people, no text, no watermarks."
)


def _build_prompt(request: StyleRequest) -> str:
    """
    AGENT: Visualizer Agent – Helper
    Selects and fills the appropriate prompt template based on product category.
    """
    ctx = request.style_context or ""
    if request.category == ProductCategory.FASHION:
        return _FASHION_PROMPT.format(product_name=request.product_name, style_context=ctx)
    return _FURNITURE_PROMPT.format(product_name=request.product_name, style_context=ctx)


# ─────────────────────────────────────────────────────────────
# Public entry-point
# ─────────────────────────────────────────────────────────────
async def run_visualizer_agent(request: StyleRequest) -> StyleResponse:
    """
    AGENT: Visualizer Agent  (Gemini native image generation via REST)
    ─────────────────────────────────────────────────────
    Generates a contextual product image:
      • Fashion → editorial outfit combo photo
      • Furniture → room placement interior shot

    Uploads the result to Supabase Storage and returns the public URL.
    Falls back to Base64 payload if the upload fails.

    Args:
        request: Validated StyleRequest (category must be fashion or furniture).

    Returns:
        StyleResponse with image_url or image_base64 on success.
    """
    logger.info(
        "VisualizerAgent → starting (product=%s, category=%s)",
        request.product_name, request.category,
    )

    prompt = _build_prompt(request)
    logger.debug("Visualizer prompt: %s", prompt[:120])

    try:
        image_bytes, _mime, model_used = await _generate_image(prompt)

        # ── Try to upload to Supabase Storage ────────────────
        try:
            public_url = await save_generated_image(request.product_name, image_bytes)
            return StyleResponse(
                status=AgentStatus.SUCCESS,
                image_url=public_url,
                prompt_used=prompt,
                model_used=model_used,
            )
        except Exception as upload_err:
            # Storage upload failed → return Base64 inline
            logger.warning("Supabase upload failed, falling back to Base64: %s", upload_err)
            b64 = base64.b64encode(image_bytes).decode("utf-8")
            return StyleResponse(
                status=AgentStatus.FALLBACK,
                image_base64=b64,
                prompt_used=prompt,
                model_used=model_used,
                error_detail=f"Storage upload failed: {upload_err}",
            )

    except GeminiAuthError as auth_err:
        logger.error("VisualizerAgent auth error: %s", auth_err)
        return StyleResponse(
            status=AgentStatus.ERROR,
            error_detail=str(auth_err),
        )
    except Exception as gen_err:
        logger.error("VisualizerAgent generation failed: %s", gen_err)
        return StyleResponse(
            status=AgentStatus.ERROR,
            error_detail=str(gen_err),
        )
