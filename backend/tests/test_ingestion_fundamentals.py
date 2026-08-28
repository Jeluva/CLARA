"""Tests for fundamentals ingestion: mock mode and the yfinance extraction."""

from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ingestion.fundamentals import (
    _bond_metrics_from_entry,
    _extract_payload,
    _fetch_bonistas_metrics,
    run_mock_fundamentals_ingestion,
)
from app.storage.models.silver import Asset, Fundamentals
from app.storage.seed import seed_database


def test_mock_ingestion_promotes_one_row_per_asset(db: Session) -> None:
    seed_database(db)
    result = run_mock_fundamentals_ingestion(db)

    assert result.quarantined == 0
    rows = db.execute(select(Fundamentals)).scalars().all()
    # One row per seeded asset (SPY included — it's a valid ticker too).
    assert len(rows) == result.promoted
    assert result.promoted > 0


def test_mock_ingestion_is_idempotent_within_the_same_day(db: Session) -> None:
    seed_database(db)
    run_mock_fundamentals_ingestion(db)
    second = run_mock_fundamentals_ingestion(db)

    # Same-day re-run: dedupe key already exists, nothing new to promote.
    assert second.promoted == 0
    rows = db.execute(select(Fundamentals)).scalars().all()
    assert len(rows) > 0


def test_extract_payload_cleans_nan_and_missing_fields() -> None:
    info = {"trailingPE": float("nan"), "marketCap": 1_000.0}
    payload = _extract_payload("AAPL", info, source="yfinance")

    assert payload["pe_ratio"] is None  # NaN -> None
    assert payload["market_cap"] == 1_000.0
    assert payload["forward_pe"] is None  # absent key -> None
    assert payload["next_earnings_date"] is None


def test_mock_ingestion_populates_bond_fields_for_bond_assets(db: Session) -> None:
    seed_database(db)
    run_mock_fundamentals_ingestion(db)

    al30 = db.execute(select(Asset).where(Asset.ticker == "AL30")).scalar_one()
    row = db.execute(
        select(Fundamentals).where(Fundamentals.asset_id == al30.id)
    ).scalar_one()
    assert row.bond_tir is not None
    assert row.bond_modified_duration is not None
    assert row.bond_days_to_coupon is not None

    aapl = db.execute(select(Asset).where(Asset.ticker == "AAPL")).scalar_one()
    equity_row = db.execute(
        select(Fundamentals).where(Fundamentals.asset_id == aapl.id)
    ).scalar_one()
    assert equity_row.bond_tir is None


def test_bond_metrics_from_entry_maps_bonistas_fields() -> None:
    # Shape of a real bonistas.com /api/bonds entry (trimmed to what we use),
    # captured live 2026-08-28.
    entry = {
        "ticker": "AL30",
        "settlement": "24hs",
        "tir": 0.08945736017479948,
        "mtir": 0.0071655285489840015,
        "tna": 0.08598634258780802,
        "modified_duration": 1.9054558194076043,
        "parity": 0.8634396070923167,
        "days_to_coupon": 133,
    }
    metrics = _bond_metrics_from_entry(entry)

    assert metrics["bond_tir"] == pytest.approx(0.08945736017479948)
    assert metrics["bond_tem"] == pytest.approx(0.0071655285489840015)
    assert metrics["bond_tna"] == pytest.approx(0.08598634258780802)
    assert metrics["bond_modified_duration"] == pytest.approx(1.9054558194076043)
    assert metrics["bond_parity"] == pytest.approx(0.8634396070923167)
    assert metrics["bond_days_to_coupon"] == 133


def test_fetch_bonistas_metrics_returns_empty_on_network_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _raise(*args: object, **kwargs: object) -> None:
        raise ConnectionError("no network in tests")

    monkeypatch.setattr("app.ingestion.fundamentals.httpx.get", _raise)
    assert _fetch_bonistas_metrics({"AL30"}) == {}


def test_fetch_bonistas_metrics_filters_ticker_and_settlement(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> list[dict]:
            return [
                {"ticker": "AL30", "settlement": "CI", "tir": 0.05, "performing": True},
                {"ticker": "AL30", "settlement": "24hs", "tir": 0.09, "performing": True},
                {"ticker": "GD30", "settlement": "24hs", "tir": 0.07, "performing": True},
                {"ticker": "VSCMC", "settlement": "24hs", "tir": 0.0, "performing": True},
            ]

    monkeypatch.setattr(
        "app.ingestion.fundamentals.httpx.get", lambda *a, **k: _FakeResponse()
    )
    metrics = _fetch_bonistas_metrics({"AL30", "GD30"})

    assert set(metrics) == {"AL30", "GD30"}
    assert metrics["AL30"]["bond_tir"] == pytest.approx(0.09)  # 24hs, not CI


def test_fetch_bonistas_metrics_skips_non_performing_and_zero_tir(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A halted/defaulted bond comes back with an all-zero row (real example:
    "VSCMC" in a live payload) instead of being omitted -- promoting that as
    if it were a genuine TIR=0% measurement would be worse than showing "—"."""

    class _FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> list[dict]:
            return [
                {
                    "ticker": "AL30",
                    "settlement": "24hs",
                    "tir": 0.0,
                    "performing": True,
                },
                {
                    "ticker": "GD30",
                    "settlement": "24hs",
                    "tir": 0.07,
                    "performing": False,
                },
            ]

    monkeypatch.setattr(
        "app.ingestion.fundamentals.httpx.get", lambda *a, **k: _FakeResponse()
    )
    metrics = _fetch_bonistas_metrics({"AL30", "GD30"})

    assert metrics == {}
