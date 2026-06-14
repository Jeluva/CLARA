"""Exposure & concentration metrics — hand-verified."""

from __future__ import annotations

import pytest

from app.analytics.exposure import (
    exposure_by_category,
    herfindahl_index,
    top_n_concentration,
)


def test_exposure_by_category_hand_computed() -> None:
    # Tech: 60 + 40 = 100 ; Energy: 100 ; total 200
    # weights Tech 0.5, Energy 0.5
    result = exposure_by_category(
        [("Tech", 60), ("Tech", 40), ("Energy", 100)]
    )
    assert result == {"Tech": pytest.approx(0.5), "Energy": pytest.approx(0.5)}


def test_exposure_weights_sum_to_one() -> None:
    result = exposure_by_category([("A", 30), ("B", 50), ("C", 20)])
    assert sum(result.values()) == pytest.approx(1.0)


def test_herfindahl_hand_computed() -> None:
    # weights 0.5, 0.3, 0.2 -> 0.25 + 0.09 + 0.04 = 0.38
    assert herfindahl_index([0.5, 0.3, 0.2]) == pytest.approx(0.38)


def test_herfindahl_single_holding_is_one() -> None:
    assert herfindahl_index([1.0]) == pytest.approx(1.0)


def test_top_n_concentration_hand_computed() -> None:
    # top 2 of [0.5, 0.3, 0.2] = 0.5 + 0.3 = 0.8
    assert top_n_concentration([0.2, 0.5, 0.3], n=2) == pytest.approx(0.8)


def test_exposure_empty_and_zero() -> None:
    assert exposure_by_category([]) == {}
    assert exposure_by_category([("A", 0)]) == {}
    assert herfindahl_index([]) == 0.0
