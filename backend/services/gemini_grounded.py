"""
Shared async Gemini REST helper with Google Search grounding.

WHY THIS EXISTS
───────────────
Three agents (Analyst, Compare Devices, Price History) plus the Chat assistant
all want the same thing: call a Gemini 3 / 2.5 Flash model with the modern
``google_search`` tool, parse JSON safely, and surface the grounding chunks
back as sources. The google-generativeai SDK 0.8.x only exposes the legacy
``google_search_retrieval`` Tool which Gemini 2.5+ models reject, so every
agent has had to bypass the SDK with httpx — duplicated three times.

This module consolidates that into one ``call_gemini`` coroutine and switches
the transport from sync httpx (which blocks the event loop) to
``httpx.AsyncClient`` — concurrent route handlers now stay responsive while a
model call is in flight.

OUTPUT GUARANTEES
─────────────────
* When ``response_json=True`` the helper extracts JSON robustly: direct parse
  first, then fenced ```json blocks, then the first ``{ … }`` slice, with
  trailing-comma repair as a last resort. On total failure the raw text is
  logged so operators can diagnose model-side regressions.
* When grounding is enabled the helper returns a list of unique
  ``{title, uri}`` source dicts pulled from the response's
  ``groundingMetadata``.
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Optional

import httpx

from ..config import get_gemini_api_key
from .gemini_client import (
    GeminiAuthError,
    is_auth_error,
    is_rate_limit_error,
)

logger = logging.getLogger("technotrack.services.gemini_grounded")

_REST_BASE = "https://generativelanguage.googleapis.com/v1beta/models"

# Permissive safety filters — product / shopping analysis should never be
# blocked as harmful.
_DEFAULT_SAFETY = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_ONLY_HIGH"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_ONLY_HIGH"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_ONLY_HIGH"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_ONLY_HIGH"},
]

_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL | re.IGNORECASE)
_TRAILING_COMMA_RE = re.compile(r",(\s*[}\]])")


def _repair_json(s: str) -> str:
    return _TRAILING_COMMA_RE.sub(r"\1", s)


def _extract_json(text: str) -> dict:
    if not text:
        raise ValueError("Empty model response.")
    text = text.strip()

    def _loads(s: str) -> dict:
        return json.loads(s, strict=False)

    for candidate in (text, _repair_json(text)):
        try:
            return _loads(candidate)
        except json.JSONDecodeError:
            continue

    fence = _JSON_FENCE_RE.search(text)
    if fence:
        for candidate in (fence.group(1), _repair_json(fence.group(1))):
            try:
                return _loads(candidate)
            except json.JSONDecodeError:
                continue

    first, last = text.find("{"), text.rfind("}")
    if first != -1 and last > first:
        slice_ = text[first : last + 1]
        for candidate in (slice_, _repair_json(slice_)):
            try:
                return _loads(candidate)
            except json.JSONDecodeError as err:
                last_err = err
        raise ValueError(f"JSON parse failed: {last_err}") from last_err

    raise ValueError("No JSON object found in response.")


def _collect_grounding_sources(data: dict, limit: int = 8) -> list[dict]:
    """Pull (title, uri) tuples from the response's groundingMetadata."""
    try:
        candidates = data.get("candidates") or []
        if not candidates:
            return []
        meta = candidates[0].get("groundingMetadata") or {}
        chunks = meta.get("groundingChunks") or []
        out: list[dict] = []
        seen: set[str] = set()
        for ch in chunks[:limit]:
            web = ch.get("web") or {}
            uri = web.get("uri")
            if not uri or uri in seen:
                continue
            seen.add(uri)
            out.append({"title": web.get("title") or uri, "uri": uri})
        return out
    except Exception:
        return []


def _extract_text(data: dict) -> str:
    """Concatenate every text part of the first candidate."""
    try:
        candidates = data.get("candidates") or []
        if not candidates:
            return ""
        parts = (candidates[0].get("content") or {}).get("parts") or []
        return "".join(p.get("text", "") for p in parts if isinstance(p, dict)).strip()
    except Exception:
        return ""


@dataclass
class GroundedResult:
    """Outcome of a grounded Gemini REST call."""
    text: str
    parsed: Optional[dict]
    sources: list[dict] = field(default_factory=list)
    model_used: str = ""
    raw: dict | None = None


