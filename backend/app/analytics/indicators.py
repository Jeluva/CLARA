"""Technical indicators: simple moving average and RSI.

Pure functions over price arrays. Leading positions that lack enough history are
returned as NaN so series stay aligned with the price dates.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np


def sma(prices: Sequence[float], window: int) -> np.ndarray:
    """Simple moving average. First `window-1` entries are NaN."""
    arr = np.asarray(prices, dtype=float)
    n = arr.size
    out = np.full(n, np.nan)
    if window <= 0 or n < window:
        return out
    cumsum = np.cumsum(arr)
    out[window - 1] = cumsum[window - 1] / window
    out[window:] = (cumsum[window:] - cumsum[:-window]) / window
    return out


def rsi(prices: Sequence[float], period: int = 14) -> np.ndarray:
    """Relative Strength Index over `period` using simple average gain/loss.

    RSI = 100 - 100/(1+RS), RS = avg_gain / avg_loss over the window. When there
    are no losses in the window, RSI is 100; when no gains, 0. First `period`
    entries are NaN (not enough changes yet).
    """
    arr = np.asarray(prices, dtype=float)
    n = arr.size
    out = np.full(n, np.nan)
    if n <= period:
        return out

    deltas = np.diff(arr)
    gains = np.where(deltas > 0, deltas, 0.0)
    losses = np.where(deltas < 0, -deltas, 0.0)

    for i in range(period, n):
        window_gains = gains[i - period : i]
        window_losses = losses[i - period : i]
        avg_gain = window_gains.mean()
        avg_loss = window_losses.mean()
        if avg_loss == 0:
            out[i] = 100.0 if avg_gain > 0 else 50.0
        elif avg_gain == 0:
            out[i] = 0.0
        else:
            rs = avg_gain / avg_loss
            out[i] = 100.0 - 100.0 / (1.0 + rs)
    return out
