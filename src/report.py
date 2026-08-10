"""Report rendering.

generate_report() builds a single, self-contained HTML report for the strategy:

  1. a Conclusion section (the verdict) placed ABOVE everything else,
  2. a strategy position-over-time chart (long vs. flat),
  3. a diagnostic chart (DFII10 real yield + its 20-day change vs. GLD price,
     shaded where the strategy is long),
  4. the QuantStats tearsheet (net strategy vs. GLD buy-and-hold) covering
     cumulative performance, drawdown, and rolling Sharpe.

Charts (2) and (3) are rendered with matplotlib and embedded as base64 PNGs; the
QuantStats tearsheet embeds its plots as inline SVG. The result has no external
file dependencies and opens offline. Output goes to ``result/report.html``.
"""

from __future__ import annotations

import base64
import io
import os
import re
import tempfile
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # headless: no display needed
import matplotlib.pyplot as plt
import pandas as pd
import quantstats as qs

from . import backtest
from . import costs
from . import signals

_REPO_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_OUTPUT = _REPO_ROOT / "result" / "report.html"
_PRICE_COLUMN = "gld_adj_close"

# Verdict shown in the Conclusion section. Kept in sync with memo.md's verdict.
_VERDICT = "MONITOR"
_VERDICT_TEXT = (
    "The real-yield / duration signal delivered genuine, statistically "
    "distinguishable edge while falling real yields were the dominant driver of "
    "gold (Regime 1, 2008–2021: ~98th percentile against exposure-matched "
    "random timing), but it broke down in 2022–2024 as central-bank reserve "
    "buying displaced the discount-rate channel, and out-of-sample it did not beat "
    "a randomly-timed benchmark with matched exposure. The mechanism is real but "
    "regime-dependent: not deployable as a standalone strategy today, yet worth "
    "monitoring for a return to a real-yield-led regime, when the signal could "
    "regain its edge."
)


def _fig_to_base64(fig) -> str:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=110, bbox_inches="tight")
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def _position_chart(pos_oos: pd.Series) -> str:
    fig, ax = plt.subplots(figsize=(11, 2.6))
    ax.fill_between(pos_oos.index, 0, pos_oos.values, step="post",
                    color="#2c7fb8", alpha=0.85, linewidth=0)
    ax.set_ylim(-0.05, 1.05)
    ax.set_yticks([0, 1])
    ax.set_yticklabels(["Flat", "Long"])
    ax.set_title("Strategy position over time (long GLD vs. flat)")
    ax.margins(x=0)
    ax.grid(True, axis="x", alpha=0.2)
    return _fig_to_base64(fig)


def _diagnostic_chart(merged_oos: pd.DataFrame, pos_oos: pd.Series,
                      change_oos: pd.Series) -> str:
    long_mask = pos_oos.to_numpy() == 1.0
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(11, 6), sharex=True)

    # Panel 1: real yield (level) + its 20-day change on a twin axis.
    ax1.plot(merged_oos.index, merged_oos[_diag_yield].to_numpy(),
             color="#1f77b4", lw=1.1, label="DFII10 real yield (T+1 aligned)")
    ax1.set_ylabel("DFII10 (%)", color="#1f77b4")
    ax1b = ax1.twinx()
    ax1b.plot(change_oos.index, change_oos.to_numpy(), color="#ff7f0e",
              lw=0.9, alpha=0.85, label="20-day change")
    ax1b.axhline(0.0, color="#ff7f0e", lw=0.7, ls="--", alpha=0.6)
    ax1b.set_ylabel("20-day change (pp)", color="#ff7f0e")
    ax1.fill_between(pos_oos.index, 0, 1, where=long_mask,
                     transform=ax1.get_xaxis_transform(),
                     color="green", alpha=0.10, linewidth=0)
    ax1.set_title("Real yield & its 20-day change  (green = strategy long)")
    ax1.grid(True, alpha=0.2)

    # Panel 2: GLD price with the same long-shading.
    ax2.plot(merged_oos.index, merged_oos[_PRICE_COLUMN].to_numpy(),
             color="black", lw=1.0, label="GLD adj. close")
    ax2.fill_between(pos_oos.index, 0, 1, where=long_mask,
                     transform=ax2.get_xaxis_transform(),
                     color="green", alpha=0.10, linewidth=0)
    ax2.set_ylabel("GLD price ($)")
    ax2.set_title("GLD price  (green = strategy long)")
    ax2.grid(True, alpha=0.2)
    ax2.margins(x=0)
    fig.tight_layout()
    return _fig_to_base64(fig)


