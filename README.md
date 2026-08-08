# gold_rate_carry

A small, auditable research study: does **10-year real-yield momentum** condition
a long/flat position in **GLD**? Built with strict separation of concerns so each
step is reproducible and every data change is documented.

## Layout

```
gold_rate_carry/
├── data/
│   ├── loaders.py      # raw retrieval only (GLD via yfinance; DFII10 from manual FRED CSV)
│   ├── audit.py        # read-only anomaly diagnostics (no fixes)
│   ├── report_audit.py # formats audit results into audit_flags.md + CSVs (display only)
│   ├── decisions.md    # human paper trail for every data change
│   └── clean.py        # applies ONLY documented fixes + T+1 DFII10 alignment
├── signal.py           # real_yield_momentum(df, lookback) -> weight series
├── costs.py            # cost drag model (bps + expense ratio)
├── backtest.py         # signal-agnostic engine -> equity curve + trade log
├── evaluate.py         # metrics, grid runner, regime splits, block bootstrap
├── report.py           # renders self-contained HTML report
├── notebooks/main.ipynb# orchestration only, in narrative order
├── outputs/            # report.html + data/ snapshots (gitignored)
├── memo.md             # thesis / risks / persistence
├── source_note.md      # every source, ticker, frequency, caveat
└── requirements.txt
```

## Design principles

- **One responsibility per file.** Loading, auditing, and cleaning never mix.
- **No lookahead bias.** DFII10 is aligned T+1 to its publication date in `clean.py`.
- **Auditable data changes.** `audit.py` only flags; fixes must be recorded in
  `decisions.md` before `clean.py` may apply them.
- **Reusable engine.** `backtest.py` and `evaluate.py` are asset- and
  strategy-agnostic.

## Data

Both series are stored as CSV under `outputs/data/raw/` (gitignored):

- **GLD** — pulled live via yfinance by `loaders.fetch_gld()` and cached to
  `gld_raw.csv`. No credentials required.
- **DFII10** — downloaded **manually** from FRED
  ([series DFII10](https://fred.stlouisfed.org/series/DFII10)) and saved as
  `outputs/data/raw/DFII10.csv` (native columns `observation_date`, `DFII10`).
  `loaders.load_dfii10()` reads it and raises clearly if the file is missing.

There are **no required environment variables** — DFII10 is a manual file, so no
API key is needed.

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate      # Windows
pip install -r requirements.txt
```

## Status

Data-loading and read-only audit stages implemented; cleaning, signal, backtest,
and evaluation stages not yet built.
