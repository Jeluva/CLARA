"""Tests for sentiment scoring, news/transcript ingestion and the news service."""

from __future__ import annotations

from unittest.mock import patch

from sqlalchemy.orm import Session

from app.ingestion.news import run_mock_news_ingestion
from app.ingestion.sentiment import label, score, _is_spanish
from app.ingestion.transcripts import (
    run_channel_transcript_ingestion,
    run_mock_transcript_ingestion,
    run_transcript_ingestion,
)
from app.services import news_service as svc
from app.services import crud_service as crud
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


def test_is_spanish_detects_spanish_text() -> None:
    assert _is_spanish("Las acciones del Merval subieron con fuerza por la baja del riesgo país")
    assert _is_spanish("El dólar blue cerró estable pero los bonos operaron con volatilidad")
    assert not _is_spanish("Apple shares surge to record high on strong earnings")
    assert not _is_spanish("hi")


def test_sentiment_spanish_falls_back_to_vader_without_keys() -> None:
    from unittest.mock import patch
    import app.ingestion.sentiment as mod
    with patch.object(mod, "_score_llm", return_value=None):
        s = score("Las acciones del Merval subieron con fuerza por la baja del riesgo país")
        assert -1.0 <= s <= 1.0


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


def test_channel_transcript_ingestion(db: Session) -> None:
    with patch(
        "app.ingestion.youtube.resolve_channel",
        return_value={"channel_id": "UC1", "handle": "@t", "display_name": "T Channel"},
    ):
        crud.create_channel(db, url_or_handle="@t")

    with (
        patch(
            "app.ingestion.transcripts.youtube.list_latest_videos",
            return_value=[{"video_id": "vid1", "title": "Market update", "upload_date": "20260701"}],
        ),
        patch(
            "app.ingestion.transcripts.youtube.fetch_transcript",
            return_value="Stocks rallied today on strong earnings.",
        ),
    ):
        result = run_channel_transcript_ingestion(db)

    assert result.promoted == 1
    transcripts = svc.list_transcripts(db)
    assert len(transcripts) == 1
    assert transcripts[0]["source_channel"] == "T Channel"


def test_channel_transcript_ingestion_skips_missing_transcript(db: Session) -> None:
    with patch(
        "app.ingestion.youtube.resolve_channel",
        return_value={"channel_id": "UC1", "handle": "@t", "display_name": "T Channel"},
    ):
        crud.create_channel(db, url_or_handle="@t")

    with (
        patch(
            "app.ingestion.transcripts.youtube.list_latest_videos",
            return_value=[{"video_id": "vid1", "title": "No captions", "upload_date": None}],
        ),
        patch("app.ingestion.transcripts.youtube.fetch_transcript", return_value=None),
    ):
        result = run_channel_transcript_ingestion(db)

    assert result.promoted == 0
    assert svc.list_transcripts(db) == []


def test_run_transcript_ingestion_falls_back_to_mock_without_channels(db: Session) -> None:
    seed_database(db)
    with patch("app.config.settings.use_mock_sources", False):
        result = run_transcript_ingestion(db)
    assert result.promoted > 0
    # Mock fixture videos, not a real channel scrape.
    assert svc.list_transcripts(db)[0]["source_channel"] in {
        "Mercado en Foco", "Wall Street AR", "Inversor Global", "Renta Fija Hoy",
    }
