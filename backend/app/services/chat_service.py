"""Fundamental-analysis chatbot.

Provider priority (first key set wins; falls through on quota/rate-limit):
  1. Groq       — GROQ_API_KEY.    Free: 14.400 req/día. console.groq.com
  2. Qwen       — QWEN_API_KEY.    Free tier. dashscope.aliyuncs.com
  3. Gemini     — GEMINI_API_KEY.  Free tier. aistudio.google.com
  4. Anthropic  — ANTHROPIC_API_KEY. console.anthropic.com
  5. Ollama     — OLLAMA_ENABLED=true, local, sin key. Último fallback
                  antes del estático (docs/devlog/BACKLOG.md, v5 item 3):
                  las 4 APIs cloud arriba tienen mejor calidad/latencia que
                  un modelo 9B cuantizado en CPU, así que solo entra si
                  ninguna de ellas está disponible.
  6. Static     — análisis regla-base, siempre disponible sin key.

Groq y Qwen usan el openai SDK con base_url personalizada (API compatible).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.analytics.returns import daily_returns, total_return
from app.analytics.risk import max_drawdown, volatility
from app.config import settings
from app.services import news_service, portfolio_service, macro_service
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


PORTFOLIO_SYSTEM_PROMPT = """\
Sos un analista de inversiones senior dentro de CLARA, una mesa de análisis de \
portfolio. Tu trabajo es responder preguntas sobre la CARTERA COMPLETA del \
usuario: composición, riesgo, exposición, noticias relevantes y contexto \
macro. Si la pregunta es sobre un activo puntual, el CONTEXTO puede incluir \
una sección de foco con más detalle sobre ese activo.

