"""Tests for asset_service: the asset detail page's per-ticker snapshot."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.services import asset_service, crud_service
from app.storage.seed import DEFAULT_PORTFOLIO_NAME, seed_database


def test_asset_summary_position_scoped_to_active_portfolio(db: Session) -> None:
    """The position card must reflect the active portfolio, not every
    portfolio merged -- otherwise it can silently disagree with the
    "Tamaño de posición"/"Simular compra" tabs on the same page, which are
    scoped (see docs/devlog/BACKLOG.md, v3 item 1)."""
    seed_database(db)
    portfolios = crud_service.list_portfolios(db)
    default = next(p for p in portfolios if p.name == DEFAULT_PORTFOLIO_NAME)
    other = crud_service.create_portfolio(db, name="Segunda cartera")
    crud_service.create_position(
        db, ticker="SPY", portfolio_id=other.id, quantity=5, avg_cost=100.0
    )

    scoped_to_default = asset_service.get_asset_summary(db, "SPY", default.id)
    scoped_to_other = asset_service.get_asset_summary(db, "SPY", other.id)
    merged = asset_service.get_asset_summary(db, "SPY", None)

    assert scoped_to_default["position"] is None
    assert scoped_to_other["position"]["quantity"] == 5
    assert merged["position"]["quantity"] == 5
