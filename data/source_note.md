# Source Note

One row per data source used in this project. Update the download date whenever a
series is refreshed.

| Source | URL | Ticker/Series | Frequency | Download date | Caveats |
|---|---|---|---|---|---|
| yfinance | yfinance package (ultimately Yahoo Finance) | GLD | Daily | 2026-08-08 | None material — standard OHLCV for a large, liquid ETF |
| FRED | https://fred.stlouisfed.org/series/DFII10 | DFII10 | Daily (business days only) | 2026-08-08 | Published on a T+1 lag relative to the date it describes — shifted forward one row before use to avoid lookahead bias. Not published on days the bond market is closed; forward-filled onto GLD's trading calendar on those days, since no new value exists to report (see README §3). |
