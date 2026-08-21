"""Tests for the bronze→silver promotion engine: validation, quarantine, idempotency."""

from __future__ import annotations

import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.quality.promote import promote_bronze
from app.storage.models.bronze import BronzeRecord
from app.storage.models.quality import Quarantine
from app.storage.models.silver import Asset, Fundamentals, Price


def _add_asset(db: Session, ticker: str = "AAPL") -> Asset:
    asset = Asset(
        ticker=ticker, name=ticker, asset_class="cedear", currency="USD"
    )
    db.add(asset)
    db.flush()
    return asset


def _bronze_price(ticker: str, date: str, close: float) -> BronzeRecord:
    return BronzeRecord(
        source_table="prices",
        source="mock",
        dedupe_key=f"{ticker}:{date}",
        payload=json.dumps(
            {"ticker": ticker, "date": date, "close": close, "source": "mock"}
        ),
    )


def test_valid_record_promoted_to_silver(db: Session) -> None:
    _add_asset(db)
    db.add(_bronze_price("AAPL", "2026-01-05", 190.0))
    db.commit()

    result = promote_bronze(db)

    assert result.promoted == 1
    assert result.quarantined == 0
    prices = db.execute(select(Price)).scalars().all()
    assert len(prices) == 1
    assert prices[0].close == 190.0
    bronze = db.execute(select(BronzeRecord)).scalars().one()
    assert bronze.status == "promoted"


def test_bad_record_goes_to_quarantine_not_silver(db: Session) -> None:
    _add_asset(db)
    db.add(_bronze_price("AAPL", "2026-01-05", -5.0))  # negative price
    db.commit()

    result = promote_bronze(db)

    assert result.promoted == 0
    assert result.quarantined == 1
    assert db.execute(select(Price)).scalars().all() == []
    q = db.execute(select(Quarantine)).scalars().one()
    assert "close must be > 0" in q.failed_check


def test_unknown_ticker_quarantined(db: Session) -> None:
    _add_asset(db, "AAPL")
    db.add(_bronze_price("TSLA", "2026-01-05", 200.0))  # not seeded
    db.commit()

    result = promote_bronze(db)

    assert result.quarantined == 1
    assert db.execute(select(Price)).scalars().all() == []


def test_promotion_is_idempotent(db: Session) -> None:
    _add_asset(db)
    db.add(_bronze_price("AAPL", "2026-01-05", 190.0))
    db.commit()

    promote_bronze(db)
    # Second run: nothing pending, no new rows, no duplicates.
    second = promote_bronze(db)

    assert second.promoted == 0
    assert len(db.execute(select(Price)).scalars().all()) == 1


def _bronze_fundamentals(ticker: str, date: str, market_cap: float) -> BronzeRecord:
    return BronzeRecord(
        source_table="fundamentals",
        source="mock",
        dedupe_key=f"{ticker}:{date}",
        payload=json.dumps({
            "ticker": ticker,
            "source": "mock",
            "market_cap": market_cap,
            "pe_ratio": 20.0,
            "next_earnings_date": None,
        }),
    )


def test_fundamentals_promoted_as_single_row_per_asset(db: Session) -> None:
    _add_asset(db)
    db.add(_bronze_fundamentals("AAPL", "2026-01-05", 3_000_000_000.0))
    db.commit()

    result = promote_bronze(db)

    assert result.promoted == 1
    rows = db.execute(select(Fundamentals)).scalars().all()
    assert len(rows) == 1
    assert rows[0].market_cap == 3_000_000_000.0
    assert rows[0].pe_ratio == 20.0


def test_fundamentals_second_run_overwrites(db: Session) -> None:
    _add_asset(db)
    db.add(_bronze_fundamentals("AAPL", "2026-01-05", 3_000_000_000.0))
    db.commit()
    promote_bronze(db)

    # A later snapshot for the same asset overwrites, doesn't duplicate —
    # fundamentals is a point-in-time view, not a history.
    db.add(_bronze_fundamentals("AAPL", "2026-01-06", 3_100_000_000.0))
    db.commit()
    promote_bronze(db)

    rows = db.execute(select(Fundamentals)).scalars().all()
    assert len(rows) == 1
    assert rows[0].market_cap == 3_100_000_000.0


def test_upsert_updates_existing_price(db: Session) -> None:
    _add_asset(db)
    db.add(_bronze_price("AAPL", "2026-01-05", 190.0))
    db.commit()
    promote_bronze(db)

    # A corrected close for the same (asset, date) should update, not duplicate.
    corrected = _bronze_price("AAPL", "2026-01-05", 191.5)
    db.add(corrected)
    db.commit()
    promote_bronze(db)

    prices = db.execute(select(Price)).scalars().all()
    assert len(prices) == 1
    assert prices[0].close == 191.5
