"""Shared async Gemini REST helper with optional Google Search grounding.

One ``call_gemini`` coroutine used by every agent: it talks to the REST API via
``httpx.AsyncClient`` (the google-generativeai SDK only exposes the legacy
``google_search_retrieval`` tool that Gemini 2.5+ rejects, and is sync-only).
With ``response_json=True`` it extracts JSON robustly (direct parse → fenced
block → first ``{…}`` slice → repair stack) and, when grounded, returns the
unique ``{title, uri}`` sources from ``groundingMetadata``.

Free-tier resilience:
  • Models whose quota is exhausted (429 + RetryInfo) or that are retired
    (404) are skipped until Google says they are usable again, so a spent
    20-requests/day counter costs no extra round-trip per call.
  • Google Search grounding has no free-tier quota on Gemini 3.x. When a
    grounded call is refused, the same model is retried without the tool
    (using the caller's ``offline_*`` prompts) and search stays disabled for
    ``_SEARCH_RECHECK_SECONDS`` before it is probed again.
"""
from __future__ import annotations

import base64
import json
import logging
import re
import time
from dataclasses import dataclass, field
from typing import Any, Optional

import httpx

from ..config import get_gemini_api_key, settings
from .gemini_client import (
    GeminiAuthError,
    is_auth_error,
    is_rate_limit_error,
)

logger = logging.getLogger("technotrack.services.gemini_grounded")

_REST_BASE = "https://generativelanguage.googleapis.com/v1beta/models"

# model name → monotonic timestamp until which the model is skipped.
_MODEL_COOLDOWN_UNTIL: dict[str, float] = {}
# Retired models ("no longer available to new users") are re-checked rarely.
_UNAVAILABLE_MODEL_COOLDOWN_SECONDS = 6 * 60 * 60
# 429 without a RetryInfo hint: assume a per-minute window.
_DEFAULT_QUOTA_COOLDOWN_SECONDS = 60.0
# An overloaded (503) or hanging model is skipped briefly so the next calls
# of the same request flow don't wait on it again.
_OVERLOAD_COOLDOWN_SECONDS = 45.0
# Read timeout for every rung except the last one in a cascade.
_NON_FINAL_TIMEOUT_SECONDS = 60.0
_search_disabled_until: float = 0.0
_SEARCH_RECHECK_SECONDS = 30 * 60


def _model_cooling_down(model_name: str) -> bool:
    return _MODEL_COOLDOWN_UNTIL.get(model_name, 0.0) > time.monotonic()


def _note_model_failure(model_name: str, err: Exception) -> None:
    """Park a model that Google told us not to call for a while."""
    cooldown: float | None = None
    if getattr(err, "is_model_unavailable", False):
        cooldown = _UNAVAILABLE_MODEL_COOLDOWN_SECONDS
    elif getattr(err, "is_quota_limited", False):
        cooldown = getattr(err, "retry_after", None) or _DEFAULT_QUOTA_COOLDOWN_SECONDS
    if cooldown:
        _MODEL_COOLDOWN_UNTIL[model_name] = time.monotonic() + cooldown
        logger.warning("Gemini model %s parked for %.0fs.", model_name, cooldown)


def search_available() -> bool:
    """False while Google Search grounding is known to be refused for this key."""
    return _search_disabled_until <= time.monotonic()


def _disable_search() -> None:
    global _search_disabled_until
    _search_disabled_until = time.monotonic() + _SEARCH_RECHECK_SECONDS
    logger.warning(
        "Google Search grounding refused for this key (no free-tier quota); "
        "continuing ungrounded for %d minutes.", _SEARCH_RECHECK_SECONDS // 60,
    )


def _parse_error_body(resp: httpx.Response) -> tuple[Optional[float], bool]:
    """Return (retry_after_seconds, has_quota_violations) from an error body."""
    retry_after: Optional[float] = None
    has_violations = False
    try:
        details = resp.json().get("error", {}).get("details", [])
    except Exception:
        return None, False
    for det in details:
        if det.get("violations"):
            has_violations = True
        delay = det.get("retryDelay")
        if isinstance(delay, str) and delay.endswith("s"):
            try:
                retry_after = float(delay[:-1])
            except ValueError:
                pass
    return retry_after, has_violations

# Permissive safety filters — product / shopping analysis should never be
# blocked as harmful.
_DEFAULT_SAFETY = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_ONLY_HIGH"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_ONLY_HIGH"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_ONLY_HIGH"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_ONLY_HIGH"},
]

