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
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

    # Model names (env-overridable defaults).
    #
    # Two families are split by capability on the current key:
    #   • Non-grounded generation (Analyst report, Chat, Vision) runs on the
    #     Gemini 3 Flash family — gemini-3.5-flash is the highest Flash tier
    #     that returns clean output on this key.
    #   • Grounded generation (multi-site Compare, Price-history) MUST use the
    #     Gemini 2.5 Flash family: the google_search tool has zero free-tier
    #     quota on every Gemini 3.x model (hard 429), while 2.5 Flash / 2.5
    #     Flash-Lite still ground normally. Leading grounded calls with a 3.x
    #     model would 429 on every request before falling through, so those
    #     defaults point straight at 2.5 Flash.
    #   • Device-compare (/compare-devices) is the exception: it runs the
    #     Gemini 3.5 Flash family UNGROUNDED (use_search=False). A device
    #     spec-vs-spec verdict needs the model's own product knowledge, not a
    #     live web fetch (the frontend never renders grounding sources here),
    #     and dropping google_search is exactly what lets a 3.x model serve as
    #     primary without the grounded-quota 429. thinkingLevel=low keeps that
    #     reasoning model fast on what is really a structured-JSON extraction.
    # Each *_FALLBACK_MODEL sits on an independent quota counter so a
    # per-minute limit on the primary doesn't sink the whole call.
    FLASH_MODEL = os.getenv("FLASH_MODEL", "gemini-3.5-flash")
    PRO_MODEL = os.getenv("PRO_MODEL", "gemini-3.5-flash")
    PRO_FALLBACK_MODEL = os.getenv("PRO_FALLBACK_MODEL", "gemini-2.5-flash")
    COMPARE_MODEL = os.getenv("COMPARE_MODEL", "gemini-2.5-flash")
    COMPARE_FALLBACK_MODEL = os.getenv("COMPARE_FALLBACK_MODEL", "gemini-2.5-flash-lite")
    ANALYST_MODEL = os.getenv("ANALYST_MODEL", "gemini-2.5-flash")
    ANALYST_FALLBACK_MODEL = os.getenv("ANALYST_FALLBACK_MODEL", "gemini-2.5-flash-lite")
    # Device-compare runs ungrounded, so it can lead with Gemini 3.5 Flash and
    # keep a 2.5 Flash fallback on an independent quota counter. (Kept separate
    # from ANALYST_MODEL, which still drives the grounded multi-site agent.)
    COMPARE_DEVICES_MODEL = os.getenv("COMPARE_DEVICES_MODEL", "gemini-3.5-flash")
    COMPARE_DEVICES_FALLBACK_MODEL = os.getenv("COMPARE_DEVICES_FALLBACK_MODEL", "gemini-2.5-flash")
    VISION_MODEL = os.getenv("VISION_MODEL", "gemini-3.5-flash")
    VISION_FALLBACK_MODEL = os.getenv("VISION_FALLBACK_MODEL", "gemini-2.5-flash")
    CHAT_MODEL = os.getenv("CHAT_MODEL", "gemini-2.5-flash")
    CHAT_FALLBACK_MODEL = os.getenv("CHAT_FALLBACK_MODEL", "gemini-2.5-flash-lite")
    PRICE_HISTORY_MODEL = os.getenv("PRICE_HISTORY_MODEL", "gemini-2.5-flash")
    PRICE_HISTORY_FALLBACK_MODEL = os.getenv("PRICE_HISTORY_FALLBACK_MODEL", "gemini-2.5-flash-lite")
    IMAGE_MODEL = os.getenv("IMAGE_MODEL", "imagen-3.0-generate-002")

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
