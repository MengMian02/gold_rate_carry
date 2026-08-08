"""Signal construction.

real_yield_momentum(df, lookback: int) -> pd.Series of position weights.
Single-responsibility: takes clean, aligned data in, returns a weight series
out. Written generally (returns a float weight, not a bool) so future signals
can plug into the same interface.
"""

from __future__ import annotations

import pandas as pd


def real_yield_momentum(df: pd.DataFrame, lookback: int) -> pd.Series:
    """Return a series of position weights (float in [0, 1]) aligned to df.index."""
    raise NotImplementedError
