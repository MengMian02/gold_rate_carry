# Source Note

One row per data source used in this project. Update the download date whenever a
series is refreshed.

| Source | URL | Ticker/Series | Frequency | Currency | Download date | Caveats |
|---|---|---|---|---|---|---|
| yfinance | yfinance package (ultimately Yahoo Finance) | GLD | Daily | USD | 2026-08-08 | None material — standard OHLCV for a large, liquid ETF |
| FRED | https://fred.stlouisfed.org/series/DFII10 | DFII10 | Daily (business days only) | N/A; percent per annum | 2026-08-08 | DFII10 values are generally not available until after that day's markets close, so a conservative one-row shift is applied before use — a trading decision never uses same-day DFII10, only the prior day's published value (reflecting the general publication timing of Treasury constant-maturity series, not a sourced timestamp for DFII10 specifically). Not published on days the bond market is closed; forward-filled onto GLD's trading calendar on those days, since no new value exists to report (see README §3). |

**Note.** Both raw data files ARE committed to the repository (`data/raw/gld_raw.csv` and
`data/raw/DFII10.csv`), so the project reproduces its core results without internet access.
To refresh them: GLD re-fetches via yfinance (`loaders.fetch_gld()`); DFII10 is re-downloaded
manually from the FRED URL above and saved to `data/raw/DFII10.csv`.
