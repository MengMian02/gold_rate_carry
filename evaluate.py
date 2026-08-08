"""Strategy-agnostic evaluation tools.

Performance metrics (Sharpe, drawdown, hit rate, turnover, etc.), a parameter
grid runner, regime-split comparison, and block bootstrap significance testing.
Operates on any equity curve -- no strategy-specific logic lives here.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
