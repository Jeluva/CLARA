"""Data-entry endpoints: CRUD for assets/positions/transactions + ingestion run."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.api.schemas import (
    AssetCreate,
    AssetOut,
    IngestionResult,
    PositionCreate,
    PositionOutFull,
    TransactionCreate,
)
from app.ingestion.prices import run_mock_price_ingestion
from app.services import crud_service as crud
from app.storage.database import get_db

router = APIRouter(tags=["data-entry"])


# --- Assets ------------------------------------------------------------------


@router.get("/api/assets", response_model=list[AssetOut])
def list_assets(db: Session = Depends(get_db)) -> list[AssetOut]:
    return [AssetOut(**a.__dict__) for a in crud.list_assets(db)]


@router.post("/api/assets", response_model=AssetOut, status_code=201)
def create_asset(body: AssetCreate, db: Session = Depends(get_db)) -> AssetOut:
    try:
        asset = crud.create_asset(db, **body.model_dump())
    except crud.ConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return AssetOut(**asset.__dict__)


@router.delete("/api/assets/{asset_id}", status_code=204, response_class=Response)
def delete_asset(asset_id: int, db: Session = Depends(get_db)) -> Response:
    try:
        crud.delete_asset(db, asset_id)
    except crud.NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return Response(status_code=204)


# --- Positions ---------------------------------------------------------------


@router.get("/api/positions", response_model=list[PositionOutFull])
def list_positions(db: Session = Depends(get_db)) -> list[PositionOutFull]:
    out: list[PositionOutFull] = []
    for position, asset in crud.list_positions(db):
        out.append(
            PositionOutFull(
                id=position.id,
                ticker=asset.ticker,
                quantity=position.quantity,
                avg_cost=position.avg_cost,
                opened_at=position.opened_at,
                status=position.status,
            )
        )
    return out


@router.post("/api/positions", response_model=PositionOutFull, status_code=201)
def create_position(
    body: PositionCreate, db: Session = Depends(get_db)
) -> PositionOutFull:
    try:
        position = crud.create_position(db, **body.model_dump())
    except crud.NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except crud.ConflictError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    # Reload ticker for the response.
    _, asset = next(
        (p, a) for p, a in crud.list_positions(db) if p.id == position.id
    )
    return PositionOutFull(
        id=position.id,
        ticker=asset.ticker,
        quantity=position.quantity,
        avg_cost=position.avg_cost,
        opened_at=position.opened_at,
        status=position.status,
    )


@router.delete(
    "/api/positions/{position_id}", status_code=204, response_class=Response
)
def delete_position(position_id: int, db: Session = Depends(get_db)) -> Response:
    try:
        crud.delete_position(db, position_id)
    except crud.NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return Response(status_code=204)


# --- Transactions ------------------------------------------------------------


@router.post("/api/transactions", status_code=201)
def create_transaction(
    body: TransactionCreate, db: Session = Depends(get_db)
) -> dict:
    try:
        tx = crud.create_transaction(db, **body.model_dump())
    except crud.NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except crud.ConflictError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"id": tx.id, "status": "created"}


# --- Ingestion ---------------------------------------------------------------


@router.post("/api/ingestion/run", response_model=IngestionResult)
def run_ingestion(
    source: str = "prices", db: Session = Depends(get_db)
) -> IngestionResult:
    """Force-run a source's ingestion now. Currently: mock price source."""
    if source != "prices":
        raise HTTPException(
            status_code=400,
            detail=f"Fuente '{source}' aún no disponible (mock).",
        )
    result = run_mock_price_ingestion(db)
    return IngestionResult(
        source=source,
        promoted=result.promoted,
        quarantined=result.quarantined,
        message=(
            f"Ingestión '{source}': {result.promoted} precios promovidos, "
            f"{result.quarantined} en cuarentena."
        ),
    )
