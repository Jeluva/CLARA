"""Tests for the CRUD service: creation, validation rules, deletion."""

from __future__ import annotations

from unittest.mock import patch

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
        crud.create_position(db, ticker="ZZZZ", portfolio_id=1, quantity=10, avg_cost=100)


def test_create_position_rejects_non_positive(db: Session) -> None:
    crud.create_asset(
        db, ticker="AAPL", name="Apple", asset_class="cedear",
        sector="Tech", country="USA", currency="USD",
    )
    portfolio = crud.create_portfolio(db, name="Test")
    with pytest.raises(crud.ConflictError):
        crud.create_position(
            db, ticker="AAPL", portfolio_id=portfolio.id, quantity=0, avg_cost=100
        )


def test_create_position_requires_existing_portfolio(db: Session) -> None:
    crud.create_asset(
        db, ticker="AAPL", name="Apple", asset_class="cedear",
        sector="Tech", country="USA", currency="USD",
    )
    with pytest.raises(crud.NotFoundError):
        crud.create_position(db, ticker="AAPL", portfolio_id=999, quantity=10, avg_cost=100)


def test_create_position_links_to_asset(db: Session) -> None:
    crud.create_asset(
        db, ticker="AAPL", name="Apple", asset_class="cedear",
        sector="Tech", country="USA", currency="USD",
    )
    portfolio = crud.create_portfolio(db, name="Test")
    crud.create_position(
        db, ticker="AAPL", portfolio_id=portfolio.id, quantity=10, avg_cost=150
    )
    positions = crud.list_positions(db)
    assert len(positions) == 1
    position, asset = positions[0]
    assert asset.ticker == "AAPL"
    assert position.quantity == 10
    assert position.portfolio_id == portfolio.id


def test_list_positions_filters_by_portfolio(db: Session) -> None:
    crud.create_asset(
        db, ticker="AAPL", name="Apple", asset_class="cedear",
        sector="Tech", country="USA", currency="USD",
    )
    crud.create_asset(
        db, ticker="MSFT", name="Microsoft", asset_class="cedear",
        sector="Tech", country="USA", currency="USD",
    )
    p1 = crud.create_portfolio(db, name="Portfolio 1")
    p2 = crud.create_portfolio(db, name="Portfolio 2")
    crud.create_position(db, ticker="AAPL", portfolio_id=p1.id, quantity=10, avg_cost=150)
    crud.create_position(db, ticker="MSFT", portfolio_id=p2.id, quantity=5, avg_cost=300)

    assert len(crud.list_positions(db, p1.id)) == 1
    assert len(crud.list_positions(db, p2.id)) == 1
    assert len(crud.list_positions(db)) == 2


def test_create_portfolio_rejects_duplicate_name(db: Session) -> None:
    crud.create_portfolio(db, name="Mi cartera")
    with pytest.raises(crud.ConflictError):
        crud.create_portfolio(db, name="Mi cartera")


def test_rename_portfolio(db: Session) -> None:
    portfolio = crud.create_portfolio(db, name="Original")
    renamed = crud.rename_portfolio(db, portfolio.id, name="Renombrado")
    assert renamed.name == "Renombrado"
    with pytest.raises(crud.NotFoundError):
        crud.rename_portfolio(db, 999, name="No existe")


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


# --- Transactions ----------------------------------------------------------


def test_create_transaction_requires_existing_asset(db: Session) -> None:
    portfolio = crud.create_portfolio(db, name="Test")
    with pytest.raises(crud.NotFoundError):
        crud.create_transaction(
            db, ticker="ZZZZ", portfolio_id=portfolio.id, type="buy", quantity=10, price=100
        )


def test_create_transaction_requires_existing_portfolio(db: Session) -> None:
    crud.create_asset(
        db, ticker="AAPL", name="Apple", asset_class="cedear",
        sector="Tech", country="USA", currency="USD",
    )
    with pytest.raises(crud.NotFoundError):
        crud.create_transaction(
            db, ticker="AAPL", portfolio_id=999, type="buy", quantity=10, price=150
        )


def test_create_transaction_rejects_non_positive(db: Session) -> None:
    crud.create_asset(
        db, ticker="AAPL", name="Apple", asset_class="cedear",
        sector="Tech", country="USA", currency="USD",
    )
    portfolio = crud.create_portfolio(db, name="Test")
    with pytest.raises(crud.ConflictError):
        crud.create_transaction(
            db, ticker="AAPL", portfolio_id=portfolio.id, type="buy", quantity=0, price=150
        )


def test_create_transaction_links_to_portfolio(db: Session) -> None:
    crud.create_asset(
        db, ticker="AAPL", name="Apple", asset_class="cedear",
        sector="Tech", country="USA", currency="USD",
    )
    portfolio = crud.create_portfolio(db, name="Test")
    tx = crud.create_transaction(
        db, ticker="AAPL", portfolio_id=portfolio.id, type="buy", quantity=10, price=150
    )
    assert tx.portfolio_id == portfolio.id
    assert tx.type == "buy"


# --- YouTube channels ----------------------------------------------------------


def _mock_resolved(channel_id="UC123", handle="@testchan", display_name="Test Channel"):
    return {"channel_id": channel_id, "handle": handle, "display_name": display_name}


def test_create_and_list_channel(db: Session) -> None:
    with patch(
        "app.ingestion.youtube.resolve_channel", return_value=_mock_resolved()
    ):
        channel = crud.create_channel(db, url_or_handle="@testchan")
    assert channel.channel_id == "UC123"
    assert channel.active is True
    assert [c.channel_id for c in crud.list_channels(db)] == ["UC123"]


def test_create_duplicate_channel_conflicts(db: Session) -> None:
    with patch(
        "app.ingestion.youtube.resolve_channel", return_value=_mock_resolved()
    ):
        crud.create_channel(db, url_or_handle="@testchan")
        with pytest.raises(crud.ConflictError):
            crud.create_channel(db, url_or_handle="https://youtube.com/@testchan")


def test_create_channel_not_found_raises_conflict(db: Session) -> None:
    from app.ingestion.youtube import ChannelNotFoundError

    with patch(
        "app.ingestion.youtube.resolve_channel",
        side_effect=ChannelNotFoundError("nope"),
    ):
        with pytest.raises(crud.ConflictError):
            crud.create_channel(db, url_or_handle="@doesnotexist")


def test_delete_channel(db: Session) -> None:
    with patch(
        "app.ingestion.youtube.resolve_channel", return_value=_mock_resolved()
    ):
        channel = crud.create_channel(db, url_or_handle="@testchan")
    crud.delete_channel(db, channel.id)
    assert crud.list_channels(db) == []


def test_delete_missing_channel_raises(db: Session) -> None:
    with pytest.raises(crud.NotFoundError):
        crud.delete_channel(db, 999)
