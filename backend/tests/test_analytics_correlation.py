"""Correlation matrix — verified against known perfect (anti)correlations."""

from __future__ import annotations

import pytest

from app.analytics.correlation import correlation_matrix


def test_perfect_positive_correlation() -> None:
    # B = 2*A -> correlation exactly 1
    m = correlation_matrix({"A": [1, 2, 3], "B": [2, 4, 6]})
    assert m.loc["A", "B"] == pytest.approx(1.0)
    assert m.loc["A", "A"] == pytest.approx(1.0)


def test_perfect_negative_correlation() -> None:
    # B is A reversed and decreasing -> correlation -1
    m = correlation_matrix({"A": [1, 2, 3], "B": [3, 2, 1]})
    assert m.loc["A", "B"] == pytest.approx(-1.0)


def test_matrix_is_symmetric() -> None:
    m = correlation_matrix(
        {"A": [1, 2, 1, 3], "B": [2, 1, 0, 2], "C": [5, 5, 6, 4]}
    )
    assert m.loc["A", "B"] == pytest.approx(m.loc["B", "A"])
    assert list(m.columns) == ["A", "B", "C"]


def test_empty_input_returns_empty_frame() -> None:
    assert correlation_matrix({}).empty
