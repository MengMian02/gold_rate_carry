"""gold_rate_carry source package.

Data pipeline (raw -> audited -> cleaned/merged):
    loaders.py       -> raw retrieval (GLD via yfinance; DFII10 from manual FRED CSV)
    audit.py         -> read-only anomaly diagnostics (no fixes)
    report_audit.py  -> format audit results for human review (writes to result/)
    clean.py         -> DFII10 T+1 alignment + calendar merge onto GLD

Strategy pipeline (signal -> backtest -> evaluate):
    signals.py       -> compute_signal + apply_monthly_rebalance
    costs.py         -> build_cost_fn (transaction bps + expense ratio)
    backtest.py      -> run_backtest (signal-agnostic equity curve + trade log)
    evaluate.py      -> parameter grid, OOS confirmation, regime split, block bootstrap
    report.py        -> self-contained HTML report (not yet implemented)

Import as a package, e.g. ``from src import loaders, clean, evaluate``. Naming the
signal module ``signals`` (and namespacing it under ``src``) avoids the stdlib
``signal`` clash.

File locations (repo-root relative):
    data/raw/DFII10.csv   -- manual FRED download (tracked)
    data/raw/gld_raw.csv  -- yfinance cache (gitignored)
    data/merged.csv       -- clean.py output (gitignored)
    data/decisions.md     -- human data-decision paper trail (tracked)
    result/               -- generated reports (gitignored)
"""
