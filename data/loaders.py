"""Raw data pulls only.

fetch_gld() and fetch_dfii10() return raw, unmodified series from source
(yfinance for GLD, FRED for DFII10). No cleaning, no validation -- just
retrieval. Anything beyond the retrieval itself belongs in audit.py or clean.py.
"""

from __future__ import annotations

import pandas as pd
import yfinance as yf
import pandas_datareader.data as web


def fetch_gld() -> pd.Series:
    """Return the raw GLD price series from yfinance, exactly as retrieved."""
    raise NotImplementedError


def fetch_dfii10() -> pd.Series:
    """Return the raw DFII10 (10y real yield) series from FRED, as retrieved."""
    raise NotImplementedError
