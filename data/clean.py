"""Applies ONLY the fixes explicitly specified in decisions.md.

No independent judgment calls -- every transformation here should be traceable
to a documented decision. Also handles DFII10 publication-date alignment
(T+1 lag) so no lookahead bias enters downstream.
"""

from __future__ import annotations

import pandas as pd
