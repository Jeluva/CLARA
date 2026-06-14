"""Tests for the CRUD service: creation, validation rules, deletion."""

from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from app.services import crud_service as crud
from app.storage.models.silver import Price


def test_create_and_list_asset(db: Session) -> None:
    crud.create_asset(
        db,
        ticker="aapl",  # lowercased input
        name="Apple",
        asset_class="cedear",
        sector="Tech",
        country="USA",
        currency="usd",
    )
    assets = crud.list_assets(db)
    assert len(assets) == 1
    # Ticker and currency normalized to upper-case.
    assert assets[0].ticker == "AAPL"
    assert assets[0].currency == "USD"


def test_duplicate_ticker_conflicts(db: Session) -> None:
    crud.create_asset(
        db, ticker="AAPL", name="Apple", asset_class="cedear",
        sector="Tech", country="USA", currency="USD",
    )
    with pytest.raises(crud.ConflictError):
        crud.create_asset(
            db, ticker="AAPL", name="Apple 2", asset_class="cedear",
            sector="Tech", country="USA", currency="USD",
        )


def test_create_position_requires_existing_asset(db: Session) -> None:
    with pytest.raises(crud.NotFoundError):
        crud.create_position(db, ticker="ZZZZ", quantity=10, avg_cost=100)


def test_create_position_rejects_non_positive(db: Session) -> None:
    crud.create_asset(
        db, ticker="AAPL", name="Apple", asset_class="cedear",
        sector="Tech", country="USA", currency="USD",
    )
    with pytest.raises(crud.ConflictError):
        crud.create_position(db, ticker="AAPL", quantity=0, avg_cost=100)


def test_create_position_links_to_asset(db: Session) -> None:
    crud.create_asset(
        db, ticker="AAPL", name="Apple", asset_class="cedear",
        sector="Tech", country="USA", currency="USD",
    )
    crud.create_position(db, ticker="AAPL", quantity=10, avg_cost=150)
    positions = crud.list_positions(db)
    assert len(positions) == 1
    position, asset = positions[0]
    assert asset.ticker == "AAPL"
    assert position.quantity == 10


def test_delete_asset_cascades_to_prices(db: Session) -> None:
    asset = crud.create_asset(
        db, ticker="AAPL", name="Apple", asset_class="cedear",
        sector="Tech", country="USA", currency="USD",
    )
    from datetime import date

    db.add(Price(asset_id=asset.id, date=date(2026, 1, 5), close=190.0))
    db.commit()

    crud.delete_asset(db, asset.id)

    assert crud.list_assets(db) == []
    assert db.query(Price).count() == 0


def test_delete_missing_asset_raises(db: Session) -> None:
    with pytest.raises(crud.NotFoundError):
        crud.delete_asset(db, 999)
