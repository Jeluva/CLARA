"""Correlation matrix between asset return series.

Detects false diversification: assets that move together don't diversify risk.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import numpy as np
import pandas as pd


def correlation_matrix(
    returns_by_ticker: Mapping[str, Sequence[float]],
) -> pd.DataFrame:
    """Pearson correlation matrix across aligned return series.

    `returns_by_ticker` maps ticker -> equal-length return series. Returns a
    square DataFrame indexed/columned by ticker. A constant series yields NaN
    correlations (no variance to correlate); callers can fill as needed.
    """
    if not returns_by_ticker:
        return pd.DataFrame()
    frame = pd.DataFrame({t: np.asarray(r, dtype=float) for t, r in returns_by_ticker.items()})
    return frame.corr(method="pearson")
