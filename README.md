# gold_rate_carry

A small, auditable research study: does **10-year real-yield momentum** condition
a long/flat position in **GLD**? Built with strict separation of concerns so each
step is reproducible and every data change is documented.

## Layout

```
gold_rate_carry/
├── data/
│   ├── loaders.py      # raw pulls only (GLD via yfinance, DFII10 via FRED)
│   ├── audit.py        # read-only anomaly diagnostics (no fixes)
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

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate      # Windows
pip install -r requirements.txt
```

## Status

Scaffold only — modules contain docstrings and interfaces, no implementation yet.
