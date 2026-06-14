"""CLARA FastAPI entrypoint.

Wires CORS and the API routers. As phases land, new routers (portfolio,
metrics, news, macro, ingestion) get included here — main.py stays thin.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api import data_entry, health, macro, news, portfolio, research
from app.config import settings


def create_app() -> FastAPI:
    """Application factory — keeps construction testable."""
    app = FastAPI(
        title="CLARA API",
        description="Mesa de análisis de portfolio: posiciones, métricas, "
        "noticias, sentimiento y macro.",
        version=__version__,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router)
    app.include_router(portfolio.router)
    app.include_router(research.router)
    app.include_router(news.router)
    app.include_router(macro.router)
    app.include_router(data_entry.router)

    return app


app = create_app()
