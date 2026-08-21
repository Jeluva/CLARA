"""Declarative data-quality checks, registered per silver table.

A check is a pure function `(payload, context) -> str | None`: it returns a
human-readable failure reason, or None if the record is fine. The registry
`CHECKS` maps a silver `source_table` to its ordered list of checks. The
promotion engine runs them in order and quarantines on the first failure.

Keeping checks as small pure functions makes them trivially unit-testable and
keeps validation declarative rather than scattered through ingestion code.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import date, datetime, timezone
from typing import Any

# A check receives the record payload and a shared context (e.g. known tickers).
CheckContext = dict[str, Any]
Check = Callable[[dict[str, Any], CheckContext], "str | None"]


def _parse_dt(value: Any) -> datetime | None:
    """Best-effort parse of an ISO datetime/date string or object."""
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime(value.year, value.month, value.day)
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


# --- Generic reusable checks --------------------------------------------------


def check_close_positive(payload: dict[str, Any], _ctx: CheckContext) -> str | None:
    """Prices must be strictly positive."""
    close = payload.get("close")
    if close is None:
        return "close is missing"
    try:
        if float(close) <= 0:
            return f"close must be > 0, got {close}"
    except (TypeError, ValueError):
        return f"close is not numeric: {close!r}"
    return None


def check_date_not_future(field: str) -> Check:
    """Factory: the given date/datetime field must not be in the future."""

    def _check(payload: dict[str, Any], _ctx: CheckContext) -> str | None:
        raw = payload.get(field)
        dt = _parse_dt(raw)
        if dt is None:
            return f"{field} is missing or unparseable: {raw!r}"
        # Compare naive UTC; allow same-day.
        if dt.date() > _now().date():
            return f"{field} is in the future: {raw}"
        return None

    return _check


def check_ticker_exists(payload: dict[str, Any], ctx: CheckContext) -> str | None:
    """The record's ticker must exist in the assets table."""
    ticker = payload.get("ticker")
    if not ticker:
        return "ticker is missing"
    known: dict[str, int] = ctx.get("known_tickers", {})
    if ticker not in known:
        return f"unknown ticker: {ticker}"
    return None


def check_sentiment_range(payload: dict[str, Any], _ctx: CheckContext) -> str | None:
    """Sentiment must be in [-1, 1] when present."""
    sentiment = payload.get("sentiment")
    if sentiment is None:
        return None  # sentiment is optional at ingestion time
    try:
        value = float(sentiment)
    except (TypeError, ValueError):
        return f"sentiment is not numeric: {sentiment!r}"
    if not (-1.0 <= value <= 1.0):
        return f"sentiment out of range [-1, 1]: {value}"
    return None


def check_numeric_if_present(
    field: str, *, minimum: float | None = None, maximum: float | None = None
) -> Check:
    """Factory: when present, the field must be numeric and within bounds.

    Unlike `check_required`, a missing value is fine here — fundamentals
    fields are frequently absent for a given ticker (e.g. a bond has no
    P/E) and that's not a data-quality failure.
    """

    def _check(payload: dict[str, Any], _ctx: CheckContext) -> str | None:
        value = payload.get(field)
        if value is None:
            return None
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            return f"{field} is not numeric: {value!r}"
        if minimum is not None and numeric < minimum:
            return f"{field} must be >= {minimum}, got {numeric}"
        if maximum is not None and numeric > maximum:
            return f"{field} must be <= {maximum}, got {numeric}"
        return None

    return _check


def check_required(*fields: str) -> Check:
    """Factory: each named field must be present and non-empty."""

    def _check(payload: dict[str, Any], _ctx: CheckContext) -> str | None:
        for field in fields:
            if not payload.get(field):
                return f"required field missing: {field}"
        return None

    return _check


# --- Registry: source_table -> ordered checks --------------------------------

CHECKS: dict[str, list[Check]] = {
    "prices": [
        check_required("ticker", "date", "close"),
        check_close_positive,
        check_date_not_future("date"),
        check_ticker_exists,
    ],
    "news": [
        check_required("title", "url", "published_at"),
        check_sentiment_range,
        check_date_not_future("published_at"),
    ],
    "transcripts": [
        check_required("video_id", "title"),
        check_sentiment_range,
    ],
    "fundamentals": [
        check_required("ticker"),
        check_ticker_exists,
        check_numeric_if_present("market_cap", minimum=0),
    ],
}


def run_checks(
    source_table: str, payload: dict[str, Any], context: CheckContext
) -> str | None:
    """Run all checks for a table; return the first failure reason, or None.

    An unknown source_table is itself a failure — we never promote data we
    don't know how to validate.
    """
    checks = CHECKS.get(source_table)
    if checks is None:
        return f"no checks registered for table '{source_table}'"
    for check in checks:
        reason = check(payload, context)
        if reason is not None:
            return reason
    return None
