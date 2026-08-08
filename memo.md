# Memo

_Target: 300–500 words. Written before results are final; update the "persistence"
section once the backtest and robustness checks are in._

## Why it may work

_(Placeholder — to be written.)_ The economic thesis links gold's price to the
real cost of holding it. Gold pays no coupon, so the opportunity cost of owning
it is the real yield available on safe assets (proxied by DFII10, the 10-year
TIPS yield). When real yields fall, that opportunity cost drops and gold tends
to become more attractive; when they rise, the reverse. A momentum reading on
real yields is therefore a plausible conditioning variable for a long/flat GLD
position.

## What could break it

_(Placeholder — to be written.)_ Candidate failure modes to address:

- **Regime dependence** — the real-rate/gold relationship may only hold in some
  monetary regimes and invert or vanish in others.
- **Overfitting the lookback** — a single tuned lookback may not survive the
  parameter grid or block bootstrap in `evaluate.py`.
- **Costs** — turnover from a momentum signal can erode a thin edge once
  one-way bps and the expense ratio are applied.
- **Data artifacts** — publication-lag / lookahead bias if DFII10 alignment is
  wrong; corporate actions or source revisions in GLD.

## Persistence

_(Placeholder — to be written after results.)_ Whether any edge is likely to
persist out-of-sample, and why or why not.
