"""Risk metrics — expected values derived by hand."""

from __future__ import annotations

import numpy as np
import pytest

from app.analytics.risk import beta, max_drawdown, sharpe_ratio, volatility


def test_volatility_hand_computed() -> None:
    # returns [0.10, -0.10], mean 0.
    # sample variance = (0.10^2 + 0.10^2) / (2-1) = 0.02 ; std = sqrt(0.02)
    # annualized = sqrt(0.02) * sqrt(252) = sqrt(5.04) = 2.244994...
    assert volatility([0.10, -0.10]) == pytest.approx(np.sqrt(5.04))


def test_volatility_with_explicit_periods() -> None:
    # Same returns, annualization 1 -> just the sample std = sqrt(0.02)
    assert volatility([0.10, -0.10], periods_per_year=1) == pytest.approx(
        np.sqrt(0.02)
    )


def test_max_drawdown_hand_computed() -> None:
    # prices 100, 120, 90, 110. running max 100,120,120,120.
    # drawdowns: 0, 0, 90/120-1 = -0.25, 110/120-1 = -0.0833
    # max drawdown = -0.25
    assert max_drawdown([100, 120, 90, 110]) == pytest.approx(-0.25)


def test_max_drawdown_monotonic_increasing_is_zero() -> None:
    assert max_drawdown([100, 101, 102, 103]) == pytest.approx(0.0)


def test_sharpe_ratio_hand_computed() -> None:
    # returns [0.01, 0.02, 0.01, 0.02], rf=0.
    # mean = 0.015 ; deviations +/-0.005 ; sample var = (4*0.005^2)/(4-1)
    #   = 0.0001/3 ; std = 0.00577350269
    # Sharpe = 0.015 / 0.00577350269 * sqrt(252)
    #   = 2.59807621 * 15.87450787 = 41.24318...
    assert sharpe_ratio([0.01, 0.02, 0.01, 0.02]) == pytest.approx(
        41.24318, abs=1e-4
    )


def test_sharpe_ratio_constant_series_is_zero() -> None:
    # zero volatility -> defined as 0.0, not inf/NaN
    assert sharpe_ratio([0.01, 0.01, 0.01]) == 0.0


def test_beta_hand_computed() -> None:
    # asset [0.02,-0.01,0.03,0.00], bench [0.01,-0.01,0.02,0.00]
    # cov numerator sum of dev products = 0.0007 ; var bench numerator = 0.0005
    # beta = 0.0007 / 0.0005 = 1.4 (the /(n-1) cancels)
    assert beta(
        [0.02, -0.01, 0.03, 0.00], [0.01, -0.01, 0.02, 0.00]
    ) == pytest.approx(1.4)


def test_beta_zero_variance_benchmark_is_zero() -> None:
    assert beta([0.01, 0.02], [0.0, 0.0]) == 0.0


def test_risk_metrics_handle_short_input() -> None:
    assert volatility([0.01]) == 0.0
    assert max_drawdown([100]) == 0.0
    assert sharpe_ratio([0.01]) == 0.0
    assert beta([0.01], [0.01]) == 0.0
