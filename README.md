# gold_rate_carry

---

## 1. Overview

**Strategy tested:** long GLD when the 20-trading-day change in the 10-Year Treasury Inflation-Protected real yield (FRED: `DFII10`) is negative; flat otherwise. Monthly rebalance.

**Core question:** does gold's price respond to the real (inflation-adjusted) discount rate in a way that's tradeable, net of costs, and does that relationship survive out-of-sample and across different rate regimes?

**Headline finding:** the mechanism shows genuine, statistically distinguishable edge in a near-zero/falling-rate regime (2008–2021), but breaks down — and underperforms a random-timing benchmark — in the 2022–2024 rate-hiking regime, consistent with a specific, named competing driver (central-bank gold buying) overwhelming the discount-rate channel in that period. Full detail in §7–8.

---

## 2. Why this project, and why this asset/mechanism

Gold pays no yield. The opportunity cost of holding it — what you give up by not holding something that does pay — is proxied by the real interest rate: falling real yields reduce that opportunity cost and should support gold's price; rising real yields raise it.

**A more precise framing than plain "opportunity cost": duration.** Treat gold as an effectively infinite-maturity, zero-coupon claim — the real-asset analogue of a perpetual bond. For an ordinary zero-coupon bond, price ≈ 1/(1+r)^T; as T grows, sensitivity to r grows without bound. Gold, having no maturity at all, should therefore be *unusually* sensitive to the discount rate — not just marginally affected by it. This is close to the framing in Barsky & Summers (1988), which modeled gold roughly as a consol-like claim on the real rate rather than treating it as an ordinary commodity.

**Why the real yield specifically, not the nominal yield.** Gold's nominal price is pushed by at least two forces that partly offset each other: the real discount rate (the duration channel above), and inflation expectations (gold as a partial inflation hedge — rising expected inflation tends to push both nominal yields and gold's nominal price up, opposite signs on the two channels). Using `DFII10` (a TIPS-implied real yield) nets out the inflation-expectation component before it reaches the signal, isolating the discount-rate channel directly rather than requiring a multi-variable regression to disentangle it — the latter would edge toward the "large optimization exercise" the case brief explicitly discourages.

**A named, third channel this strategy deliberately does not capture.** Central-bank reserve diversification and geopolitical safe-haven demand are a separate, real driver of gold demand — most plausibly the dominant explanation for 2022–2024, when real yields spiked (Fed hiking) but gold did not fall, plausibly linked to accelerated central-bank gold buying (China and others) following the 2022 freezing of Russian FX reserves, which made large USD reserve holdings look more politically exposed. This strategy tests one specific, real channel; it does not claim to be a complete model of gold pricing, and §8 shows this limitation appearing exactly where expected.

### Candidates considered and rejected

Four candidates were evaluated against the case's permitted universe (economic/seasonal, mean-reversion, momentum categories):

| Candidate | Mechanism | Reason not selected |
|---|---|---|
| Turn-of-month SPY seasonality | Structural month-end/month-start flows (payroll, pension rebalancing) | Well-documented since the 1980s with clear post-decay evidence; likely verdict is generic ("known anomaly decayed") rather than mechanism-specific |
| 2–5 day mean reversion, SPY | Liquidity-provision compensation after sharp declines | High turnover makes the honest verdict close to "selected a strategy already known to fail under costs" unless very deliberately framed |
| 12-1 time-series momentum, small basket | Slow information diffusion / risk premium | Most standard, most crowded choice; low differentiation, generic post-2010 decay story |
| **GLD × real yield (selected)** | Discount-rate/duration channel | Genuine economic mechanism, natural two-era regime split, honest and *specific* (not generic) known weakness |

---

## 3. Pre-commitment block

Per the case's requirement to commit to design choices before touching data, the following was fixed in advance:

**Mechanism:** real-yield discount-rate/duration channel (§2).

**Falsifiable condition:** the mechanism is considered unsupported if (a) net-of-cost performance in the signal-on state is statistically indistinguishable from signal-off (tested via block bootstrap), (b) any apparent edge concentrates in one narrow sub-period rather than persisting across regimes, or (c) results only hold for one specific lookback in the parameter grid (a tuning artifact rather than a real relationship).

**Parameter grid:** lookback window for the DFII10 change, N ∈ {10, 20, 40, 60} trading days — chosen because these track the natural cadence of the underlying macro data (roughly two weeks, one month, two months, one quarter), not arbitrary numbers. Sign of change only — no magnitude threshold — to keep N the single tunable parameter in the entire strategy.

