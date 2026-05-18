"""
Techno Track AI - Application Settings
Yüklenen ortam değişkenleri ve güvenlik yapılandırmaları.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# .env dosyasını backend klasöründen yükle (çalıştırma dizininden bağımsız)
_BASE_DIR = Path(__file__).resolve().parent
_ENV_PATH = _BASE_DIR / ".env"
load_dotenv(_ENV_PATH)


def reload_env() -> None:
    """Re-read backend/.env into os.environ, overriding existing values.

    Allows operators to rotate keys (e.g. GEMINI_API_KEY) without restarting
    the backend — callers that resolve env vars at request-time will see the
    new value on the next call.
    """
    load_dotenv(_ENV_PATH, override=True)

class Settings:
    # ── Google AI ──────────────────────────────
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

    # Model names (env-overridable defaults).
    #
    # POLICY: Every agent defaults to ``gemini-3-flash-preview`` — the
    # highest non-Pro Gemini 3 Flash tier currently exposed on the key — for
    # best quality. Pro variants are skipped because the free-tier key has
    # effectively no Pro quota in practice. Fallbacks step DOWN to
    # ``gemini-2.5-flash`` (the last stable non-lite Flash) so the cascade
    # survives a per-minute quota hit on the Flash-preview with a fresh
    # quota counter on the 2.5 family. Lite variants stay in each agent's
    # cascade as deeper rungs for quota-survival, but are no longer the
    # default starting point. The "PRO_MODEL" / "FLASH_MODEL" names are
    # retained for backwards compatibility with imports — both VALUES now
    # point to the Flash-preview. Operators with a paid plan can override
    # any of these via env vars.
    FLASH_MODEL = os.getenv("FLASH_MODEL", "gemini-3-flash-preview")
    PRO_MODEL = os.getenv("PRO_MODEL", "gemini-3-flash-preview")
    # Analyst's secondary model — kicks in only when PRO_MODEL hits its
    # per-minute quota. Picked from the 2.5 family so the quota counter is
    # independent.
    PRO_FALLBACK_MODEL = os.getenv("PRO_FALLBACK_MODEL", "gemini-2.5-flash")
    # Multi-site product comparison (CompareAgent). Two-tier with no per-model
    # retries keeps the worst case at 2 API calls so a limited quota lasts.
    COMPARE_MODEL = os.getenv("COMPARE_MODEL", "gemini-3-flash-preview")
    COMPARE_FALLBACK_MODEL = os.getenv("COMPARE_FALLBACK_MODEL", "gemini-2.5-flash")
    # Deep review intelligence (Blind Spots / Chronic Issues / Trust Score /
    # Honest Pros-Cons). Defaults to Gemini 3 Flash-preview for maximum
    # answer quality; the cascade in compare_agent falls through to 2.5
    # Flash, then lite tiers if grounding misbehaves (see compare_agent).
    ANALYST_MODEL = os.getenv("ANALYST_MODEL", "gemini-3-flash-preview")
    ANALYST_FALLBACK_MODEL = os.getenv("ANALYST_FALLBACK_MODEL", "gemini-2.5-flash")
    # Vision (product scan & match) — Flash is multimodal and handles
    # brand/variant ID well on clear product shots.
    VISION_MODEL = os.getenv("VISION_MODEL", "gemini-3-flash-preview")
    VISION_FALLBACK_MODEL = os.getenv("VISION_FALLBACK_MODEL", "gemini-2.5-flash")
    # Chat: sub-second replies. CHAT_FALLBACK_MODEL is the non-lite 2.5
    # Flash so a transient failure on the Flash-preview still leaves an
    # answer-capable fallback on an independent quota counter.
    CHAT_MODEL = os.getenv("CHAT_MODEL", "gemini-3-flash-preview")
    CHAT_FALLBACK_MODEL = os.getenv("CHAT_FALLBACK_MODEL", "gemini-2.5-flash")
    # Price-history grounded research model. Flash-preview is the default;
    # cascade in price_history.py keeps a 2.5 Flash rung in reserve and
    # lite variants beyond it because ``google_search`` grounding can flake
    # on flash-lite tiers.
    PRICE_HISTORY_MODEL = os.getenv("PRICE_HISTORY_MODEL", "gemini-3-flash-preview")
    PRICE_HISTORY_FALLBACK_MODEL = os.getenv("PRICE_HISTORY_FALLBACK_MODEL", "gemini-2.5-flash")
    IMAGE_MODEL = os.getenv("IMAGE_MODEL", "imagen-3.0-generate-002")

    # ── Supabase ───────────────────────────────
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY")

    # ── App ────────────────────────────────────
    APP_ENV = os.getenv("APP_ENV", "development")
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    PORT = int(os.getenv("PORT", 8000))

settings = Settings()


def get_gemini_api_key(*, reload: bool = False) -> str:
    """Return the current GEMINI_API_KEY, optionally reloading .env first.

    When ``reload=True`` we re-read backend/.env with override=True so a
    freshly rotated key takes effect without a server restart.
    """
    if reload:
        reload_env()
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("Eksik ortam değişkeni: GEMINI_API_KEY. Lütfen backend/.env dosyasını doldurun.")
    return api_key

# Güvenlik Kontrolü: Gerekli anahtarlar eksikse hata ver
if not settings.GEMINI_API_KEY:
    raise ValueError("Eksik ortam değişkeni: GEMINI_API_KEY. Lütfen backend/.env dosyasını doldurun.")
if not settings.SUPABASE_URL:
    raise ValueError("Eksik ortam değişkeni: SUPABASE_URL. Lütfen backend/.env dosyasını doldurun.")
if not settings.SUPABASE_KEY:
    raise ValueError("Eksik ortam değişkeni: SUPABASE_KEY. Lütfen backend/.env dosyasını doldurun.")
settings.SUPABASE_SERVICE_KEY = settings.SUPABASE_KEY
