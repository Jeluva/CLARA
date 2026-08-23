"""Tests for the thesis journal: creation, validation, contrast vs. real price."""

from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from app.services import crud_service as crud
from app.services import thesis_service
from app.services.market_data import latest_prices
from app.storage.seed import seed_database


def test_create_thesis_captures_price_at_entry(db: Session) -> None:
    seed_database(db)
    price = latest_prices(db)["AAPL"]
    created = thesis_service.create_thesis(
        db, ticker="aapl", note="Buen momentum y earnings sólidos", conviction="alta"
    )
    assert created["ticker"] == "AAPL"
    assert created["price_at_entry"] == pytest.approx(price)
    assert created["current_price"] == pytest.approx(price)
    assert created["return_since_entry"] == pytest.approx(0.0, abs=1e-9)
    assert created["status"] == "en_curso"


def test_status_objetivo_alcanzado_when_price_above_target(db: Session) -> None:
    seed_database(db)
    price = latest_prices(db)["AAPL"]
    created = thesis_service.create_thesis(
        db, ticker="AAPL", note="Ya superó mi objetivo", target_price=price - 1
    )
    assert created["status"] == "objetivo_alcanzado"


def test_status_stop_tocado_when_price_below_stop(db: Session) -> None:
    seed_database(db)
    price = latest_prices(db)["AAPL"]
    created = thesis_service.create_thesis(
        db, ticker="AAPL", note="Tocó el stop", stop_loss=price + 1
    )
    assert created["status"] == "stop_tocado"


def test_create_thesis_unknown_ticker_raises_not_found(db: Session) -> None:
    with pytest.raises(crud.NotFoundError):
        thesis_service.create_thesis(db, ticker="ZZZZ", note="no existe")


def test_create_thesis_rejects_empty_note(db: Session) -> None:
    seed_database(db)
    with pytest.raises(crud.ConflictError):
        thesis_service.create_thesis(db, ticker="AAPL", note="   ")


def test_create_thesis_rejects_invalid_conviction(db: Session) -> None:
    seed_database(db)
    with pytest.raises(crud.ConflictError):
        thesis_service.create_thesis(db, ticker="AAPL", note="motivo", conviction="mucha")


def test_create_thesis_rejects_non_positive_target(db: Session) -> None:
    seed_database(db)
    with pytest.raises(crud.ConflictError):
        thesis_service.create_thesis(db, ticker="AAPL", note="motivo", target_price=0)


def test_list_theses_filters_by_ticker(db: Session) -> None:
    seed_database(db)
    thesis_service.create_thesis(db, ticker="AAPL", note="tesis AAPL")
    thesis_service.create_thesis(db, ticker="KO", note="tesis KO")

    all_theses = thesis_service.list_theses(db)
    assert len(all_theses) == 2

    only_aapl = thesis_service.list_theses(db, ticker="aapl")
    assert len(only_aapl) == 1
    assert only_aapl[0]["ticker"] == "AAPL"


def test_delete_thesis(db: Session) -> None:
    seed_database(db)
    created = thesis_service.create_thesis(db, ticker="AAPL", note="tesis")
    thesis_service.delete_thesis(db, created["id"])
    assert thesis_service.list_theses(db) == []


def test_delete_missing_thesis_raises(db: Session) -> None:
    with pytest.raises(crud.NotFoundError):
        thesis_service.delete_thesis(db, 999)
