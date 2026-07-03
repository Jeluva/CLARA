"""Fundamental-analysis chatbot.

Provider priority (first key set wins; falls through on quota/rate-limit):
  1. Groq       — GROQ_API_KEY.    Free: 14.400 req/día. console.groq.com
  2. Qwen       — QWEN_API_KEY.    Free tier. dashscope.aliyuncs.com
  3. Gemini     — GEMINI_API_KEY.  Free tier. aistudio.google.com
  4. Anthropic  — ANTHROPIC_API_KEY. console.anthropic.com
  5. Static     — análisis regla-base, siempre disponible sin key.

Groq y Qwen usan el openai SDK con base_url personalizada (API compatible).
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
from app.storage.models.silver import Asset, Transcript

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

    transcripts = _relevant_transcripts(db, ticker, asset.name)
    if transcripts:
        lines.append("Transcripciones de YouTube relevantes:")
        for t in transcripts:
            lines.append(
                f"  - [{t.sentiment:+.2f}] \"{t.title}\" ({t.source_channel}, "
                f"{t.published_at.date().isoformat()}): {t.summary}"
            )

    return "\n".join(lines)


def _relevant_transcripts(db: Session, ticker: str, asset_name: str) -> list[Transcript]:
    """Recent transcripts whose title/text mention this ticker or asset name."""
    needles = {ticker.lower(), asset_name.lower()}
    rows = db.execute(
        select(Transcript).order_by(Transcript.published_at.desc()).limit(50)
    ).scalars().all()
    matches = [
        t for t in rows
        if any(n in (t.title + " " + t.transcript).lower() for n in needles)
    ]
    return matches[:3]


def _reply_openai_compat(
    context: str,
    messages: list[ChatMessage],
    api_key: str,
    base_url: str,
    model: str,
    provider: str,
) -> dict | None:
    """Generic OpenAI-compatible call. Returns None on quota/rate-limit."""
    from openai import OpenAI, APIStatusError
    client = OpenAI(api_key=api_key, base_url=base_url)
    system = f"{SYSTEM_PROMPT}\n\nCONTEXTO DEL ACTIVO:\n{context}"
    api_messages = [{"role": "system", "content": system}]
    api_messages += [{"role": m.role, "content": m.content} for m in messages]
    try:
        response = client.chat.completions.create(
            model=model,
            messages=api_messages,
            max_tokens=2000,
        )
        text = response.choices[0].message.content or ""
        return {"reply": text.strip(), "configured": True}
    except APIStatusError as exc:
        # Any provider-side failure (quota, rate-limit, invalid/expired key,
        # auth, etc.) falls through to the next provider in the chain rather
        # than surfacing the raw error to the user.
        if exc.status_code in (401, 402, 403, 429):
            return None
        return {"reply": f"Error de {provider}: {exc.message}", "configured": True, "error": True}
    except Exception:
        # Network errors, timeouts, etc. — also fall through.
        return None


def _reply_groq(context: str, messages: list[ChatMessage]) -> dict | None:
    return _reply_openai_compat(
        context, messages,
        api_key=settings.groq_api_key,
        base_url="https://api.groq.com/openai/v1",
        model=settings.chat_model or settings.groq_model,
        provider="Groq",
    )


def _reply_qwen(context: str, messages: list[ChatMessage]) -> dict | None:
    return _reply_openai_compat(
        context, messages,
        api_key=settings.qwen_api_key,
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        model=settings.chat_model or settings.qwen_model,
        provider="Qwen",
    )


def _reply_anthropic(context: str, messages: list[ChatMessage]) -> dict | None:
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
    except anthropic.APIError:
        return None  # fall back to static analysis


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
        if any(
            token in msg
            for token in ("429", "401", "403", "RESOURCE_EXHAUSTED", "API_KEY_INVALID")
        ) or "quota" in msg.lower():
            return None  # signal: fall back to the next provider
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

    transcripts = _relevant_transcripts(db, ticker, asset.name)
    if transcripts:
        lines.append("### Transcripciones de YouTube relevantes")
        for t in transcripts:
            icon = "+" if t.sentiment >= 0.05 else "-" if t.sentiment <= -0.05 else "·"
            lines.append(f"- [{icon}] \"{t.title}\" _{t.source_channel}_: {t.summary}")
        lines.append("")

    lines.append("---")
    lines.append("_Análisis estático basado en datos del portfolio. Configurá una API key de LLM en `.env` para respuestas conversacionales._")
    return "\n".join(lines)


def fundamental_analysis(
    db: Session, ticker: str, messages: list[ChatMessage]
) -> dict:
    context = _build_asset_context(db, ticker)

    if settings.groq_api_key:
        result = _reply_groq(context, messages)
        if result is not None:
            return result

    if settings.qwen_api_key:
        result = _reply_qwen(context, messages)
        if result is not None:
            return result

    if settings.gemini_api_key:
        result = _reply_gemini(context, messages)
        if result is not None:
            return result

    if settings.anthropic_api_key:
        result = _reply_anthropic(context, messages)
        if result is not None:
            return result

    return {
        "reply": _static_analysis(db, ticker),
        "configured": False,
    }
