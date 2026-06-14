"""Return metrics — every expected value is computed by hand in the comments."""

from __future__ import annotations

import numpy as np
import pytest

from app.analytics.returns import (
    cumulative_returns,
    daily_returns,
    time_weighted_return,
    total_return,
)


def test_daily_returns_hand_computed() -> None:
    # prices 100 -> 110 -> 99
    # r1 = 110/100 - 1 = 0.10 ; r2 = 99/110 - 1 = -0.10
    result = daily_returns([100, 110, 99])
    np.testing.assert_allclose(result, [0.10, -0.10], atol=1e-12)


def test_total_return_hand_computed() -> None:
    # 99/100 - 1 = -0.01
    assert total_return([100, 110, 99]) == pytest.approx(-0.01)


def test_cumulative_returns_hand_computed() -> None:
    # [100/100-1, 110/100-1, 99/100-1] = [0.0, 0.10, -0.01]
    result = cumulative_returns([100, 110, 99])
    np.testing.assert_allclose(result, [0.0, 0.10, -0.01], atol=1e-12)


def test_time_weighted_return_hand_computed() -> None:
    # sub-period returns 0.10, -0.05, 0.02
    # TWR = 1.10 * 0.95 * 1.02 - 1 = 1.0659 - 1 = 0.0659
    assert time_weighted_return([0.10, -0.05, 0.02]) == pytest.approx(0.0659)


def test_returns_handle_short_input() -> None:
    assert daily_returns([100]).size == 0
    assert total_return([]) == 0.0
    assert cumulative_returns([]).size == 0
    assert time_weighted_return([]) == 0.0
