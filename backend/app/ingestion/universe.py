"""Curated ticker universe for the screener.

Seeded on demand (not automatically) so the user can browse fundamentals and
technicals across names they haven't manually loaded, instead of only what
they already hold or added one by one. Deliberately small and yfinance-
friendly: real US listings (no separate CEDEAR pricing/ratio modeling) plus
the Argentine equities and sovereign bonds already supported via the `.BA`
suffix in `app.ingestion.prices._BA_TICKERS`.

The corporate bonds (ONs) below get no price from yfinance either -- same
gap as the sovereigns -- but bonistas.com's `/api/bonds` payload (already
used for sovereign TIR/duration, v4 item 1) turned out to cover 582
corporate ON tickers too (`bond_family in {"ONS", "ONS-CABLE"}`), not just
the 4 sovereigns it was originally scraped for (docs/devlog/BACKLOG.md v5
item 1). One liquid, real-maturity ("Ley Arg.", not Dollar Linked -- that
family's TIR convention reads oddly around near-term rolls) ticker per
issuer, picked from `performing=True` entries with a plausible TIR
(0-30%) captured live 2026-08-28.
"""

from __future__ import annotations

SCREENER_UNIVERSE: list[dict[str, str]] = [
    # US mega-caps, tracked as "cedear" (matches how they're actually held
    # from Argentina) — technology / consumer
    {"ticker": "AAPL", "name": "Apple Inc.", "asset_class": "cedear", "sector": "Technology", "country": "USA", "currency": "USD"},
    {"ticker": "MSFT", "name": "Microsoft Corp.", "asset_class": "cedear", "sector": "Technology", "country": "USA", "currency": "USD"},
    {"ticker": "GOOGL", "name": "Alphabet Inc.", "asset_class": "cedear", "sector": "Technology", "country": "USA", "currency": "USD"},
    {"ticker": "AMZN", "name": "Amazon.com Inc.", "asset_class": "cedear", "sector": "Consumer Discretionary", "country": "USA", "currency": "USD"},
    {"ticker": "META", "name": "Meta Platforms Inc.", "asset_class": "cedear", "sector": "Technology", "country": "USA", "currency": "USD"},
    {"ticker": "NVDA", "name": "NVIDIA Corp.", "asset_class": "cedear", "sector": "Technology", "country": "USA", "currency": "USD"},
    {"ticker": "TSLA", "name": "Tesla Inc.", "asset_class": "cedear", "sector": "Consumer Discretionary", "country": "USA", "currency": "USD"},
    # US — finance / healthcare / staples / energy / media
    {"ticker": "JPM", "name": "JPMorgan Chase & Co.", "asset_class": "cedear", "sector": "Financials", "country": "USA", "currency": "USD"},
    {"ticker": "V", "name": "Visa Inc.", "asset_class": "cedear", "sector": "Financials", "country": "USA", "currency": "USD"},
    {"ticker": "JNJ", "name": "Johnson & Johnson", "asset_class": "cedear", "sector": "Healthcare", "country": "USA", "currency": "USD"},
    {"ticker": "PG", "name": "Procter & Gamble Co.", "asset_class": "cedear", "sector": "Consumer Staples", "country": "USA", "currency": "USD"},
    {"ticker": "KO", "name": "Coca-Cola Co.", "asset_class": "cedear", "sector": "Consumer Staples", "country": "USA", "currency": "USD"},
    {"ticker": "XOM", "name": "Exxon Mobil Corp.", "asset_class": "cedear", "sector": "Energy", "country": "USA", "currency": "USD"},
    {"ticker": "DIS", "name": "Walt Disney Co.", "asset_class": "cedear", "sector": "Communication Services", "country": "USA", "currency": "USD"},
    {"ticker": "NFLX", "name": "Netflix Inc.", "asset_class": "cedear", "sector": "Communication Services", "country": "USA", "currency": "USD"},
    # Broad ETFs
    {"ticker": "SPY", "name": "SPDR S&P 500 ETF", "asset_class": "etf", "sector": "Diversified", "country": "USA", "currency": "USD"},
    {"ticker": "QQQ", "name": "Invesco QQQ Trust", "asset_class": "etf", "sector": "Diversified", "country": "USA", "currency": "USD"},
    # Merval — Argentine equities
    {"ticker": "GGAL", "name": "Grupo Financiero Galicia", "asset_class": "equity", "sector": "Financials", "country": "Argentina", "currency": "ARS"},
    {"ticker": "YPFD", "name": "YPF S.A.", "asset_class": "equity", "sector": "Energy", "country": "Argentina", "currency": "ARS"},
    {"ticker": "PAMP", "name": "Pampa Energía", "asset_class": "equity", "sector": "Energy", "country": "Argentina", "currency": "ARS"},
    {"ticker": "BMA", "name": "Banco Macro", "asset_class": "equity", "sector": "Financials", "country": "Argentina", "currency": "ARS"},
    {"ticker": "LOMA", "name": "Loma Negra", "asset_class": "equity", "sector": "Materials", "country": "Argentina", "currency": "ARS"},
    {"ticker": "TECO2", "name": "Telecom Argentina", "asset_class": "equity", "sector": "Communication Services", "country": "Argentina", "currency": "ARS"},
    {"ticker": "TXAR", "name": "Ternium Argentina", "asset_class": "equity", "sector": "Materials", "country": "Argentina", "currency": "ARS"},
    # Argentine sovereign bonds
    {"ticker": "AL30", "name": "Bonar 2030 (Ley Argentina)", "asset_class": "bond", "sector": "Government", "country": "Argentina", "currency": "USD"},
    {"ticker": "GD30", "name": "Global 2030 (Ley NY)", "asset_class": "bond", "sector": "Government", "country": "Argentina", "currency": "USD"},
    {"ticker": "AL35", "name": "Bonar 2035 (Ley Argentina)", "asset_class": "bond", "sector": "Government", "country": "Argentina", "currency": "USD"},
    {"ticker": "AE38", "name": "Global 2038 (Ley NY)", "asset_class": "bond", "sector": "Government", "country": "Argentina", "currency": "USD"},
    # Argentine corporate bonds (ONs) -- TIR/duration via bonistas.com, same
    # source and code path as the sovereigns above (v5 item 1).
    {"ticker": "YM37O", "name": "YPF S.A. ON 7.00% 2027", "asset_class": "bond", "sector": "Energy", "country": "Argentina", "currency": "USD"},
    {"ticker": "MGCQO", "name": "Pampa Energía ON 7.25% 2028", "asset_class": "bond", "sector": "Energy", "country": "Argentina", "currency": "USD"},
    {"ticker": "VSCOO", "name": "Vista Energy ON 6.50% 2027", "asset_class": "bond", "sector": "Energy", "country": "Argentina", "currency": "USD"},
    {"ticker": "PN34O", "name": "Pan American Energy ON 4.97% 2027", "asset_class": "bond", "sector": "Energy", "country": "Argentina", "currency": "USD"},
    {"ticker": "IRCNO", "name": "IRSA ON 5.75% 2027", "asset_class": "bond", "sector": "Real Estate", "country": "Argentina", "currency": "USD"},
    {"ticker": "TSC3O", "name": "TGS ON 8.50% 2031", "asset_class": "bond", "sector": "Utilities", "country": "Argentina", "currency": "USD"},
    {"ticker": "NPCCO", "name": "Central Puerto ON 8.00% 2029", "asset_class": "bond", "sector": "Utilities", "country": "Argentina", "currency": "USD"},
    {"ticker": "TTCEO", "name": "Tecpetrol ON 5.50% 2029", "asset_class": "bond", "sector": "Energy", "country": "Argentina", "currency": "USD"},
]