Reglas:
- Respondé en español, claro y conciso, con estructura (bullets cuando ayude).
- Basate en el CONTEXTO provisto (datos reales de la cartera del usuario). El \
contexto está acotado a lo más relevante para la pregunta -- no incluye todas \
las noticias/transcripciones del sistema, solo las de mayor impacto en los \
activos que tenés en cartera (o del activo puntual si la pregunta lo nombra). \
Si necesitás un dato que no está ahí, decilo en vez de inventarlo.
- Los precios del contexto pueden ser datos de ejemplo (mock); si el usuario \
pregunta por niveles exactos, aclaralo.
- NO des recomendaciones personalizadas de compra/venta ni consejo financiero \
individualizado. Ofrecé análisis educativo y marcos de decisión. Si te piden \
"¿compro o vendo?", explicá los factores a considerar, no una orden.
- Sé honesto sobre la incertidumbre.
"""

_WORD = re.compile(r"[A-Za-zÀ-ÿ0-9]+")

# Hard caps that keep the portfolio context bounded no matter how large the
# portfolio or the news/transcript tables get -- the LLM always sees a fixed,
# small amount of the *most relevant* data instead of a dump that grows
# without limit and eventually blows the context window or drowns the
# signal in noise.
_MAX_POSITIONS_LISTED = 15
_MAX_FOCUS_TICKERS = 3
_MAX_BROAD_NEWS = 6
_MAX_BROAD_TRANSCRIPTS = 3
_MAX_MOVERS = 3


def _mentioned_tickers(text: str, held: dict[str, str]) -> list[str]:
    """Held tickers/asset names the user's latest message references.

    Bounds the deep per-asset dive to what the question is actually about
    (see `_build_asset_context`) instead of running it for every position.
    """
    words = {w.upper() for w in _WORD.findall(text)}
    lower_text = text.lower()
    return [
        ticker
        for ticker, name in held.items()
        if ticker in words or (name and name.lower() in lower_text)
    ]


def _build_portfolio_context(
    db: Session, messages: list[ChatMessage], portfolio_id: int | None = None
) -> str:
    overview = portfolio_service.get_portfolio_overview(db, portfolio_id)
    if not overview.positions:
        return "(La cartera no tiene posiciones abiertas todavía.)"

    risk = portfolio_service.get_risk_metrics(db, portfolio_id)
    exposure = portfolio_service.get_exposure(db, portfolio_id)

    lines: list[str] = ["RESUMEN DE CARTERA"]
    lines.append(
        f"Valor total: {overview.total_value:,.2f} USD | "
        f"P&L total: {overview.total_pnl:+,.2f} ({overview.total_pnl_pct * 100:+.1f}%) | "
        f"P&L diario: {overview.daily_pnl:+,.2f} ({overview.daily_pnl_pct * 100:+.1f}%)"
    )
    lines.append(
        f"Riesgo: volatilidad anualizada {risk.volatility * 100:.1f}%, "
        f"Sharpe {risk.sharpe:.2f}, max drawdown {risk.max_drawdown * 100:.1f}%, "
        f"beta vs SPY {risk.beta:.2f}, concentración top 3 {risk.top3_concentration * 100:.1f}%"
    )
    for dim in ("sector", "country", "currency"):
        breakdown = exposure.get(dim, {})
        if breakdown:
            top = sorted(breakdown.items(), key=lambda kv: kv[1], reverse=True)[:5]
            lines.append(
                f"Exposición por {dim}: "
                + ", ".join(f"{k} {v * 100:.0f}%" for k, v in top)
            )

    sorted_positions = sorted(overview.positions, key=lambda s: s.weight, reverse=True)
    lines.append(f"\nPosiciones ({len(sorted_positions)} en total, por peso):")
    for s in sorted_positions[:_MAX_POSITIONS_LISTED]:
        lines.append(
            f"  - {s.ticker}: peso {s.weight * 100:.1f}%, "
            f"P&L {s.pnl_pct * 100:+.1f}%, sector {s.sector}"
        )
    if len(sorted_positions) > _MAX_POSITIONS_LISTED:
        lines.append(
            f"  … y {len(sorted_positions) - _MAX_POSITIONS_LISTED} posiciones más, "
            "cada una de menor peso que las listadas arriba."
        )

    lines.append("\nCONTEXTO MACRO")
    for m in macro_service.get_macro():
        lines.append(f"  - {m['label']}: {m['value']} {m['unit']} ({m['change_pct']:+.2f}%)")

    held = {s.ticker: "" for s in overview.positions}
    assets = db.execute(
        select(Asset).where(Asset.ticker.in_(held.keys()))
    ).scalars().all()
    held = {a.ticker: a.name for a in assets}

    last_user = next(
        (m.content for m in reversed(messages) if m.role == "user"), ""
    )
    focus = _mentioned_tickers(last_user, held)[:_MAX_FOCUS_TICKERS]

    if focus:
        lines.append(f"\nFOCO EN ACTIVOS MENCIONADOS EN LA PREGUNTA: {', '.join(focus)}")
        for ticker in focus:
            lines.append(f"\n--- {ticker} ---")
            lines.append(_build_asset_context(db, ticker))
        return "\n".join(lines)

    # No specific asset named -> broad-but-bounded signals across the whole
    # portfolio: only the highest-impact items, not everything on file.
    all_news = news_service.list_news(db)
    held_news = [n for n in all_news if n.ticker in held]
    top_news = sorted(held_news, key=lambda n: abs(n.sentiment), reverse=True)[:_MAX_BROAD_NEWS]
    if top_news:
        lines.append("\nNOTICIAS MÁS RELEVANTES DE LA CARTERA (mayor impacto de sentimiento):")
        for n in top_news:
            lines.append(f"  - [{n.sentiment:+.2f}] {n.ticker}: {n.title} ({n.source}, {n.published_at})")

    needles = {t.lower() for t in held} | {n.lower() for n in held.values() if n}
    held_transcripts = [
        t for t in news_service.list_transcripts(db)
        if any(needle in (t["title"] + " " + t["summary"]).lower() for needle in needles)
    ]
    top_transcripts = sorted(
        held_transcripts, key=lambda t: abs(t["sentiment"]), reverse=True
    )[:_MAX_BROAD_TRANSCRIPTS]
    if top_transcripts:
        lines.append("\nTRANSCRIPCIONES DE YOUTUBE MÁS RELEVANTES DE LA CARTERA:")
        for t in top_transcripts:
            lines.append(f"  - [{t['sentiment']:+.2f}] \"{t['title']}\" ({t['source_channel']}): {t['summary']}")

    by_pnl = sorted(overview.positions, key=lambda s: s.pnl_pct, reverse=True)
    gainers = by_pnl[:_MAX_MOVERS]
    losers = list(reversed(by_pnl[-_MAX_MOVERS:])) if len(by_pnl) > _MAX_MOVERS else []
    if gainers:
        lines.append(
            "\nMayores ganadores: "
            + ", ".join(f"{s.ticker} ({s.pnl_pct * 100:+.1f}%)" for s in gainers)
        )
    if losers:
        lines.append(
            "Mayores perdedores: "
            + ", ".join(f"{s.ticker} ({s.pnl_pct * 100:+.1f}%)" for s in losers)
        )

    return "\n".join(lines)


def _reply_openai_compat(
    context: str,
    messages: list[ChatMessage],
    api_key: str,
    base_url: str,
    model: str,
    provider: str,
    system_prompt: str = SYSTEM_PROMPT,
) -> dict | None:
    """Generic OpenAI-compatible call. Returns None on quota/rate-limit."""
    from openai import OpenAI, APIStatusError
    client = OpenAI(api_key=api_key, base_url=base_url)
    system = f"{system_prompt}\n\nCONTEXTO:\n{context}"
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


def _reply_groq(
    context: str, messages: list[ChatMessage], system_prompt: str = SYSTEM_PROMPT
) -> dict | None:
    return _reply_openai_compat(
        context, messages,
        api_key=settings.groq_api_key,
        base_url="https://api.groq.com/openai/v1",
        model=settings.chat_model or settings.groq_model,
        provider="Groq",
        system_prompt=system_prompt,
    )


def _reply_qwen(
    context: str, messages: list[ChatMessage], system_prompt: str = SYSTEM_PROMPT
) -> dict | None:
    return _reply_openai_compat(
        context, messages,
        api_key=settings.qwen_api_key,
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        model=settings.chat_model or settings.qwen_model,
        provider="Qwen",
        system_prompt=system_prompt,
    )


def _reply_anthropic(
    context: str, messages: list[ChatMessage], system_prompt: str = SYSTEM_PROMPT
) -> dict | None:
    import anthropic
    model = settings.chat_model or "claude-haiku-4-5-20251001"
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    system = f"{system_prompt}\n\nCONTEXTO:\n{context}"
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


def _reply_gemini(
    context: str, messages: list[ChatMessage], system_prompt: str = SYSTEM_PROMPT
) -> dict | None:
    """Returns None if quota/rate-limit is hit, so caller can fall back."""
    from google import genai
    from google.genai import types
    model = settings.chat_model or "gemini-2.0-flash"
    client = genai.Client(api_key=settings.gemini_api_key)
    system = f"{system_prompt}\n\nCONTEXTO:\n{context}"

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


_THINK_BLOCK = re.compile(r"<think>.*?</think>", re.DOTALL)
# The model echoes the "/no_think" directive itself at the start of its
# reply in some runs (seen live: "/stop\n\nAquí tienes...", "/\n\n4") --
# likely because the Modelfile has no explicit chat TEMPLATE, so Ollama is
# guessing one for this fine-tune. Strip a leading "/word" line rather than
# chase the template issue (v5 item 3): a wrong-but-harmless leading token
# in the reply is not worth debugging further given the latency/quality
# findings below already rule this out as a default-on fallback.
_LEADING_DIRECTIVE_ECHO = re.compile(r"^/\S*\n+")


def _strip_thinking(text: str) -> str:
    """Qwen3.5 (el modelo cargado en Ollama) es un "thinking model": por
    default envuelve su razonamiento en <think>...</think> antes de la
    respuesta. Si el bloque llegó a cerrarse, lo saca de cualquier parte del
    texto. Si quedó abierto -- el modelo se quedó sin presupuesto de tokens
    pensando y nunca llegó a contestar, visto en vivo con `max_tokens=150`:
    71s y ni un token de respuesta real -- se descarta todo desde el
    "<think>" en adelante, quedándose solo con lo que el modelo haya dicho
    antes (a veces nada). También pela el eco de la directiva "/no_think"
    cuando el modelo la repite como primera línea de la respuesta."""
    text = _THINK_BLOCK.sub("", text)
    if "<think>" in text:
        text = text.split("<think>", 1)[0]
    text = _LEADING_DIRECTIVE_ECHO.sub("", text.strip())
    return text.strip()


def _reply_ollama(
    context: str, messages: list[ChatMessage], system_prompt: str = SYSTEM_PROMPT
) -> dict | None:
    """Local model via Ollama's OpenAI-compatible endpoint -- último
    fallback antes del análisis estático (v5 item 3). A diferencia de
    `_reply_openai_compat`, cualquier fallo (servidor no corriendo, modelo
    no registrado con `ollama create`, timeout) cae a `None` sin
    distinguir por status code: no tiene sentido mostrarle al usuario un
    "Error de Ollama" cuando la razón más probable es simplemente que no
    prendió el servidor local -- lo correcto es caer al estático
    directamente, igual que un proveedor sin API key configurada.

    "/no_think" al final del último mensaje desactiva el modo thinking de
    Qwen3.5 -- verificado en vivo: la misma pregunta tardó 71s+ sin llegar
    a responder con thinking activado (150 tokens, todos de razonamiento,
    finish_reason="length") contra 6-25s con respuesta directa usando
    "/no_think" para una pregunta trivial.

    Aun así, con `/no_think`, un CPU sin GPU corriendo este 9B cuantizado
    mide ~0.68s/token en la máquina de desarrollo (500 tokens, contexto
    real de un activo: 5m42s) -- demasiado lento para una espera cómoda de
    chat sincrónico si se le da rienda suelta a `max_tokens`. `max_tokens`
    se capea bajo para acotar la espera peor-caso a unos pocos minutos en
    vez de diez-mas; `timeout` da margen para que una respuesta lenta pero
    real no se corte antes de llegar. Con ese límite bajo de tokens
    también se vio una respuesta completamente fuera de tema (preguntando
    por AAPL, contestó sobre el tipo de cambio EUR/USD) -- no es solo un
    problema de latencia, la calidad con /no_think en este modelo/hardware
    es floja; documentado en docs/devlog/BACKLOG.md v5 item 3 en vez de
    ocultarlo, así quien lo prenda sabe qué esperar."""
    from openai import OpenAI
    model = settings.chat_model or settings.ollama_model
    client = OpenAI(api_key="ollama", base_url=settings.ollama_base_url, timeout=180.0)
    system = f"{system_prompt}\n\nCONTEXTO:\n{context}"
    api_messages = [{"role": "system", "content": system}]
    api_messages += [{"role": m.role, "content": m.content} for m in messages]
    if api_messages:
        last = api_messages[-1]
        api_messages[-1] = {**last, "content": f"{last['content']}\n/no_think"}
    try:
        response = client.chat.completions.create(
            model=model, messages=api_messages, max_tokens=350,
        )
        text = _strip_thinking(response.choices[0].message.content or "")
        return {"reply": text, "configured": True} if text else None
    except Exception:
        return None


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


def _chat_with_fallback(
    context: str, messages: list[ChatMessage], system_prompt: str
) -> dict | None:
    """Provider chain shared by every chat mode (per-asset, portfolio-wide):
    first configured/working provider wins (see module docstring for the
    priority order and why each one falls through instead of erroring)."""
    if settings.groq_api_key:
        result = _reply_groq(context, messages, system_prompt)
        if result is not None:
            return result

    if settings.qwen_api_key:
        result = _reply_qwen(context, messages, system_prompt)
        if result is not None:
            return result

    if settings.gemini_api_key:
        result = _reply_gemini(context, messages, system_prompt)
        if result is not None:
            return result

    if settings.anthropic_api_key:
        result = _reply_anthropic(context, messages, system_prompt)
        if result is not None:
            return result

    if settings.ollama_enabled:
        result = _reply_ollama(context, messages, system_prompt)
        if result is not None:
            return result

    return None


def fundamental_analysis(
    db: Session, ticker: str, messages: list[ChatMessage]
) -> dict:
    context = _build_asset_context(db, ticker)
    result = _chat_with_fallback(context, messages, SYSTEM_PROMPT)
    if result is not None:
        return result
    return {
        "reply": _static_analysis(db, ticker),
        "configured": False,
    }


def _static_portfolio_analysis(db: Session, portfolio_id: int | None = None) -> str:
    """Rule-based portfolio snapshot when no LLM is available."""
    overview = portfolio_service.get_portfolio_overview(db, portfolio_id)
    if not overview.positions:
        return "La cartera no tiene posiciones abiertas todavía."

    risk = portfolio_service.get_risk_metrics(db, portfolio_id)

    lines = ["## Resumen de cartera\n"]
    lines.append(f"- Valor total: **{overview.total_value:,.2f} USD**")
    lines.append(
        f"- P&L total: **{overview.total_pnl:+,.2f} "
        f"({overview.total_pnl_pct * 100:+.1f}%)**"
    )
    lines.append(
        f"- P&L diario: {overview.daily_pnl:+,.2f} "
        f"({overview.daily_pnl_pct * 100:+.1f}%)\n"
    )
    lines.append("### Riesgo")
    lines.append(f"- Volatilidad anualizada: {risk.volatility * 100:.1f}%")
    lines.append(f"- Sharpe: {risk.sharpe:.2f}")
    lines.append(f"- Max drawdown: {risk.max_drawdown * 100:.1f}%")
    lines.append(f"- Concentración top 3: {risk.top3_concentration * 100:.1f}%\n")

    by_pnl = sorted(overview.positions, key=lambda s: s.pnl_pct, reverse=True)
    lines.append("### Mayores ganadores")
    for s in by_pnl[:3]:
        lines.append(f"- {s.ticker}: {s.pnl_pct * 100:+.1f}%")
    lines.append("\n### Mayores perdedores")
    for s in reversed(by_pnl[-3:]):
        lines.append(f"- {s.ticker}: {s.pnl_pct * 100:+.1f}%")

    lines.append("\n---")
    lines.append(
        "_Análisis estático basado en datos de la cartera. Configurá una API "
        "key de LLM en `.env` para respuestas conversacionales._"
    )
    return "\n".join(lines)


def portfolio_analysis(
    db: Session, messages: list[ChatMessage], portfolio_id: int | None = None
) -> dict:
    """Chat scoped to the whole portfolio instead of one asset -- context is
    bounded (see `_build_portfolio_context`) so it stays useful regardless
    of how many positions/news/transcripts exist."""
    context = _build_portfolio_context(db, messages, portfolio_id)
    result = _chat_with_fallback(context, messages, PORTFOLIO_SYSTEM_PROMPT)
    if result is not None:
        return result
    return {
        "reply": _static_portfolio_analysis(db, portfolio_id),
        "configured": False,
    }
