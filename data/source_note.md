# Source Note

One row per data source used in this project. Update the download date whenever a
series is refreshed.

| Source | URL | Ticker/Series | Frequency | Currency | Download date | Caveats |
|---|---|---|---|---|---|---|
| yfinance | yfinance package (ultimately Yahoo Finance) | GLD | Daily | USD | 2026-08-08 | None material — standard OHLCV for a large, liquid ETF |
| FRED | https://fred.stlouisfed.org/series/DFII10 | DFII10 | Daily (business days only) | USD | 2026-08-08 | Published on a T+1 lag relative to the date it describes — shifted forward one row before use to avoid lookahead bias. Not published on days the bond market is closed; forward-filled onto GLD's trading calendar on those days, since no new value exists to report (see README §3). |

**Note.** Both raw data files ARE committed to the repository (`data/raw/gld_raw.csv` and
`data/raw/DFII10.csv`), so the project reproduces its core results without internet access.
To refresh them: GLD re-fetches via yfinance (`loaders.fetch_gld()`); DFII10 is re-downloaded
manually from the FRED URL above and saved to `data/raw/DFII10.csv`.
