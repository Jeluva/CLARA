"""CLARA FastAPI entrypoint.

Wires CORS and the API routers. As phases land, new routers (portfolio,
metrics, news, macro, ingestion) get included here — main.py stays thin.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api import data_entry, health, macro, news, portfolio, research
from app.config import settings

logger = logging.getLogger("clara")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start the ingestion scheduler on boot if enabled; stop it on shutdown."""
    scheduler = None
    if settings.scheduler_enabled:
        from app.scheduler.jobs import build_scheduler

        scheduler = build_scheduler()
        scheduler.start()
        logger.info("ingestion scheduler started")
    try:
        yield
    finally:
        if scheduler is not None:
            scheduler.shutdown(wait=False)
            logger.info("ingestion scheduler stopped")


def create_app() -> FastAPI:
    """Application factory — keeps construction testable."""
    app = FastAPI(
        title="CLARA API",
        description="Mesa de análisis de portfolio: posiciones, métricas, "
        "noticias, sentimiento y macro.",
        version=__version__,
        lifespan=lifespan,
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
