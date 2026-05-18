"""
╔══════════════════════════════════════════════════════════════════════╗
║                      VISION AGENT  –  Pro → Flash Cascade            ║
╠══════════════════════════════════════════════════════════════════════╣
║  Identifies the EXACT product in an image with calibrated confidence.║
║  Cascades through the best multimodal models available — Pro variants║
║  first, then Flash — and returns the first response that meets the   ║
║  confidence threshold (or the highest-confidence response if none do).║
║                                                                      ║
║  Why a cascade?                                                      ║
║   • gemini-3-pro-preview is the strongest at brand/variant ID but is ║
║     quota-walled on free-tier keys (returns 429).                    ║
║   • gemini-2.5-pro and Flash variants pick up when Pro is blocked.   ║
║   • A stronger structured prompt + higher confidence floor (0.55)    ║
║     keeps the agent from confidently returning the wrong model.      ║
╚══════════════════════════════════════════════════════════════════════╝
"""
from __future__ import annotations

import base64
import json
import logging
import re
from datetime import datetime
from typing import Optional

import google.generativeai as genai

from ..models.requests import VisionRequest
from ..models.responses import VisionResponse, AgentStatus, DetectedSpec
from ..services.gemini_client import (
    GeminiAuthError,
    configure_gemini_client,
    is_auth_error,
    is_rate_limit_error,
)

logger = logging.getLogger("technotrack.vision_agent")


# ─────────────────────────────────────────────────────────────────────
# Model cascade — highest-capability first. Mirrors the campaigns route
# so a single Gemini key with Pro quota benefits both surfaces.
# ─────────────────────────────────────────────────────────────────────
_VISION_MODEL_CASCADE: list[str] = [
    "gemini-3-pro-preview",
    "gemini-2.5-pro",
    "gemini-3-flash-preview",
    "gemini-2.5-flash",
    # Flash-Lite is multimodal and has the most generous free-tier RPM, so it
    # rescues rapid-fire requests where every higher-capability model has
    # already hit its per-minute window.
    "gemini-2.5-flash-lite",
]

# Minimum confidence we'll trust for a direct catalog match. Below this we
# either keep trying higher-capability models or hand off to the user.
_TRUST_CONFIDENCE = 0.55

# Image safety: cap the bytes we send to the model. 8 MB is plenty for any
# phone photo and keeps the request body bounded.
_MAX_IMAGE_BYTES = 8 * 1024 * 1024

_ALLOWED_MIME = {"image/jpeg", "image/jpg", "image/png", "image/webp", "image/heic", "image/heif"}


# ─────────────────────────────────────────────────────────────────────
# Prompt — multi-step structured reasoning. Forces the model to read
# visible text first, justify its identification, and calibrate its
# confidence by how much of the model name it could actually pin down.
# ─────────────────────────────────────────────────────────────────────
_VISION_PROMPT = """
You are a world-class product identification expert specializing in consumer
electronics. The current date is {today}. Your job is to identify the EXACT
product shown in the image, NOT a generic category. When the image shows a
flagship phone / laptop / tablet, prefer the NEWEST released generation
consistent with the visible design — Galaxy S25 over S24, MacBook Air M4
over M3, Galaxy Tab S11 over S9 — unless the image clearly shows an older
generation. Wrong-but-confident answers are much worse than admitting
uncertainty.

ANALYSIS STEPS (think through silently, then output JSON):
1. Read ALL visible text in the image: brand logos, model labels, sticker
   codes, words on the box, content on the screen, port labels.
2. Use the visible text PLUS distinctive design cues (camera layout, port
   placement, button arrangement, hinge style, color, proportions) to pin
   down the exact model. Cross-check against the current date when the
   generation is ambiguous.
3. Calibrate confidence:
   • 0.85–1.00 → You can see the model name in the image OR the design is a
     unique flagship you can name with certainty (e.g. "iPhone 15 Pro Max",
     "Sony WH-1000XM5").
   • 0.55–0.84 → Brand and product family are clear, exact variant inferred
     from design but not directly visible.
   • 0.30–0.54 → Only the brand and broad category are confident; model is
     guessed.
   • Below 0.30 → Image is blurry, dark, or contains no recognizable product;
     return null for product_name and search_keywords.

OUTPUT — return ONLY this JSON object, no markdown fences, no extra text:
{
  "visible_text": "All readable text concatenated, or null if none",
  "brand": "Brand name (e.g. 'Apple', 'Samsung', 'Sony') or null",
  "category": "smartphone | laptop | tablet | headphones | console | smartwatch | tv | camera | accessory | other",
  "product_name": "Full canonical product name with variant (English)",
  "search_keywords": "3-6 word search query: brand + family + variant (English)",
  "color": "Single English colour token of the product chassis as it appears in the image (e.g. 'Black', 'White', 'Blue', 'Pink', 'Yellow', 'Green', 'Silver', 'Gold', 'Titanium', 'Graphite', 'Purple', 'Red'). Use null only if the colour is genuinely ambiguous (severe lighting, monochrome render).",
  "specs": [{"key": "spec name", "value": "spec value"}],
  "confidence": 0.0,
  "reasoning": "One sentence citing the concrete visual evidence that decided the ID"
}

RULES — apply strictly:
  • Do NOT invent specs you can't see (no internal codes, no storage sizes
    unless the label shows them). ``color`` IS exempt — you always SEE the
    physical colour of the product, so always fill it.
  • Do NOT guess a model when only the brand is visible — use the brand
    name as ``product_name`` and set confidence ≤0.50.
  • Do NOT return generic class names like "Smartphone" or "Laptop" as the
    product_name — that's a refusal disguised as an answer. Return null
    instead with confidence ≤0.25.
  • ``product_name`` and ``search_keywords`` MUST be in English (used for
    catalog matching). Other free-text fields can be in locale: {locale}.
""".strip()


