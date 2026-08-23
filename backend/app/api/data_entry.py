"""Data-entry endpoints: CRUD for assets/positions/transactions + ingestion run."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException, Response
from sqlalchemy.orm import Session

from app.api.schemas import (
    AlertCreate,
    AlertOut,
    AssetCreate,
    AssetOut,
    ChannelCreate,
    ChannelOut,
    FreshnessOut,
    IngestionResult,
    PositionCreate,
    PositionOutFull,
    ThesisCreate,
    ThesisOut,
    TransactionCreate,
    TranscriptIngestItem,
)
from app.config import settings
from app.ingestion.fundamentals import run_fundamentals_ingestion
from app.ingestion.news import run_news_ingestion
from app.ingestion.prices import run_price_ingestion
from app.ingestion.transcripts import (
    ingest_external_transcripts,
    run_transcript_ingestion,
)
from app.ingestion.universe import SCREENER_UNIVERSE
from app.services import alert_service
from app.services import asset_service
from app.services import crud_service as crud
from app.services import freshness_service
from app.services import thesis_service
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


@router.get("/api/assets/{ticker}/summary")
def asset_summary(ticker: str, db: Session = Depends(get_db)) -> dict:
    """Aggregated per-asset snapshot for the asset detail page."""
    summary = asset_service.get_asset_summary(db, ticker)
    if summary is None:
        raise HTTPException(status_code=404, detail=f"No existe el activo {ticker}")
    return summary


@router.post("/api/screener/seed")
def seed_screener_universe(db: Session = Depends(get_db)) -> dict:
    """Load the curated screener universe: creates any of its ~30 tickers
    that aren't already tracked (existing assets are left untouched). Run
    price/fundamentals ingestion afterwards to fill in the new rows."""
    created = crud.seed_assets(db, SCREENER_UNIVERSE)
    return {
        "created": created,
        "already_tracked": len(SCREENER_UNIVERSE) - created,
        "message": f"{created} activos nuevos agregados al universo del screener.",
    }


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


# --- Investment thesis journal ------------------------------------------------


@router.get("/api/theses", response_model=list[ThesisOut])
def list_theses(ticker: str | None = None, db: Session = Depends(get_db)) -> list[ThesisOut]:
    """Thesis journal entries, newest first, with the real outcome so far
    (current price, return since entry, target/stop status). Optionally
    filtered to one ticker."""
    return [ThesisOut(**t) for t in thesis_service.list_theses(db, ticker)]


@router.post("/api/theses", response_model=ThesisOut, status_code=201)
def create_thesis(body: ThesisCreate, db: Session = Depends(get_db)) -> ThesisOut:
    try:
        created = thesis_service.create_thesis(db, **body.model_dump())
    except crud.NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except crud.ConflictError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ThesisOut(**created)


@router.delete("/api/theses/{thesis_id}", status_code=204, response_class=Response)
def delete_thesis(thesis_id: int, db: Session = Depends(get_db)) -> Response:
    try:
        thesis_service.delete_thesis(db, thesis_id)
    except crud.NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return Response(status_code=204)


# --- Alerts --------------------------------------------------------------------


@router.get("/api/alerts", response_model=list[AlertOut])
def list_alerts(
    ticker: str | None = None,
    only_triggered: bool = False,
    db: Session = Depends(get_db),
) -> list[AlertOut]:
    """Reglas de alerta (precio, sentimiento, valuación) con su estado
    evaluado en vivo -- reemplaza tener que entrar a mirar cada activo a
    mano para saber si algo cambió."""
    return [
        AlertOut(**a) for a in alert_service.list_alerts(db, ticker, only_triggered)
    ]


@router.post("/api/alerts", response_model=AlertOut, status_code=201)
def create_alert(body: AlertCreate, db: Session = Depends(get_db)) -> AlertOut:
    try:
        created = alert_service.create_alert(db, **body.model_dump())
    except crud.NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except crud.ConflictError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return AlertOut(**created)


@router.delete("/api/alerts/{alert_id}", status_code=204, response_class=Response)
def delete_alert(alert_id: int, db: Session = Depends(get_db)) -> Response:
    try:
        alert_service.delete_alert(db, alert_id)
    except crud.NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return Response(status_code=204)


# --- Ingestion ---------------------------------------------------------------


@router.get("/api/ingestion/freshness", response_model=list[FreshnessOut])
def ingestion_freshness(db: Session = Depends(get_db)) -> list[FreshnessOut]:
    """Cuándo se actualizó por última vez cada fuente (ver
    docs/devlog/BACKLOG.md, v2 item 9) -- relevante por los workarounds de
    yfinance/proxy ya documentados en fase-12: una corrida puede "andar" sin
    haber promovido nada nuevo."""
    return [FreshnessOut(**f) for f in freshness_service.get_freshness(db)]


_INGESTORS = {
    "prices": (run_price_ingestion, "precios"),
    "news": (run_news_ingestion, "noticias"),
    "transcripts": (run_transcript_ingestion, "transcripciones"),
    "fundamentals": (run_fundamentals_ingestion, "fundamentals"),
}


@router.post("/api/ingestion/run", response_model=IngestionResult)
def run_ingestion(
    source: str = "prices", db: Session = Depends(get_db)
) -> IngestionResult:
    """Force-run a source's ingestion now: prices, news or transcripts."""
    entry = _INGESTORS.get(source)
    if entry is None:
        raise HTTPException(
            status_code=400,
            detail=f"Fuente '{source}' no disponible. "
            f"Opciones: {', '.join(_INGESTORS)}.",
        )
    runner, noun = entry
    result = runner(db)
    message = (
        f"Ingestión '{source}': {result.promoted} {noun} promovidas, "
        f"{result.quarantined} en cuarentena."
    )
    if result.errors:
        message += " Errores: " + "; ".join(result.errors)
    return IngestionResult(
        source=source,
        promoted=result.promoted,
        quarantined=result.quarantined,
        message=message,
    )


