"""Read-only diagnostics.

Flags anomalies (price jumps beyond N std devs, repeated/stale values, gaps
beyond the expected trading calendar, zero/negative prices, DFII10
publication-date misalignment). Makes NO judgment calls about what caused an
anomaly or how to fix it -- outputs a list of flagged dates/issues for human
review only. Every fix that follows is decided by a human and recorded in
decisions.md, then applied by clean.py.
"""

from __future__ import annotations

import pandas as pd
