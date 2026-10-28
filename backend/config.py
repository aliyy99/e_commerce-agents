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

def _env_list(name: str, default: str) -> list[str]:
    """Comma-separated env var → list of non-empty, stripped model names."""
    return [m.strip() for m in os.getenv(name, default).split(",") if m.strip()]


class Settings:
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

    # Model names (env-overridable defaults).
    #
    # Free-tier ladder, verified against the Gemini API on 2026-10-28:
    #   1. gemini-3.8-flash  — strongest model with free-tier quota, but only
    #      20 requests/day (shared with gemini-3.7-flash) and frequent 503
    #      "high demand" responses.
    #   2. gemini-3.6-flash  — next best; gemini-3.5-flash is served by it.
    #   3. EXTRA_FALLBACK_MODELS — older / lite Flash models on independent
    #      quota counters, so one exhausted counter never sinks a request.
    # Not usable on the free tier: Pro models (gemini-3.1-pro-preview,
    # gemini-4-argon), every image-generation model, Google Search grounding,
    # and the 2.5 family (404 "no longer available to new users").
    # ``services.gemini_grounded`` skips a model for as long as Google says
    # its quota is exhausted, so a spent 3.8 counter costs nothing per call.
    FLASH_MODEL = os.getenv("FLASH_MODEL", "gemini-3.8-flash")
    FLASH_FALLBACK_MODEL = os.getenv("FLASH_FALLBACK_MODEL", "gemini-3.6-flash")
    EXTRA_FALLBACK_MODELS = _env_list(
        "EXTRA_FALLBACK_MODELS",
        "gemini-3-flash-preview,gemini-3.5-flash-lite,gemini-flash-lite-latest",
    )

    # Per-feature overrides; each defaults to the ladder above.
    VISION_MODEL = os.getenv("VISION_MODEL", FLASH_MODEL)
    VISION_FALLBACK_MODEL = os.getenv("VISION_FALLBACK_MODEL", FLASH_FALLBACK_MODEL)
    # Product analysis (Compare Agent) and the review-only Analyst Agent.
    ANALYST_MODEL = os.getenv("ANALYST_MODEL", FLASH_MODEL)
    ANALYST_FALLBACK_MODEL = os.getenv("ANALYST_FALLBACK_MODEL", FLASH_FALLBACK_MODEL)
    COMPARE_DEVICES_MODEL = os.getenv("COMPARE_DEVICES_MODEL", FLASH_MODEL)
    COMPARE_DEVICES_FALLBACK_MODEL = os.getenv("COMPARE_DEVICES_FALLBACK_MODEL", FLASH_FALLBACK_MODEL)
    DETECTIVE_MODEL = os.getenv("DETECTIVE_MODEL", FLASH_MODEL)
    DETECTIVE_FALLBACK_MODEL = os.getenv("DETECTIVE_FALLBACK_MODEL", FLASH_FALLBACK_MODEL)
    CHAT_MODEL = os.getenv("CHAT_MODEL", FLASH_MODEL)
    CHAT_FALLBACK_MODEL = os.getenv("CHAT_FALLBACK_MODEL", FLASH_FALLBACK_MODEL)
    PRICE_HISTORY_MODEL = os.getenv("PRICE_HISTORY_MODEL", FLASH_MODEL)
    PRICE_HISTORY_FALLBACK_MODEL = os.getenv("PRICE_HISTORY_FALLBACK_MODEL", FLASH_FALLBACK_MODEL)
    NEWS_MODEL = os.getenv("NEWS_MODEL", FLASH_MODEL)
    NEWS_FALLBACK_MODEL = os.getenv("NEWS_FALLBACK_MODEL", FLASH_FALLBACK_MODEL)
    # Native Gemini image generation ("Nano Banana"). Requires a billed key —
    # image models have no free-tier quota.
    IMAGE_MODEL = os.getenv("IMAGE_MODEL", "gemini-nano-banana-2.1")
    IMAGE_FALLBACK_MODEL = os.getenv("IMAGE_FALLBACK_MODEL", "gemini-3.1-flash-image")

    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY")

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

if not settings.GEMINI_API_KEY:
    raise ValueError("Eksik ortam değişkeni: GEMINI_API_KEY. Lütfen backend/.env dosyasını doldurun.")
if not settings.SUPABASE_URL:
    raise ValueError("Eksik ortam değişkeni: SUPABASE_URL. Lütfen backend/.env dosyasını doldurun.")
if not settings.SUPABASE_KEY:
    raise ValueError("Eksik ortam değişkeni: SUPABASE_KEY. Lütfen backend/.env dosyasını doldurun.")
settings.SUPABASE_SERVICE_KEY = settings.SUPABASE_KEY
