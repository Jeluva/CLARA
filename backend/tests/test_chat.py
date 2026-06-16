"""Tests for the chatbot service (no API key needed — fallback path)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.services import chat_service
from app.services.asset_service import get_asset_summary
from app.services.chat_service import ChatMessage
from app.storage.seed import seed_database


def test_chat_without_key_returns_fallback_with_context(db: Session) -> None:
    seed_database(db)
    result = chat_service.fundamental_analysis(
        db, "AAPL", [ChatMessage(role="user", content="¿Qué es Apple?")]
    )
    assert result["configured"] is False
    # The fallback still surfaces the assembled context so it's useful.
    assert "AAPL" in result["reply"]
    assert "Apple" in result["reply"]


def test_asset_summary_shape(db: Session) -> None:
    seed_database(db)
    summary = get_asset_summary(db, "AAPL")
    assert summary is not None
    assert summary["ticker"] == "AAPL"
    assert summary["position"] is not None  # AAPL is held in the seed
    assert summary["latest_price"] is not None
    assert summary["news_count"] >= 0


def test_asset_summary_missing(db: Session) -> None:
    seed_database(db)
    assert get_asset_summary(db, "ZZZZ") is None
