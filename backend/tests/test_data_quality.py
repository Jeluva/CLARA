"""Unit tests for the declarative data-quality checks."""

from __future__ import annotations

from app.quality.checks import run_checks

CTX = {"known_tickers": {"AAPL": 1}}


def test_valid_price_passes() -> None:
    payload = {"ticker": "AAPL", "date": "2026-01-05", "close": 190.0}
    assert run_checks("prices", payload, CTX) is None


def test_negative_price_quarantined() -> None:
    payload = {"ticker": "AAPL", "date": "2026-01-05", "close": -1.0}
    reason = run_checks("prices", payload, CTX)
    assert reason is not None and "close must be > 0" in reason


def test_zero_price_quarantined() -> None:
    payload = {"ticker": "AAPL", "date": "2026-01-05", "close": 0}
    assert run_checks("prices", payload, CTX) is not None


def test_future_date_quarantined() -> None:
    payload = {"ticker": "AAPL", "date": "2999-01-01", "close": 10.0}
    reason = run_checks("prices", payload, CTX)
    assert reason is not None and "future" in reason


def test_unknown_ticker_quarantined() -> None:
    payload = {"ticker": "ZZZZ", "date": "2026-01-05", "close": 10.0}
    reason = run_checks("prices", payload, CTX)
    assert reason is not None and "unknown ticker" in reason


def test_missing_required_field_quarantined() -> None:
    payload = {"ticker": "AAPL", "close": 10.0}  # no date
    reason = run_checks("prices", payload, CTX)
    assert reason is not None and "date" in reason


def test_sentiment_out_of_range_quarantined() -> None:
    payload = {
        "title": "x",
        "url": "http://x",
        "published_at": "2026-01-01",
        "sentiment": 1.5,
    }
    reason = run_checks("news", payload, CTX)
    assert reason is not None and "out of range" in reason


def test_sentiment_in_range_passes() -> None:
    payload = {
        "title": "x",
        "url": "http://x",
        "published_at": "2026-01-01",
        "sentiment": -0.4,
    }
    assert run_checks("news", payload, CTX) is None


def test_unknown_table_quarantined() -> None:
    reason = run_checks("nonexistent", {}, CTX)
    assert reason is not None and "no checks registered" in reason


def test_fundamentals_missing_optional_fields_passes() -> None:
    # A bond has no P/E, no margins — absence isn't a quality failure.
    payload = {"ticker": "AAPL", "market_cap": None, "pe_ratio": None}
    assert run_checks("fundamentals", payload, CTX) is None


def test_fundamentals_negative_market_cap_quarantined() -> None:
    payload = {"ticker": "AAPL", "market_cap": -1.0}
    reason = run_checks("fundamentals", payload, CTX)
    assert reason is not None and "market_cap" in reason


def test_fundamentals_unknown_ticker_quarantined() -> None:
    payload = {"ticker": "ZZZZ", "market_cap": 1000.0}
    reason = run_checks("fundamentals", payload, CTX)
    assert reason is not None and "unknown ticker" in reason


def test_fundamentals_negative_bond_tir_quarantined() -> None:
    payload = {"ticker": "AAPL", "bond_tir": -0.05}
    reason = run_checks("fundamentals", payload, CTX)
    assert reason is not None and "bond_tir" in reason


def test_fundamentals_negative_bond_duration_quarantined() -> None:
    payload = {"ticker": "AAPL", "bond_modified_duration": -1.0}
    reason = run_checks("fundamentals", payload, CTX)
    assert reason is not None and "bond_modified_duration" in reason


def test_fundamentals_positive_bond_metrics_pass() -> None:
    payload = {"ticker": "AAPL", "bond_tir": 0.09, "bond_modified_duration": 1.9}
    assert run_checks("fundamentals", payload, CTX) is None


def test_fundamentals_negative_bond_days_to_coupon_quarantined() -> None:
    payload = {"ticker": "AAPL", "bond_days_to_coupon": -5}
    reason = run_checks("fundamentals", payload, CTX)
    assert reason is not None and "bond_days_to_coupon" in reason
