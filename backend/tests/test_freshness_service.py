"""Tests for per-source data freshness (bronze layer fetched_at)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.services import freshness_service
from app.storage.models.bronze import BronzeRecord
from app.storage.seed import seed_database


def test_unknown_source_never_ingested_reports_none(db: Session) -> None:
    result = {f["source"]: f for f in freshness_service.get_freshness(db)}
    assert set(result) == set(freshness_service.SOURCES)
    for f in result.values():
        assert f["last_success_at"] is None
        assert f["last_attempt_at"] is None


def test_seed_prices_show_up_as_promoted(db: Session) -> None:
    seed_database(db)
    result = {f["source"]: f for f in freshness_service.get_freshness(db)}
    assert result["prices"]["last_success_at"] is not None
    assert result["prices"]["last_attempt_at"] is not None
    # Other sources weren't touched by the price-only seed.
    assert result["news"]["last_success_at"] is None


def test_attempt_after_last_success_reports_both(db: Session) -> None:
    older = datetime(2026, 1, 1, 12, 0, 0)
    newer = datetime(2026, 1, 2, 12, 0, 0)
    db.add_all([
        BronzeRecord(
            source_table="news", source="mock", dedupe_key="a",
            payload="{}", status="promoted", fetched_at=older,
        ),
        BronzeRecord(
            source_table="news", source="mock", dedupe_key="b",
            payload="{}", status="quarantined", fetched_at=newer,
        ),
    ])
    db.commit()

    result = {f["source"]: f for f in freshness_service.get_freshness(db)}
    assert result["news"]["last_success_at"] == older.isoformat()
    assert result["news"]["last_attempt_at"] == newer.isoformat()
    assert result["news"]["last_attempt_at"] != result["news"]["last_success_at"]


def test_all_known_sources_present_even_when_empty(db: Session) -> None:
    result = freshness_service.get_freshness(db)
    assert {f["source"] for f in result} == {
        "prices", "news", "transcripts", "fundamentals",
    }
