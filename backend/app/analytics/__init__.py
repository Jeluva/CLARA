"""Analytics: pure functions computing portfolio performance, risk, exposure.

Nothing here touches the database. Inputs are plain numbers / numpy arrays /
pandas objects, so every function is trivially unit-testable and verifiable by
hand. The service layer (Phase 3) feeds these from the silver tables.

Convention: returns are simple (arithmetic) unless stated; annualization uses
252 trading days.
"""

TRADING_DAYS_PER_YEAR = 252
