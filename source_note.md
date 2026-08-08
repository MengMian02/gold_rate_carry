# Source Note

Every data source used, with enough detail to reproduce the pull. Fill in the
download date each time raw data is refreshed.

| Series | Meaning | Source | Ticker / ID | Frequency | Download date | Caveats |
|--------|---------|--------|-------------|-----------|---------------|---------|
| GLD | SPDR Gold Shares ETF price | yfinance (Yahoo Finance) | `GLD` | Daily | _TBD_ | Adjusted vs. unadjusted close; splits/dividends; Yahoo revisions. |
| DFII10 | 10-Year Treasury Inflation-Indexed (real) yield | FRED | `DFII10` | Daily (business days) | _TBD_ | Publication lag (aligned T+1 in `clean.py`); missing on some holidays; occasional revisions. |

## Notes

- Record the exact download date for each refresh so results are reproducible.
- Any source-side revision that changes historical values must be captured in
  `data/decisions.md`.
- Raw snapshots are saved under `outputs/data/` for offline reproducibility.
