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

from . import backtest
from . import costs
from . import signals

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
    cost_fn=None,
) -> dict:
    """Compare the actual strategy's Sharpe to random month-level position draws.

    Each draw holds the SAME number of "on" calendar months as the actual
    strategy over [is_start, is_end], chosen uniformly at random from that
    window's months (month-level, to match the monthly rebalance granularity),
    then goes through the identical backtest + cost pipeline. Sharpe is computed
    the same way as the actual. Used for both the IS grid winner and the OOS
    confirmation, so the two are directly comparable.
    """
    # cost_fn (default build_cost_fn()) applies to every draw, so the random
    # draws carry the same cost assumptions as the actual at this cost level.
    if cost_fn is None:
        cost_fn = costs.build_cost_fn()
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
        r = backtest.run_backtest(prices, rand_pos, cost_fn=cost_fn)
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
    cost_fn=None,
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
    if cost_fn is None:
        cost_fn = costs.build_cost_fn()

    positions, res = _run_pipeline(merged_df, winning_lookback, cost_fn)
    oos_metrics = _is_metrics(positions, res, oos_start, oos_end)

    random_benchmark = _random_benchmark(
        merged_df,
        positions,
        oos_metrics["sharpe"],
        oos_start,
        oos_end,
        n_random_draws,
        seed=seed,
        cost_fn=cost_fn,
    )

    return {"oos_metrics": oos_metrics, "random_benchmark": random_benchmark}


def run_regime_split(
    merged_df: pd.DataFrame,
    winning_lookback: int,
    regime_1=("2008-01-01", "2021-12-31"),
    regime_2=("2022-01-01", "2024-12-31"),
    n_random_draws: int = 500,
    seed: int = _RANDOM_SEED,
    cost_fn=None,
) -> dict:
    """Compare the winning lookback across two date regimes.

    The full pipeline (signal on the FULL range with real burn-in -> monthly
    rebalance -> backtest -> costs) is run ONCE; the resulting output is then
    filtered to each regime separately for metrics and its exposure-matched
    random benchmark. Metrics and the benchmark use the SAME shared helpers --
    hence the SAME QuantStats conventions -- as run_parameter_grid and
    run_oos_confirmation, for direct comparability.

    Returns:
        {"regime_1": {"metrics": {...}, "random_benchmark": {...}},
         "regime_2": {"metrics": {...}, "random_benchmark": {...}}}
    """
    # Run the actual strategy pipeline once; both regimes filter this same output.
    if cost_fn is None:
        cost_fn = costs.build_cost_fn()
    positions, res = _run_pipeline(merged_df, winning_lookback, cost_fn)

    def _one_regime(window) -> dict:
        start, end = window
        metrics = _is_metrics(positions, res, start, end)
        benchmark = _random_benchmark(
            merged_df, positions, metrics["sharpe"], start, end, n_random_draws,
            seed=seed, cost_fn=cost_fn,
        )
        return {"metrics": metrics, "random_benchmark": benchmark}

    return {
        "regime_1": _one_regime(regime_1),
        "regime_2": _one_regime(regime_2),
    }


# --------------------------------------------------------------------------
# moving block bootstrap of the Sharpe ratio
# --------------------------------------------------------------------------
def _sharpe_from_array(arr: np.ndarray) -> float:
    """Annualized Sharpe of a returns array, matching qs.stats.sharpe's default
    convention (mean / std(ddof=1) * sqrt(252), rf=0). Verified equal to
    qs.stats.sharpe on a clean series; used in the bootstrap loop for speed."""
    std = arr.std(ddof=1)
    if std == 0 or np.isnan(std):
        return float("nan")
    return float(arr.mean() / std * np.sqrt(_TRADING_DAYS_PER_YEAR))


def run_block_bootstrap(
    daily_returns: pd.Series,
    block_size: int = 21,
    n_boot: int = 1000,
    seed: int = _RANDOM_SEED,
) -> dict:
    """Moving block bootstrap of the annualized Sharpe ratio.

    Resamples ``daily_returns`` by drawing random contiguous blocks of length
    ``block_size`` (with replacement, overlapping starts allowed) and
    concatenating them until the resampled series matches the original length
    (last block truncated to hit the exact length). For each of ``n_boot``
    replicates the annualized Sharpe is computed (same QuantStats convention used
    elsewhere).
    """
    r = daily_returns.dropna().to_numpy(dtype=float)
    n = len(r)

    # Sharpe of the real, unresampled input (same QuantStats convention).
    actual_sharpe = float(qs.stats.sharpe(daily_returns.dropna()))

    # block_size=21 ~ one month of trading days, matching the strategy's MONTHLY
    # rebalance cadence so each contiguous block preserves within-holding-period
    # autocorrelation. This is a JUDGMENT CALL, not a derived value -- worth a
    # sensitivity check (e.g. re-running at block_size=10 and 42) rather than
    # treating 21 as definitively correct.
    eff_block = min(block_size, n) if n > 0 else block_size
    max_start = max(0, n - eff_block)
    n_blocks = int(np.ceil(n / eff_block)) if eff_block else 0
    offsets = np.arange(eff_block)

    rng = np.random.default_rng(seed)
    boot = np.empty(n_boot, dtype=float)
    for b in range(n_boot):
        starts = rng.integers(0, max_start + 1, size=n_blocks)
        idx = (starts[:, None] + offsets[None, :]).ravel()[:n]
        boot[b] = _sharpe_from_array(r[idx])

    return {
        "actual_sharpe": actual_sharpe,
        "bootstrap_mean": float(np.mean(boot)),
        "bootstrap_std": float(np.std(boot, ddof=1)),
        "ci_lower": float(np.percentile(boot, 2.5)),
        "ci_upper": float(np.percentile(boot, 97.5)),
        "pct_bootstrap_leq_zero": float(np.mean(boot <= 0)),
        "block_size": block_size,
        "n_boot": n_boot,
        "seed": seed,
    }


