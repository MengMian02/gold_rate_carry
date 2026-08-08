# Source Note

Every data source used, with enough detail to reproduce the pull. Fill in the
download date each time raw data is refreshed.

| Series | Meaning | Source | Ticker / ID | Frequency | Download date | Stored as | Caveats |
|--------|---------|--------|-------------|-----------|---------------|-----------|---------|
| GLD | SPDR Gold Shares ETF price | yfinance (Yahoo Finance), live pull | `GLD` | Daily | live per `fetch_gld()` run | `data/raw/gld_raw.csv` | Adjusted vs. unadjusted close; splits/dividends; Yahoo revisions. |
| DFII10 | 10-Year Treasury Inflation-Indexed (real) yield | FRED, **manual CSV download** | `DFII10` | Daily (business days) | 2026-08-08 | `data/raw/DFII10.csv` (native cols `observation_date`, `DFII10`) | Publication lag (aligned T+1 in `clean.py`); missing on holidays (NaN preserved); occasional revisions. |

## Notes

- **DFII10 is not fetched programmatically.** Download it manually from
  <https://fred.stlouisfed.org/series/DFII10> and save it to
  `data/raw/DFII10.csv`. Update the download date above on each refresh.
- Record the exact download date for each refresh so results are reproducible.
- Any source-side revision that changes historical values must be captured in
  `data/decisions.md`.
- Both series are stored as CSV under `data/` for offline reproducibility.
