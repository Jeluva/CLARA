"""Fundamental-analysis chatbot backed by Claude.

Builds a compact, factual context for one asset (price performance, the user's
position, risk, recent news + sentiment) and asks Claude to reason about it as an
equity analyst. The model never sees the network — only the context we assemble
from our own silver/gold data.

If no ANTHROPIC_API_KEY is configured, the endpoint returns a documented message
instead of erroring, so the app runs out of the box and lights up the moment a
key is added.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.analytics.returns import daily_returns, total_return
from app.analytics.risk import max_drawdown, volatility
from app.config import settings
from app.services import news_service
from app.services.market_data import price_series_by_ticker
from app.services.portfolio_service import _position_inputs
from app.storage.models.silver import Asset

SYSTEM_PROMPT = """\
Sos un analista de inversiones senior dentro de CLARA, una mesa de análisis de \
portfolio. Tu trabajo es ayudar al usuario a hacer **análisis fundamental** del \
activo en cuestión: qué tipo de empresa/instrumento es, qué impulsa su valor, \
qué dicen los datos y las noticias recientes, riesgos y catalizadores.

Reglas:
- Respondé en español, claro y conciso, con estructura (bullets cuando ayude).
- Basate en el CONTEXTO provisto (datos reales del portfolio del usuario) y en \
tu conocimiento general del activo. Si algo no está en el contexto, decilo.
- Los precios del contexto pueden ser datos de ejemplo (mock); si el usuario \
pregunta por niveles exactos, aclaralo.
- NO des recomendaciones personalizadas de compra/venta ni consejo financiero \
individualizado. Ofrecé análisis educativo y marcos de decisión. Si te piden \
"¿compro o vendo?", explicá los factores a considerar, no una orden.
- Sé honesto sobre la incertidumbre.
"""


@dataclass
class ChatMessage:
    role: str  # "user" | "assistant"
    content: str


def _build_asset_context(db: Session, ticker: str) -> str:
    ticker = ticker.upper()
    asset = db.execute(
        select(Asset).where(Asset.ticker == ticker)
    ).scalar_one_or_none()
    if asset is None:
        return f"(No hay datos para el ticker {ticker} en el portfolio.)"

    lines: list[str] = [
        f"Activo: {asset.ticker} — {asset.name}",
        f"Clase: {asset.asset_class} | Sector: {asset.sector} | "
        f"País: {asset.country} | Moneda: {asset.currency}",
    ]

    # Price performance.
    series = price_series_by_ticker(db, [ticker]).get(ticker)
    if series is not None and series.size >= 2:
        closes = series.to_numpy(dtype=float)
        rets = daily_returns(closes)
        last = float(closes[-1])
        recent = closes[-21:] if closes.size >= 21 else closes
        lines += [
            f"Último precio: {last:.2f} {asset.currency}",
            f"Rendimiento del período ({series.size} ruedas): "
            f"{total_return(closes) * 100:+.1f}%",
            f"Rendimiento ~1 mes: {total_return(recent) * 100:+.1f}%",
            f"Volatilidad anualizada: {volatility(rets) * 100:.1f}%",
            f"Max drawdown del período: {max_drawdown(closes) * 100:.1f}%",
        ]

    # Position (if held).
    pos = next(
        (p for p in _position_inputs(db) if p.ticker == ticker), None
    )
    if pos is not None:
        mv = pos.quantity * pos.latest_price
        cost = pos.quantity * pos.avg_cost
        pnl_pct = (mv / cost - 1) * 100 if cost else 0.0
        lines += [
            f"Posición del usuario: {pos.quantity:g} unidades @ costo "
            f"{pos.avg_cost:.2f} (P&L {pnl_pct:+.1f}%)",
        ]
    else:
        lines.append("El usuario no tiene posición abierta en este activo.")

    # Recent news + sentiment.
    news = news_service.list_news(db, ticker)[:5]
    if news:
        avg_sent = float(np.mean([n.sentiment for n in news]))
        lines.append(
            f"Sentimiento de noticias recientes (promedio): {avg_sent:+.2f}"
        )
        lines.append("Titulares recientes:")
        for n in news:
            lines.append(
                f"  - [{n.sentiment:+.2f}] {n.title} ({n.source}, {n.published_at})"
            )
    else:
        lines.append("Sin noticias recientes para este activo.")

    return "\n".join(lines)


def fundamental_analysis(
    db: Session, ticker: str, messages: list[ChatMessage]
) -> dict:
    """Answer the user's question about an asset, grounded in its context."""
    context = _build_asset_context(db, ticker)

    if not settings.anthropic_api_key:
        return {
            "reply": (
                "El chatbot de análisis fundamental necesita una API key de "
                "Anthropic para funcionar. Configurá `ANTHROPIC_API_KEY` en "
                "`backend/.env` y reiniciá el backend.\n\n"
                "Mientras tanto, este es el contexto que CLARA arma para "
                f"**{ticker.upper()}** y que el modelo usaría:\n\n```\n{context}\n```"
            ),
            "configured": False,
        }

    # Import here so the SDK is only needed when a key is set.
    import anthropic

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    system = f"{SYSTEM_PROMPT}\n\nCONTEXTO DEL ACTIVO:\n{context}"

    api_messages = [{"role": m.role, "content": m.content} for m in messages]
    try:
        response = client.messages.create(
            model=settings.chat_model,
            max_tokens=2000,
            system=system,
            messages=api_messages,
        )
    except anthropic.APIError as exc:  # surface a clean message, never a 500
        return {
            "reply": f"No se pudo contactar al modelo: {exc}",
            "configured": True,
            "error": True,
        }

    text = "".join(
        block.text for block in response.content if block.type == "text"
    )
    return {"reply": text.strip(), "configured": True}
