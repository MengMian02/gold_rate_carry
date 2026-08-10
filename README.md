# gold_rate_carry

A backtest of a real-yield-driven timing strategy on GLD (SPDR Gold Shares).

---

## Abstract

Gold pays no yield, so the opportunity cost of holding it is proxied by the real
(inflation-adjusted) interest rate. This project tests a simple rule — long GLD when the
20-trading-day change in the 10-Year TIPS real yield (FRED: `DFII10`) is negative, flat
otherwise, monthly rebalance — and asks whether that relationship is tradeable net of
costs, whether it holds out-of-sample, and whether it survives across different real-rate
regimes.

**Finding:** the strategy shows genuine, statistically distinguishable edge in a
near-zero/falling-rate regime (2008–2021), but breaks down — and underperforms a
randomly-timed benchmark with matched exposure — in the 2022–2024 rate-hiking regime. This
is consistent with, and corroborated by, independent research on gold's real-yield
relationship weakening after 2022 as central-bank reserve buying became the dominant
marginal driver of gold demand (§8, §9).

---

## 1. Mechanism

Gold's opportunity cost of carry rises with the real interest rate: when real yields fall,
holding non-yielding gold becomes relatively more attractive; when real yields rise, the
opposite. This project isolates that channel specifically by using the *real* yield
(`DFII10`, derived from TIPS) rather than the nominal 10-year yield, which would also embed
inflation-expectation effects that move gold through a separate channel (gold as a partial
inflation hedge) with the opposite sign — using the real yield nets that channel out before
it reaches the signal, rather than requiring a multi-variable regression to separate the two.

**Theoretical grounding.** Barsky and Summers (1988) explain the historical correlation
between interest rates and the price level under the gold standard through an
opportunity-cost mechanism: a shock that raises the real rate of return reduces gold's
equilibrium relative price, operating through how gold is allocated between monetary and
non-monetary uses. This project's discount-rate framing draws directly on that mechanism —
see §9 for the full citation and further reading.

**A named limitation, not a hidden one.** This strategy tests one specific, real channel
(the discount-rate/opportunity-cost effect). It does not model, and does not claim to
capture, other drivers of gold demand — most importantly, central-bank reserve
diversification and geopolitical hedging, which independent research identifies as the
dominant force behind gold's resilience despite rising real yields from 2022 onward (§8).
The regime split in §7.3 shows this limitation appearing exactly where that research would
predict it.

---

## 2. Design

**Signal:** for lookback N, long GLD (weight = 1) if `DFII10` has fallen over the past N
trading days, flat (weight = 0) otherwise. Sign only, no magnitude threshold — this keeps N
the single tunable parameter in the entire strategy.

**Parameter grid:** N ∈ {10, 20, 40, 60} trading days — roughly two weeks, one month, two
months, one quarter, tracking the natural cadence of the macro data (CPI prints, FOMC
meetings, Treasury auctions) that moves real yields, rather than arbitrary numbers.

**Rebalance frequency vs. signal lookback — a deliberate separation, with an open cost.**
The lookback window (N) and the rebalance frequency are independent decisions, not the same
parameter. Tying rebalance frequency to N would conflate two effects inside the parameter
grid — a Sharpe difference between candidates could reflect either "this lookback reads the
real-yield trend more accurately" or "this rebalance cadence trades more efficiently," with
no way to separate the two. Fixing rebalance at monthly, independent of N, keeps N isolated
as the only thing under test.

This has a real cost, worth stating plainly rather than assuming away: the signal is
computed *daily*, but only the reading on each month's first trading day is ever acted on —
roughly 19 out of every 20 daily signal readings are computed and then never used for a
decision. This isn't a loss of underlying data (each daily reading already incorporates a
full N-day window of real-yield history), but it is a loss of decision frequency — a
signal flip mid-month that reverses before the next rebalance is invisible to the strategy,
not because the information wasn't there, but because it was never checked on a day that
mattered. Monthly rebalancing happens to roughly match N=20's own timescale, which is a
plausible reason more frequent rebalancing wouldn't help much — but this is untested, not
demonstrated, and is flagged in §10 as the natural first robustness check for future work
(e.g., re-running at weekly rebalance to see whether the additional decision frequency
improves results or mainly adds transaction cost).

