"""APScheduler wiring for the ingestion jobs.

Each job opens its own DB session, runs a source's (mock) ingestion through the
medallion pipeline, and logs the outcome. Schedules follow the BRIEF: prices at
market close, news every few hours, transcripts daily. All jobs are idempotent,
so a missed/duplicated run is harmless.
"""

from __future__ import annotations

import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.ingestion.news import run_news_ingestion
from app.ingestion.prices import run_price_ingestion
from app.ingestion.transcripts import run_mock_transcript_ingestion
from app.storage.database import SessionLocal

logger = logging.getLogger("clara.scheduler")


def _run(name: str, runner) -> None:
    """Run one ingestion job in its own session, logging the result."""
    try:
        with SessionLocal() as db:
            result = runner(db)
        logger.info(
            "ingestion job '%s': %d promoted, %d quarantined",
            name,
            result.promoted,
            result.quarantined,
        )
    except Exception:  # noqa: BLE001 - jobs must never crash the scheduler
        logger.exception("ingestion job '%s' failed", name)


def build_scheduler() -> BackgroundScheduler:
    """Construct (but don't start) the scheduler with all ingestion jobs."""
    scheduler = BackgroundScheduler(timezone="UTC")

    # Prices: weekdays shortly after the US market close (21:10 UTC).
    scheduler.add_job(
        lambda: _run("prices", run_price_ingestion),
        CronTrigger(day_of_week="mon-fri", hour=21, minute=10),
        id="ingest_prices",
        replace_existing=True,
    )
    # News: every 4 hours.
    scheduler.add_job(
        lambda: _run("news", run_news_ingestion),
        CronTrigger(hour="*/4"),
        id="ingest_news",
        replace_existing=True,
    )
    # Transcripts: once a day (08:00 UTC).
    scheduler.add_job(
        lambda: _run("transcripts", run_mock_transcript_ingestion),
        CronTrigger(hour=8, minute=0),
        id="ingest_transcripts",
        replace_existing=True,
    )
    return scheduler
