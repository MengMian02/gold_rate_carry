"""Report rendering.

Renders the self-contained HTML report (conclusion, cumulative performance vs
benchmark, drawdown, rolling Sharpe, signal/position chart, diagnostic chart)
from backtest + evaluate outputs. Output is written to outputs/report.html.
"""

from __future__ import annotations

import pandas as pd