**In-sample / out-of-sample split:** IS = January 2005 – December 2016 (parameter
selection only); OOS = January 2017 – December 2025 (rules frozen, no further tuning).
Twelve years of IS spans more than one full real-rate cycle (2008 collapse, 2013 taper
tantrum, subsequent grind lower) — enough to avoid selecting a lookback that only fits one
directional trend, without shrinking OOS (and its statistical power) further than
necessary. The 2022–2024 breakdown is deliberately left inside OOS rather than tuned
around, so the out-of-sample test is not artificially friendly.

**Regime split (a separate axis from IS/OOS, answering a different question):** Regime 1 =
2008–2021 (near-zero/falling real yields), Regime 2 = 2022–2024 (sharply rising real
yields — the period gold's relationship with real yields is documented to have broken
down, §8). Defined by the real-yield trend itself, matching the mechanism under test.
IS/OOS asks "was this parameter chosen honestly, without peeking at the future"; the
regime split asks "does performance hold up across different macro conditions" — the two
windows deliberately overlap in calendar time because they're different questions.

**Benchmark:** GLD buy-and-hold (primary), plus an exposure-matched random-timing
benchmark. Since the strategy isn't invested 100% of the time, a raw Sharpe comparison to
buy-and-hold conflates real timing skill with the effect of simply not always being
exposed — mixing flat, zero-variance periods into a return series can move a Sharpe ratio
independent of any skill, and how much depends entirely on which days happen to be flat.
The random benchmark instead generates many (500) random month-level position series with
the same total exposure as the actual strategy, and reports where the actual Sharpe falls
within that distribution — isolating timing skill specifically.

**Costs:** 8 bps one-way per trade (applied only when the position changes) plus GLD's
0.40% annual expense ratio (applied continuously while holding, independent of trading
activity) — kept as two separable components since they respond differently to changes in
trading frequency versus holding duration.

---

## 3. Data

| Series | Source | Notes |
|---|---|---|
| GLD (OHLCV) | yfinance | Exchange-traded, standard ticker coverage |
| DFII10 (10Y real yield) | FRED (manual CSV download) | A published Treasury/Fed statistic, not a tradeable instrument — not covered by yfinance; downloaded by hand and read from `data/raw/DFII10.csv` |

**Publication-date (T+1) alignment.** FRED's DFII10 is labeled by the date it describes,
not the date it was published — a value dated day T is not actually knowable until T+1.
Before merging, DFII10 is shifted forward by one row (relative to its own date-ordered
index, not a blind calendar-day shift, so it stays correct around holidays/gaps) so that
any trading decision on day T uses only what was genuinely public by day T.

**Trading-calendar mismatch and forward-fill.** GLD trades on the NYSE calendar; DFII10 is
published on Treasury/bond-market business days — these calendars are not identical. The
merge uses GLD's calendar as the base. On a GLD trading day where the bond market is
closed (no new DFII10 print exists), the most recent published value is forward-filled,
flagged in a dedicated column. This is not data invention: on a day the bond market is
closed, nothing occurred to change the real yield — there is no unobserved "true" value
different from the last print, only the absence of a new one. This differs from filling a
gap in a series where the true value genuinely could have been anything and simply wasn't
recorded (e.g., a missing GLD price) — that kind of gap is left as NA, never filled. GLD
itself is never forward-filled in this project.

**Data quality review.** Both series were independently audited for hard errors
(duplicate/non-monotonic dates, implausible units, OHLC inconsistencies) and anomalies
(extreme moves via median-absolute-deviation threshold, repeated/stale values, zero-volume
days) before merging. Flags were triaged by category rather than reviewed row-by-row:
repeated-value flags in DFII10 were resolved as a batch, reflecting the series' native
reporting precision and lower TIPS-market turnover rather than a stale feed; extreme-move
flags were reviewed individually against known market events. Full disposition:
`data/decisions.md`.

---

## 4. Methodology

The pipeline is split into single-responsibility, composable modules — raw data loading,
read-only audit, alignment/merge, signal generation (general float weight output, not a
hardcoded boolean), cost modeling, an asset- and signal-agnostic backtest engine, and
evaluation. This keeps the strategy itself simple while the engine, cost model, and
evaluation tools remain reusable for future strategies and assets (§10).

**Parameter selection (in-sample only).** Each candidate lookback runs the full pipeline
on the full available data range (for correct signal burn-in), then results are filtered
to the IS window only before any metric is computed — no OOS date ever influences IS
selection. All four candidates are reported.