async def _call_once(
    client: httpx.AsyncClient,
    model_name: str,
    *,
    system: str,
    user_prompt: str,
    use_search: bool,
    response_json: bool,
    max_output_tokens: int,
    temperature: float,
    top_p: float,
) -> GroundedResult:
    """Single REST roundtrip — surfaces detailed diagnostics on failure."""
    api_key = get_gemini_api_key()
    url = f"{_REST_BASE}/{model_name}:generateContent?key={api_key}"

    body: dict[str, Any] = {
        "systemInstruction": {"parts": [{"text": system}]},
        "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
        "safetySettings": _DEFAULT_SAFETY,
        "generationConfig": {
            "temperature": temperature,
            "topP": top_p,
            "maxOutputTokens": max_output_tokens,
        },
    }
    if use_search:
        body["tools"] = [{"google_search": {}}]
    # IMPORTANT: when tools=[google_search] is set, Gemini 3 Flash Preview
    # rejects responseMimeType=application/json (causes silent empty text).
    # We rely on the prompt + robust extractor instead.
    if response_json and not use_search:
        body["generationConfig"]["responseMimeType"] = "application/json"

    resp = await client.post(url, json=body)
    if resp.status_code != 200:
        snippet = resp.text[:300]
        # Hard "your key is broken" failures short-circuit the cascade. A plain
        # PERMISSION_DENIED, by contrast, often means "this model has zero
        # quota on your tier" (very common for Pro variants on free keys) —
        # treat those as transient so the cascade can fall through to the
        # next, lower-capability model.
        hard_auth_markers = (
            "API_KEY_INVALID",
            "API key not valid",
            "API key expired",
        )
        if any(m in snippet for m in hard_auth_markers):
            raise GeminiAuthError(
                "Gemini API anahtarı geçersiz veya yetkisiz. backend/.env içindeki "
                "GEMINI_API_KEY değerini yenileyin."
            )
        raise RuntimeError(
            f"Gemini REST {resp.status_code} (model={model_name}): {snippet}"
        )

    data = resp.json()
    text = _extract_text(data)
    sources = _collect_grounding_sources(data) if use_search else []
    parsed: dict | None = None
    if response_json:
        try:
            parsed = _extract_json(text)
        except Exception as err:
            preview = text[:400].replace("\n", " ")
            logger.warning(
                "Gemini JSON extraction failed (model=%s): %s | raw=%r",
                model_name, err, preview,
            )
            raise
    return GroundedResult(
        text=text,
        parsed=parsed,
        sources=sources,
        model_used=model_name,
        raw=data,
    )


async def call_gemini(
    primary_model: str,
    fallback_model: Optional[str],
    *,
    extra_models: Optional[list[str]] = None,
    system: str,
    user_prompt: str,
    use_search: bool = True,
    response_json: bool = True,
    max_output_tokens: int = 4096,
    temperature: float = 0.3,
    top_p: float = 0.95,
    timeout_seconds: float = 90.0,
) -> GroundedResult:
    """
    Multi-tier async Gemini call. Tries ``primary_model`` first; on transient
    failure or quota error, falls back to ``fallback_model`` and then each
    entry in ``extra_models`` in order. The first model that returns a usable
    response wins — useful for "always use the highest-capability model that
    actually works" cascades (e.g. Pro → Pro Preview → Flash → Flash-Lite).

    Auth errors short-circuit the cascade.
    """
    candidates = [m for m in [primary_model, fallback_model, *(extra_models or [])] if m]
    # De-dup while preserving order so ``primary == fallback`` doesn't waste a slot.
    seen: set[str] = set()
    deduped: list[str] = []
    for m in candidates:
        if m in seen:
            continue
        seen.add(m)
        deduped.append(m)
    candidates = deduped
    if not candidates:
        raise ValueError("At least one Gemini model name is required.")

    timeout = httpx.Timeout(connect=10.0, read=timeout_seconds, write=20.0, pool=20.0)
    last_err: Exception | None = None
    async with httpx.AsyncClient(timeout=timeout) as client:
        for idx, model_name in enumerate(candidates):
            try:
                result = await _call_once(
                    client, model_name,
                    system=system,
                    user_prompt=user_prompt,
                    use_search=use_search,
                    response_json=response_json,
                    max_output_tokens=max_output_tokens,
                    temperature=temperature,
                    top_p=top_p,
                )
                if idx > 0:
                    logger.warning(
                        "call_gemini -> fallback model used: %s", model_name
                    )
                return result
            except GeminiAuthError:
                raise
            except Exception as err:
                last_err = err
                if is_rate_limit_error(err):
                    logger.warning("call_gemini quota on %s, trying fallback.", model_name)
                else:
                    logger.warning("call_gemini failed on %s: %s", model_name, err)

    raise RuntimeError(
        f"All Gemini model candidates failed. Last error: {last_err}"
    ) from last_err
