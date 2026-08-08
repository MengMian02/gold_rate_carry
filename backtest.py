"""Signal-agnostic backtest engine.

Takes ANY weight series + price series + cost model and returns an equity curve
and trade log. Must not contain any GLD- or DFII10-specific logic --
asset-agnostic by design so future strategies reuse this unchanged.
"""

from __future__ import annotations

import pandas as pd
