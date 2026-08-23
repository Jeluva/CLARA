"""Tests for the screener: universe seeding + fundamentals/technicals rows."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.ingestion.fundamentals import run_mock_fundamentals_ingestion
from app.ingestion.universe import SCREENER_UNIVERSE
from app.services import crud_service as crud
from app.services.screener_service import get_screener
from app.storage.seed import seed_database


def test_seed_assets_creates_only_missing_tickers(db: Session) -> None:
    seed_database(db)  # already loads AAPL among others
    before = {a.ticker for a in crud.list_assets(db)}
    assert "AAPL" in before

    created = crud.seed_assets(db, SCREENER_UNIVERSE)

    after = {a.ticker for a in crud.list_assets(db)}
    assert after - before == {
        e["ticker"] for e in SCREENER_UNIVERSE if e["ticker"] not in before
    }
    assert created == len(SCREENER_UNIVERSE) - len(
        before & {e["ticker"] for e in SCREENER_UNIVERSE}
    )

    # Idempotent: running again creates nothing new.
    assert crud.seed_assets(db, SCREENER_UNIVERSE) == 0


def test_get_screener_returns_row_per_asset_without_fundamentals(db: Session) -> None:
    seed_database(db)
    rows = get_screener(db)
    tickers = {r["ticker"] for r in rows}
    assert "AAPL" in tickers
    row = next(r for r in rows if r["ticker"] == "AAPL")
    assert row["latest_price"] is not None  # seeded with price history
    assert row["pe_ratio"] is None  # no fundamentals ingested yet


def test_get_screener_includes_fundamentals_once_ingested(db: Session) -> None:
    seed_database(db)
    run_mock_fundamentals_ingestion(db)

    rows = get_screener(db)
    row = next(r for r in rows if r["ticker"] == "AAPL")
    assert row["pe_ratio"] is not None
    assert row["roe"] is not None