def _render_vision_prompt(locale: str) -> str:
    today = datetime.utcnow().strftime("%B %Y")
    return _VISION_PROMPT.replace("{locale}", locale).replace("{today}", today)


# ─────────────────────────────────────────────────────────────────────
# Robust JSON extraction
# ─────────────────────────────────────────────────────────────────────
_FENCE_RE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL | re.IGNORECASE)
_TRAILING_COMMA_RE = re.compile(r",(\s*[}\]])")


def _parse_vision_json(raw_text: str) -> dict:
    if not raw_text:
        raise ValueError("Vision model returned empty text.")
    text = raw_text.strip()

    def _loads(s: str) -> dict:
        return json.loads(s, strict=False)

    for candidate in (text, _TRAILING_COMMA_RE.sub(r"\1", text)):
        try:
            return _loads(candidate)
        except json.JSONDecodeError:
            pass

    fenced = _FENCE_RE.search(text)
    if fenced:
        for candidate in (fenced.group(1), _TRAILING_COMMA_RE.sub(r"\1", fenced.group(1))):
            try:
                return _loads(candidate)
            except json.JSONDecodeError:
                continue

    first, last = text.find("{"), text.rfind("}")
    if first != -1 and last > first:
        slice_ = text[first : last + 1]
        for candidate in (slice_, _TRAILING_COMMA_RE.sub(r"\1", slice_)):
            try:
                return _loads(candidate)
            except json.JSONDecodeError as err:
                last_err = err
        raise ValueError(f"JSON parse failed: {last_err}") from last_err

    raise ValueError("No JSON object found in vision response.")


# ─────────────────────────────────────────────────────────────────────
# Single-model call
# ─────────────────────────────────────────────────────────────────────
def _call_vision_model(model_name: str, image_part: dict, locale: str) -> dict:
    """Run one Gemini vision call. Raises on transport / parse failures."""
    configure_gemini_client()
    model = genai.GenerativeModel(model_name=model_name)
    prompt = _render_vision_prompt(locale)

    try:
        response = model.generate_content(
            [prompt, image_part],
            generation_config=genai.GenerationConfig(
                # Near-deterministic so the same image yields stable IDs.
                temperature=0.05,
                top_p=0.9,
                max_output_tokens=1024,
                response_mime_type="application/json",
            ),
        )
    except Exception as err:
        # Auth = hard stop; quota = transient → cascade falls through.
        if is_auth_error(err) and not is_rate_limit_error(err):
            raise GeminiAuthError(
                "Gemini API anahtarı geçersiz veya yetkisiz. backend/.env içindeki "
                "GEMINI_API_KEY değerini yenileyin."
            ) from err
        raise

    text = (getattr(response, "text", None) or "").strip()
    if not text:
        raise ValueError(f"Empty response from {model_name}.")
    return _parse_vision_json(text)


