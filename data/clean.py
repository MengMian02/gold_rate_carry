"""Publication-date alignment and calendar merge for GLD + DFII10.

Per data/decisions.md, the 2026-08-08 validation review found NO anomalies that
require correction in either series. So this module does NOT do anomaly fixing.
Its job is exactly two things:

  1. Apply the DFII10 T+1 publication lag (shift by one ROW, not one calendar
     day) so each date carries only information that was public as of that date.
  2. Merge GLD and DFII10 onto GLD's trading calendar (the calendar we can
     actually trade on), forward-filling DFII10 across genuine calendar gaps.

No signal, cost, or backtest logic lives here -- alignment and merging only.
"""

from __future__ import annotations

import warnings
from pathlib import Path

import numpy as np
import pandas as pd

_MERGED_CACHE = (
    Path(__file__).resolve().parent.parent / "outputs" / "data" / "merged.csv"
)

# Heuristic threshold for the GLD-gap sanity check (step 2b). Between two
# consecutive GLD trading days a normal weekend is 0 missing weekdays, a single
# holiday is 1, and a rare two-holiday week is 2. More than this many
# *consecutive missing weekdays* looks like a real data hole rather than a
# holiday, so we warn (never fill). This is a heuristic, not a precise NYSE
# calendar check -- tune if it proves too noisy or too quiet.
_SUSPICIOUS_GLD_GAP_MISSING_BDAYS = 4


def clean_and_merge(gld_df: pd.DataFrame, dfii10_df: pd.DataFrame) -> pd.DataFrame:
    """Align DFII10 to T+1 and merge with GLD onto GLD's trading calendar.

    Returns a DataFrame indexed by ``date`` with columns:
        gld_close, gld_adj_close, dfii10_aligned, dfii10_forward_filled (bool)

    ``dfii10_forward_filled`` marks any row where the DFII10 value was carried
    forward from an earlier publication (a calendar gap or an in-series NaN),
    rather than being a direct same-day observation. Caches the result to
    ``outputs/data/merged.csv``.
    """
    gld = gld_df.sort_index()
    dfii = dfii10_df.sort_index()

    # ------------------------------------------------------------------
    # Step 1: DFII10 T+1 publication-lag alignment.
    #
    # ASSUMPTION (stated, not fully verified): DFII10 for observation date T is
    # published one business day later, so the most recent value publicly known
    # ON date T is the one labeled T-1. We therefore shift the series forward by
    # ONE ROW in its own date-ordered index -- "the previous available DFII10
    # publication" -- NOT by a blind 24-hour / 1-calendar-day offset, so the
    # shift stays correct across holidays and gaps in the series.
    #
    # A reader may want to verify this single-business-day lag against FRED's
    # actual DFII10 release calendar; it is a modeling assumption here, not an
    # established fact.
    # ------------------------------------------------------------------
    dfii_shifted = dfii["dfii10_value"].shift(1)

    # ------------------------------------------------------------------
    # Step 2: merge onto GLD's trading calendar (the base -- we can only act on
    # days GLD trades).
    #
    # For each GLD trading day we take the most recently AVAILABLE shifted DFII10
    # value as of that day. We reindex the shifted series onto the union of both
    # calendars and forward-fill with a plain value-ffill, which carries the last
    # *non-NaN* published value across both (a) genuine calendar gaps -- GLD
    # trading days that are bond-market holidays -- and (b) NaN holiday rows
    # inside the DFII10 series itself.
    #
    # This forward-fill is a DELIBERATE, NARROW exception to the project's
    # "don't fill gaps" rule. It is justified because it reflects what a real
    # trader would actually know on that day: the last published real yield. It
    # is NOT an attempt to paper over a data-quality problem (decisions.md
    # confirmed there are none).
    # ------------------------------------------------------------------
    union_index = dfii_shifted.index.union(gld.index)
    aligned_full = dfii_shifted.reindex(union_index).ffill()
    dfii10_aligned = aligned_full.reindex(gld.index)

    # A row was forward-filled when it now has a value but there was NO direct,
    # same-dated, non-NaN shifted DFII10 observation on that GLD day.
    direct = dfii_shifted.reindex(gld.index)
    dfii10_forward_filled = dfii10_aligned.notna() & direct.isna()

    # ------------------------------------------------------------------
    # Step 2b: never forward-fill GLD. If GLD's own trading calendar has a gap
    # that looks like genuinely missing data (not a plausible holiday cluster),
    # warn -- do not fill.
    # ------------------------------------------------------------------
    _warn_on_gld_gaps(gld.index)

    merged = pd.DataFrame(
        {
            "gld_close": gld["close"],
            "gld_adj_close": gld["adj_close"],
            "dfii10_aligned": dfii10_aligned,
            "dfii10_forward_filled": dfii10_forward_filled,
        },
        index=gld.index,
    )
    merged.index.name = "date"

    _MERGED_CACHE.parent.mkdir(parents=True, exist_ok=True)
    merged.to_csv(_MERGED_CACHE)
    return merged


def _warn_on_gld_gaps(gld_index: pd.DatetimeIndex) -> None:
    """Warn about suspiciously large gaps in GLD's own trading calendar.

    Heuristic only: counts consecutive missing weekdays between successive GLD
    trading days and warns when that exceeds _SUSPICIOUS_GLD_GAP_MISSING_BDAYS.
    Never fills -- a real gap is surfaced for human verification.
    """
    if len(gld_index) < 2:
        return
    days = gld_index.normalize().to_numpy(dtype="datetime64[D]")
    missing = np.busday_count(days[:-1], days[1:]) - 1  # weekdays strictly between
    for i in np.where(missing >= _SUSPICIOUS_GLD_GAP_MISSING_BDAYS)[0]:
        warnings.warn(
            f"GLD trading-calendar gap: {int(missing[i])} consecutive weekdays "
            f"missing between {pd.Timestamp(days[i]).date()} and "
            f"{pd.Timestamp(days[i + 1]).date()}. Not filled -- verify whether this "
            "is a real market closure or missing source data.",
            stacklevel=2,
        )
