"""Signal-agnostic backtest engine.

Takes ANY position (weight) series + price series and produces an equity curve
and trade log. There is deliberately NO GLD- or DFII10-specific logic here --
it works for any asset and any strategy, so future strategies reuse it
unchanged.

Scope: equity curve + trade log only. No performance metrics (Sharpe, drawdown,
turnover stats) -- those live in evaluate.py. No cost model -- that lives in
costs.py and is injected via ``cost_fn``.
"""

from __future__ import annotations

from typing import Callable

import pandas as pd


def run_backtest(
    prices: pd.Series,
    positions: pd.Series,
    cost_fn: Callable[[pd.Series, pd.Series], pd.Series] | None = None,
) -> dict:
    """Run a gross/net backtest of ``positions`` held against ``prices``.

    Parameters
    ----------
    prices : pd.Series
        Date-indexed price level (e.g. an adjusted close).
    positions : pd.Series
        Date-indexed target weight series (e.g. 0/1 from a monthly-rebalanced
        signal). May carry leading NaN before the strategy has a defined
        position; those are treated as flat (0 weight = in cash) for execution
        -- operationally you hold nothing until the first real position. This is
        an execution choice, not the signal-off/NaN conflation that signals.py
        deliberately avoids at the signal layer.
    cost_fn : callable, optional
        ``cost_fn(positions, prices) -> pd.Series`` of per-date cost drag. If
        None, zero cost is applied (gross-only first pass). The full returned
        series is subtracted per date; cost_fn owns where cost lands (a turnover
        model naturally yields cost only on trade days, while a daily component
        such as an expense ratio applies every day). The engine does not mask
        cost to trade days, so it never silently drops a daily-drag component.

    Returns
    -------
    dict with:
        equity_curve       : net cumulative equity (starts at 1.0)
        daily_returns      : net daily strategy returns
        trade_log          : DataFrame (index=date) of from_position/to_position
                             on every date the position changed
        gross_equity_curve : cumulative equity with zero cost (starts at 1.0)
    """
    prices = prices.sort_index().astype(float)
    # Align positions to the price calendar; undefined positions -> flat (cash).
    positions_exec = positions.reindex(prices.index).astype(float).fillna(0.0)

    # Daily price return; first row is NaN (no prior price).
    price_return = prices.pct_change()

    # No lookahead: today's P&L uses YESTERDAY's end-of-day position. You cannot
    # act on today's rebalance decision and also capture today's return from it.
    gross_daily = (positions_exec.shift(1) * price_return).fillna(0.0)

    # Cost drag (per date). Default: zero.
    if cost_fn is None:
        cost = pd.Series(0.0, index=prices.index)
    else:
        cost = cost_fn(positions, prices).reindex(prices.index).fillna(0.0)

    net_daily = gross_daily - cost

    # Equity curves. day-0 return is 0 (no prior price / flat), so both curves
    # start at exactly 1.0 on the first date.
    gross_equity = (1.0 + gross_daily).cumprod()
    equity = (1.0 + net_daily).cumprod()

    gross_daily.name = "gross_daily_returns"
    net_daily.name = "daily_returns"
    gross_equity.name = "gross_equity_curve"
    equity.name = "equity_curve"

    trade_log = _build_trade_log(positions_exec)

    return {
        "equity_curve": equity,
        "daily_returns": net_daily,
        "trade_log": trade_log,
        "gross_equity_curve": gross_equity,
    }


def _build_trade_log(positions_exec: pd.Series) -> pd.DataFrame:
    """Every date the (execution) position changed, with from/to weights.

    The state before the first date is taken as flat (0 = cash), so entering an
    initial non-zero position is recorded as a trade, while starting flat is not.
    """
    prior = positions_exec.shift(1)
    if len(prior) > 0:
        prior.iloc[0] = 0.0  # flat/cash before the backtest begins
    changed = positions_exec != prior

    trade_log = pd.DataFrame(
        {
            "from_position": prior[changed].to_numpy(),
            "to_position": positions_exec[changed].to_numpy(),
        },
        index=positions_exec.index[changed],
    )
    trade_log.index.name = "date"
    return trade_log