# ─────────────────────────────────────────────────────────────────────
# Public entry-point
# ─────────────────────────────────────────────────────────────────────
async def run_vision_agent(request: VisionRequest) -> VisionResponse:
    """
    Run the cascade. Keep the highest-confidence answer seen across all
    models tried so even if every model returns below threshold the caller
    receives the best available identification.
    """
    logger.info("VisionAgent → start (input_type=%s, mime=%s)", request.input_type, request.mime_type)

    # ── 1. Decode + validate image ────────────────────────────
    try:
        image_bytes = base64.b64decode(request.image_data)
    except Exception as decode_err:
        return VisionResponse(
            status=AgentStatus.ERROR,
            error_detail=f"Could not decode image: {decode_err}",
        )
    if len(image_bytes) > _MAX_IMAGE_BYTES:
        return VisionResponse(
            status=AgentStatus.ERROR,
            error_detail=f"Image too large ({len(image_bytes)} bytes); limit is {_MAX_IMAGE_BYTES}.",
        )

    mime = (request.mime_type or "image/jpeg").lower()
    if mime not in _ALLOWED_MIME:
        # Default to JPEG for unknown types — the model is tolerant of mislabel
        # for common formats but we don't want to send "application/pdf".
        logger.warning("Unsupported mime_type=%s, falling back to image/jpeg.", mime)
        mime = "image/jpeg"

    image_part = {
        "mime_type": mime,
        "data": base64.b64encode(image_bytes).decode("utf-8"),
    }

    # ── 2. Cascade through models, keeping the best response ──
    best: Optional[dict] = None
    best_model: Optional[str] = None
    best_conf: float = -1.0
    errors: list[str] = []

    for model_name in _VISION_MODEL_CASCADE:
        try:
            data = _call_vision_model(model_name, image_part, request.locale)
        except GeminiAuthError as auth_err:
            logger.error("VisionAgent auth error on %s: %s", model_name, auth_err)
            return VisionResponse(
                status=AgentStatus.ERROR,
                error_detail=str(auth_err),
            )
        except Exception as err:
            tag = "quota" if is_rate_limit_error(err) else "error"
            logger.warning("VisionAgent %s on %s: %s", tag, model_name, err)
            errors.append(f"{model_name}: {err}")
            continue

        conf = float(data.get("confidence") or 0.0)
        logger.info("VisionAgent %s -> confidence=%.2f product=%r", model_name, conf, data.get("product_name"))

        if conf > best_conf:
            best, best_model, best_conf = data, model_name, conf

        # Early-exit when this model is already confident enough — no point
        # spending more quota on lower-tier models.
        if conf >= _TRUST_CONFIDENCE:
            break

    if best is None:
        return VisionResponse(
            status=AgentStatus.ERROR,
            error_detail="All vision models failed. " + " | ".join(errors[-3:]),
        )

    # ── 3. Sanitize and return ────────────────────────────────
    specs = []
    for s in (best.get("specs") or []):
        if isinstance(s, dict) and s.get("key"):
            specs.append(DetectedSpec(key=str(s["key"]), value=str(s.get("value") or "")))

    status = AgentStatus.SUCCESS if best_model == _VISION_MODEL_CASCADE[0] else AgentStatus.FALLBACK

    # Refuse to emit obviously-generic "product_name"s — these slip through as
    # high-confidence guesses ("Smartphone", "Laptop") and poison the catalog
    # matcher. Hand-off becomes "we saw brand X, you pick the model".
    product_name = best.get("product_name")
    if product_name and len(str(product_name).split()) <= 1:
        # Single-word answers like "Smartphone", "Laptop", "Phone" are not real
        # product names. Treat as brand-only signal.
        product_name = None

    color_raw = best.get("color")
    color = str(color_raw).strip() if isinstance(color_raw, str) and color_raw.strip() else None

    return VisionResponse(
        status=status,
        product_name=product_name,
        search_keywords=best.get("search_keywords"),
        brand=best.get("brand"),
        category=best.get("category"),
        color=color,
        specs=specs,
        confidence=best_conf if best_conf >= 0 else None,
        raw_text=best.get("reasoning"),
        model_used=best_model or "unknown",
    )
