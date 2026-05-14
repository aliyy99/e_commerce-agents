"""Gemini client bootstrap helpers.

Supports hot-rotation of GEMINI_API_KEY: each call to
``configure_gemini_client()`` re-reads backend/.env (override=True) and only
issues ``genai.configure(...)`` when the resolved key actually changed.
"""
from __future__ import annotations

import logging

import google.generativeai as genai

from ..config import get_gemini_api_key

logger = logging.getLogger("shopsage.services.gemini_client")

_AUTH_ERROR_MARKERS = (
    "API_KEY_INVALID",
    "API key expired",
    "API key not valid",
    "PERMISSION_DENIED",
)

_last_configured_key: str | None = None


class GeminiAuthError(RuntimeError):
    """Raised when Gemini rejects the current API key.

    Distinct from transient errors so callers can short-circuit retries and
    surface an actionable message to the user/operator.
    """


def configure_gemini_client() -> str:
    """Re-read .env and configure the Gemini SDK if the key changed.

    Returns the currently active API key (useful for callers that want to log
    a partial fingerprint).
    """
    global _last_configured_key
    api_key = get_gemini_api_key(reload=True)
    if api_key != _last_configured_key:
        genai.configure(api_key=api_key)
        if _last_configured_key is not None:
            logger.info("Gemini API key rotated; SDK re-configured.")
        _last_configured_key = api_key
    return api_key


def is_auth_error(exc: BaseException) -> bool:
    """Return True if ``exc`` looks like a Gemini authentication failure."""
    message = str(exc)
    return any(marker in message for marker in _AUTH_ERROR_MARKERS)


_AUTH_USER_MESSAGE = (
    "Gemini API anahtarı geçersiz veya süresi dolmuş. "
    "Lütfen backend/.env içindeki GEMINI_API_KEY değerini güncelleyin; "
    "yeni anahtar bir sonraki istekte otomatik olarak yüklenecektir."
)


def raise_if_auth_error(exc: BaseException) -> None:
    """If ``exc`` is an auth failure, raise GeminiAuthError; otherwise no-op."""
    if is_auth_error(exc):
        raise GeminiAuthError(_AUTH_USER_MESSAGE) from exc
