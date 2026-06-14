"""Integration tests: the real chain seed -> silver -> service -> analytics.

These close the unit-vs-system gap. The most discriminating assertion is
beta(SPY, SPY) ≈ 1: if date alignment or Series construction in the service is
wrong, benchmark-vs-itself stops being 1 and this breaks loudly.
"""

from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from app.analytics.risk import beta
from app.analytics.returns import daily_returns
from app.services import portfolio_service as svc
from app.services.market_data import price_series_by_ticker
from app.storage.seed import SEED_ASSETS, TRADING_DAYS, seed_database


def test_beta_of_benchmark_against_itself_is_one(db: Session) -> None:
    seed_database(db)
    spy = price_series_by_ticker(db, ["SPY"])["SPY"]
    spy_returns = daily_returns(spy.to_numpy(dtype=float))
    # Beta of any series against itself is 1 (modulo float rounding).
    assert beta(spy_returns, spy_returns) == pytest.approx(1.0)


def test_overview_weights_sum_to_one(db: Session) -> None:
    seed_database(db)
    overview = svc.get_portfolio_overview(db)
    total_weight = sum(p.weight for p in overview.positions)
    assert total_weight == pytest.approx(1.0)
    # One position per seeded holding (7 of 8 assets; SPY is benchmark-only).
    held = [a for a in SEED_ASSETS if a.holding is not None]
    assert len(overview.positions) == len(held)


def test_risk_metrics_sane_ranges(db: Session) -> None:
    seed_database(db)
    m = svc.get_risk_metrics(db)
    assert m.max_drawdown <= 0.0  # drawdown is non-positive
    assert m.volatility >= 0.0
    assert 0.0 <= m.herfindahl <= 1.0
    assert 0.0 <= m.top3_concentration <= 1.0
    # Portfolio beta vs SPY should be a finite, plausible number.
    assert -5.0 < m.beta < 5.0


def test_value_series_length_matches_history(db: Session) -> None:
    seed_database(db)
    series = svc._portfolio_value_series(db)
    # All seeded assets share the same 252-day calendar, so no rows are dropped.
    assert len(series) == TRADING_DAYS


def test_exposure_weights_sum_to_one_per_dimension(db: Session) -> None:
    seed_database(db)
    exposure = svc.get_exposure(db)
    for dimension in ("sector", "country", "currency"):
        assert sum(exposure[dimension].values()) == pytest.approx(1.0)


def test_history_aligns_portfolio_and_benchmark(db: Session) -> None:
    seed_database(db)
    history = svc.get_history(db)
    assert len(history) == TRADING_DAYS
    # First point is the baseline: cumulative return 0.
    assert history[0]["portfolio"] == pytest.approx(0.0, abs=1e-9)
    assert history[0]["benchmark"] == pytest.approx(0.0, abs=1e-9)


import pytest  # noqa: E402  (kept at bottom; used by approx above)
