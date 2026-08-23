"""Alert rules: price / sentiment / valuation thresholds evaluated live on
every read (see docs/devlog/BACKLOG.md, v2 item 8). No background job or
notification channel exists yet -- "triggered" means the condition holds
right now, computed the same way `asset_service`/`thesis_service` compute
their own live numbers, so it's always as fresh as the last ingestion run.
Reuses crud_service's error types so the router maps them the same way as
the rest of data-entry.
"""

from __future__ import annotations

from datetime import datetime, timezone

import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.services import news_service
from app.services.crud_service import ConflictError, NotFoundError, _asset_by_ticker
from app.services.market_data import latest_prices
from app.storage.models.silver import Alert, Asset, Fundamentals

_METRICS = {"price", "sentiment", "pe_ratio"}
_CONDITIONS = {"above", "below"}


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _current_value(
    db: Session, asset: Asset, metric: str, prices: dict[str, float]
) -> float | None:
    if metric == "price":
        return prices.get(asset.ticker)
    if metric == "sentiment":
        news = news_service.list_news(db, asset.ticker)
        return float(np.mean([n.sentiment for n in news])) if news else None
    if metric == "pe_ratio":
        fund = db.execute(
            select(Fundamentals).where(Fundamentals.asset_id == asset.id)
        ).scalar_one_or_none()
        return fund.pe_ratio if fund else None
    return None


def _to_dict(alert: Alert, ticker: str, current_value: float | None) -> dict:
    triggered = False
    if alert.active and current_value is not None:
        triggered = (
            current_value >= alert.threshold
            if alert.condition == "above"
            else current_value <= alert.threshold
        )
    status = (
        "inactiva"
        if not alert.active
        else "sin_dato"
        if current_value is None
        else "disparada"
        if triggered
        else "en_seguimiento"
    )
    return {
        "id": alert.id,
        "ticker": ticker,
        "metric": alert.metric,
        "condition": alert.condition,
        "threshold": alert.threshold,
        "active": alert.active,
        "created_at": alert.created_at.isoformat(),
        "current_value": round(current_value, 6) if current_value is not None else None,
        "triggered": triggered,
        "status": status,
    }


def list_alerts(
    db: Session, ticker: str | None = None, only_triggered: bool = False
) -> list[dict]:
    query = select(Alert, Asset).join(Asset, Asset.id == Alert.asset_id)
    if ticker:
        query = query.where(Asset.ticker == ticker.upper())
    query = query.order_by(Alert.created_at.desc())

    rows = db.execute(query).all()
    prices = latest_prices(db)
    out = [
        _to_dict(alert, asset.ticker, _current_value(db, asset, alert.metric, prices))
        for alert, asset in rows
    ]
    if only_triggered:
        out = [a for a in out if a["triggered"]]
    return out


def create_alert(
    db: Session, *, ticker: str, metric: str, condition: str, threshold: float
) -> dict:
    if metric not in _METRICS:
        raise ConflictError(f"metric debe ser una de: {', '.join(sorted(_METRICS))}")
    if condition not in _CONDITIONS:
        raise ConflictError(f"condition debe ser una de: {', '.join(sorted(_CONDITIONS))}")

    asset = _asset_by_ticker(db, ticker.strip().upper())
    alert = Alert(
        asset_id=asset.id,
        metric=metric,
        condition=condition,
        threshold=threshold,
        active=True,
        created_at=_now(),
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)
    prices = latest_prices(db)
    return _to_dict(alert, asset.ticker, _current_value(db, asset, metric, prices))


def delete_alert(db: Session, alert_id: int) -> None:
    alert = db.get(Alert, alert_id)
    if alert is None:
        raise NotFoundError(f"No existe la alerta id={alert_id}")
    db.delete(alert)
    db.commit()
