"""Tests for fundamentals ingestion: mock mode and the yfinance extraction."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ingestion.fundamentals import _extract_payload, run_mock_fundamentals_ingestion
from app.storage.models.silver import Fundamentals
from app.storage.seed import seed_database


def test_mock_ingestion_promotes_one_row_per_asset(db: Session) -> None:
    seed_database(db)
    result = run_mock_fundamentals_ingestion(db)

    assert result.quarantined == 0
    rows = db.execute(select(Fundamentals)).scalars().all()
    # One row per seeded asset (SPY included — it's a valid ticker too).
    assert len(rows) == result.promoted
    assert result.promoted > 0


def test_mock_ingestion_is_idempotent_within_the_same_day(db: Session) -> None:
    seed_database(db)
    run_mock_fundamentals_ingestion(db)
    second = run_mock_fundamentals_ingestion(db)

    # Same-day re-run: dedupe key already exists, nothing new to promote.
    assert second.promoted == 0
    rows = db.execute(select(Fundamentals)).scalars().all()
    assert len(rows) > 0


def test_extract_payload_cleans_nan_and_missing_fields() -> None:
    info = {"trailingPE": float("nan"), "marketCap": 1_000.0}
    payload = _extract_payload("AAPL", info, source="yfinance")

    assert payload["pe_ratio"] is None  # NaN -> None
    assert payload["market_cap"] == 1_000.0
    assert payload["forward_pe"] is None  # absent key -> None
    assert payload["next_earnings_date"] is None
