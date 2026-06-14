"""Tests for sentiment scoring, news/transcript ingestion and the news service."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.ingestion.news import run_mock_news_ingestion
from app.ingestion.sentiment import label, score
from app.ingestion.transcripts import run_mock_transcript_ingestion
from app.services import news_service as svc
from app.storage.models.silver import News
from app.storage.seed import seed_database


# --- Sentiment scorer --------------------------------------------------------


def test_sentiment_positive_headline() -> None:
    s = score("Apple shares surge to record high on strong earnings beat")
    assert s > 0.05
    assert label(s) == "positive"


def test_sentiment_negative_headline() -> None:
    s = score("Stocks plunge as crisis deepens; investors flee in panic")
    assert s < -0.05
    assert label(s) == "negative"


def test_sentiment_in_range_and_empty_neutral() -> None:
    assert -1.0 <= score("anything at all here") <= 1.0
    assert score("") == 0.0
    assert label(0.0) == "neutral"


# --- Ingestion ---------------------------------------------------------------


def test_news_ingestion_populates_and_is_idempotent(db: Session) -> None:
    seed_database(db)  # need assets for ticker linkage
    first = run_mock_news_ingestion(db)
    assert first.promoted > 0
    assert first.quarantined == 0

    count_after_first = db.query(News).count()
    second = run_mock_news_ingestion(db)
    assert second.promoted == 0  # nothing new on a second run
    assert db.query(News).count() == count_after_first


def test_news_linked_to_assets(db: Session) -> None:
    seed_database(db)
    run_mock_news_ingestion(db)
    items = svc.list_news(db, ticker="AAPL")
    assert len(items) > 0
    assert all(i.ticker == "AAPL" for i in items)


def test_sentiment_by_ticker_aggregates(db: Session) -> None:
    seed_database(db)
    run_mock_news_ingestion(db)
    agg = svc.sentiment_by_ticker(db)
    assert len(agg) > 0
    # Sorted descending by score.
    scores = [t.score for t in agg]
    assert scores == sorted(scores, reverse=True)
    assert all(-1.0 <= t.score <= 1.0 for t in agg)


def test_transcript_ingestion(db: Session) -> None:
    seed_database(db)
    result = run_mock_transcript_ingestion(db)
    assert result.promoted > 0
    transcripts = svc.list_transcripts(db)
    assert len(transcripts) == result.promoted
    assert all("sentiment_label" in t for t in transcripts)
