"""
╔══════════════════════════════════════════════════════════════╗
║         VISUALIZER AGENT  –  Imagen 3 (Google AI)           ║
╠══════════════════════════════════════════════════════════════╣
║  WHY IMAGEN 3?                                               ║
║  ▸ State-of-the-art photorealistic image synthesis           ║
║  ▸ Understands spatial context: furniture layout, fashion    ║
║    outfit combinations, color harmony                        ║
║  ▸ Supports negative prompting for clean, ad-free outputs   ║
║                                                              ║
║  TRIGGER CONDITIONS:                                         ║
║  ▸ Category == "fashion"   → outfit combination image        ║
║  ▸ Category == "furniture" → room placement / interior shot  ║
╚══════════════════════════════════════════════════════════════╝
"""
from __future__ import annotations

import base64
import logging

import google.generativeai as genai

from ..config import settings
from ..db import save_generated_image
from ..models.requests import StyleRequest, ProductCategory
from ..models.responses import StyleResponse, AgentStatus
from ..services.gemini_client import (
    GeminiAuthError,
    configure_gemini_client,
    raise_if_auth_error,
)

logger = logging.getLogger("shopsage.visualizer_agent")

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
    AGENT: Visualizer Agent  (Imagen 3 via Google AI SDK)
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
        configure_gemini_client()
        # WHY IMAGEN 3: Photorealistic synthesis with spatial awareness.
        # The model understands fashion styling and interior design natively.
        imagen = genai.ImageGenerationModel(settings.IMAGE_MODEL)
        try:
            result = imagen.generate_images(
                prompt=prompt,
                number_of_images=1,
                safety_filter_level="block_only_high",
                person_generation="dont_allow",
            )
        except Exception as err:
            raise_if_auth_error(err)
            raise

        image_bytes: bytes = result.images[0]._image_bytes

        # ── Try to upload to Supabase Storage ────────────────
        try:
            public_url = await save_generated_image(request.product_name, image_bytes)
            return StyleResponse(
                status=AgentStatus.SUCCESS,
                image_url=public_url,
                prompt_used=prompt,
            )
        except Exception as upload_err:
            # Storage upload failed → return Base64 inline
            logger.warning("Supabase upload failed, falling back to Base64: %s", upload_err)
            b64 = base64.b64encode(image_bytes).decode("utf-8")
            return StyleResponse(
                status=AgentStatus.FALLBACK,
                image_base64=b64,
                prompt_used=prompt,
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