@router.post("/api/transcripts/ingest-external", response_model=IngestionResult)
def ingest_external_transcripts_endpoint(
    items: list[TranscriptIngestItem],
    db: Session = Depends(get_db),
    x_ingest_secret: str | None = Header(default=None),
) -> IngestionResult:
    """Accept transcripts scraped elsewhere (e.g. a local machine with a
    residential IP) instead of fetching them ourselves — a free workaround
    for YouTube blocking datacenter IPs like this server's."""
    if not settings.ingest_secret:
        raise HTTPException(
            status_code=501,
            detail="INGEST_SECRET no está configurado en el servidor.",
        )
    if x_ingest_secret != settings.ingest_secret:
        raise HTTPException(status_code=401, detail="Secreto inválido.")

    result = ingest_external_transcripts(db, [item.model_dump() for item in items])
    message = (
        f"Ingestión externa: {result.promoted} transcripciones promovidas, "
        f"{result.quarantined} en cuarentena."
    )
    return IngestionResult(
        source="transcripts-external",
        promoted=result.promoted,
        quarantined=result.quarantined,
        message=message,
    )


# --- YouTube channels ----------------------------------------------------------


@router.get("/api/youtube/channels", response_model=list[ChannelOut])
def list_channels(db: Session = Depends(get_db)) -> list[ChannelOut]:
    return [ChannelOut(**c.__dict__) for c in crud.list_channels(db)]


@router.post("/api/youtube/channels", response_model=ChannelOut, status_code=201)
def create_channel(body: ChannelCreate, db: Session = Depends(get_db)) -> ChannelOut:
    try:
        channel = crud.create_channel(db, url_or_handle=body.url_or_handle)
    except crud.ConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return ChannelOut(**channel.__dict__)


@router.delete("/api/youtube/channels/{channel_id}", status_code=204, response_class=Response)
def delete_channel(channel_id: int, db: Session = Depends(get_db)) -> Response:
    try:
        crud.delete_channel(db, channel_id)
    except crud.NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return Response(status_code=204)
