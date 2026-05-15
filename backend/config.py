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
    # POLICY: Pro-family models (gemini-*-pro / *-pro-preview) have ZERO free-
    # tier quota on this key (limit=0), so every default below points to a
    # Flash variant. Operators with a paid plan can override any of these via
    # env vars without touching code. The "PRO_MODEL" name is retained for
    # backwards-compat with imports — its VALUE is a Flash model.
    FLASH_MODEL = os.getenv("FLASH_MODEL", "gemini-2.5-flash")
    PRO_MODEL = os.getenv("PRO_MODEL", "gemini-2.5-flash")
    # Analyst's secondary model — used only when PRO_MODEL hits its daily
    # per-model quota. Picked from a separate model family so its quota
    # counter is independent.
    PRO_FALLBACK_MODEL = os.getenv("PRO_FALLBACK_MODEL", "gemini-2.5-flash-lite")
    # Multi-site product comparison (CompareAgent). Two-tier with no per-model
    # retries keeps the worst case at 2 API calls so a limited quota lasts.
    COMPARE_MODEL = os.getenv("COMPARE_MODEL", "gemini-3-flash-preview")
    COMPARE_FALLBACK_MODEL = os.getenv("COMPARE_FALLBACK_MODEL", "gemini-2.5-flash")
    # Vision (product scan & match) — multimodal Flash is strong on brand/
    # variant disambiguation.
    VISION_MODEL = os.getenv("VISION_MODEL", "gemini-3-flash-preview")
    VISION_FALLBACK_MODEL = os.getenv("VISION_FALLBACK_MODEL", "gemini-2.5-flash")
    # Chat: sub-second replies, free-tier safe. CHAT_FALLBACK_MODEL is a
    # second Flash family member so a single model's transient failure still
    # leaves an answer-capable fallback.
    CHAT_MODEL = os.getenv("CHAT_MODEL", "gemini-3-flash-preview")
    CHAT_FALLBACK_MODEL = os.getenv("CHAT_FALLBACK_MODEL", "gemini-2.5-flash-lite")
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
