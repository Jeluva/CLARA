"""Tests for alert rules: creation, validation, live-evaluated trigger status."""

from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ingestion.fundamentals import run_mock_fundamentals_ingestion
from app.services import alert_service
from app.services import crud_service as crud
from app.services.market_data import latest_prices
from app.storage.models.silver import Asset, Fundamentals
from app.storage.seed import seed_database


def test_price_alert_triggers_when_condition_holds(db: Session) -> None:
    seed_database(db)
    price = latest_prices(db)["AAPL"]
    created = alert_service.create_alert(
        db, ticker="aapl", metric="price", condition="above", threshold=price - 1
    )
    assert created["ticker"] == "AAPL"
    assert created["current_value"] == pytest.approx(price)
    assert created["triggered"] is True
    assert created["status"] == "disparada"


def test_price_alert_not_triggered_when_condition_not_met(db: Session) -> None:
    seed_database(db)
    price = latest_prices(db)["AAPL"]
    created = alert_service.create_alert(
        db, ticker="AAPL", metric="price", condition="below", threshold=price - 1
    )
    assert created["triggered"] is False
    assert created["status"] == "en_seguimiento"


def test_sentiment_alert_without_news_has_no_data(db: Session) -> None:
    seed_database(db)
    created = alert_service.create_alert(
        db, ticker="AAPL", metric="sentiment", condition="below", threshold=-0.5
    )
    assert created["current_value"] is None
    assert created["triggered"] is False
    assert created["status"] == "sin_dato"


def test_pe_ratio_alert_uses_fundamentals(db: Session) -> None:
    seed_database(db)
    run_mock_fundamentals_ingestion(db)
    asset_id = db.execute(select(Fundamentals)).scalars().first().asset_id
    ticker = db.get(Asset, asset_id).ticker
    fund = db.execute(
        select(Fundamentals).where(Fundamentals.asset_id == asset_id)
    ).scalar_one()
    pe = fund.pe_ratio
    if pe is None:
        pytest.skip("Mock fundamentals didn't assign a pe_ratio for this asset")

    created = alert_service.create_alert(
        db, ticker=ticker, metric="pe_ratio", condition="above", threshold=pe - 1
    )
    assert created["current_value"] == pytest.approx(pe)
    assert created["triggered"] is True


def test_create_alert_unknown_ticker_raises_not_found(db: Session) -> None:
    with pytest.raises(crud.NotFoundError):
        alert_service.create_alert(
            db, ticker="ZZZZ", metric="price", condition="above", threshold=100.0
        )


def test_create_alert_rejects_invalid_metric(db: Session) -> None:
    seed_database(db)
    with pytest.raises(crud.ConflictError):
        alert_service.create_alert(
            db, ticker="AAPL", metric="volume", condition="above", threshold=100.0
        )


def test_create_alert_rejects_invalid_condition(db: Session) -> None:
    seed_database(db)
    with pytest.raises(crud.ConflictError):
        alert_service.create_alert(
            db, ticker="AAPL", metric="price", condition="equal", threshold=100.0
        )


def test_list_alerts_filters_by_ticker_and_only_triggered(db: Session) -> None:
    seed_database(db)
    price = latest_prices(db)["AAPL"]
    alert_service.create_alert(
        db, ticker="AAPL", metric="price", condition="above", threshold=price - 1
    )
    alert_service.create_alert(
        db, ticker="AAPL", metric="price", condition="above", threshold=price + 1
    )
    alert_service.create_alert(
        db, ticker="KO", metric="price", condition="above", threshold=0.01
    )

    assert len(alert_service.list_alerts(db)) == 3
    assert len(alert_service.list_alerts(db, ticker="aapl")) == 2

    triggered = alert_service.list_alerts(db, only_triggered=True)
    assert len(triggered) == 2  # AAPL above (price-1) + KO above (0.01)
    assert all(a["triggered"] for a in triggered)


def test_delete_alert(db: Session) -> None:
    seed_database(db)
    created = alert_service.create_alert(
        db, ticker="AAPL", metric="price", condition="above", threshold=1.0
    )
    alert_service.delete_alert(db, created["id"])
    assert alert_service.list_alerts(db) == []


def test_delete_missing_alert_raises(db: Session) -> None:
    with pytest.raises(crud.NotFoundError):
        alert_service.delete_alert(db, 999)