**Exposure-matched random benchmark.** Described in §2. Generates 500 random position
series matching the strategy's actual exposure in a given window, runs each through the
identical pipeline, and reports the actual strategy's percentile rank within that
distribution.

**Block bootstrap significance.** Daily returns within a monthly holding period are
autocorrelated, violating the independence assumption behind standard significance tests.
A moving block bootstrap (block length 21 trading days, matching the rebalance cadence — a
stated judgment call) resamples contiguous chunks of the return series to preserve that
dependency, and reports where zero falls relative to the resulting Sharpe distribution.

**A key distinction, easy to conflate:** the block bootstrap tests whether the Sharpe
ratio is reliably *above zero* — satisfiable purely through directional market exposure
(beta) if the underlying asset trended up over the period, with no timing skill required.
The random exposure-matched benchmark tests whether the *specific dates chosen*
outperform other, randomly-chosen date sets with the same exposure — isolating timing
skill specifically. These can and do disagree (§7.2).

---

## 5. Costs and real-vs-nominal returns

**Costs.** Per-trade cost (8 bps) applies only on the specific dates the position changes;
the expense-ratio drag (0.40%/year) applies continuously while holding, independent of
trading. Position timing follows `position(t-1) × return(t)` throughout, so the
expense-ratio drag begins accruing the day after a position opens, not the day it's
decided.

**Real yield vs. nominal price convention.** `DFII10` is a real (inflation-adjusted)
yield, while GLD's price and return series used throughout are nominal. At the ~20-day
horizon the signal operates on, this is not a meaningful source of bias: expected
inflation over such a short window is small relative to gold's own short-horizon
volatility, so it does not distort the relationship being tested. It does matter for the
headline cumulative and annualized return figures in §7, since realized inflation
compounds meaningfully over the multi-year windows and is embedded in every nominal GLD
return — strategy and benchmark alike. Because both the strategy and every benchmark it's
compared against hold the same nominal asset, this inflation drift enters both sides
symmetrically: it inflates the level of headline returns reported, but does not bias the
relative comparisons (Sharpe differentials, random-benchmark percentiles) the conclusions
rest on.

---

## 6. Results

### 6.1 In-sample parameter grid (2005–2016)

| Lookback | Sharpe | Ann. return | Ann. vol | Max DD | Hit rate | Turnover | Trades | Avg hold (d) | Cost drag |
|---|---|---|---|---|---|---|---|---|---|
| 10 | 0.465 | 5.7% | 13.9% | −26.1% | 0.515 | 6.0 | 72 | 49.2 | 0.173 |
| **20 (selected)** | **0.601** | **7.4%** | 13.3% | −16.9% | 0.519 | 6.2 | 74 | 43.6 | 0.207 |
| 40 | 0.219 | 2.1% | 13.5% | −44.7% | 0.515 | 5.0 | 60 | 54.6 | 0.098 |
| 60 | 0.522 | 6.5% | 13.9% | −21.8% | 0.524 | 3.3 | 40 | 88.3 | 0.132 |

Selected by highest IS Sharpe: **N = 20**. The win over N = 60 is real but not dominant
(0.601 vs. 0.522) — a narrow win among economically plausible neighbors is more consistent
with genuine, moderately robust signal than a single spiking outlier would be.

IS random-benchmark check: N=20 beat 473 of 500 exposure-matched random draws (**94.6th
percentile**).

### 6.2 Out-of-sample confirmation (January 2017 – December 2025), N = 20 frozen

| Metric | Value |
|---|---|
| Sharpe | 0.636 |
| Ann. return | 6.6% |
| Ann. vol | 11.0% |
| Max drawdown | −19.0% |
| Hit rate | 0.543 |
| Trades | 49 |
| Avg hold (d) | 50.4 |
| Random-benchmark percentile | **36.2nd** (beat 181/500; random mean 0.711) |

A Sharpe of 0.636 looks respectable in isolation, but falls *below* the exposure-matched
random benchmark's own mean — the pooled OOS result does not show genuine timing skill
once exposure-driven dilution is controlled for.

### 6.3 Regime split, N = 20 frozen

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

### 6.4 Block bootstrap significance (block = 21 days, 1,000 replicates, seed 42)

