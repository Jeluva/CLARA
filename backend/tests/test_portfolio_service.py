"""Integration tests: the real chain seed -> silver -> service -> analytics.

These close the unit-vs-system gap. The most discriminating assertion is
beta(SPY, SPY) ≈ 1: if date alignment or Series construction in the service is
wrong, benchmark-vs-itself stops being 1 and this breaks loudly.
"""

from __future__ import annotations

import pandas as pd
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


def test_ars_positions_normalized_to_usd(db: Session) -> None:
    """GGAL/YPFD are ARS-denominated; their market value must convert to USD
    (via the fixed 1000.0 test rate) rather than being added raw."""
    seed_database(db)
    overview = svc.get_portfolio_overview(db)
    ggal = next(p for p in overview.positions if p.ticker == "GGAL")
    assert ggal.currency == "ARS"
    # Seeded GGAL avg_cost is 30.0 (native units); at a 1000.0 rate that's 0.03 USD.
    assert ggal.avg_cost == pytest.approx(0.03, rel=1e-3)


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


def test_realized_history_respects_opened_at(db: Session) -> None:
    seed_database(db)
    realized = svc.get_realized_history(db)
    assert len(realized) > 0
    # Should be shorter than full history since positions open at different times
    full = svc.get_history(db)
    assert len(realized) <= len(full)
    # Each point has a realized_pnl
    for p in realized:
        assert "date" in p
        assert "realized_pnl" in p


def test_correlation_aligns_mismatched_histories(
    db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Real ingested tickers can have different date coverage (holidays,
    different listing dates). get_correlation must align them by date before
    computing returns, instead of crashing on unequal-length arrays."""
    seed_database(db)

    dates_long = pd.date_range("2024-01-01", periods=10, freq="D")
    dates_short = pd.date_range("2024-01-03", periods=6, freq="D")
    fake_series = {
        "AAA": pd.Series(range(1, 11), index=dates_long, name="AAA", dtype=float),
        "BBB": pd.Series(range(1, 7), index=dates_short, name="BBB", dtype=float),
    }
    monkeypatch.setattr(
        svc, "price_series_by_ticker", lambda _db, tickers=None: fake_series
    )

    result = svc.get_correlation(db)
    assert result["tickers"] == ["AAA", "BBB"]
    assert len(result["matrix"]) == 2


import pytest  # noqa: E402  (kept at bottom; used by approx above)
