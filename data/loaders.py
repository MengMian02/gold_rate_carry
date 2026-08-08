"""Raw data pulls only.

fetch_gld() returns the raw, unmodified GLD price series from yfinance. No
cleaning, no validation -- just retrieval. Anything beyond the retrieval itself
belongs in audit.py or clean.py.

DFII10 (the 10-year real yield) is NOT loaded here. It is downloaded manually
from FRED and stored at ``outputs/data/raw/DFII10.csv`` (columns
``observation_date``, ``DFII10``); see README.md / source_note.md.

fetch_gld caches its raw pull to ``outputs/data/raw/`` as parquet so later steps
can run offline. Pass ``force_refresh=True`` to bypass the cache and pull from
source again. The cache is keyed only by series (fixed filename), not by date
range -- use ``force_refresh`` when changing ``start``/``end``.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import yfinance as yf

# outputs/data/raw/ resolved relative to the repo root, independent of cwd.
_RAW_DIR = Path(__file__).resolve().parent.parent / "outputs" / "data" / "raw"
_GLD_CACHE = _RAW_DIR / "gld_raw.parquet"


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