**In-sample / out-of-sample split:** IS = Jan 2005–Dec 2016 (parameter selection only), OOS = Jan 2017–present (rules frozen, no further tuning). GLD inception is Nov 2004; the ~2-month gap before the IS start is used only to satisfy each candidate's lookback burn-in with real data, never counted toward any reported IS metric.

*Why 12 years IS vs. ~9 years OOS, not an even split:* selecting among four discrete lookback values doesn't require extensive data to resolve — 2005–2016 spans more than one full real-rate cycle (2008 collapse, 2013 taper tantrum, subsequent grind lower), which is enough to avoid picking a lookback that only fits one directional trend. Extending IS further would mostly shrink OOS, at direct cost to statistical power on the number that matters most for the verdict, and at the cost of pulling the 2022–2024 breakdown period — deliberately left in OOS rather than tuned around — out of the honest test.

**Regime split (separate axis from IS/OOS):** Regime 1 = 2008–2021 (near-zero/falling real yields), Regime 2 = 2022–2024 (sharply rising real yields, the acknowledged breakdown period). Defined by the real-yield trend itself, matching the mechanism under test, rather than an arbitrary volatility-based cut. Regime and IS/OOS windows deliberately overlap in calendar time — they answer different questions (did you tune on the future? vs. does performance hold across macro conditions?).

**Benchmark:** GLD buy-and-hold (primary), plus an exposure-matched random-timing benchmark (§6) — since the strategy is not invested 100% of the time, a raw comparison to buy-and-hold conflates timing skill with simply not being exposed some of the time.

**Costs:** applied on every position change (one-way bps) plus GLD's ongoing expense ratio (continuous holding cost) — see §5.

---

## 4. Data

| Series | Source | Notes |
|---|---|---|
| GLD (OHLCV) | yfinance | Listed, exchange-traded — standard ticker coverage |
| DFII10 (10Y real yield) | FRED (manual CSV download) | Not a tradeable instrument — a published Treasury/Fed statistic, not covered by yfinance; downloaded by hand and read from `data/raw/DFII10.csv` |

**Publication-date (T+1) alignment.** FRED's DFII10 is labeled by the date it describes, not the date it was published — a value dated day T is not actually knowable until T+1. Before merging, DFII10 is shifted forward by one row (relative to its own date-ordered index, not a blind calendar-day shift, so it remains correct around holidays/gaps) so that the value used in any trading decision on day T reflects only what was genuinely public knowledge by day T. This assumption (single-business-day publication lag) is stated, not independently verified against FRED's release calendar in detail — worth a closer check if extended further.

**Trading-calendar mismatch.** GLD trades on the NYSE calendar; DFII10 is published on Treasury/bond-market business days — these calendars are not identical (some bond-market holidays are NYSE trading days and vice versa). The merge uses GLD's calendar as the base (the calendar actually traded on); on any GLD trading day where no T+1-aligned DFII10 value yet exists, the most recent published value is forward-filled, with a flag column marking every row where this occurred — a deliberate, narrow, documented exception, since it reflects what a real trader would actually know rather than papering over a genuine data gap. GLD itself is never forward-filled.

**Data quality review.** Both series were independently audited for hard errors (duplicate/non-monotonic dates, implausible units, price/OHLC inconsistencies — designed to raise immediately) and anomalies (extreme moves via median-absolute-deviation threshold, repeated/stale values, zero-volume days) before merging. Flags were triaged by category rather than reviewed row-by-row: repeated-value flags in DFII10 were resolved as a batch, reflecting the series' native reporting precision and lower TIPS-market turnover rather than a stale feed; extreme-move flags were reviewed individually against known market events. Full disposition and reasoning: `data/decisions.md`.

---

## 5. Costs

Two components, kept separable (they respond differently to changes in trading frequency vs. holding duration, and the case requires cost-sensitivity testing):

