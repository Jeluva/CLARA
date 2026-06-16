"""Technical indicators — hand-verified."""

from __future__ import annotations

import math

import numpy as np
import pytest

from app.analytics.indicators import ema, macd, rsi, sma


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


def test_ema_hand_computed() -> None:
    # prices [1,2,3], period 2 -> alpha = 2/3, seeded EMA[0]=1
    # EMA[1] = 2/3*2 + 1/3*1 = 5/3 ; EMA[2] = 2/3*3 + 1/3*(5/3) = 2 + 5/9 = 2.5556
    result = ema([1, 2, 3], 2)
    np.testing.assert_allclose(result, [1.0, 5 / 3, 2.0 + 5 / 9], atol=1e-9)


def test_macd_constant_series_is_zero() -> None:
    macd_line, signal_line, hist = macd([5.0] * 40)
    # No price movement -> fast and slow EMA equal -> MACD and histogram are 0.
    assert macd_line[-1] == pytest.approx(0.0, abs=1e-9)
    assert hist[-1] == pytest.approx(0.0, abs=1e-9)
    assert signal_line[-1] == pytest.approx(0.0, abs=1e-9)


def test_macd_uptrend_is_positive() -> None:
    # Strictly rising series: the fast EMA leads the slow EMA -> MACD > 0.
    macd_line, _signal, _hist = macd(list(range(1, 60)))
    assert macd_line[-1] > 0


def test_macd_lengths_align_with_input() -> None:
    prices = list(range(1, 50))
    macd_line, signal_line, hist = macd(prices)
    assert len(macd_line) == len(signal_line) == len(hist) == len(prices)


def test_indicators_handle_short_input() -> None:
    assert np.all(np.isnan(sma([1, 2], 5)))
    assert np.all(np.isnan(rsi([1, 2, 3], period=14)))