def _supports_thinking_level(model_name: str) -> bool:
    """``thinkingLevel`` is a Gemini 3.x knob. The 2.5 family hard-rejects it
    with HTTP 400 "Thinking level is not supported for this model.", so a
    cascade that falls back from a 3.x primary to a 2.5 model must attach the
    param ONLY while the active model is a Gemini 3 member.
    """
    name = (model_name or "").lower()
    return name.startswith("gemini-3") or name.startswith("models/gemini-3")


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
    """Outcome of a Gemini REST call."""
    text: str
    parsed: Optional[dict]
    sources: list[dict] = field(default_factory=list)
    model_used: str = ""
    raw: dict | None = None
    # True when the google_search tool was attached to the successful call.
    search_used: bool = False


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
    thinking_level: Optional[str] = None,
    images: Optional[list[tuple[str, bytes]]] = None,
    history: Optional[list[dict]] = None,
) -> GroundedResult:
    """Single REST roundtrip — surfaces detailed diagnostics on failure."""
    api_key = get_gemini_api_key()
    url = f"{_REST_BASE}/{model_name}:generateContent"

    parts: list[dict[str, Any]] = [{"text": user_prompt}]
    for mime_type, data in images or []:
        parts.append({"inlineData": {"mimeType": mime_type, "data": base64.b64encode(data).decode("ascii")}})
    contents = [
        {"role": turn["role"], "parts": [{"text": turn["text"]}]} for turn in history or []
    ]
    contents.append({"role": "user", "parts": parts})
    body: dict[str, Any] = {
        "contents": contents,
        "safetySettings": _DEFAULT_SAFETY,
        "generationConfig": {
            "temperature": temperature,
            "topP": top_p,
            "maxOutputTokens": max_output_tokens,
        },
    }
    if system:
        body["systemInstruction"] = {"parts": [{"text": system}]}
    # Gemini 3.x reasoning models spend part of the output-token budget on an
    # internal "thinking" pass before the answer. For a structured JSON
    # extraction that reasoning is mostly wasted latency (and can starve the
    # JSON of tokens at small budgets), so callers can pin a lower level.
    # Attached 3.x-only — see _supports_thinking_level — so it stays safe when
    # the cascade falls back to a 2.5 model that rejects the param.
    if thinking_level and _supports_thinking_level(model_name):
        body["generationConfig"]["thinkingConfig"] = {"thinkingLevel": thinking_level}
    if use_search:
        body["tools"] = [{"google_search": {}}]
    # IMPORTANT: when tools=[google_search] is set, Gemini 3 Flash Preview
    # rejects responseMimeType=application/json (causes silent empty text).
    # We rely on the prompt + robust extractor instead.
    if response_json and not use_search:
        body["generationConfig"]["responseMimeType"] = "application/json"

    # Key goes in a header, not the query string, so it never lands in logs.
    resp = await client.post(url, json=body, headers={"x-goog-api-key": api_key})
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
        retry_after, has_violations = _parse_error_body(resp)
        err.is_transient = resp.status_code == 503 or "UNAVAILABLE" in snippet
        err.is_quota_limited = resp.status_code == 429
        err.retry_after = retry_after
        err.is_model_unavailable = resp.status_code == 404
        # A grounded 429 that names no model quota means the key has no
        # google_search allowance at all (free tier on Gemini 3.x).
        err.is_search_unavailable = use_search and resp.status_code == 429 and not has_violations
        raise err

    data = resp.json()
    text = _extract_text(data)
    if not text:
        candidate = (data.get("candidates") or [{}])[0]
        err = RuntimeError(
            f"Gemini returned no text (model={model_name}, finishReason={candidate.get('finishReason')})."
        )
        err.is_transient = False
        raise err
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
        search_used=use_search,
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
    thinking_level: Optional[str] = None,
    images: Optional[list[tuple[str, bytes]]] = None,
    history: Optional[list[dict]] = None,
    offline_system: Optional[str] = None,
    offline_prompt: Optional[str] = None,
) -> GroundedResult:
    """
    Multi-tier async Gemini call. Tries ``primary_model`` first; on transient
    failure or quota error, falls back to ``fallback_model`` and then each
    entry in ``extra_models`` (default: ``settings.EXTRA_FALLBACK_MODELS``)
    in order. The first model that returns a usable response wins.

    ``images`` are ``(mime_type, bytes)`` pairs sent after the prompt.
    ``history`` holds earlier chat turns as ``{"role": "user"|"model", "text": ...}``.
    ``offline_system`` / ``offline_prompt`` replace the grounded prompts when
    Google Search is unavailable, so callers never ask the model to "search"
    without a search tool. ``result.search_used`` tells which variant ran.

    Auth errors short-circuit the cascade.
    """
    # Re-read backend/.env so a rotated GEMINI_API_KEY applies without a restart.
    get_gemini_api_key(reload=True)
    if extra_models is None:
        extra_models = settings.EXTRA_FALLBACK_MODELS
    candidates = [m for m in [primary_model, fallback_model, *extra_models] if m]
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

    active = [m for m in candidates if not _model_cooling_down(m)]
    if not active:
        err = RuntimeError(f"Every Gemini model is out of quota for now: {', '.join(candidates)}")
        err.is_quota_limited = True
        raise err
    skipped = [m for m in candidates if m not in active]
    if skipped:
        logger.info("call_gemini skipping parked models: %s", ", ".join(skipped))

    search = use_search and search_available()
    last_err: Exception | None = None
    async with httpx.AsyncClient() as client:
        for idx, model_name in enumerate(active):
            # A congested preview model can hang without answering; cap every
            # rung except the last so one stuck model can't eat the request.
            is_last = idx == len(active) - 1
            read_timeout = timeout_seconds if is_last else min(timeout_seconds, _NON_FINAL_TIMEOUT_SECONDS)
            client.timeout = httpx.Timeout(connect=10.0, read=read_timeout, write=20.0, pool=20.0)
            while True:
                try:
                    result = await _call_once(
                        client, model_name,
                        system=system if search else (offline_system or system),
                        user_prompt=user_prompt if search else (offline_prompt or user_prompt),
                        use_search=search,
                        response_json=response_json,
                        max_output_tokens=max_output_tokens,
                        temperature=temperature,
                        top_p=top_p,
                        thinking_level=thinking_level,
                        images=images,
                        history=history,
                    )
                    if idx > 0:
                        logger.warning("call_gemini -> recovered with model=%s", model_name)
                    return result
                except GeminiAuthError:
                    raise
                except Exception as err:
                    last_err = err
                    if search and getattr(err, "is_search_unavailable", False):
                        # Same model, no tool — the model itself is fine.
                        _disable_search()
                        search = False
                        continue
                    _note_model_failure(model_name, err)
                    timed_out = isinstance(err, httpx.TimeoutException)
                    transient_overload = timed_out or bool(getattr(err, "is_transient", False))
                    quota_limited = bool(getattr(err, "is_quota_limited", False)) or is_rate_limit_error(err)
                    if quota_limited:
                        logger.warning("call_gemini quota on %s, trying fallback.", model_name)
                    elif transient_overload:
                        # Retrying an overloaded (503) or hanging model right
                        # away almost never helps; park it and move down.
                        _MODEL_COOLDOWN_UNTIL[model_name] = time.monotonic() + _OVERLOAD_COOLDOWN_SECONDS
                        logger.warning(
                            "call_gemini %s on %s, parked for %.0fs, trying fallback.",
                            "timeout" if timed_out else "overload", model_name, _OVERLOAD_COOLDOWN_SECONDS,
                        )
                    else:
                        logger.warning("call_gemini failed on %s: %s: %s", model_name, type(err).__name__, err)
                    break  # Move on to the next model.

    # Friendlier UI message — different copy for "everyone's busy" vs "we hit
    # OUR per-minute quota with this key". The latter is the more common case
    # during demo bursts.
    if last_err is not None:
        if getattr(last_err, "is_quota_limited", False) or is_rate_limit_error(last_err):
            raise RuntimeError(
                "Every Gemini model on this key is out of quota right now. Please "
                "wait a minute and try again — per-minute limits reset quickly, and "
                "repeat analyses of the same product are served from cache."
            ) from last_err
        if getattr(last_err, "is_transient", False) or "UNAVAILABLE" in str(last_err):
            raise RuntimeError(
                "Gemini's analysis models are overloaded right now. Please try again "
                "in a few seconds."
            ) from last_err

    raise RuntimeError(
        f"All Gemini model candidates failed. Last error: {last_err}"
    ) from last_err
