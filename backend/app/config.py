"""Central configuration loaded from environment variables.

All knobs live here so nothing is hardcoded across the codebase. Values come
from a local `.env` (never committed) with `.env.example` documenting them.
SQLite in dev, Postgres in prod — only `database_url` changes.
"""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Repo-relative default DB location so dev "just works" without a .env.
_BACKEND_DIR = Path(__file__).resolve().parent.parent
_DEFAULT_DB = f"sqlite:///{(_BACKEND_DIR / 'clara.db').as_posix()}"


class Settings(BaseSettings):
    """Application settings. Override any field via the environment."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "CLARA"
    environment: str = "development"

    # Storage — swap to a Postgres URL in prod, schema is identical.
    database_url: str = _DEFAULT_DB

    # Frontend dev/preview origins, for CORS (5180 dev, 4180 vite preview).
    cors_origins: list[str] = [
        "http://localhost:5180",
        "http://127.0.0.1:5180",
        "http://localhost:4180",
        "http://127.0.0.1:4180",
    ]

    # External sources. Empty => the module falls back to documented mocks.
    news_api_key: str = ""
    youtube_api_key: str = ""

    # Qwen (Alibaba DashScope) — prioridad principal para el chatbot.
    # Key en: dashscope.aliyuncs.com → Consola → API Key
    qwen_api_key: str = ""
    qwen_model: str = "qwen-plus"   # opciones: qwen-turbo, qwen-plus, qwen-max

    # Google Gemini — fallback si no hay key de Qwen.
    gemini_api_key: str = ""

    # Anthropic (Claude) — fallback final.
    anthropic_api_key: str = ""

    # chat_model sobrescribe el modelo del provider activo si se especifica.
    chat_model: str = ""

    # Ingestion behaviour. During unattended dev runs we never hit the network.
    use_mock_sources: bool = True

    # Background scheduler. Off by default so dev/tests don't mutate data.
    scheduler_enabled: bool = False


settings = Settings()
