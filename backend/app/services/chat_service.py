"""Fundamental-analysis chatbot.

Provider priority:
  1. Anthropic (Claude) — if ANTHROPIC_API_KEY is set.
  2. Google Gemini    — if GEMINI_API_KEY is set (free tier: 1500 req/day).

If neither key is configured the endpoint returns a descriptive message
so the app runs out of the box and lights up the moment a key is added.
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

    news = news_service.list_news(db, ticker)[:5]
    if news:
        avg_sent = float(np.mean([n.sentiment for n in news]))
        lines.append(f"Sentimiento de noticias recientes (promedio): {avg_sent:+.2f}")
        lines.append("Titulares recientes:")
        for n in news:
            lines.append(f"  - [{n.sentiment:+.2f}] {n.title} ({n.source}, {n.published_at})")
    else:
        lines.append("Sin noticias recientes para este activo.")

    return "\n".join(lines)


def _reply_anthropic(context: str, messages: list[ChatMessage]) -> dict:
    import anthropic
    model = settings.chat_model or "claude-haiku-4-5-20251001"
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    system = f"{SYSTEM_PROMPT}\n\nCONTEXTO DEL ACTIVO:\n{context}"
    try:
        response = client.messages.create(
            model=model,
            max_tokens=2000,
            system=system,
            messages=[{"role": m.role, "content": m.content} for m in messages],
        )
        text = "".join(b.text for b in response.content if b.type == "text")
        return {"reply": text.strip(), "configured": True}
    except anthropic.APIError as exc:
        return {"reply": f"No se pudo contactar al modelo: {exc}", "configured": True, "error": True}


def _reply_gemini(context: str, messages: list[ChatMessage]) -> dict | None:
    """Returns None if quota/rate-limit is hit, so caller can fall back."""
    from google import genai
    from google.genai import types
    model = settings.chat_model or "gemini-2.0-flash"
    client = genai.Client(api_key=settings.gemini_api_key)
    system = f"{SYSTEM_PROMPT}\n\nCONTEXTO DEL ACTIVO:\n{context}"

    history = []
    for m in messages[:-1]:
        role = "user" if m.role == "user" else "model"
        history.append(types.Content(role=role, parts=[types.Part(text=m.content)]))

    last_msg = messages[-1].content if messages else ""

    try:
        chat = client.chats.create(
            model=model,
            config=types.GenerateContentConfig(system_instruction=system),
            history=history,
        )
        response = chat.send_message(last_msg)
        return {"reply": response.text.strip(), "configured": True}
    except Exception as exc:
        msg = str(exc)
        if "429" in msg or "RESOURCE_EXHAUSTED" in msg or "quota" in msg.lower():
            return None  # signal: fall back to static
        return {"reply": f"No se pudo contactar al modelo: {exc}", "configured": True, "error": True}


def _static_analysis(db: Session, ticker: str) -> str:
    """Rule-based fundamental snapshot when no LLM is available."""
    ticker = ticker.upper()
    from sqlalchemy import select as sa_select
    asset = db.execute(sa_select(Asset).where(Asset.ticker == ticker)).scalar_one_or_none()
    if asset is None:
        return f"No hay datos para {ticker} en el portfolio."

    lines = [f"## Análisis de {asset.ticker} — {asset.name}\n"]

    # Asset class description
    class_desc = {
        "cedear": "CEDEAR (certificado de depósito argentino que replica una acción extranjera)",
        "equity": "acción local que cotiza en el mercado argentino",
        "etf": "ETF (fondo cotizado que sigue un índice)",
        "bond": "bono soberano o corporativo",
        "fx": "activo de tipo de cambio",
        "crypto": "activo cripto",
    }.get(asset.asset_class, asset.asset_class)
    lines.append(f"**Tipo de instrumento:** {class_desc}  ")
    lines.append(f"**Sector:** {asset.sector} | **País:** {asset.country} | **Moneda:** {asset.currency}\n")

    # Price performance
    series = price_series_by_ticker(db, [ticker]).get(ticker)
    if series is not None and series.size >= 2:
        closes = series.to_numpy(dtype=float)
        rets = daily_returns(closes)
        last = float(closes[-1])
        vol = volatility(rets) * 100
        dd = max_drawdown(closes) * 100
        ret_total = total_return(closes) * 100
        recent = closes[-21:] if closes.size >= 21 else closes
        ret_mes = total_return(recent) * 100

        lines.append("### Precio y rendimiento")
        lines.append(f"- Último precio: **{last:.2f} {asset.currency}**")
        lines.append(f"- Rendimiento período completo: **{ret_total:+.1f}%**")
        lines.append(f"- Rendimiento último mes: **{ret_mes:+.1f}%**")
        lines.append(f"- Volatilidad anualizada: {vol:.1f}%")
        lines.append(f"- Max drawdown: {dd:.1f}%\n")

        risk_label = "bajo" if vol < 20 else "moderado" if vol < 40 else "alto"
        lines.append(f"_Nivel de riesgo estimado: **{risk_label}** (vol. {vol:.1f}% anual)_\n")

    # Position
    pos = next((p for p in _position_inputs(db) if p.ticker == ticker), None)
    if pos is not None:
        mv = pos.quantity * pos.latest_price
        cost = pos.quantity * pos.avg_cost
        pnl = mv - cost
        pnl_pct = (mv / cost - 1) * 100 if cost else 0.0
        lines.append("### Tu posición")
        lines.append(f"- Cantidad: {pos.quantity:g} unidades @ costo {pos.avg_cost:.2f}")
        lines.append(f"- Valor de mercado: {mv:,.2f} {asset.currency}")
        pnl_sign = "ganancia" if pnl >= 0 else "pérdida"
        lines.append(f"- P&L: **{pnl:+,.2f} ({pnl_pct:+.1f}%)** — {pnl_sign} no realizada\n")

    # News sentiment
    news = news_service.list_news(db, ticker)[:5]
    if news:
        avg_sent = float(np.mean([n.sentiment for n in news]))
        sent_label = "positivo" if avg_sent >= 0.05 else "negativo" if avg_sent <= -0.05 else "neutro"
        lines.append("### Sentimiento de noticias recientes")
        lines.append(f"Promedio VADER: **{avg_sent:+.2f}** ({sent_label})\n")
        for n in news[:3]:
            icon = "+" if n.sentiment >= 0.05 else "-" if n.sentiment <= -0.05 else "·"
            lines.append(f"- [{icon}] {n.title} _{n.source}_")
        lines.append("")

    lines.append("---")
    lines.append("_Análisis estático basado en datos del portfolio. Configurá una API key de LLM en `.env` para respuestas conversacionales._")
    return "\n".join(lines)


def fundamental_analysis(
    db: Session, ticker: str, messages: list[ChatMessage]
) -> dict:
    context = _build_asset_context(db, ticker)

    if settings.gemini_api_key:
        result = _reply_gemini(context, messages)
        if result is not None:
            return result

    if settings.anthropic_api_key:
        return _reply_anthropic(context, messages)

    return {
        "reply": _static_analysis(db, ticker),
        "configured": False,
    }
