"""Raw data retrieval only. Everything is stored/read as CSV.

fetch_gld()   -> pulls the raw GLD OHLCV series from yfinance (live) and caches
                 it to ``data/raw/gld_raw.csv``.
load_dfii10() -> reads the raw DFII10 real-yield series from the manually
                 downloaded ``data/raw/DFII10.csv`` (FRED series DFII10).

Both return a DataFrame indexed by a ``date`` DatetimeIndex with standardized
column name(s). "Raw" means values are passed through unchanged -- only column
names and the date index are normalized. No cleaning, no validation, no
fill/drop. Anything beyond retrieval belongs in audit.py or clean.py.

Storage format is CSV for both series (small data, human-inspectable, and DFII10
arrives as CSV anyway). CSV is text, so reads MUST parse the date column back to
datetimes and rely on pandas' default empty-field == NaN handling; floats
round-trip losslessly with pandas' default writer.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

import yfinance as yf

# data/raw/ resolved relative to the repo root, independent of cwd.
_RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"
_GLD_CACHE = _RAW_DIR / "gld_raw.csv"
# DFII10 is downloaded manually from FRED and dropped in the same folder.
_DFII10_CSV = _RAW_DIR / "DFII10.csv"


def fetch_gld(start: str, end: str, force_refresh: bool = False) -> pd.DataFrame:
    """Pull raw GLD daily OHLCV from yfinance and cache it as CSV.

    Returns a DataFrame indexed by ``date`` with columns
    ``open, high, low, close, adj_close, volume`` exactly as returned by the
    source -- no forward-fill, no dropping, no other modification.

    Cached to ``data/raw/gld_raw.csv``. Set ``force_refresh=True`` to
    bypass the cache and re-pull. The cache is keyed only by series (fixed
    filename), not by date range -- use ``force_refresh`` when changing
    ``start``/``end``.
    """
    if _GLD_CACHE.exists() and not force_refresh:
        return pd.read_csv(_GLD_CACHE, index_col="date", parse_dates=["date"])

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
    raw.to_csv(_GLD_CACHE)
    return raw


def load_dfii10() -> pd.DataFrame:
    """Read the raw DFII10 real-yield series from the manual FRED download.

    DFII10 is the 10-Year Treasury Inflation-Indexed Security, Constant Maturity.
    It is not pulled programmatically -- it is downloaded manually from FRED
    (https://fred.stlouisfed.org/series/DFII10) and saved to
    ``data/raw/DFII10.csv`` with columns ``observation_date`` and
    ``DFII10``.

    Returns a DataFrame indexed by ``date`` with a single column
    ``dfii10_value``. Values are passed through unchanged; NaNs on no-data days
    (e.g. holidays) are preserved. Raises FileNotFoundError if the file is
    missing and ValueError if its columns are not the expected FRED layout.
    """
    if not _DFII10_CSV.exists():
        raise FileNotFoundError(
            f"DFII10 source file not found at {_DFII10_CSV}. Download it manually "
            "from FRED (series DFII10, https://fred.stlouisfed.org/series/DFII10) "
            "and place it there. See README.md."
        )

    # FRED marks missing observations as an empty field or '.'; treat both as NaN.
    raw = pd.read_csv(_DFII10_CSV, na_values=["."])

    expected = {"observation_date", "DFII10"}
    if not expected.issubset(raw.columns):
        raise ValueError(
            f"{_DFII10_CSV} does not have the expected FRED columns "
            f"{sorted(expected)}; found {list(raw.columns)}."
        )

    raw = raw.rename(columns={"observation_date": "date", "DFII10": "dfii10_value"})
    raw["date"] = pd.to_datetime(raw["date"])
    raw = raw.set_index("date")[["dfii10_value"]]
    return raw
