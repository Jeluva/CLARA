"""Tests for research service: asset comparator and sentiment series."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.ingestion.news import run_mock_news_ingestion
from app.services.research_service import compare_assets
from app.services.news_service import sentiment_series
from app.storage.seed import seed_database


def _seed_with_news(db: Session) -> None:
    seed_database(db)
    run_mock_news_ingestion(db)


def test_compare_assets_returns_metrics(db: Session) -> None:
    seed_database(db)
    result = compare_assets(db, ["AAPL", "MSFT"])
    assert len(result) == 2
    for item in result:
        assert item["data_points"] > 0
        assert "latest_price" in item
        assert "total_return" in item
        assert "volatility" in item
        assert "sharpe" in item


def test_compare_assets_unknown_ticker(db: Session) -> None:
    seed_database(db)
    result = compare_assets(db, ["AAPL", "ZZZZ"])
    assert len(result) == 2
    assert result[1]["ticker"] == "ZZZZ"
    assert result[1]["data_points"] == 0
    assert "latest_price" not in result[1]


def test_sentiment_series_returns_daily_points(db: Session) -> None:
    _seed_with_news(db)
    result = sentiment_series(db)
    assert len(result) > 0
    for point in result:
        assert -1 <= point.score <= 1
        assert point.count > 0


def test_sentiment_series_filtered_by_ticker(db: Session) -> None:
    _seed_with_news(db)
    all_points = sentiment_series(db)
    filtered = sentiment_series(db, "AAPL")
    assert len(filtered) <= len(all_points)
