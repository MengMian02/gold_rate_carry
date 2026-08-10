"""Cost model for the backtest.

Builds a ``cost_fn`` compatible with backtest.py's ``cost_fn`` parameter:
``(positions, prices) -> pd.Series`` of per-date cost drag on the SAME date
index as positions, in the same units as the backtest's daily returns
(fractional, i.e. fraction of portfolio value), so it can be subtracted from
``gross_daily`` directly.

Two components are kept deliberately SEPARATE (not silently blended), because
they behave differently:

  1. transaction cost  -- one-way bps, only on dates the position changes.
  2. expense ratio     -- continuous annual ETF fee, charged every day held.
     DEFAULT 0.0: the backtest's price series (gld_adj_close) is GLD's own traded
     price, which ALREADY reflects the fund's ongoing expense-ratio drag (the
     trust continuously sells gold holdings to pay the fee, which is why GLD's
     return trails spot gold's). Deducting a separate expense ratio on top would
     double-count it. The component is retained for reuse with a price series that
     does NOT already embed fund fees.

The returned object is callable (the summed drag) and, after being called, also
exposes ``.transaction_costs`` and ``.expense_ratio_costs`` as separate series so
gross/net reporting can attribute a result to the component that drove it.

UNITS NOTE: the backtest is normalised (portfolio = 1.0, positions are 0/1
WEIGHTS, P&L is fractional). So a transaction cost is ``bps * |weight change|``
-- a fraction of portfolio value traded -- and is NOT multiplied by the price
level (that would be a dollar cost, ~price-times too large, and inconsistent
with subtracting it from fractional returns). ``prices`` is therefore accepted
only to satisfy the cost_fn signature; it is not needed in weight/return space.

Sensitivity testing (sweeping bps / expense values) belongs in evaluate.py, not
here. This file builds ONE parameterised cost function.
"""

from __future__ import annotations

import pandas as pd

# Standard count of US trading days per year, used to convert the annual expense
# ratio into a daily-equivalent drag.
_TRADING_DAYS_PER_YEAR = 252


class CostFunction:
    """Callable cost model summing a per-trade bps cost and a daily expense drag.

    Call signature matches backtest.py: ``cost_fn(positions, prices) -> pd.Series``.
    After a call, ``.transaction_costs`` and ``.expense_ratio_costs`` hold the two
    component series (and ``.total_costs`` their sum) from that call.
    """

    def __init__(
        self,
        bps: float = 8.0,
        annual_expense_ratio: float = 0.0,
        trading_days_per_year: int = _TRADING_DAYS_PER_YEAR,
    ) -> None:
        self.bps = bps
        self.annual_expense_ratio = annual_expense_ratio
        self.trading_days_per_year = trading_days_per_year
        self.transaction_costs: pd.Series | None = None
        self.expense_ratio_costs: pd.Series | None = None
        self.total_costs: pd.Series | None = None

    def __call__(self, positions: pd.Series, prices: pd.Series) -> pd.Series:
        # Undefined positions (leading NaN before the first signal) are treated
        # as flat (0 = cash), matching backtest.py's execution treatment, so
        # cost timing lines up with the position actually held.
        pos = positions.astype(float).fillna(0.0)

        # --- 1. transaction cost: one-way bps on the WEIGHT traded, trade days only ---
        # State before the series starts is flat (0), so the initial entry into a
        # non-zero position is charged; flat-to-flat / held-to-held days are 0.
        prior = pos.shift(1)
        if len(prior) > 0:
            prior.iloc[0] = 0.0
        turnover = (pos - prior).abs()                     # |weight change|
        transaction = (self.bps / 1e4) * turnover          # bps as a fraction of portfolio

        # --- 2. expense ratio: continuous daily-equivalent drag while holding ---
        # Charged on the position HELD during day t. Per backtest.py's convention
        # the position held through day t (which earns day t's return) is
        # position(t-1), so we base the daily fee on pos.shift(1). Over any
        # holding stretch the total fee is identical to charging pos(t); only the
        # day-alignment shifts, and this alignment matches the return timing.
        daily_rate = self.annual_expense_ratio / self.trading_days_per_year
        held = pos.shift(1).fillna(0.0)
        expense = daily_rate * held

        self.transaction_costs = transaction.rename("transaction_costs")
        self.expense_ratio_costs = expense.rename("expense_ratio_costs")
        self.total_costs = (transaction + expense).rename("total_costs")
        return self.total_costs

    def __repr__(self) -> str:
        return (
            f"CostFunction(bps={self.bps}, "
            f"annual_expense_ratio={self.annual_expense_ratio}, "
            f"trading_days_per_year={self.trading_days_per_year})"
        )


def build_cost_fn(bps: float = 8.0, annual_expense_ratio: float = 0.0) -> CostFunction:
    """Factory returning a configured, callable cost function.

    Parameters
    ----------
    bps : float
        One-way transaction cost in basis points, applied to the weight traded on
        each rebalance. Default 8 bps (midpoint of the 5-10 bps range for liquid
        commodity ETFs). Configurable for cost-sensitivity testing.
    annual_expense_ratio : float
        Annual ETF expense ratio as a fraction, converted to a daily-equivalent
        drag applied while held. DEFAULT 0.0: gld_adj_close (the traded price used
        throughout this project) already reflects GLD's expense-ratio drag, so a
        separate deduction would double-count it. Set this only for a price series
        that does NOT already embed fund fees.

    Returns
    -------
    CostFunction
        Callable with signature ``(positions, prices) -> pd.Series`` (the summed
        drag), also exposing ``.transaction_costs`` / ``.expense_ratio_costs``
        after being called.
    """
    return CostFunction(bps=bps, annual_expense_ratio=annual_expense_ratio)
