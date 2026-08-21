"""Fundamentals ingestion: real data via yfinance, with a mock fallback.

Real mode (USE_MOCK_SOURCES=false): pulls `Ticker.info` for every asset in
silver and extracts valuation/profitability/growth metrics. Unlike prices,
this is a snapshot, not a time series — a single fundamentals row per asset
is overwritten on each run (see `promote._upsert_fundamentals`). Many fields
are legitimately absent for some assets (e.g. a bond has no P/E) — that's
not a data-quality failure, just a smaller payload.

Mock mode: deterministic per-ticker fixture values, no network.
"""

from __future__ import annotations

import json
import math
from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.ingestion.prices import _yf_symbol
from app.quality.promote import PromotionResult, promote_bronze
from app.storage.models.bronze import BronzeRecord
from app.storage.models.silver import Asset

# yfinance `Ticker.info` key -> our field name.
_INFO_MAP = {
    "market_cap": "marketCap",
    "pe_ratio": "trailingPE",
    "forward_pe": "forwardPE",
    "pb_ratio": "priceToBook",
    "ev_to_ebitda": "enterpriseToEbitda",
    "peg_ratio": "trailingPegRatio",
    # Verified live against KO (~2.3, matches its real ~2-3% yield): this
    # yfinance version already returns dividendYield as a percent number
    # (2.34 = 2.34%), not a 0-1 fraction — unlike payoutRatio below. This
    # has flipped between yfinance versions before; re-check if it does.
    "dividend_yield": "dividendYield",
    "payout_ratio": "payoutRatio",
    "revenue_growth": "revenueGrowth",
    "earnings_growth": "earningsGrowth",
    "gross_margin": "grossMargins",
    "operating_margin": "operatingMargins",
    "profit_margin": "profitMargins",
    "roe": "returnOnEquity",
    "debt_to_equity": "debtToEquity",
    "analyst_target_mean": "targetMeanPrice",
}


def _today() -> date:
    return datetime.now(timezone.utc).date()


def _clean_numeric(value: Any) -> float | None:
    if value is None:
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(numeric) or math.isinf(numeric) else numeric


def _extract_payload(ticker: str, info: dict[str, Any], *, source: str) -> dict[str, Any]:
    payload: dict[str, Any] = {"ticker": ticker, "source": source}
    for field, info_key in _INFO_MAP.items():
        payload[field] = _clean_numeric(info.get(info_key))
    payload["analyst_recommendation"] = info.get("recommendationKey")

    # Best-effort next earnings date — yfinance exposes this as an epoch
    # timestamp on `.info` (a range start when a window, not a single day).
    ts = info.get("earningsTimestampStart") or info.get("earningsTimestamp")
    if ts:
        try:
            payload["next_earnings_date"] = (
                datetime.fromtimestamp(ts, tz=timezone.utc).date().isoformat()
            )
        except (TypeError, ValueError, OSError):
            payload["next_earnings_date"] = None
    else:
        payload["next_earnings_date"] = None
    return payload


# ---------------------------------------------------------------------------
# Real ingestion
# ---------------------------------------------------------------------------

def _run_real_fundamentals_ingestion(db: Session) -> PromotionResult:
    import yfinance as yf

    assets = db.execute(select(Asset)).scalars().all()
    if not assets:
        return PromotionResult(promoted=0, quarantined=0)

    today = _today()

    for asset in assets:
        ticker = asset.ticker.upper()
        dedupe = f"{ticker}:{today.isoformat()}"
        already = db.execute(
            select(BronzeRecord).where(
                BronzeRecord.source_table == "fundamentals",
                BronzeRecord.dedupe_key == dedupe,
            )
        ).first()
        if already is not None:
            continue

        try:
            info = yf.Ticker(_yf_symbol(ticker)).info
        except Exception:
            continue
        if not info:
            continue

        payload = _extract_payload(ticker, info, source="yfinance")
        db.add(BronzeRecord(
            source_table="fundamentals",
            source="yfinance",
            dedupe_key=dedupe,
            payload=json.dumps(payload),
        ))

    db.commit()
    return promote_bronze(db)


# ---------------------------------------------------------------------------
# Mock ingestion
# ---------------------------------------------------------------------------

def _mock_info(ticker: str) -> dict[str, Any]:
    """Deterministic, plausible-looking fixture keyed by ticker so repeated
    runs are stable and different tickers don't all look identical."""
    seed = sum(ord(c) for c in ticker)
    frac = (math.sin(seed) + 1) / 2  # stable pseudo-random in [0, 1]
    return {
        "marketCap": round(5e9 + frac * 2e12, 2),
        "trailingPE": round(8 + frac * 35, 2),
        "forwardPE": round(7 + frac * 30, 2),
        "priceToBook": round(1 + frac * 12, 2),
        "enterpriseToEbitda": round(4 + frac * 20, 2),
        "trailingPegRatio": round(0.5 + frac * 3, 2),
        "dividendYield": round(frac * 4, 2),
        "payoutRatio": round(frac * 0.8, 2),
        "revenueGrowth": round(-0.05 + frac * 0.4, 4),
        "earningsGrowth": round(-0.1 + frac * 0.6, 4),
        "grossMargins": round(0.2 + frac * 0.6, 4),
        "operatingMargins": round(0.05 + frac * 0.35, 4),
        "profitMargins": round(0.02 + frac * 0.3, 4),
        "returnOnEquity": round(0.05 + frac * 0.35, 4),
        "debtToEquity": round(frac * 150, 2),
        "targetMeanPrice": None,
        "recommendationKey": ("buy", "hold", "sell")[int(frac * 3) % 3],
        "earningsTimestampStart": None,
    }


def run_mock_fundamentals_ingestion(db: Session) -> PromotionResult:
    today = _today()
    assets = db.execute(select(Asset)).scalars().all()

    for asset in assets:
        ticker = asset.ticker.upper()
        dedupe = f"{ticker}:{today.isoformat()}"
        already = db.execute(
            select(BronzeRecord).where(
                BronzeRecord.source_table == "fundamentals",
                BronzeRecord.dedupe_key == dedupe,
            )
        ).scalar_one_or_none()
        if already is not None:
            continue
        payload = _extract_payload(ticker, _mock_info(ticker), source="mock")
        db.add(BronzeRecord(
            source_table="fundamentals",
            source="mock",
            dedupe_key=dedupe,
            payload=json.dumps(payload),
        ))

    db.commit()
    return promote_bronze(db)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def run_fundamentals_ingestion(db: Session) -> PromotionResult:
    if settings.use_mock_sources:
        return run_mock_fundamentals_ingestion(db)
    return _run_real_fundamentals_ingestion(db)
