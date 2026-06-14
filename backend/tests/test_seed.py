"""Tests for the example-data seed: content and idempotency."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.storage.models.silver import Asset, Position, Price
from app.storage.seed import SEED_ASSETS, TRADING_DAYS, seed_database


def test_seed_populates_expected_entities(db: Session) -> None:
    counts = seed_database(db)

    assert counts["assets"] == len(SEED_ASSETS)
    # Every asset gets a full price history, nothing quarantined.
    assert counts["prices_quarantined"] == 0
    assert counts["prices_promoted"] == len(SEED_ASSETS) * TRADING_DAYS

    # SPY is the benchmark — present as an asset but with no position.
    spy = db.execute(select(Asset).where(Asset.ticker == "SPY")).scalar_one()
    assert (
        db.execute(select(Position).where(Position.asset_id == spy.id)).first()
        is None
    )


def test_seed_is_idempotent(db: Session) -> None:
    first = seed_database(db)
    second = seed_database(db)

    # Counts of stored entities are identical after a second run.
    assert second["assets"] == first["assets"]
    assert second["positions"] == first["positions"]
    assert second["transactions"] == first["transactions"]

    # No duplicate prices were created on the second pass.
    total_prices = len(db.execute(select(Price)).scalars().all())
    assert total_prices == len(SEED_ASSETS) * TRADING_DAYS
    # Second run promotes nothing new (all bronze already promoted).
    assert second["prices_promoted"] == 0


def test_prices_are_deterministic(db: Session) -> None:
    seed_database(db)
    aapl = db.execute(select(Asset).where(Asset.ticker == "AAPL")).scalar_one()
    series = (
        db.execute(
            select(Price.close)
            .where(Price.asset_id == aapl.id)
            .order_by(Price.date)
        )
        .scalars()
        .all()
    )
    # First price is anchored to the configured start price.
    assert series[0] == 190.0
    assert len(series) == TRADING_DAYS