# The four analysis windows, matching the earlier functions' conventions.
_BOOTSTRAP_PERIODS = {
    "IS": ("2005-01-01", "2016-12-31"),
    "OOS": ("2017-01-01", "2025-12-31"),
    "regime_1": ("2008-01-01", "2021-12-31"),
    "regime_2": ("2022-01-01", "2024-12-31"),
}


def run_block_bootstrap_all_periods(
    merged_df: pd.DataFrame,
    winning_lookback: int,
    block_size: int = 21,
    n_boot: int = 1000,
    seed: int = _RANDOM_SEED,
) -> dict:
    """Run run_block_bootstrap on the four analysis windows for one lookback.

    The pipeline is run ONCE for ``winning_lookback``; its net daily returns are
    then sliced to each window (IS, OOS, Regime 1, Regime 2) and bootstrapped,
    rather than re-running the pipeline per period. Returns a dict keyed by
    period name.
    """
    _, res = _run_pipeline(merged_df, winning_lookback, costs.build_cost_fn())
    net_daily = res["daily_returns"]
    return {
        name: run_block_bootstrap(
            net_daily.loc[start:end].fillna(0.0),
            block_size=block_size,
            n_boot=n_boot,
            seed=seed,
        )
        for name, (start, end) in _BOOTSTRAP_PERIODS.items()
    }


# --------------------------------------------------------------------------
# cost sensitivity
# --------------------------------------------------------------------------
def run_cost_sensitivity(
    merged_df: pd.DataFrame,
    winning_lookback: int,
    bps_values=(5.0, 8.0, 10.0),
    oos_end: str = "2025-12-31",
) -> dict:
    """Re-run OOS confirmation and the regime split at several transaction-cost levels.

    For each bps in ``bps_values`` a single cost function is built via
    ``build_cost_fn(bps=bps)`` (the annual expense ratio stays at its default of
    0.0; only bps varies) and passed to ``run_oos_confirmation`` and
    ``run_regime_split`` -- reusing the existing pipeline, no backtest logic
    duplicated here. The same cost level applies to both the actual strategy and
    its exposure-matched random draws, so each percentile stays an apples-to-
    apples comparison at that cost level.

    ``oos_end`` (default "2025-12-31", the project's locked OOS cutoff) is passed
    through to ``run_oos_confirmation`` so the OOS window matches every other
    result rather than silently extending to the last available date. Regime
    windows are fixed dates and are unaffected.

    Returns a dict keyed by bps value, each with ``oos`` / ``regime_1`` /
    ``regime_2`` sub-dicts of {sharpe, percentile}, plus a ``"summary"`` key
    reporting whether the three directional conclusions (OOS underperforms
    random, Regime 1 beats random, Regime 2 underperforms random) hold at every
    bps tested. "Beats random" is taken as percentile > 50 (above the median
    random draw); "underperforms" as percentile < 50.
    """
    out: dict = {}
    for bps in bps_values:
        cost_fn = costs.build_cost_fn(bps=bps)  # expense ratio at its default (0.0)
        oos = run_oos_confirmation(merged_df, winning_lookback, oos_end=oos_end, cost_fn=cost_fn)
        reg = run_regime_split(merged_df, winning_lookback, cost_fn=cost_fn)
        out[bps] = {
            "oos": {
                "sharpe": oos["oos_metrics"]["sharpe"],
                "percentile": oos["random_benchmark"]["percentile"],
            },
            "regime_1": {
                "sharpe": reg["regime_1"]["metrics"]["sharpe"],
                "percentile": reg["regime_1"]["random_benchmark"]["percentile"],
            },
            "regime_2": {
                "sharpe": reg["regime_2"]["metrics"]["sharpe"],
                "percentile": reg["regime_2"]["random_benchmark"]["percentile"],
            },
        }

    oos_underperforms = all(v["oos"]["percentile"] < 50 for v in out.values())
    regime_1_beats = all(v["regime_1"]["percentile"] > 50 for v in out.values())
    regime_2_underperforms = all(v["regime_2"]["percentile"] < 50 for v in out.values())
    stable = oos_underperforms and regime_1_beats and regime_2_underperforms

    out["summary"] = {
        "bps_tested": list(bps_values),
        "oos_underperforms_random_all_bps": oos_underperforms,
        "regime_1_beats_random_all_bps": regime_1_beats,
        "regime_2_underperforms_random_all_bps": regime_2_underperforms,
        "all_conclusions_stable": stable,
        "note": (
            "All three directional conclusions (OOS underperforms random, "
            "Regime 1 beats random, Regime 2 underperforms random) hold at every "
            "bps value tested."
            if stable
            else "At least one directional conclusion changes across the tested "
            "bps values -- inspect the per-bps percentiles."
        ),
    }
    return out
