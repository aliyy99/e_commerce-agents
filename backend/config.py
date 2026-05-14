"""
ShopSage AI - Application Settings
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

    # Model names (env-overridable defaults)
    FLASH_MODEL = os.getenv("FLASH_MODEL", "gemini-2.5-flash")
    PRO_MODEL = os.getenv("PRO_MODEL", "gemini-2.5-pro")
    # Chat defaults to the smarter Pro model for higher answer quality.
    # Falls back to Flash inside generate_chat_reply if Pro errors.
    CHAT_MODEL = os.getenv("CHAT_MODEL", "gemini-2.5-pro")
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
