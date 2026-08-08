"""Read-only diagnostics.

Flags anomalies (price jumps beyond N std devs, repeated/stale values, gaps
beyond the expected trading calendar, zero/negative prices, DFII10
publication-date misalignment). Makes NO judgment calls about what caused an
anomaly or how to fix it -- outputs a list of flagged dates/issues for human
review only. Every fix that follows is decided by a human and recorded in
decisions.md, then applied by clean.py.

Scope of this module: GLD and DFII10 are audited *independently*. No merging,
no cross-series calendar-mismatch check, no cleaning -- those are later steps.

Each function returns a dict:
    hard_errors_checked : list[str]   -- names of hard-error checks that passed
    anomalies           : pd.DataFrame with columns [date, issue_type, value, detail]
    summary             : dict        -- counts by anomaly type (+ nan_count, n_rows)

Hard errors raise ValueError immediately. Anomalies are only recorded, never
raised and never fixed.

MAD-threshold method (shared by both series): for each row, compare the daily
change to the median +/- k * (1.4826 * MAD) of the *trailing window of daily
changes*, where the window includes the current row. MAD is robust, so a single
outlier does not appreciably inflate its own window's spread. NaNs inside a
window are ignored (nan-aware median), which matters for DFII10's holiday gaps.
"""

from __future__ import annotations

import warnings

import numpy as np
import pandas as pd

# --- anomaly-detection parameters (documented, tunable) -------------------
_MAD_WINDOW = 60            # trailing window length (rows) for the MAD threshold
_MAD_MIN_PERIODS = 40       # min non-NaN obs required before flagging; < window so
                            # DFII10's holiday NaNs don't disable detection entirely
_MAD_K = 4.0                # threshold multiplier (flag |mod z-score| > k)
_MAD_SCALE = 1.4826         # scales MAD to a normal-equivalent sigma
_STALE_RUN = 3              # a value repeated this many consecutive rows (or more) is stale
_ADJ_DIVERGENCE_RTOL = 1e-4  # relative tolerance below which close vs adj_close diff is float noise

# --- hard-error units bounds (deliberately wide: only "wildly outside" raises) --
_GLD_PRICE_FLOOR = 5.0
_GLD_PRICE_CEILING = 1000.0
_DFII10_FLOOR = -5.0
_DFII10_CEILING = 10.0

_ANOMALY_COLUMNS = ["date", "issue_type", "value", "detail"]
_GLD_PRICE_COLS = ["open", "high", "low", "close", "adj_close"]


# --------------------------------------------------------------------------
# shared helpers
# --------------------------------------------------------------------------
def _fmt_dates(index: pd.Index, limit: int = 10) -> str:
    """Render the first few offending dates for a clear error message."""
    dates = [str(d) for d in list(index)[:limit]]
    suffix = "" if len(index) <= limit else f" ... (+{len(index) - limit} more)"
    return ", ".join(dates) + suffix


def _mad_outlier_flags(series: pd.Series, use_pct: bool):
    """Return (changes, flags, mod_z) for the trailing-MAD outlier test.

    changes : daily % change (use_pct) or daily diff, aligned to series.index
    flags   : bool Series, True where the change exceeds the k*MAD threshold
    mod_z   : the modified z-score (change - median) / (1.4826 * MAD)
    """
    changes = series.pct_change() if use_pct else series.diff()
    roll = changes.rolling(_MAD_WINDOW, min_periods=_MAD_MIN_PERIODS)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)
        med = roll.apply(np.nanmedian, raw=True)
        mad = roll.apply(
            lambda w: np.nanmedian(np.abs(w - np.nanmedian(w))), raw=True
        )
    scaled = _MAD_SCALE * mad
    threshold = _MAD_K * scaled
    dev = (changes - med).abs()
    # NaN comparisons yield False, so early rows / insufficient windows aren't flagged.
    flags = dev > threshold
    with np.errstate(divide="ignore", invalid="ignore"):
        mod_z = (changes - med) / scaled
    return changes, flags, mod_z


def _stale_flags(series: pd.Series) -> pd.Series:
    """True where a value is part of a run of >= _STALE_RUN identical values.

    NaN never equals NaN, so NaN runs are never treated as stale.
    """
    eq_prev = series.eq(series.shift())
    run_id = (~eq_prev).cumsum()
    run_size = series.groupby(run_id).transform("size")
    return (run_size >= _STALE_RUN) & series.notna()


def _rows(mask: pd.Series, values: pd.Series, issue_type: str,
          details: pd.Series | None = None) -> pd.DataFrame:
    """Build anomaly rows for the True positions of `mask`."""
    m = mask.to_numpy()
    if not m.any():
        return pd.DataFrame(columns=_ANOMALY_COLUMNS)
    out = pd.DataFrame(
        {
            "date": values.index[m],
            "issue_type": issue_type,
            "value": values.to_numpy()[m],
        }
    )
    out["detail"] = details.to_numpy()[m] if details is not None else ""
    return out


def _assemble(frames: list[pd.DataFrame]) -> pd.DataFrame:
    non_empty = [f for f in frames if not f.empty]
    if not non_empty:
        return pd.DataFrame(columns=_ANOMALY_COLUMNS)
    return pd.concat(non_empty, ignore_index=True)


