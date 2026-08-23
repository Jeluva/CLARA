"""CRUD for user-entered reference data: assets, positions, transactions.

Business rules (ticker uniqueness, asset existence, positive quantities) live
here and raise typed errors the router maps to HTTP 400/404 — never a bare 500.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.storage.models.silver import (
    Asset,
    Portfolio,
    Position,
    Transaction,
    YoutubeChannel,
)


class NotFoundError(Exception):
    """Referenced entity does not exist."""


class ConflictError(Exception):
    """Violates a uniqueness/business rule."""


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _asset_by_ticker(db: Session, ticker: str) -> Asset:
    asset = db.execute(
        select(Asset).where(Asset.ticker == ticker)
    ).scalar_one_or_none()
    if asset is None:
        raise NotFoundError(f"No existe un activo con ticker '{ticker}'")
    return asset


# --- Assets ------------------------------------------------------------------


def list_assets(db: Session) -> list[Asset]:
    return list(db.execute(select(Asset).order_by(Asset.ticker)).scalars().all())


def create_asset(
    db: Session,
    *,
    ticker: str,
    name: str,
    asset_class: str,
    sector: str,
    country: str,
    currency: str,
) -> Asset:
    ticker = ticker.strip().upper()
    existing = db.execute(
        select(Asset).where(Asset.ticker == ticker)
    ).scalar_one_or_none()
    if existing is not None:
        raise ConflictError(f"Ya existe un activo con ticker '{ticker}'")
    asset = Asset(
        ticker=ticker,
        name=name.strip(),
        asset_class=asset_class.strip(),
        sector=sector.strip() or "Unknown",
        country=country.strip() or "Unknown",
        currency=currency.strip().upper() or "USD",
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return asset


def seed_assets(db: Session, entries: list[dict]) -> int:
    """Create any of `entries` not already loaded (matched by ticker).
    Existing assets are left untouched. Returns how many were created."""
    created = 0
    for entry in entries:
        try:
            create_asset(
                db,
                ticker=entry["ticker"],
                name=entry["name"],
                asset_class=entry["asset_class"],
                sector=entry.get("sector", "Unknown"),
                country=entry.get("country", "Unknown"),
                currency=entry.get("currency", "USD"),
            )
            created += 1
        except ConflictError:
            continue
    return created


def delete_asset(db: Session, asset_id: int) -> None:
    asset = db.get(Asset, asset_id)
    if asset is None:
        raise NotFoundError(f"No existe el activo id={asset_id}")
    db.delete(asset)  # cascades to positions + prices via relationship config
    db.commit()


# --- Portfolios ----------------------------------------------------------------


def list_portfolios(db: Session) -> list[Portfolio]:
    return list(
        db.execute(select(Portfolio).order_by(Portfolio.created_at)).scalars().all()
    )


def create_portfolio(db: Session, *, name: str) -> Portfolio:
    name = name.strip()
    if not name:
        raise ConflictError("El nombre del portfolio no puede estar vacío")
    existing = db.execute(
        select(Portfolio).where(Portfolio.name == name)
    ).scalar_one_or_none()
    if existing is not None:
        raise ConflictError(f"Ya existe un portfolio llamado '{name}'")
    portfolio = Portfolio(name=name)
    db.add(portfolio)
    db.commit()
    db.refresh(portfolio)
    return portfolio


def rename_portfolio(db: Session, portfolio_id: int, *, name: str) -> Portfolio:
    name = name.strip()
    if not name:
        raise ConflictError("El nombre del portfolio no puede estar vacío")
    portfolio = db.get(Portfolio, portfolio_id)
    if portfolio is None:
        raise NotFoundError(f"No existe el portfolio id={portfolio_id}")
    existing = db.execute(
        select(Portfolio).where(Portfolio.name == name, Portfolio.id != portfolio_id)
    ).scalar_one_or_none()
    if existing is not None:
        raise ConflictError(f"Ya existe un portfolio llamado '{name}'")
    portfolio.name = name
    db.commit()
    db.refresh(portfolio)
    return portfolio


# --- Positions ---------------------------------------------------------------


def list_positions(
    db: Session, portfolio_id: int | None = None
) -> list[tuple[Position, Asset]]:
    query = select(Position, Asset).join(Asset, Asset.id == Position.asset_id)
    if portfolio_id is not None:
        query = query.where(Position.portfolio_id == portfolio_id)
    rows = db.execute(query.order_by(Position.id)).all()
    return [(p, a) for p, a in rows]


def create_position(
    db: Session,
    *,
    ticker: str,
    portfolio_id: int,
    quantity: float,
    avg_cost: float,
    opened_at: datetime | None = None,
) -> Position:
    if quantity <= 0 or avg_cost <= 0:
        raise ConflictError("quantity y avg_cost deben ser > 0")
    asset = _asset_by_ticker(db, ticker.strip().upper())
    if db.get(Portfolio, portfolio_id) is None:
        raise NotFoundError(f"No existe el portfolio id={portfolio_id}")
    position = Position(
        asset_id=asset.id,
        portfolio_id=portfolio_id,
        quantity=quantity,
        avg_cost=avg_cost,
        opened_at=opened_at or _now(),
        status="open",
    )
    db.add(position)
    db.commit()
    db.refresh(position)
    return position


def delete_position(db: Session, position_id: int) -> None:
    position = db.get(Position, position_id)
    if position is None:
        raise NotFoundError(f"No existe la posición id={position_id}")
    db.delete(position)
    db.commit()


# --- Transactions ------------------------------------------------------------


def create_transaction(
    db: Session,
    *,
    ticker: str,
    portfolio_id: int,
    type: str,
    quantity: float,
    price: float,
    fee: float = 0.0,
    executed_at: datetime | None = None,
) -> Transaction:
    if quantity <= 0 or price <= 0:
        raise ConflictError("quantity y price deben ser > 0")
    asset = _asset_by_ticker(db, ticker.strip().upper())
    if db.get(Portfolio, portfolio_id) is None:
        raise NotFoundError(f"No existe el portfolio id={portfolio_id}")
    tx = Transaction(
        asset_id=asset.id,
        portfolio_id=portfolio_id,
        type=type,
        quantity=quantity,
        price=price,
        fee=fee,
        executed_at=executed_at or _now(),
    )
    db.add(tx)
    db.commit()
    db.refresh(tx)
    return tx


# --- YouTube channels ---------------------------------------------------------


def list_channels(db: Session) -> list[YoutubeChannel]:
    return list(
        db.execute(select(YoutubeChannel).order_by(YoutubeChannel.added_at)).scalars().all()
    )


def create_channel(db: Session, *, url_or_handle: str) -> YoutubeChannel:
    from app.ingestion.youtube import ChannelNotFoundError, resolve_channel

    try:
        resolved = resolve_channel(url_or_handle)
    except ChannelNotFoundError as exc:
        raise ConflictError(str(exc)) from exc

    existing = db.execute(
        select(YoutubeChannel).where(YoutubeChannel.channel_id == resolved["channel_id"])
    ).scalar_one_or_none()
    if existing is not None:
        raise ConflictError(f"Ya seguís el canal '{resolved['display_name']}'")

    channel = YoutubeChannel(
        channel_id=resolved["channel_id"],
        handle=resolved["handle"],
        display_name=resolved["display_name"],
    )
    db.add(channel)
    db.commit()
    db.refresh(channel)
    return channel


def delete_channel(db: Session, channel_id: int) -> None:
    channel = db.get(YoutubeChannel, channel_id)
    if channel is None:
        raise NotFoundError(f"No existe el canal id={channel_id}")
    db.delete(channel)
    db.commit()
