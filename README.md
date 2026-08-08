# gold_rate_carry

A small, auditable research study: does **10-year real-yield momentum** condition
a long/flat position in **GLD**? Built with strict separation of concerns so each
step is reproducible and every data change is documented.

## Layout

Three top-level folders — code, data, results:

```
gold_rate_carry/
├── src/                  # all source code (import as a package: `from src import ...`)
│   ├── loaders.py        # raw retrieval (GLD via yfinance; DFII10 from manual FRED CSV)
│   ├── audit.py          # read-only anomaly diagnostics (no fixes)
│   ├── report_audit.py   # formats audit results into result/audit_flags.md + CSVs
│   ├── clean.py          # DFII10 T+1 alignment + calendar merge onto GLD
│   ├── signals.py        # compute_signal + apply_monthly_rebalance
│   ├── costs.py          # cost drag model (bps + expense ratio)
│   ├── backtest.py       # signal-agnostic engine -> equity curve + trade log
│   ├── evaluate.py       # grid runner, OOS, regime split, block bootstrap
│   └── report.py         # self-contained HTML report (not yet implemented)
├── data/
│   ├── raw/
│   │   ├── DFII10.csv     # manual FRED download (tracked)
│   │   └── gld_raw.csv    # yfinance cache (gitignored, regenerable)
│   ├── merged.csv         # clean.py output (gitignored)
│   └── decisions.md       # human paper trail for every data change (tracked)
├── result/               # generated audit_flags.* / report.html (gitignored)
├── source_note.md        # every source, ticker, frequency, caveat
├── requirements.txt
└── README.md
```

## Design principles

- **One responsibility per file.** Loading, auditing, and cleaning never mix.
- **No lookahead bias.** DFII10 is aligned T+1 to its publication date in `clean.py`.
- **Auditable data changes.** `audit.py` only flags; fixes must be recorded in
  `data/decisions.md` before `clean.py` may apply them.
- **Reusable engine.** `backtest.py` and `evaluate.py` are asset- and
  strategy-agnostic.

## Data

Both series are stored as CSV under `data/`:

- **GLD** — pulled live via yfinance by `loaders.fetch_gld()` and cached to
  `data/raw/gld_raw.csv` (gitignored, regenerable). No credentials required.
- **DFII10** — downloaded **manually** from FRED
  ([series DFII10](https://fred.stlouisfed.org/series/DFII10)) and saved as
  `data/raw/DFII10.csv` (native columns `observation_date`, `DFII10`). This file
  **is tracked** (public-domain FRED data) so the repo is reproducible without a
  manual re-download. `loaders.load_dfii10()` raises clearly if it is missing.
- **merged** — `clean.py` writes the aligned/merged frame to `data/merged.csv`
  (gitignored, regenerable).

There are **no required environment variables** — DFII10 is a manual file, so no
API key is needed.

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate      # Windows
pip install -r requirements.txt
```

## Usage

Run the pipeline by importing the package from the repo root, e.g.:

```python
from src import loaders, clean, evaluate
gld = loaders.fetch_gld("2004-11-01", "2026-08-07")
dfii = loaders.load_dfii10()
merged = clean.clean_and_merge(gld, dfii)
grid = evaluate.run_parameter_grid(merged)
```

## Status

Data loading, audit, cleaning, signal, costs, backtest, and evaluation
(parameter grid / OOS / regime split / block bootstrap) implemented. The HTML
report (`src/report.py`) is not yet built.