# --------------------------------------------------------------------------
# GLD
# --------------------------------------------------------------------------
def audit_gld(df: pd.DataFrame) -> dict:
    """Read-only audit of a raw GLD OHLCV frame. See module docstring."""
    hard_errors_checked: list[str] = []

    # -- hard errors (raise immediately) --
    dup = df.index[df.index.duplicated()]
    if len(dup) > 0:
        raise ValueError(f"Duplicate dates in GLD index: {_fmt_dates(dup)}")
    hard_errors_checked.append("no_duplicate_dates")

    if not df.index.is_monotonic_increasing:
        raise ValueError("GLD index is not monotonically increasing (dates out of order).")
    hard_errors_checked.append("monotonic_increasing_dates")

    prices = df[_GLD_PRICE_COLS]
    neg = (prices < 0).any(axis=1)
    if neg.any():
        raise ValueError(
            f"Negative price(s) in GLD OHLC/adj_close on: {_fmt_dates(df.index[neg.to_numpy()])}"
        )
    hard_errors_checked.append("no_negative_prices")

    bad_ohlc = (
        (df["low"] > df["high"])
        | (df["close"] < df["low"])
        | (df["close"] > df["high"])
        | (df["open"] < df["low"])
        | (df["open"] > df["high"])
    )
    if bad_ohlc.any():
        raise ValueError(
            "OHLC inconsistency (low > high, or open/close outside [low, high]) on: "
            f"{_fmt_dates(df.index[bad_ohlc.to_numpy()])}"
        )
    hard_errors_checked.append("ohlc_consistency")

    pmin = float(np.nanmin(prices.to_numpy()))
    pmax = float(np.nanmax(prices.to_numpy()))
    if pmin < _GLD_PRICE_FLOOR or pmax > _GLD_PRICE_CEILING:
        raise ValueError(
            f"GLD prices outside plausible range [{_GLD_PRICE_FLOOR}, {_GLD_PRICE_CEILING}]: "
            f"observed min={pmin}, max={pmax}. Possible units error."
        )
    hard_errors_checked.append("price_units_within_bounds")

    # -- anomalies (flag only) --
    adj = df["adj_close"]
    close = df["close"]
    volume = df["volume"]

    changes, mad_flags, mod_z = _mad_outlier_flags(adj, use_pct=True)
    stale_flags = _stale_flags(adj)
    zero_vol_flags = volume == 0

    denom = close.abs().replace(0, np.nan)
    rel_div = (close - adj).abs() / denom
    div_flags = (rel_div > _ADJ_DIVERGENCE_RTOL).fillna(False)

    anomalies = _assemble(
        [
            _rows(mad_flags, changes, "mad_outlier_pct_change",
                  details="mod_z=" + mod_z.round(2).astype(str)),
            _rows(stale_flags, adj, "stale_adj_close"),
            _rows(zero_vol_flags, volume, "zero_volume"),
            _rows(div_flags, close - adj, "close_adj_divergence",
                  details="rel=" + rel_div.round(6).astype(str)),
        ]
    )

    summary = {
        "mad_outlier_pct_change": int((anomalies["issue_type"] == "mad_outlier_pct_change").sum()),
        "stale_adj_close": int((anomalies["issue_type"] == "stale_adj_close").sum()),
        "zero_volume": int((anomalies["issue_type"] == "zero_volume").sum()),
        "close_adj_divergence": int((anomalies["issue_type"] == "close_adj_divergence").sum()),
        "nan_count": int(df.isna().to_numpy().sum()),
        "n_rows": int(len(df)),
    }

    return {
        "hard_errors_checked": hard_errors_checked,
        "anomalies": anomalies,
        "summary": summary,
    }


# --------------------------------------------------------------------------
# DFII10
# --------------------------------------------------------------------------
def audit_dfii10(df: pd.DataFrame) -> dict:
    """Read-only audit of a raw DFII10 real-yield frame. See module docstring.

    Negative values are NOT flagged -- negative real yields are a genuine market
    condition. NaNs (holidays / non-trading days) are only counted, not flagged.
    """
    hard_errors_checked: list[str] = []
    val = df["dfii10_value"]

    # -- hard errors (raise immediately) --
    dup = df.index[df.index.duplicated()]
    if len(dup) > 0:
        raise ValueError(f"Duplicate dates in DFII10 index: {_fmt_dates(dup)}")
    hard_errors_checked.append("no_duplicate_dates")

    if not df.index.is_monotonic_increasing:
        raise ValueError("DFII10 index is not monotonically increasing (dates out of order).")
    hard_errors_checked.append("monotonic_increasing_dates")

    if val.notna().any():
        vmin = float(np.nanmin(val.to_numpy()))
        vmax = float(np.nanmax(val.to_numpy()))
        if vmin < _DFII10_FLOOR or vmax > _DFII10_CEILING:
            raise ValueError(
                f"DFII10 values outside plausible percent range "
                f"[{_DFII10_FLOOR}, {_DFII10_CEILING}]: observed min={vmin}, max={vmax}. "
                "Possible units error."
            )
    hard_errors_checked.append("value_units_within_bounds")

    # -- anomalies (flag only); negatives intentionally not flagged --
    changes, mad_flags, mod_z = _mad_outlier_flags(val, use_pct=False)
    stale_flags = _stale_flags(val)

    anomalies = _assemble(
        [
            _rows(mad_flags, changes, "mad_outlier_change",
                  details="mod_z=" + mod_z.round(2).astype(str)),
            _rows(stale_flags, val, "stale_value"),
        ]
    )

    summary = {
        "mad_outlier_change": int((anomalies["issue_type"] == "mad_outlier_change").sum()),
        "stale_value": int((anomalies["issue_type"] == "stale_value").sum()),
        "nan_count": int(val.isna().sum()),
        "n_rows": int(len(df)),
    }

    return {
        "hard_errors_checked": hard_errors_checked,
        "anomalies": anomalies,
        "summary": summary,
    }
