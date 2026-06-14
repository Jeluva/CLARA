"""Risk metrics: annualized volatility, max drawdown, Sharpe ratio, beta.

Sample statistics use ddof=1 (unbiased). Annualization uses 252 trading days.
Edge cases (too-short or constant series) return 0.0 rather than NaN/inf so the
serving layer never has to special-case divide-by-zero.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np

from app.analytics import TRADING_DAYS_PER_YEAR


def volatility(
    returns: Sequence[float], periods_per_year: int = TRADING_DAYS_PER_YEAR
) -> float:
    """Annualized volatility = sample stddev of returns * sqrt(periods/year)."""
    arr = np.asarray(returns, dtype=float)
    if arr.size < 2:
        return 0.0
    return float(np.std(arr, ddof=1) * np.sqrt(periods_per_year))


def max_drawdown(prices: Sequence[float]) -> float:
    """Maximum drawdown as a non-positive fraction (e.g. -0.25 = -25%).

    The largest peak-to-trough decline: min_t (P_t / running_max_t - 1).
    """
    arr = np.asarray(prices, dtype=float)
    if arr.size < 2:
        return 0.0
    running_max = np.maximum.accumulate(arr)
    drawdowns = arr / running_max - 1.0
    return float(drawdowns.min())


def sharpe_ratio(
    returns: Sequence[float],
    risk_free_rate: float = 0.0,
    periods_per_year: int = TRADING_DAYS_PER_YEAR,
) -> float:
    """Annualized Sharpe ratio.

    Computed from per-period excess returns:
        Sharpe = mean(excess) / std(excess) * sqrt(periods/year)
    where excess = returns - (risk_free_rate / periods_per_year). A constant
    series (zero volatility) returns 0.0.
    """
    arr = np.asarray(returns, dtype=float)
    if arr.size < 2:
        return 0.0
    rf_per_period = risk_free_rate / periods_per_year
    excess = arr - rf_per_period
    sd = np.std(excess, ddof=1)
    if sd == 0:
        return 0.0
    return float(np.mean(excess) / sd * np.sqrt(periods_per_year))


def beta(
    asset_returns: Sequence[float], benchmark_returns: Sequence[float]
) -> float:
    """Beta of an asset vs. a benchmark = cov(asset, bench) / var(bench).

    Series must align (same length). Zero benchmark variance returns 0.0.
    """
    a = np.asarray(asset_returns, dtype=float)
    b = np.asarray(benchmark_returns, dtype=float)
    if a.size != b.size or a.size < 2:
        return 0.0
    var_b = np.var(b, ddof=1)
    if var_b == 0:
        return 0.0
    cov_ab = np.cov(a, b, ddof=1)[0, 1]
    return float(cov_ab / var_b)
