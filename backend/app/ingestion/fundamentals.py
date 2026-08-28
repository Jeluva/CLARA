"""Fundamentals ingestion: real data via yfinance, with a mock fallback.

Real mode (USE_MOCK_SOURCES=false): pulls `Ticker.info` for every asset in
silver and extracts valuation/profitability/growth metrics. Unlike prices,
this is a snapshot, not a time series — a single fundamentals row per asset
is overwritten on each run (see `promote._upsert_fundamentals`). Many fields
are legitimately absent for some assets (e.g. a bond has no P/E) — that's
not a data-quality failure, just a smaller payload.

For `asset_class == "bond"` (AR sovereigns), yfinance has nothing useful
(docs/devlog/BACKLOG.md v2 item 1/3) so this also pulls TIR/TEM/TNA/duration/
parity from bonistas.com's public JSON API and merges it into the same
payload (v4 item 1) — one fundamentals row per asset either way, just with a
different set of populated fields depending on asset class.

Mock mode: deterministic per-ticker fixture values, no network.
"""

from __future__ import annotations

import json
import math
from datetime import date, datetime, timezone
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.ingestion.prices import _yf_symbol
from app.quality.promote import PromotionResult, promote_bronze
from app.storage.models.bronze import BronzeRecord
from app.storage.models.silver import Asset

# bonistas.com's own Next.js frontend calls this same endpoint client-side to
# render its bonds table -- public, no auth, no JS execution needed (confirmed
# live 2026-08-28 via Chrome network inspection; see docs/BLOCKED.md history,
# which documents why curl-ing the page HTML directly does NOT work: the
# table itself is populated by this API call after the page mounts).
_BONISTAS_BONDS_URL = "https://bonistas.com/api/bonds"

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
# Bond metrics (bonistas.com) -- yfinance has nothing for AR sovereigns
# ---------------------------------------------------------------------------

def _bond_metrics_from_entry(entry: dict[str, Any]) -> dict[str, Any]:
    """Map one bonistas.com `/api/bonds` entry to our bond_* fields.

    `days_to_coupon` stands in for "próximo cupón" -- the API has no explicit
    next-coupon date/amount field to compute from without guessing at fields
    the site's own frontend derives client-side (dQ/dF/c$m); days-to-coupon
    is the one directly-given, unambiguous number.
    """
    return {
        "bond_tir": _clean_numeric(entry.get("tir")),
        "bond_tem": _clean_numeric(entry.get("mtir")),
        "bond_tna": _clean_numeric(entry.get("tna")),
        "bond_modified_duration": _clean_numeric(entry.get("modified_duration")),
        "bond_parity": _clean_numeric(entry.get("parity")),
        "bond_days_to_coupon": entry.get("days_to_coupon"),
    }


def _fetch_bonistas_metrics(tickers: set[str]) -> dict[str, dict[str, Any]]:
    """TIR/TEM/TNA/duration/parity for the given AR sovereign tickers.

    Each ticker appears twice in the response, once per settlement ("CI" vs
    "24hs" -- next-business-day vs same-day); "24hs" is bonistas.com's own
    default view, so that's the one kept. Network/parse failures return {}
    (same fail-open behaviour as the yfinance path below) rather than raising
    -- a scrape hiccup shouldn't block ingestion for every other asset.

    Also skips non-performing bonds (`performing: false`, e.g. in default or
    a coupon halt) and any entry with `tir` falsy/zero: bonistas.com returns
    an all-zero row in that case (real example: "VSCMC" in the live payload
    captured 2026-08-28) rather than omitting the ticker, and a zero TIR
    would otherwise pass the ">= 0" quality check as if it were a genuine
    measurement instead of "no usable quote right now".
    """
    if not tickers:
        return {}
    try:
        resp = httpx.get(_BONISTAS_BONDS_URL, timeout=10)
        resp.raise_for_status()
        bonds = resp.json()
    except Exception:
        return {}

    out: dict[str, dict[str, Any]] = {}
    for entry in bonds:
        ticker = entry.get("ticker")
        if ticker not in tickers or entry.get("settlement") != "24hs":
            continue
        if not entry.get("performing") or not entry.get("tir"):
            continue
        out[ticker] = _bond_metrics_from_entry(entry)
    return out


# ---------------------------------------------------------------------------
# Real ingestion
# ---------------------------------------------------------------------------

def _run_real_fundamentals_ingestion(db: Session) -> PromotionResult:
    import yfinance as yf

    assets = db.execute(select(Asset)).scalars().all()
    if not assets:
        return PromotionResult(promoted=0, quarantined=0)

    today = _today()
    bond_tickers = {a.ticker.upper() for a in assets if a.asset_class == "bond"}
    bond_metrics = _fetch_bonistas_metrics(bond_tickers)

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
            info = None

        bond_payload = bond_metrics.get(ticker)
        if not info and not bond_payload:
            continue

        payload = _extract_payload(ticker, info or {}, source="yfinance")
        if bond_payload:
            payload.update(bond_payload)
            payload["source"] = "yfinance+bonistas" if info else "bonistas"

        db.add(BronzeRecord(
            source_table="fundamentals",
            source=payload["source"],
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


def _mock_bond_metrics(ticker: str) -> dict[str, Any]:
    """Deterministic bond fixture, same shape as `_bond_metrics_from_entry`,
    so mock mode exercises the bond_* columns without hitting bonistas.com."""
    seed = sum(ord(c) for c in ticker)
    frac = (math.sin(seed + 1) + 1) / 2
    return {
        "bond_tir": round(0.04 + frac * 0.12, 4),
        "bond_tem": round(0.003 + frac * 0.01, 4),
        "bond_tna": round(0.04 + frac * 0.11, 4),
        "bond_modified_duration": round(1 + frac * 6, 2),
        "bond_parity": round(0.6 + frac * 0.4, 4),
        "bond_days_to_coupon": int(10 + frac * 170),
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
        if asset.asset_class == "bond":
            payload.update(_mock_bond_metrics(ticker))
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