| Period | Actual Sharpe | Bootstrap mean | 95% CI | P(Sharpe ≤ 0) |
|---|---|---|---|---|
| IS (2005–2016) | 0.601 | 0.615 | [0.067, 1.172] | 0.012 |
| OOS (2017–2025) | 0.636 | 0.638 | [0.075, 1.246] | 0.012 |
| Regime 1 (2008–2021) | 0.589 | 0.550 | [0.070, 1.082] | 0.013 |
| Regime 2 (2022–2024) | −0.043 | 0.013 | [−0.886, 0.878] | 0.482 |

---

## 7. Discussion

IS, OOS, and Regime 1 are all bootstrap-distinguishable from zero — but OOS's positive
result should not be read as validation of timing skill. OOS's Sharpe is reliably positive
largely because GLD trended upward over 2017–2025 and the strategy was long roughly half
the time — a beta effect a randomly-timed strategy with the same exposure captures just as
well, and in fact did slightly better (§7.2). The bootstrap test and the random-timing
benchmark answer different questions and can disagree; only Regime 1 shows both a reliably
positive Sharpe *and* genuine outperformance of random timing — the strongest evidence of
real, mechanism-driven edge in this project.

Regime 2's failure is not merely "worse" — it is a different kind of result, and one the
mechanism (§1) predicts. Its Sharpe is negative but not statistically distinguishable from
zero given the regime's short window (36 months, 20 trades), and it underperformed random
timing (8.8th percentile). Both facts are consistent with the discount-rate channel being
overwhelmed by a separate, non-modeled driver once that driver became dominant — see §9 for
independent evidence this is exactly what happened to gold's real-yield relationship after
2022.

---

## 8. Related research

**Barsky, R.B. and Summers, L.H. (1988).** "Gibson's Paradox and the Gold Standard."
*Journal of Political Economy*, Vol. 96, No. 3, pp. 528–550.
https://www.journals.uchicago.edu/doi/abs/10.1086/261550 (NBER working paper version:
https://www.nber.org/papers/w1680). Explains the historical correlation between interest
rates and the price level under the gold standard through an opportunity-cost mechanism —
a rise in the real rate of return reduces gold's equilibrium relative price, operating
through the allocation of gold between monetary and non-monetary uses. This project's
discount-rate framing draws on this mechanism.

**European Central Bank (2025).** "Gold demand: the role of the official sector and
geopolitics." *In-Focus*, ECB Economic Bulletin.
https://www.ecb.europa.eu/press/other-publications/ire/focus/html/ecb.irebox202506_01~f93400a4aa.en.html.
Documents that gold prices were negatively correlated with real yields from 2008 to early
2022, and that this correlation broke down following Russia's 2022 invasion of Ukraine;
cites research linking the imposition of financial sanctions to central banks increasing
the gold share of their reserves.

**RBC Wealth Management (2025).** "Gold's regime change?"
https://www.rbcwealthmanagement.com/en-asia/insights/golds-regime-change. Reports that the
rolling correlation between gold prices and 10-year TIPS yields ran around 84% from
1997–2004, but fell to approximately 3% in 2022–2023 — a direct empirical measure of the
regime break this project's Regime 1 / Regime 2 split is built around.

**World Gold Council.** *Gold Demand Trends*, Central Banks section.
https://www.gold.org/goldhub/research/central-banks. Reports that central banks purchased
over 1,000 tonnes of gold annually in 2022, 2023, and 2024 — around a quarter of total gold
demand in 2022–2023 — well above the 2010–2021 average of roughly 473 tonnes/year,
providing direct evidence for the competing demand channel named in §1 and §8.

---

## 9. Status and next steps

**Completed:** data collection, audit, cleaning/merge, signal, costs, backtest engine, IS
parameter selection, OOS confirmation, regime split, block bootstrap significance.

**Pending:** final verdict and memo (`memo.md`), source note (`source_note.md`), a
self-contained HTML report, cost-sensitivity testing across a range of bps assumptions.

**Open questions for extension, not yet tested:**
- Whether rebalancing more frequently than monthly (e.g., weekly) captures meaningful
  additional signal value, or mainly adds transaction cost (§2).
- A continuous-weighting version of the signal, and generalization to other assets — the
  engine and evaluation modules were built asset- and signal-agnostic specifically to
  support this without rewriting the core pipeline.

**Environment:** Python virtual environment at `.venv`; no credentials required — DFII10 is
obtained as a manually downloaded FRED CSV (`data/raw/DFII10.csv`) and GLD via yfinance. See
`CLAUDE.md` for coding-agent working conventions used on this project.
