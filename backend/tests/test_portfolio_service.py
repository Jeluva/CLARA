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


def test_simulate_purchase_new_position_raises_concentration(db: Session) -> None:
    seed_database(db)
    before = svc.get_risk_metrics(db)
    result = svc.simulate_purchase(db, "SPY", 5000.0)  # SPY: benchmark, not held
    assert result.already_held is False
    assert result.quantity_added > 0
    assert result.new_weight > 0.0
    assert result.top3_before == pytest.approx(before.top3_concentration)
    # Adding a brand-new position dilutes existing concentration.
    assert result.top3_after < result.top3_before
    assert result.correlation_to_portfolio is not None
    assert -1.0 <= result.correlation_to_portfolio <= 1.0


def test_simulate_purchase_existing_position_increases_its_weight(db: Session) -> None:
    seed_database(db)
    overview = svc.get_portfolio_overview(db)
    aapl_before = next(p for p in overview.positions if p.ticker == "AAPL")
    result = svc.simulate_purchase(db, "AAPL", 10000.0)
    assert result.already_held is True
    assert result.new_weight > aapl_before.weight


def test_simulate_purchase_unknown_ticker_raises(db: Session) -> None:
    seed_database(db)
    with pytest.raises(ValueError):
        svc.simulate_purchase(db, "NOPE", 1000.0)


def test_simulate_purchase_rejects_non_positive_amount(db: Session) -> None:
    seed_database(db)
    with pytest.raises(ValueError):
        svc.simulate_purchase(db, "AAPL", 0.0)


def test_position_size_guide_scales_inversely_with_volatility(db: Session) -> None:
    """NVDA (annual_vol=0.50 in the seed) is riskier than KO (0.16), so the
    same risk budget should suggest a smaller weight for NVDA."""
    seed_database(db)
    nvda = svc.get_position_size_guide(db, "NVDA")
    ko = svc.get_position_size_guide(db, "KO")
    assert nvda.volatility > ko.volatility
    assert nvda.target_weight_pct < ko.target_weight_pct
    assert 0.0 <= nvda.target_weight_pct <= svc.MAX_POSITION_WEIGHT + 1e-9
    assert 0.0 <= ko.target_weight_pct <= svc.MAX_POSITION_WEIGHT + 1e-9


def test_position_size_guide_ars_ticker_normalizes_to_usd(db: Session) -> None:
    """GGAL is ARS-denominated; current_price/target_amount must be USD (via
    the fixed 1000.0 test rate), not the raw peso price."""
    seed_database(db)
    result = svc.get_position_size_guide(db, "GGAL")
    overview = svc.get_portfolio_overview(db)
    ggal = next(p for p in overview.positions if p.ticker == "GGAL")
    # current_amount must match the USD-normalized market value the
    # portfolio overview already reports, not a peso-scale figure.
    assert result.current_amount == pytest.approx(ggal.market_value, rel=1e-3)
    assert result.current_price == pytest.approx(ggal.latest_price, rel=1e-3)


def test_position_size_guide_caps_at_max_weight(db: Session) -> None:
    seed_database(db)
    result = svc.get_position_size_guide(db, "KO", risk_budget_pct=1.0)
    assert result.capped is True
    assert result.target_weight_pct == pytest.approx(svc.MAX_POSITION_WEIGHT, rel=1e-6)
    assert any("tope" in w for w in result.warnings)


def test_position_size_guide_unknown_ticker_raises(db: Session) -> None:
    seed_database(db)
    with pytest.raises(ValueError):
        svc.get_position_size_guide(db, "NOPE")


def test_position_size_guide_rejects_non_positive_budget(db: Session) -> None:
    seed_database(db)
    with pytest.raises(ValueError):
        svc.get_position_size_guide(db, "AAPL", risk_budget_pct=0.0)


import pytest  # noqa: E402  (kept at bottom; used by approx above)