- **Per-trade cost:** 8 bps one-way (midpoint of the case's suggested 5–10 bps range for liquid commodity ETFs), applied only on the specific dates the position changes.
- **Expense ratio drag:** 0.40% annually (GLD's published expense ratio), applied continuously while holding, independent of trading activity.

Position timing follows `position(t-1) × return(t)` throughout (avoiding same-day lookahead), so the expense-ratio drag begins accruing the day *after* a position is opened, not the day it's decided — consistent with the same execution-timing convention used in the backtest engine.

---

## 6. Methodology

**Signal-agnostic, reusable design.** The pipeline is deliberately split into single-responsibility, composable modules — `src/loaders.py` (raw fetch), `src/audit.py` (read-only diagnostics), `src/clean.py` (alignment/merge only), `src/signals.py` (position weights, general float output not hardcoded boolean), `src/costs.py`, `src/backtest.py` (asset- and signal-agnostic engine), `src/evaluate.py`. This keeps the current strategy's logic simple — matching the case's explicit "no large optimization exercise" instruction — while the engine, cost model, and evaluation tools stay reusable for future strategies/assets beyond this submission.

**Parameter selection (in-sample only).** For each candidate lookback, the full pipeline runs on the full available data range (for correct signal burn-in), then results are filtered to the IS window only before any metric is computed — no date outside IS ever influences IS metric selection. All four candidates are reported, not just the winner.

**Exposure-matched random benchmark.** Since the strategy is not invested 100% of the time, comparing directly to GLD buy-and-hold's Sharpe is not a fair test: mixing in flat (zero-return, zero-variance) periods can mechanically move a Sharpe ratio independent of any real timing skill, and how much it moves depends entirely on which days happen to be flat — not something inferable from a single number. The benchmark instead generates many (500) random month-level position series with the same total exposure (same count of "on" months) as the actual strategy in a given window, runs each through the identical pipeline, and reports where the actual strategy's Sharpe falls within that distribution — directly testing timing skill, isolated from the effect of simply not always being exposed.

**Block bootstrap significance.** Daily returns within a monthly holding period are autocorrelated, violating the independence assumption behind standard significance tests. A moving block bootstrap (block length 21 trading days, matching the monthly rebalance cadence — a stated judgment call, not a derived value) resamples contiguous chunks of the return series to preserve that within-period dependency, builds a distribution of plausible Sharpe outcomes under resampling, and reports where zero falls relative to that distribution.

**A key distinction between the two significance checks, easy to conflate:** the block bootstrap tests whether the Sharpe ratio is reliably *above zero* — which a strategy can satisfy purely from directional market exposure (beta) during a period the underlying asset trended up, with no timing skill at all. The random exposure-matched benchmark tests whether the *specific dates chosen* outperform other equally-sized, randomly-chosen date sets — isolating timing skill specifically. The two can and do disagree (§8).

---

## 7. Results

### 7.1 In-sample parameter grid (2005–2016)

| Lookback | Sharpe | Ann. return | Ann. vol | Max DD | Hit rate | Turnover | Trades | Avg hold (d) | Cost drag |
|---|---|---|---|---|---|---|---|---|---|
| 10 | 0.465 | 5.7% | 13.9% | −26.1% | 0.515 | 6.0 | 72 | 49.2 | 0.173 |
| **20 (selected)** | **0.601** | **7.4%** | 13.3% | −16.9% | 0.519 | 6.2 | 74 | 43.6 | 0.207 |
| 40 | 0.219 | 2.1% | 13.5% | −44.7% | 0.515 | 5.0 | 60 | 54.6 | 0.098 |
| 60 | 0.522 | 6.5% | 13.9% | −21.8% | 0.524 | 3.3 | 40 | 88.3 | 0.132 |

Selected by highest IS Sharpe: **N = 20** (≈ one calendar month — also the strategy's rebalance frequency, and roughly the natural refresh interval of the CPI/FOMC-driven information flow that moves real yields). N = 20's win over N = 60 is real but not dominant (0.601 vs. 0.522) — a narrow win among economically plausible neighbors is more consistent with a genuine, moderately robust signal than a single spiking outlier would have been.

IS random-benchmark check: N=20 beat 473 of 500 exposure-matched random draws (**94.6th percentile**) — meaningfully better than dilution alone would produce.

### 7.2 Out-of-sample confirmation (2017–2025), N = 20 frozen

| Metric | Value |
|---|---|
| Sharpe | 0.636 |
| Ann. return | 6.6% |
| Ann. vol | 11.0% |
| Max drawdown | −19.0% |
| Hit rate | 0.543 |
| Trades | 49 |
| Avg hold (d) | 50.4 |
| Random-benchmark percentile | **36.2nd** (beat 181/500 random draws; random mean 0.711) |

An OOS Sharpe of 0.636 looks respectable in isolation, but falls *below* the exposure-matched random benchmark's own mean — the pooled OOS result does not show genuine timing skill once dilution is controlled for.

### 7.3 Regime split, N = 20 frozen

| Metric | Regime 1 (2008–2021) | Regime 2 (2022–2024) |
|---|---|---|
| Sharpe | 0.589 | −0.043 |
| Ann. return | 6.9% | −0.9% |
| Ann. vol | 12.8% | 9.5% |
| Max drawdown | −17.7% | −19.0% |
| Hit rate | 0.529 | 0.514 |
| Trades | 80 | 20 |
| Random-benchmark percentile | **98.2nd** (beat 491/500) | **8.8th** (beat 44/500) |
| Random draws' mean Sharpe | 0.231 | 0.553 |

The pooled OOS result (§7.2) is a blend of a genuinely strong late stretch of Regime 1 and the Regime 2 collapse — the regime split is what actually explains the weak aggregate OOS figure.

### 7.4 Block bootstrap significance (block = 21 days, 1,000 replicates, seed 42)

| Period | Actual Sharpe | Bootstrap mean | 95% CI | P(Sharpe ≤ 0) |
|---|---|---|---|---|
| IS (2005–2016) | 0.601 | 0.615 | [0.067, 1.172] | 0.012 |
| OOS (2017–2025) | 0.636 | 0.638 | [0.075, 1.246] | 0.012 |
| Regime 1 (2008–2021) | 0.589 | 0.550 | [0.070, 1.082] | 0.013 |
| Regime 2 (2022–2024) | −0.043 | 0.013 | [−0.886, 0.878] | 0.482 |

---

## 8. Discussion

**IS, OOS, and Regime 1 are all bootstrap-distinguishable from zero — but OOS's positive bootstrap result should not be read as validation.** OOS's Sharpe is reliably positive (95% CI excludes zero) largely because GLD trended upward over 2017–2025 and the strategy was long roughly half the time — a beta effect that a randomly-timed strategy with the same exposure would capture just as well, and indeed did slightly better (§7.2's 36.2nd percentile). The bootstrap test and the random-timing benchmark answer genuinely different questions and can disagree; only Regime 1 shows both a reliably-positive Sharpe *and* genuine outperformance of random timing — the strongest evidence of real, mechanism-driven skill in this project.

**Regime 2's failure is not just "worse" — it is a different kind of result, and one predicted in advance.** Its Sharpe is negative but not statistically distinguishable from zero (95% CI spans from −0.89 to 0.88, driven by the regime's short window — 36 months, 20 trades). It also underperformed random timing (8.8th percentile). Both facts point toward the same interpretation named at the outset (§2): the discount-rate/duration channel this strategy is built on was real and exploitable when it was the dominant driver of gold pricing (Regime 1), and was overwhelmed by a separate, non-modeled channel — plausibly central-bank reserve diversification — once that channel began to dominate (Regime 2). The strategy correctly stopped adding value exactly where its own stated mechanism predicted it would.

**Real yield vs. nominal price convention.** DFII10 is a real (inflation-adjusted) yield, while GLD's price and return series used throughout are nominal. At the ~20-trading-day horizon the signal operates on, this is not a meaningful source of bias: expected inflation over such a short window is small relative to gold's own short-horizon volatility, so it does not distort the relationship the signal tests. It does matter for the headline cumulative and annualized return figures reported in §7, since realized inflation compounds meaningfully over the multi-year IS/OOS/regime windows and is embedded in every nominal GLD return, strategy and benchmark alike. Because both the strategy's returns and every benchmark it's compared against (buy-and-hold, exposure-matched random draws) hold the same nominal asset, this inflation drift enters both sides symmetrically — it inflates the level of headline returns reported, but does not bias the relative comparisons (Sharpe differentials, random-benchmark percentiles) that the verdict actually rests on.

---

## 9. Status and reproducibility

**Completed:** data collection, audit, cleaning/merge, signal, costs, backtest engine, IS parameter selection, OOS confirmation, regime split, block bootstrap significance.

**Pending:** final verdict and 300–500 word memo (`memo.md`), source note (`source_note.md`), self-contained HTML report (`result/report.html`), cost-sensitivity testing across the case's suggested bps range.

**Environment:** Python virtual environment at `.venv`; no API keys required — DFII10 is a manually downloaded FRED CSV (`data/raw/DFII10.csv`). See `CLAUDE.md` for coding-agent working conventions used on this project (data-integrity rules, staged-process discipline).

**Planned extension (post-submission):** this repo's signal/backtest/evaluate interfaces were deliberately kept generic (asset-agnostic engine, pluggable signal functions returning float weights) so they can be reused for a broader project beyond this case — additional signals, a continuous-weighting version of this strategy, and cross-asset generalization tests.
