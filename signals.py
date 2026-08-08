"""Signal construction for the real-yield / GLD strategy.

The work is split into two intentionally separate functions:

  compute_signal()         -- answers "what does the real-yield trend say TODAY?"
                              A pure, rebalance-agnostic daily signal.
  apply_monthly_rebalance() -- answers "given that we only act once a month,
                              what position are we actually HOLDING?"

Keeping these separable means a future non-monthly rebalance scheme (weekly,
threshold-triggered, etc.) can reuse ``compute_signal`` unchanged and only swap
out the rebalancing rule. Do NOT merge them.

No backtest, cost, or benchmark logic lives here.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def compute_signal(df: pd.DataFrame, lookback: int) -> pd.Series:
    """Daily real-yield-momentum signal (sign only, no magnitude threshold).

    For each date, compare ``dfii10_aligned`` to its value ``lookback`` trading
    days earlier (one row = one trading day, since the frame is on GLD's trading
    calendar). Returns a float weight series:

        1.0  if the real yield has FALLEN   (current < value `lookback` days ago)
        0.0  otherwise
        NaN  for the initial `lookback` days (or wherever the comparison is
             undefined) -- "insufficient history" is deliberately NOT collapsed
             into "signal off".

    This is generic: ``lookback`` is required (no silent default), and it works
    for any lookback (e.g. 10/20/40/60). The only project-specific coupling is
    reading the ``dfii10_aligned`` column name.
    """
    current = df["dfii10_aligned"]
    past = current.shift(lookback)  # `lookback` trading days earlier (by row)

    signal = pd.Series(np.where(current < past, 1.0, 0.0), index=df.index, name="signal")
    # Undefined comparison (initial lookback window, or any NaN input) -> NaN,
    # not 0. np.where above turns NaN comparisons into 0.0, so override them here.
    signal[current.isna() | past.isna()] = np.nan
    return signal


def apply_monthly_rebalance(
    daily_signal: pd.Series, trading_dates: pd.DatetimeIndex
) -> pd.Series:
    """Convert a daily signal into the position actually held under monthly rebalancing.

    On each month's first trading day we read that day's daily signal and hold
    that position (1.0 or 0.0) unchanged until the next month's first trading
    day, regardless of what the daily signal does in between. Returns a position
    series aligned to ``trading_dates``, forward-filled from each rebalance date
    to the next.
    """
    trading_dates = pd.DatetimeIndex(trading_dates)
    signal = daily_signal.reindex(trading_dates)

    # First trading day of each month = where the calendar-month period changes.
    periods = trading_dates.to_period("M")
    is_rebalance = np.empty(len(trading_dates), dtype=bool)
    if len(trading_dates) > 0:
        is_rebalance[0] = True
        is_rebalance[1:] = periods[1:] != periods[:-1]
    rebalance_mask = pd.Series(is_rebalance, index=trading_dates)

    # Keep the signal only on rebalance dates, NaN elsewhere, then forward-fill.
    # The single ffill does two jobs:
    #   - holds each month's position to the next rebalance date, and
    #   - ASSUMPTION: if the daily signal is NaN on a rebalance date (insufficient
    #     history), the rebalance value stays NaN and the ffill carries the
    #     PREVIOUS held position forward -- we do NOT treat NaN as 0 (flat).
    # Dates before the first valid signal remain NaN (no prior position to carry);
    # we do not fabricate a position we cannot determine.
    position = signal.where(rebalance_mask).ffill()
    position.name = "position"
    return position
