"""Shared async Gemini REST helper with Google Search grounding.

One ``call_gemini`` coroutine used by every agent: it talks to the REST API via
``httpx.AsyncClient`` (the google-generativeai SDK only exposes the legacy
``google_search_retrieval`` tool that Gemini 2.5+ rejects, and is sync-only).
With ``response_json=True`` it extracts JSON robustly (direct parse → fenced
block → first ``{…}`` slice → repair stack) and, when grounded, returns the
unique ``{title, uri}`` sources from ``groundingMetadata``.
"""
from __future__ import annotations

import asyncio
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
# JSON spec allows exactly these chars after a backslash. Anything else inside
# a string literal is an invalid escape sequence and json.loads chokes — Gemini
# happily emits things like "\share-button" or Turkish "\ı" so we have to fix
# them up before parsing.
_VALID_JSON_ESCAPE_CHARS = set('"\\/bfnrtu')


def _repair_json_aggressive(s: str) -> str:
    r"""Repair invalid escape sequences and unescaped control chars inside JSON
    string literals.

    The function is a small state machine that tracks whether we're inside a
    "..." literal. It only edits content within string boundaries so structural
    JSON characters (braces, brackets, colons, commas) are never touched.

    Three repairs are applied:

    1. Invalid backslash escapes — for any backslash whose follow-up byte is
       NOT one of ``" \ / b f n r t u``, we double the backslash so the parser
       reads it as a literal ``\``. This handles the most common Gemini bug
       (``\ı``, ``\s``, ``\share-button``, unescaped Windows paths).
    2. Bare control characters — raw ``\n``, ``\r`` or ``\t`` bytes inside a
       string literal violate the JSON spec. We replace them with their JSON
       escape sequences so multi-line model output stays parseable.
    3. Unescaped embedded quotes — when the model emits a verbatim review
       quote inside a string value (e.g. ``"evidence": "user said "harika""``)
       a naive parser sees the inner ``"`` as a string terminator and trips
       on the next non-structural char ("Expecting ',' delimiter"). We
       lookahead past whitespace: if the next byte is a JSON structural
       delimiter (`,`, `:`, `}`, `]`) or EOF, the quote really did close
       the string; otherwise we escape it as ``\"`` and keep reading.

    Whitespace OUTSIDE strings is preserved verbatim because the parser is
    tolerant of it; we only normalise content the parser would otherwise reject.
    """
    out: list[str] = []
    in_string = False
    i = 0
    n = len(s)
    while i < n:
        c = s[i]

        if not in_string:
            if c == '"':
                in_string = True
            out.append(c)
            i += 1
            continue

        # Inside a string literal.
        if c == '"':
            # Disambiguate "real close" from "embedded quote the model forgot
            # to escape" by peeking past whitespace. A genuine closing quote
            # is followed by one of the JSON structural delimiters (or EOF).
            # Anything else — a letter, a digit, an opening quote — means the
            # model emitted a verbatim quote inside the value and we need to
            # escape it instead of terminating the string here.
            j = i + 1
            while j < n and s[j] in " \t\r\n":
                j += 1
            nxt = s[j] if j < n else ""
            if j >= n or nxt in (",", ":", "}", "]"):
                in_string = False
                out.append(c)
                i += 1
                continue
            out.append("\\\"")
            i += 1
            continue

        if c == "\\":
            nxt = s[i + 1] if i + 1 < n else ""
            if nxt in _VALID_JSON_ESCAPE_CHARS:
                # Valid escape — copy verbatim. For \uXXXX we also need to copy
                # the 4 hex digits, but the parser will validate them itself;
                # if they're malformed we can't trivially repair without
                # ambiguity, so we leave that case to the outer fallback.
                out.append(c)
                out.append(nxt)
                i += 2
                continue
            # Invalid escape → double the backslash so it becomes literal.
            out.append("\\\\")
            i += 1
            continue

        if c == "\n":
            out.append("\\n"); i += 1; continue
        if c == "\r":
            out.append("\\r"); i += 1; continue
        if c == "\t":
            out.append("\\t"); i += 1; continue
        # Other control bytes (< 0x20) the parser also rejects; escape them.
        if ord(c) < 0x20:
            out.append("\\u%04x" % ord(c)); i += 1; continue

        out.append(c)
        i += 1
    return "".join(out)


def _repair_json(s: str) -> str:
    """Cheap structural repairs (only trailing commas). Combine with
    ``_repair_json_aggressive`` for content-level fixes when needed.
    """
    return _TRAILING_COMMA_RE.sub(r"\1", s)


def _try_parse_with_repairs(s: str) -> Optional[dict]:
    """Try a stack of progressively more aggressive repairs. Returns the
    parsed dict on first success, None if every pass fails.
    """
    candidates = (
        s,
        _repair_json(s),
        _repair_json_aggressive(s),
        _repair_json_aggressive(_repair_json(s)),
    )
    for c in candidates:
        try:
            return json.loads(c, strict=False)
        except json.JSONDecodeError:
            continue
    return None


