"""Return calculations: simple daily returns, total, cumulative, time-weighted.

All functions are pure and defensive about short/empty inputs.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np


def daily_returns(prices: Sequence[float]) -> np.ndarray:
    """Simple daily returns r_t = P_t / P_{t-1} - 1.

    Returns an array of length len(prices) - 1. Fewer than 2 prices -> empty.
    """
    arr = np.asarray(prices, dtype=float)
    if arr.size < 2:
        return np.array([], dtype=float)
    return arr[1:] / arr[:-1] - 1.0


def total_return(prices: Sequence[float]) -> float:
    """Total return over the whole series: P_last / P_first - 1."""
    arr = np.asarray(prices, dtype=float)
    if arr.size < 2 or arr[0] == 0:
        return 0.0
    return float(arr[-1] / arr[0] - 1.0)


def cumulative_returns(prices: Sequence[float]) -> np.ndarray:
    """Cumulative return at each point relative to the first price (starts at 0)."""
    arr = np.asarray(prices, dtype=float)
    if arr.size == 0 or arr[0] == 0:
        return np.zeros(arr.size, dtype=float)
    return arr / arr[0] - 1.0


def time_weighted_return(period_returns: Sequence[float]) -> float:
    """Time-weighted return: geometric chaining of sub-period returns.

    TWR = prod(1 + r_i) - 1. Neutralises the effect of cash flows when each
    sub-period return is measured between flows.
    """
    arr = np.asarray(period_returns, dtype=float)
    if arr.size == 0:
        return 0.0
    return float(np.prod(1.0 + arr) - 1.0)
