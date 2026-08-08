"""Cost model.

Takes a trade/weight series and cost assumptions (one-way bps, annual expense
ratio) and returns the cost drag applied to returns. Kept separate from
backtest.py so cost assumptions can be swapped and sensitivity-tested
independently of the backtest engine.
"""

from __future__ import annotations

import pandas as pd