def _extract_json(text: str) -> dict:
    if not text:
        raise ValueError("Empty model response.")
    text = text.strip()

    # Pass 1 — raw text as-is, with repair stack.
    parsed = _try_parse_with_repairs(text)
    if parsed is not None:
        return parsed

    # Pass 2 — fenced ```json block.
    fence = _JSON_FENCE_RE.search(text)
    if fence:
        parsed = _try_parse_with_repairs(fence.group(1))
        if parsed is not None:
            return parsed

    # Pass 3 — first {...} slice.
    first, last = text.find("{"), text.rfind("}")
    if first != -1 and last > first:
        sliced = text[first : last + 1]
        parsed = _try_parse_with_repairs(sliced)
        if parsed is not None:
            return parsed
        # Diagnostic: surface the exact JSON error so logs are actionable.
        try:
            json.loads(_repair_json_aggressive(sliced), strict=False)
        except json.JSONDecodeError as err:
            raise ValueError(f"JSON parse failed: {err}") from err

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
        err = RuntimeError(
            f"Gemini REST {resp.status_code} (model={model_name}): {snippet}"
        )
        # Two flavours of "try again later":
        #   503 UNAVAILABLE = traffic shaper spike. Usually clears in 2-3s, so
        #     worth one same-model retry before falling through.
        #   429 Too Many Requests = quota window (per-minute RPM). Won't clear
        #     in 2s; retrying the same model wastes another HTTP round-trip
        #     for nothing. Mark as quota-limited and skip retry — the cascade
        #     immediately moves to the next model, which has independent RPM.
        err.is_transient = resp.status_code == 503 or "UNAVAILABLE" in snippet
        err.is_quota_limited = resp.status_code == 429
        raise err

    data = resp.json()
    text = _extract_text(data)
    sources = _collect_grounding_sources(data) if use_search else []
    parsed: dict | None = None
    if response_json:
        try:
            parsed = _extract_json(text)
        except Exception as err:
            # Bigger preview — when parsing fails at e.g. char 6650 the prior
            # 400-char snippet was useless. 2000 chars is large enough to
            # inspect the offending region in logs without flooding them, and
            # we strip raw newlines so the message stays on one line.
            preview = text[:2000].replace("\n", " ").replace("\r", " ")
            logger.warning(
                "Gemini JSON extraction failed (model=%s, response_len=%d): %s | raw=%r",
                model_name, len(text), err, preview,
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
            # One retry per model when the failure is transient (503/429 from
            # Google's traffic shaper). Brief backoff before the second try —
            # demand spikes are usually < 3 seconds.
            for attempt in range(2):
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
                    if idx > 0 or attempt > 0:
                        logger.warning(
                            "call_gemini -> recovered with model=%s (attempt=%d)",
                            model_name, attempt + 1,
                        )
                    return result
                except GeminiAuthError:
                    raise
                except Exception as err:
                    last_err = err
                    transient_overload = bool(getattr(err, "is_transient", False))
                    quota_limited = bool(getattr(err, "is_quota_limited", False)) or is_rate_limit_error(err)
                    # Only 503/UNAVAILABLE warrants a same-model retry. A 429
                    # quota window won't clear in 2 seconds, so don't waste
                    # the second HTTP round-trip on it.
                    if transient_overload and not quota_limited and attempt == 0:
                        logger.warning(
                            "call_gemini transient on %s — retrying once after 2s backoff.",
                            model_name,
                        )
                        await asyncio.sleep(2.0)
                        continue  # Retry the same model once.
                    if quota_limited:
                        logger.warning("call_gemini quota on %s, trying fallback.", model_name)
                    elif transient_overload:
                        logger.warning("call_gemini overload on %s, trying fallback.", model_name)
                    else:
                        logger.warning("call_gemini failed on %s: %s", model_name, err)
                    break  # Stop retrying this model, move on to the next.

    # Friendlier UI message — different copy for "everyone's busy" vs "we hit
    # OUR per-minute quota with this key". The latter is the more common case
    # during demo bursts.
    if last_err is not None:
        if getattr(last_err, "is_quota_limited", False) or is_rate_limit_error(last_err):
            raise RuntimeError(
                "Your Gemini key hit its per-minute quota. Please wait about a "
                "minute and try again — the analysis will then run normally and "
                "subsequent calls for the same product return instantly from cache."
            ) from last_err
        if getattr(last_err, "is_transient", False) or "UNAVAILABLE" in str(last_err):
            raise RuntimeError(
                "Gemini's analysis models are overloaded right now. Please try again "
                "in a few seconds."
            ) from last_err

    raise RuntimeError(
        f"All Gemini model candidates failed. Last error: {last_err}"
    ) from last_err
