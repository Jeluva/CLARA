"""Portfolio snapshot & value series — hand-verified."""

from __future__ import annotations

import pandas as pd
import pytest

from app.analytics.portfolio import (
    PositionInput,
    build_position_snapshots,
    portfolio_value_series,
)


def test_position_snapshot_pnl_and_weight_hand_computed() -> None:
    # Pos1: 10 @ cost 100 -> cost 1000 ; price 120 -> mv 1200 ; pnl 200 (+20%)
    # Pos2: 5  @ cost 50  -> cost  250 ; price 40  -> mv  200 ; pnl -50 (-20%)
    # total mv 1400 -> weights 1200/1400=0.857142..., 200/1400=0.142857...
    positions = [
        PositionInput("AAA", 10, 100, 120),
        PositionInput("BBB", 5, 50, 40),
    ]
    snaps = build_position_snapshots(positions)

    aaa, bbb = snaps
    assert aaa.market_value == pytest.approx(1200)
    assert aaa.cost_basis == pytest.approx(1000)
    assert aaa.pnl == pytest.approx(200)
    assert aaa.pnl_pct == pytest.approx(0.20)
    assert aaa.weight == pytest.approx(1200 / 1400)

    assert bbb.pnl == pytest.approx(-50)
    assert bbb.pnl_pct == pytest.approx(-0.20)
    assert bbb.weight == pytest.approx(200 / 1400)

    # Weights sum to 1.
    assert sum(s.weight for s in snaps) == pytest.approx(1.0)


def test_portfolio_total_pnl_consistent() -> None:
    positions = [
        PositionInput("AAA", 10, 100, 120),
        PositionInput("BBB", 5, 50, 40),
    ]
    snaps = build_position_snapshots(positions)
    total_mv = sum(s.market_value for s in snaps)  # 1400
    total_cost = sum(s.cost_basis for s in snaps)  # 1250
    total_pnl = sum(s.pnl for s in snaps)  # 150
    assert total_mv == pytest.approx(1400)
    assert total_cost == pytest.approx(1250)
    assert total_pnl == pytest.approx(150)
    assert total_mv / total_cost - 1 == pytest.approx(0.12)  # +12%


def test_portfolio_value_series_hand_computed() -> None:
    # 2 shares of AAA and 3 of BBB.
    # day1: 2*100 + 3*10 = 230 ; day2: 2*110 + 3*12 = 256
    dates = pd.to_datetime(["2026-01-01", "2026-01-02"])
    prices = {
        "AAA": pd.Series([100, 110], index=dates),
        "BBB": pd.Series([10, 12], index=dates),
    }
    series = portfolio_value_series({"AAA": 2, "BBB": 3}, prices)
    assert series.iloc[0] == pytest.approx(230)
    assert series.iloc[1] == pytest.approx(256)


def test_portfolio_value_series_forward_fills_gaps() -> None:
    # BBB missing on day2 -> ffill carries 10 ; day2 = 2*110 + 3*10 = 250
    dates = pd.to_datetime(["2026-01-01", "2026-01-02"])
    prices = {
        "AAA": pd.Series([100, 110], index=dates),
        "BBB": pd.Series([10], index=dates[:1]),
    }
    series = portfolio_value_series({"AAA": 2, "BBB": 3}, prices)
    assert series.iloc[1] == pytest.approx(250)


def test_portfolio_value_series_empty() -> None:
    assert portfolio_value_series({}, {}).empty
