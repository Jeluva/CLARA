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

    # Frontend origins, for CORS (5180 dev, 4180 vite preview, Vercel prod).
    # Override via CORS_ORIGINS (JSON list) if the prod frontend URL changes.
    cors_origins: list[str] = [
        "http://localhost:5180",
        "http://127.0.0.1:5180",
        "http://localhost:4180",
        "http://127.0.0.1:4180",
        "https://clara-jet.vercel.app",
    ]

    # External sources. Empty => the module falls back to documented mocks.
    news_api_key: str = ""
    youtube_api_key: str = ""

    # Webshare residential proxy — routes yt-dlp / youtube-transcript-api
    # traffic around YouTube's blanket block on cloud-provider IPs (Render,
    # AWS, etc). Empty => requests go out direct (works locally, blocked in
    # prod). Get credentials at webshare.io (their "Residential" plan is the
    # one youtube-transcript-api's docs recommend; the free "Proxy Server"
    # plan is datacenter IPs and gets blocked the same as Render's).
    webshare_proxy_username: str = ""
    webshare_proxy_password: str = ""

    # Shared secret for POST /api/transcripts/ingest-external — lets a
    # trusted machine (e.g. your own PC, with a residential IP YouTube
    # doesn't block) push pre-scraped transcripts into prod without needing
    # a paid proxy. Empty => the endpoint is disabled.
    ingest_secret: str = ""

    # Groq — prioridad 1. Free tier: 14.400 req/día. Key: console.groq.com
    # NOTA: "llama-3.3-70b-versatile" figura como modelo de producción en la
    # doc de Groq pero devuelve 404 en cuentas sin verificación de
    # organización (restricción de licencia de Meta) -- gpt-oss-120b no
    # tiene esa restricción y no requiere verificación.
    groq_api_key: str = ""
    groq_model: str = "openai/gpt-oss-120b"

    # Qwen (Alibaba DashScope) — prioridad 2. Key: dashscope.aliyuncs.com
    qwen_api_key: str = ""
    qwen_model: str = "qwen-plus"

    # Google Gemini — prioridad 3. Key: aistudio.google.com
    gemini_api_key: str = ""

    # Anthropic (Claude) — prioridad 4. Key: console.anthropic.com
    anthropic_api_key: str = ""

    # Sobrescribe el modelo del provider activo si se especifica.
    chat_model: str = ""

    # LLM local via Ollama (docs/devlog/BACKLOG.md, v5 item 3) -- último
    # fallback antes del análisis estático, para no depender pura y
    # exclusivamente de las 4 APIs cloud. Off por default: en prod (Render)
    # no hay Ollama corriendo, y localmente el usuario lo prende a mano
    # cuando levantó `ollama serve` con el modelo cargado (ver README de
    # E:/private-gpt). Ollama expone un endpoint OpenAI-compatible; no pide
    # una API key real.
    ollama_enabled: bool = False
    ollama_base_url: str = "http://localhost:11434/v1"
    # Nombre real confirmado en vivo (`ollama list`, 2026-08-28): el usuario
    # ya había registrado el modelo de E:/private-gpt bajo este tag.
    ollama_model: str = "qwen-aggressive"

    # Ingestion behaviour. During unattended dev runs we never hit the network.
    use_mock_sources: bool = True

    # Background scheduler. Off by default so dev/tests don't mutate data.
    scheduler_enabled: bool = False


settings = Settings()
