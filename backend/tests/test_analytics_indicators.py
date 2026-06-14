"""Technical indicators — hand-verified."""

from __future__ import annotations

import math

import numpy as np

from app.analytics.indicators import rsi, sma


def test_sma_hand_computed() -> None:
    # window 3 over [1,2,3,4,5]:
    # idx2 = (1+2+3)/3 = 2 ; idx3 = (2+3+4)/3 = 3 ; idx4 = (3+4+5)/3 = 4
    result = sma([1, 2, 3, 4, 5], 3)
    assert math.isnan(result[0]) and math.isnan(result[1])
    np.testing.assert_allclose(result[2:], [2.0, 3.0, 4.0])


def test_rsi_alternating_is_fifty() -> None:
    # Alternating +/-1 over 14 changes: 7 gains of 1, 7 losses of 1.
    # avg_gain = avg_loss = 0.5 -> RS = 1 -> RSI = 50.
    prices = [10, 11] * 8  # 16 points -> 15 changes; last window of 14 is balanced
    result = rsi(prices, period=14)
    assert result[14] == 50.0 or result[15] == 50.0


def test_rsi_all_gains_is_hundred() -> None:
    prices = list(range(1, 20))  # strictly increasing
    result = rsi(prices, period=14)
    assert result[-1] == 100.0


def test_rsi_all_losses_is_zero() -> None:
    prices = list(range(20, 1, -1))  # strictly decreasing
    result = rsi(prices, period=14)
    assert result[-1] == 0.0


def test_indicators_handle_short_input() -> None:
    assert np.all(np.isnan(sma([1, 2], 5)))
    assert np.all(np.isnan(rsi([1, 2, 3], period=14)))
