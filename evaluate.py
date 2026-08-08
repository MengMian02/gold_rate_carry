"""Evaluation tools: in-sample parameter-grid selection + random benchmark.

This module wires the project pipeline (signals -> monthly rebalance -> backtest
-> costs) and scores candidate lookbacks on an IN-SAMPLE window only. Performance
metrics are computed with QuantStats.

Selection is deliberately confined to the IS window: the signal is computed on
the FULL merged frame (so the lookback burn-in uses real pre-IS data rather than
being truncated), the whole pipeline runs, and only THEN are daily returns
filtered to [is_start, is_end] before any metric is computed. Nothing outside the
IS window influences a reported IS metric.

Out-of-sample and regime-split evaluation are intentionally NOT here -- they come
after N is chosen, as separate functions.

Reproducibility: the random benchmark uses a fixed seed (see _RANDOM_SEED).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import quantstats as qs

import backtest
import costs
import signals

_RANDOM_SEED = 42                 # fixed for reproducible random-benchmark draws
_TRADING_DAYS_PER_YEAR = 252
_PRICE_COLUMN = "gld_adj_close"   # column of merged_df used as the traded price


# --------------------------------------------------------------------------
# pipeline + metrics helpers
# --------------------------------------------------------------------------
def _run_pipeline(merged_df: pd.DataFrame, lookback: int, cost_fn):
    """signals -> monthly rebalance -> backtest, on the FULL merged range."""
    prices = merged_df[_PRICE_COLUMN]
    daily_sig = signals.compute_signal(merged_df, lookback)
    positions = signals.apply_monthly_rebalance(daily_sig, merged_df.index)
    res = backtest.run_backtest(prices, positions, cost_fn=cost_fn)
    return positions, res


def _avg_holding_period(pos_is: pd.Series) -> float:
    """Average length (in trading days) of consecutive position==1 runs in IS."""
    holding = pos_is.fillna(0.0).eq(1.0)
    if len(holding) == 0:
        return float("nan")
    grp = (holding != holding.shift()).cumsum()
    runs = [len(g) for _, g in holding.groupby(grp) if bool(g.iloc[0])]
    return float(np.mean(runs)) if runs else 0.0


def _is_metrics(positions: pd.Series, res: dict, is_start: str, is_end: str) -> dict:
    """Compute IS-window metrics from an already-run backtest.

    Return-based metrics (Sharpe, ann return, ann vol, max drawdown, hit rate)
    come from QuantStats on the NET daily returns filtered to the IS window.
    Position/cost metrics (turnover, trades, holding period, cost drag) are
    derived from the positions and gross-vs-net returns.
    """
    net_daily = res["daily_returns"]
    # Recover gross daily returns from the gross equity curve.
    gross_daily = res["gross_equity_curve"].pct_change()

    net_is = net_daily.loc[is_start:is_end].fillna(0.0)
    gross_is = gross_daily.loc[is_start:is_end].fillna(0.0)

    pos_full = positions.fillna(0.0)
    abs_change_is = pos_full.diff().abs().loc[is_start:is_end]
    pos_is = pos_full.loc[is_start:is_end]
    trade_log_is = res["trade_log"].loc[is_start:is_end]

    years = len(net_is) / _TRADING_DAYS_PER_YEAR if len(net_is) else float("nan")

    # gross-vs-net total return over IS -> total cost drag
    gross_total = float((1.0 + gross_is).prod() - 1.0)
    net_total = float((1.0 + net_is).prod() - 1.0)

    return {
        # --- QuantStats, on net IS returns ---
        "sharpe": float(qs.stats.sharpe(net_is)),
        "ann_return": float(qs.stats.cagr(net_is)),
        "ann_vol": float(qs.stats.volatility(net_is)),
        "max_drawdown": float(qs.stats.max_drawdown(net_is)),
        "hit_rate": float(qs.stats.win_rate(net_is)),
        # --- position / cost derived ---
        "turnover": float(abs_change_is.sum() / years) if years else float("nan"),
        "n_trades": int(len(trade_log_is)),
        "avg_holding_period": _avg_holding_period(pos_is),
        "total_cost_drag": gross_total - net_total,
    }


# --------------------------------------------------------------------------
# exposure-matched random benchmark (winning lookback only)
# --------------------------------------------------------------------------
def _random_benchmark(
    merged_df: pd.DataFrame,
    winning_positions: pd.Series,
    actual_sharpe: float,
    is_start: str,
    is_end: str,
    n_random_draws: int,
    seed: int = _RANDOM_SEED,
) -> dict:
    """Compare the actual strategy's Sharpe to random month-level position draws.

    Each draw holds the SAME number of "on" calendar months as the actual
    strategy over [is_start, is_end], chosen uniformly at random from that
    window's months (month-level, to match the monthly rebalance granularity),
    then goes through the identical backtest + cost pipeline. Sharpe is computed
    the same way as the actual. Used for both the IS grid winner and the OOS
    confirmation, so the two are directly comparable.
    """
    prices = merged_df[_PRICE_COLUMN]
    idx = merged_df.index
    in_is = (idx >= pd.Timestamp(is_start)) & (idx <= pd.Timestamp(is_end))
    day_months = idx.to_period("M")

    unique_months = day_months[in_is].unique()
    total_months = len(unique_months)

    # winner's "on" months (position is constant within a month under monthly
    # rebalancing; max is a defensive reduction).
    win_is = winning_positions.loc[is_start:is_end].fillna(0.0)
    month_pos = win_is.groupby(win_is.index.to_period("M")).max()
    on_count = int((month_pos == 1.0).sum())

    rng = np.random.default_rng(seed)
    month_arr = np.array(list(unique_months), dtype=object)

    draws = np.empty(n_random_draws, dtype=float)
    for i in range(n_random_draws):
        chosen = rng.choice(total_months, size=on_count, replace=False)
        chosen_periods = set(month_arr[chosen])
        rand_pos = pd.Series(0.0, index=idx)
        rand_pos[in_is & day_months.isin(chosen_periods)] = 1.0
        r = backtest.run_backtest(prices, rand_pos, cost_fn=costs.build_cost_fn())
        draws[i] = float(qs.stats.sharpe(r["daily_returns"].loc[is_start:is_end].fillna(0.0)))

    n_beaten = int((draws < actual_sharpe).sum())
    percentile = 100.0 * n_beaten / n_random_draws
    return {
        "draws": draws.tolist(),
        "actual_sharpe": float(actual_sharpe),
        "mean": float(np.mean(draws)),
        "std": float(np.std(draws, ddof=1)),
        "n_beaten": n_beaten,
        "n_draws": int(n_random_draws),
        "percentile": float(percentile),
        "on_count": on_count,
        "total_months": int(total_months),
        "seed": int(seed),
    }


# --------------------------------------------------------------------------
# public entry point
# --------------------------------------------------------------------------
def run_parameter_grid(
    merged_df: pd.DataFrame,
    lookback_values=(10, 20, 40, 60),
    is_start: str = "2005-01-01",
    is_end: str = "2016-12-31",
    n_random_draws: int = 500,
) -> dict:
    """In-sample lookback grid + exposure-matched random benchmark (winner only).

    Returns a dict:
        grid              : DataFrame, one row per lookback, all metrics as columns
        winning_lookback  : int, the lookback with the highest IS Sharpe
        selection         : str explaining the choice
        random_benchmark  : dict with the random-draw Sharpe distribution vs actual
    """
    rows = []
    positions_by_lb: dict[int, pd.Series] = {}
    for lb in lookback_values:
        positions, res = _run_pipeline(merged_df, lb, costs.build_cost_fn())
        positions_by_lb[lb] = positions
        rows.append({"lookback": int(lb), **_is_metrics(positions, res, is_start, is_end)})

    grid = pd.DataFrame(rows)

    win_row = grid.loc[grid["sharpe"].idxmax()]
    winning_lookback = int(win_row["lookback"])
    winning_sharpe = float(win_row["sharpe"])
    selection = (
        f"selected by highest in-sample Sharpe: N={winning_lookback}, "
        f"Sharpe={winning_sharpe:.4f}"
    )

    random_benchmark = _random_benchmark(
        merged_df,
        positions_by_lb[winning_lookback],
        winning_sharpe,
        is_start,
        is_end,
        n_random_draws,
    )

    return {
        "grid": grid,
        "winning_lookback": winning_lookback,
        "selection": selection,
        "random_benchmark": random_benchmark,
    }


def run_oos_confirmation(
    merged_df: pd.DataFrame,
    winning_lookback: int,
    oos_start: str = "2017-01-01",
    oos_end=None,
    n_random_draws: int = 500,
    seed: int = _RANDOM_SEED,
) -> dict:
    """Out-of-sample confirmation of the IS-selected lookback.

    Runs the SAME pipeline as run_parameter_grid for a single (already-chosen)
    lookback, computes the SAME metric set with the SAME QuantStats
    conventions (via the shared _is_metrics helper), and runs the SAME
    exposure-matched random benchmark (via the shared _random_benchmark helper)
    -- but on the OOS window [oos_start, oos_end] instead of the IS window.

    ``oos_end=None`` uses the last available date in merged_df. The signal is
    computed on the FULL merged range (burn-in uses real data, not truncated);
    only the resulting daily returns are filtered to the OOS window before any
    metric is computed. No lookback re-selection happens here -- the winning
    lookback is taken as given.

    Returns {"oos_metrics": {...}, "random_benchmark": {...}}.
    """
    if oos_end is None:
        oos_end = merged_df.index.max()

    positions, res = _run_pipeline(merged_df, winning_lookback, costs.build_cost_fn())
    oos_metrics = _is_metrics(positions, res, oos_start, oos_end)

    random_benchmark = _random_benchmark(
        merged_df,
        positions,
        oos_metrics["sharpe"],
        oos_start,
        oos_end,
        n_random_draws,
        seed=seed,
    )

    return {"oos_metrics": oos_metrics, "random_benchmark": random_benchmark}
