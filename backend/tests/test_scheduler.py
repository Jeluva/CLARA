"""The scheduler registers all ingestion jobs with the right triggers."""

from __future__ import annotations

from app.scheduler.jobs import build_scheduler


def test_scheduler_registers_all_jobs() -> None:
    scheduler = build_scheduler()
    job_ids = {job.id for job in scheduler.get_jobs()}
    assert job_ids == {"ingest_prices", "ingest_news", "ingest_transcripts"}
    # Not started, so nothing runs during the test.
    assert not scheduler.running