_diag_yield = "dfii10_aligned"


def _top_section(pos_b64: str, diag_b64: str, oos_start: str, oos_end: str) -> str:
    return f"""
<div style="max-width:1100px;margin:20px auto;padding:0 16px;
            font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;color:#222;">
  <div style="border-left:5px solid #b8860b;background:#fbf7ec;padding:14px 20px;border-radius:4px;">
    <h2 style="margin:0 0 6px;">Conclusion &mdash; Verdict: {_VERDICT}</h2>
    <p style="margin:0;line-height:1.5;">{_VERDICT_TEXT}</p>
  </div>

  <h3 style="margin-top:26px;">Strategy position over time (OOS {oos_start[:4]}&ndash;{oos_end[:4]})</h3>
  <img alt="Strategy position over time" style="width:100%;max-width:1100px;display:block;"
       src="data:image/png;base64,{pos_b64}"/>

  <h3 style="margin-top:26px;">Diagnostic: real yield (DFII10) &amp; 20-day change vs. GLD price</h3>
  <img alt="Real yield and GLD price diagnostic" style="width:100%;max-width:1100px;display:block;"
       src="data:image/png;base64,{diag_b64}"/>
  <p style="color:#555;font-size:0.9em;line-height:1.4;">
    Green shading marks periods the strategy held GLD. A position is opened on a month's
    first trading day when the real yield's trailing 20-day change is negative, and held
    until the next monthly rebalance.
  </p>

  <hr style="margin:28px 0;border:none;border-top:1px solid #ddd;"/>
  <h3>QuantStats tearsheet &mdash; strategy (net of costs) vs. GLD buy-and-hold</h3>
  <p style="color:#555;font-size:0.9em;">
    Out-of-sample net daily returns, {oos_start} to {oos_end}. Cumulative performance vs.
    benchmark, drawdown, and rolling Sharpe below.
  </p>
</div>
"""


def generate_report(
    merged_df: pd.DataFrame,
    lookback: int = 20,
    oos_start: str = "2017-01-01",
    oos_end: str = "2025-12-31",
    output_path=None,
) -> Path:
    """Build the self-contained HTML report and write it to ``result/report.html``.

    Runs the strategy pipeline for ``lookback``, takes the NET out-of-sample daily
    returns over [oos_start, oos_end], benchmarks them against GLD buy-and-hold via
    QuantStats, and prepends the verdict + position/diagnostic charts above the
    tearsheet. Returns the path written.
    """
    output_path = Path(output_path) if output_path is not None else _DEFAULT_OUTPUT
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # --- run the strategy pipeline; slice OOS ---
    prices = merged_df[_PRICE_COLUMN]
    positions = signals.apply_monthly_rebalance(
        signals.compute_signal(merged_df, lookback), merged_df.index
    )
    res = backtest.run_backtest(prices, positions, cost_fn=costs.build_cost_fn())

    strat = res["daily_returns"].loc[oos_start:oos_end].fillna(0.0)
    strat.name = "Real-yield timing (net)"
    bench = prices.pct_change().loc[oos_start:oos_end].fillna(0.0)
    bench.name = "GLD buy & hold"

    # --- custom charts over the OOS window ---
    merged_oos = merged_df.loc[oos_start:oos_end]
    pos_oos = positions.loc[oos_start:oos_end].fillna(0.0)
    change_oos = merged_df[_diag_yield].diff(lookback).loc[oos_start:oos_end]
    pos_b64 = _position_chart(pos_oos)
    diag_b64 = _diagnostic_chart(merged_oos, pos_oos, change_oos)

    # --- QuantStats tearsheet into a temp file, then read it back ---
    fd, tmp = tempfile.mkstemp(suffix=".html")
    os.close(fd)
    try:
        qs.reports.html(
            strat,
            benchmark=bench,
            title="Real-Yield Timing on GLD",
            output=tmp,
        )
        html = Path(tmp).read_text(encoding="utf-8")
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)

    # --- drop the one external favicon link so nothing is fetched offline ---
    html = re.sub(r"<link[^>]*qtpylib\.io[^>]*>", "", html)

    # --- inject the conclusion + charts immediately after <body ...> ---
    fragment = _top_section(pos_b64, diag_b64, oos_start, oos_end)
    html, n = re.subn(r"<body[^>]*>", lambda m: m.group(0) + fragment, html, count=1)
    if n == 0:  # no <body> found (unexpected) -> prepend so nothing is lost
        html = fragment + html

    output_path.write_text(html, encoding="utf-8")
    return output_path
