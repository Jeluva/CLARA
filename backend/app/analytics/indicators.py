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


def ema(prices: Sequence[float], period: int) -> np.ndarray:
    """Exponential moving average, seeded with the first price.

    alpha = 2/(period+1); EMA[0] = price[0]; EMA[t] = a*price[t] + (1-a)*EMA[t-1].
    """
    arr = np.asarray(prices, dtype=float)
    n = arr.size
    out = np.full(n, np.nan)
    if n == 0 or period <= 0:
        return out
    alpha = 2.0 / (period + 1.0)
    out[0] = arr[0]
    for i in range(1, n):
        out[i] = alpha * arr[i] + (1.0 - alpha) * out[i - 1]
    return out


def macd(
    prices: Sequence[float],
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """MACD: (macd_line, signal_line, histogram), all aligned to `prices`.

    macd_line = EMA(fast) - EMA(slow); signal_line = EMA(signal) of macd_line;
    histogram = macd_line - signal_line.
    """
    arr = np.asarray(prices, dtype=float)
    if arr.size == 0:
        empty = np.array([], dtype=float)
        return empty, empty, empty
    macd_line = ema(arr, fast) - ema(arr, slow)
    signal_line = ema(macd_line, signal)
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


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
