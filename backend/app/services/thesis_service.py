"""Investment thesis journal: why an asset was bought, target/stop, conviction
— and the contrast against what actually happened (see docs/devlog/BACKLOG.md,
v2 item 6). Reuses crud_service's error types so the router maps them the
same way as the rest of data-entry.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.services.crud_service import ConflictError, NotFoundError, _asset_by_ticker
from app.services.market_data import latest_prices
from app.storage.models.silver import Asset, Thesis

_CONVICTIONS = {"baja", "media", "alta"}


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _contrast(thesis: Thesis, current_price: float | None) -> dict:
    """How the thesis is playing out against real prices, if any are known."""
    if current_price is None:
        return {"current_price": None, "return_since_entry": None, "status": "sin_precio"}

    return_since_entry = (
        (current_price / thesis.price_at_entry - 1.0) if thesis.price_at_entry else None
    )

    status = "en_curso"
    if thesis.target_price is not None and current_price >= thesis.target_price:
        status = "objetivo_alcanzado"
    elif thesis.stop_loss is not None and current_price <= thesis.stop_loss:
        status = "stop_tocado"

    return {
        "current_price": round(current_price, 4),
        "return_since_entry": (
            round(return_since_entry, 6) if return_since_entry is not None else None
        ),
        "status": status,
    }


def _to_dict(thesis: Thesis, ticker: str, current_price: float | None) -> dict:
    return {
        "id": thesis.id,
        "ticker": ticker,
        "note": thesis.note,
        "price_at_entry": thesis.price_at_entry,
        "target_price": thesis.target_price,
        "stop_loss": thesis.stop_loss,
        "conviction": thesis.conviction,
        "created_at": thesis.created_at.isoformat(),
        **_contrast(thesis, current_price),
    }


def list_theses(db: Session, ticker: str | None = None) -> list[dict]:
    query = select(Thesis, Asset).join(Asset, Asset.id == Thesis.asset_id)
    if ticker:
        query = query.where(Asset.ticker == ticker.upper())
    query = query.order_by(Thesis.created_at.desc())

    rows = db.execute(query).all()
    prices = latest_prices(db)
    return [_to_dict(thesis, asset.ticker, prices.get(asset.ticker)) for thesis, asset in rows]


def create_thesis(
    db: Session,
    *,
    ticker: str,
    note: str,
    target_price: float | None = None,
    stop_loss: float | None = None,
    conviction: str = "media",
) -> dict:
    if not note.strip():
        raise ConflictError("El motivo de la tesis no puede estar vacío.")
    if conviction not in _CONVICTIONS:
        raise ConflictError(f"conviction debe ser una de: {', '.join(sorted(_CONVICTIONS))}")
    if target_price is not None and target_price <= 0:
        raise ConflictError("target_price debe ser > 0 si se especifica.")
    if stop_loss is not None and stop_loss <= 0:
        raise ConflictError("stop_loss debe ser > 0 si se especifica.")

    asset = _asset_by_ticker(db, ticker.strip().upper())
    prices = latest_prices(db)
    thesis = Thesis(
        asset_id=asset.id,
        note=note.strip(),
        price_at_entry=prices.get(asset.ticker),
        target_price=target_price,
        stop_loss=stop_loss,
        conviction=conviction,
        created_at=_now(),
    )
    db.add(thesis)
    db.commit()
    db.refresh(thesis)
    return _to_dict(thesis, asset.ticker, prices.get(asset.ticker))


def delete_thesis(db: Session, thesis_id: int) -> None:
    thesis = db.get(Thesis, thesis_id)
    if thesis is None:
        raise NotFoundError(f"No existe la tesis id={thesis_id}")
    db.delete(thesis)
    db.commit()
