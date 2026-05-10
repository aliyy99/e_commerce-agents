"""
ShopSage AI - Application Settings
Loaded from environment variables via pydantic-settings.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # ── Google AI ──────────────────────────────
    GOOGLE_API_KEY: str = ""

    # Model names – update these as new versions release
    FLASH_MODEL: str = "gemini-2.0-flash"           # Low-latency multimodal tasks
    PRO_MODEL:   str = "gemini-2.5-pro"             # Complex reasoning & long context
    IMAGE_MODEL: str = "imagen-3.0-generate-002"    # Photorealistic image generation

    # ── Supabase ───────────────────────────────
    SUPABASE_URL:         str = ""
    SUPABASE_ANON_KEY:    str = ""
    SUPABASE_SERVICE_KEY: str = ""

    # ── App ────────────────────────────────────
    APP_ENV:   str = "development"
    LOG_LEVEL: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()
