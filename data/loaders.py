"""Raw data pulls only.

fetch_gld() and fetch_dfii10() return raw, unmodified series from source
(yfinance for GLD, FRED for DFII10). No cleaning, no validation -- just
retrieval. Anything beyond the retrieval itself belongs in audit.py or clean.py.

Each function caches its raw pull to ``outputs/data/raw/`` as parquet so later
steps can run offline. Pass ``force_refresh=True`` to bypass the cache and pull
from source again. The cache is keyed only by series (fixed filenames), not by
date range -- use ``force_refresh`` when changing ``start``/``end``.
"""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
import yfinance as yf
from fredapi import Fred

# outputs/data/raw/ resolved relative to the repo root, independent of cwd.
_RAW_DIR = Path(__file__).resolve().parent.parent / "outputs" / "data" / "raw"
_GLD_CACHE = _RAW_DIR / "gld_raw.parquet"
_DFII10_CACHE = _RAW_DIR / "dfii10_raw.parquet"


def fetch_gld(start: str, end: str, force_refresh: bool = False) -> pd.DataFrame:
    """Pull raw GLD daily OHLCV from yfinance.

    Returns a DataFrame indexed by ``date`` with columns
    ``open, high, low, close, adj_close, volume`` exactly as returned by the
    source -- no forward-fill, no dropping, no other modification.

    Results are cached to ``outputs/data/raw/gld_raw.parquet``. Set
    ``force_refresh=True`` to bypass the cache.
    """
    if _GLD_CACHE.exists() and not force_refresh:
        return pd.read_parquet(_GLD_CACHE)

    raw = yf.download(
        "GLD",
        start=start,
        end=end,
        auto_adjust=False,  # keep both close and adj_close
        progress=False,
    )

    # A single-ticker download can come back with MultiIndex columns
    # (field, ticker); flatten to the field level only.
    if isinstance(raw.columns, pd.MultiIndex):
        raw.columns = raw.columns.get_level_values(0)
    raw.columns.name = None

    raw = raw.rename(
        columns={
            "Open": "open",
            "High": "high",
            "Low": "low",
            "Close": "close",
            "Adj Close": "adj_close",
            "Volume": "volume",
        }
    )
    raw = raw[["open", "high", "low", "close", "adj_close", "volume"]]
    raw.index.name = "date"

    _RAW_DIR.mkdir(parents=True, exist_ok=True)
    raw.to_parquet(_GLD_CACHE)
    return raw


def fetch_dfii10(start: str, end: str, force_refresh: bool = False) -> pd.DataFrame:
    """Pull the raw DFII10 real-yield series from FRED.

    DFII10 is the 10-Year Treasury Inflation-Indexed Security, Constant
    Maturity. Returns a DataFrame indexed by ``date`` with a single column
    ``dfii10_value``. NaNs on no-data days (e.g. holidays) are preserved -- no
    fill, no drop.

    Requires the FRED API key in the ``FRED_API_KEY`` environment variable.
    Results are cached to ``outputs/data/raw/dfii10_raw.parquet``. Set
    ``force_refresh=True`` to bypass the cache.
    """
    if _DFII10_CACHE.exists() and not force_refresh:
        return pd.read_parquet(_DFII10_CACHE)

    api_key = os.environ.get("FRED_API_KEY")
    if not api_key:
        raise RuntimeError(
            "FRED_API_KEY environment variable is not set. A free key is "
            "available at https://fred.stlouisfed.org/docs/api/api_key.html"
        )

    fred = Fred(api_key=api_key)
    series = fred.get_series(
        "DFII10",
        observation_start=start,
        observation_end=end,
    )

    raw = series.to_frame(name="dfii10_value")
    raw.index.name = "date"

    _RAW_DIR.mkdir(parents=True, exist_ok=True)
    raw.to_parquet(_DFII10_CACHE)
    return raw
