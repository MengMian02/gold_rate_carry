# gold_rate_carry

A backtest of a real-yield-driven timing strategy on GLD (SPDR Gold Shares).

---

## Abstract

Gold pays no yield, so the opportunity cost of holding it is proxied by the real
(inflation-adjusted) interest rate. This project tests a simple rule: long GLD when the
20-trading-day change in the 10-Year TIPS real yield (FRED: `DFII10`) is negative, flat
otherwise, monthly rebalance. It asks whether that relationship is tradeable net of costs,
whether it holds out-of-sample, and whether it survives across different real-rate regimes.

The strategy shows genuine, statistically distinguishable edge in a near-zero/falling-rate
regime (2008–2021), but breaks down, and underperforms a randomly-timed benchmark with
matched exposure, in the 2022–2024 rate-hiking regime. This lines up with independent
research on gold's real-yield relationship weakening after 2022, as central-bank reserve
buying became the dominant driver of gold demand (§7, §8).

---

## 1. Mechanism

Gold's opportunity cost of carry rises with the real interest rate. When real yields fall,
holding non-yielding gold becomes relatively more attractive; when real yields rise, the
opposite is true. This project isolates that channel specifically by using the *real* yield
(`DFII10`, derived from TIPS) rather than the nominal 10-year yield, which would also embed
inflation-expectation effects that move gold through a separate channel (gold as a partial
inflation hedge) with the opposite sign. Using DFII10 separates the real-rate component from
nominal yields; it does not eliminate inflation expectations or other drivers from gold
returns, but it does keep the signal to a single series rather than requiring a
multi-variable regression to separate the two.

Gold generates no contractual cash flow, so higher real yields increase the opportunity cost
of holding it relative to interest-bearing safe assets. Falling real yields may therefore
support gold demand and prices, all else equal. Barsky and Summers (1988) explain the
historical correlation between interest rates and the price level under the gold standard
through this same opportunity-cost mechanism: a shock that raises the real rate of return
reduces gold's equilibrium relative price, working through how gold is allocated between
monetary and non-monetary uses. This project's discount-rate framing draws directly on that
work (full citation in §8).

This strategy tests one specific, real channel: the discount-rate/opportunity-cost effect. It
does not model, and doesn't claim to capture, other drivers of gold demand, most importantly
central-bank reserve diversification and geopolitical hedging, which independent research
identifies as the dominant force behind gold's resilience despite rising real yields from
2022 onward (§8). The regime split in §6.3 shows this limitation appearing exactly where that
research would predict it.

---

## 2. Design

For a given lookback N, the signal goes long GLD (weight = 1) if `DFII10` has fallen over the
past N trading days, and stays flat (weight = 0) otherwise. It uses the sign of the change
only, with no magnitude threshold, which keeps N the single tunable parameter in the entire
strategy. The parameter grid is N ∈ {10, 20, 40, 60} trading days, roughly two weeks, one
month, two months, and one quarter. These track the natural cadence of the macro data (CPI
prints, FOMC meetings, Treasury auctions) that moves real yields, rather than being arbitrary
numbers.

The lookback window and the rebalance frequency are kept as independent decisions rather than
tied together. Tying rebalance frequency to N would conflate two effects inside the parameter
grid: a Sharpe difference between candidates could reflect either a lookback reading the
real-yield trend more accurately, or a rebalance cadence trading more efficiently, with no way
to tell which. Fixing rebalance at monthly, independent of N, keeps N isolated as the only
thing under test.

That choice has a real cost. The signal is computed daily, but only the reading on each month's first trading day is ever acted on, so
roughly 19 out of every 20 daily signal readings are computed and then never used for a
decision. This isn't a loss of underlying data, since each daily reading already incorporates
a full N-day window of real-yield history, but it is a loss of decision frequency. A signal
flip mid-month that reverses before the next rebalance is invisible to the strategy, not
because the information wasn't there, but because it was never checked on a day that
mattered. Monthly rebalancing happens to roughly match N=20's own timescale, which is a
plausible reason more frequent rebalancing wouldn't help much, but this is untested rather
than demonstrated. §9 lists it as the natural first robustness check for future work
(re-running at a weekly rebalance to see whether the extra decision frequency improves
results or mainly adds transaction cost).

The in-sample window is January 2005 to December 2016, used for parameter selection only, and
the out-of-sample window is January 2017 to December 2025, with rules frozen and no further
tuning. Twelve years of in-sample data spans more than one full real-rate cycle (the 2008
collapse, the 2013 taper tantrum, the subsequent grind lower), which is enough to avoid
selecting a lookback that only fits one directional trend, without shrinking the out-of-sample
window, and its statistical power, further than necessary. The 2022–2024 breakdown is
deliberately left inside the out-of-sample window rather than tuned around, so that test isn't
artificially friendly.

The regime split is a separate axis from the in-sample/out-of-sample split and answers a
different question. Regime 1 covers 2008–2021, when real yields were near zero or falling.
Regime 2 covers 2022–2024, when real yields rose sharply, the period during which gold's
relationship with real yields is documented to have broken down (§8). Both regimes are
defined by the real-yield trend itself, matching the mechanism under test. The
in-sample/out-of-sample split asks whether the parameter was chosen honestly, without peeking
at the future; the regime split asks whether performance holds up across different macro
conditions. The two windows deliberately overlap in calendar time because they're answering
different questions.

The primary benchmark is GLD buy-and-hold, alongside an exposure-matched random-timing
benchmark. Since the strategy isn't invested 100% of the time, a raw Sharpe comparison to
buy-and-hold conflates real timing skill with the effect of simply not always being exposed:
mixing flat, zero-variance periods into a return series can move a Sharpe ratio independent
of any skill, and how much depends entirely on which days happen to be flat. The random
benchmark instead generates 500 random month-level position series with the same total
exposure as the actual strategy, and reports where the actual Sharpe falls within that
distribution, which isolates timing skill specifically.

The only cost applied is a per-trade cost of 8 bps one-way, charged on the specific dates the
position changes. No separate expense-ratio deduction is taken, since the backtest's price
series (`gld_adj_close`) is GLD's own traded price, which already embeds the fund's ongoing
expense-ratio drag (the trust continuously sells gold holdings to pay the fee, so GLD's return
already trails spot gold's). Charging it again would double-count.

---

## 3. Data

| Series | Source | Notes |
|---|---|---|
| GLD (OHLCV) | yfinance | Exchange-traded, standard ticker coverage |
| DFII10 (10Y real yield) | FRED (manual CSV download) | A published Treasury/Fed statistic, not a tradeable instrument, not covered by yfinance; downloaded by hand and read from `data/raw/DFII10.csv` |

`gld_adj_close` is used throughout. GLD pays no dividends and has never split, so adjusted and
unadjusted close are effectively identical in practice; adjusted close is used for consistency
with standard data-vendor convention and to correctly handle any future corporate action, even
though none has occurred to date.

Both raw series are checked into the repository (`data/raw/gld_raw.csv` and
`data/raw/DFII10.csv`), so the core results reproduce without any network access. To refresh
them, GLD re-fetches automatically via yfinance (`loaders.fetch_gld()`) and DFII10 is
re-downloaded manually from FRED (<https://fred.stlouisfed.org/series/DFII10>) and saved to
`data/raw/DFII10.csv`. `loaders.load_dfii10()` raises a clear error with these instructions if
that file is missing.

DFII10 values are generally not available until after that day's bond and equity markets have
already closed. This project applies a conservative one-row shift, relative to the series' own
date-ordered index rather than a blind calendar-day shift so it stays correct around
holidays and gaps, so that a trading decision never uses same-day DFII10 data, only the prior
day's published value. This reflects the general publication timing of Treasury
constant-maturity series rather than a confirmed, sourced timestamp for DFII10 specifically.

DFII10, like most FRED series, can in principle be revised after its initial release. Here
that's immaterial, since TIPS-derived real yields are computed from live market pricing rather
than the survey or estimate methodology behind the large revisions seen in series like GDP or
employment, so they aren't subject to meaningful revision. This project treats the
currently-published values as final and doesn't attempt to reconstruct what an earlier,
unrevised vintage would have shown.

GLD trades on the NYSE calendar, while DFII10 is published on Treasury and bond-market
business days, and the two calendars don't always line up. The merge uses GLD's calendar as
the base. On a GLD trading day where the bond market is closed and no new DFII10 print exists,
the most recent published value is forward-filled, and the row is flagged in a dedicated
column. This isn't data invention: on a day the bond market is closed, nothing occurred to
change the real yield, so there's no unobserved "true" value different from the last print,
only the absence of a new one. That's a different situation from a gap where the true value
genuinely could have been anything and simply wasn't recorded, such as a missing GLD price,
which is left as NA and never filled. GLD itself is never forward-filled in this project.

Both series were independently audited for hard errors (duplicate or non-monotonic dates,
implausible units, OHLC inconsistencies) and anomalies (extreme moves via a
median-absolute-deviation threshold, repeated or stale values, zero-volume days) before
merging. Flags were triaged by category rather than reviewed row by row: repeated-value flags
in DFII10 were resolved as a batch, reflecting the series' native reporting precision and
lower TIPS-market turnover rather than a stale feed, while extreme-move flags were reviewed
individually against known market events. Full disposition is in `data/decisions.md`.

---

## 4. Methodology

The pipeline is split into single-responsibility, composable modules: raw data loading,
read-only audit, alignment and merge, signal generation (which returns a general float weight
rather than a hardcoded boolean), cost modeling, an asset- and signal-agnostic backtest
engine, and evaluation. This keeps the strategy itself simple while the engine, cost model,
and evaluation tools stay reusable for future strategies and assets (§9).

Parameter selection happens on in-sample data only. Each candidate lookback runs the full
pipeline on the full available data range, for correct signal burn-in, and results are then
filtered to the in-sample window before any metric is computed, so no out-of-sample date ever
influences in-sample selection. All four candidates are reported, not just the winner.

The exposure-matched random benchmark, described in §2, generates 500 random position series
matching the strategy's actual exposure in a given window, runs each through the identical
pipeline, and reports the actual strategy's percentile rank within that distribution.

Daily returns within a monthly holding period are autocorrelated, which violates the
independence assumption behind standard significance tests. A moving block bootstrap, with a
block length of 21 trading days matching the rebalance cadence, resamples contiguous chunks of
the return series to preserve that dependency, and reports where zero falls relative to the
resulting Sharpe distribution.

The block bootstrap and the random benchmark test different things, and it's easy to
conflate them. The block bootstrap tests whether the Sharpe ratio is reliably above zero, which can be satisfied purely through
directional market exposure if the underlying asset trended up over the period, with no timing
skill required. The random exposure-matched benchmark tests whether the specific dates chosen
outperform other, randomly-chosen date sets with the same exposure, which isolates timing
skill specifically. These two tests can and do disagree (§6.2).

---

## 5. Costs and real-vs-nominal returns

The only cost applied is a per-trade cost of 8 bps one-way, on the specific dates the position
changes. No separate expense-ratio drag is deducted, since `gld_adj_close`, GLD's own traded
price used throughout, already reflects the fund's ongoing expense ratio (the trust
continuously sells gold to pay it), so deducting it again would double-count. Position timing
follows `position(t-1) × return(t)` throughout, so any cost is charged against the position
actually held.

Flat periods, when the strategy holds no position, are treated as earning 0% return, for
simplicity. This keeps the current strategy and random-benchmark calculations internally
consistent under a common zero-cash-return convention. However, because the actual and random
strategies are flat in different months, introducing time-varying cash returns could still
change their relative Sharpe rankings and percentiles. Absolute returns are conservative
relative to a cash-efficient implementation; the effect on Sharpe and benchmark-relative
rankings is not necessarily one-directional.

DFII10 is a real, inflation-adjusted yield, while GLD's price and return series used
throughout are nominal. At the roughly 20-day horizon the signal operates on, this isn't a
meaningful source of bias, since expected inflation over such a short window is small relative
to gold's own short-horizon volatility and doesn't distort the relationship being tested. It
matters more for the headline cumulative and annualized return figures in §6, since realized
inflation compounds meaningfully over the multi-year windows and is embedded in every nominal
GLD return, strategy and benchmark alike. Because both the strategy and every benchmark it's
compared against hold the same nominal asset, this inflation drift enters both sides
symmetrically. It inflates the level of headline returns reported, but doesn't bias the
relative comparisons, such as Sharpe differentials and random-benchmark percentiles, that the
conclusions actually rest on.

---

## 6. Results

### 6.1 In-sample parameter grid (2005–2016)

| Lookback | Sharpe | Calmar | Ann. return | Ann. vol | Max DD | Hit rate | Avg exp | Turnover | Trades | Avg hold (d) | Cost drag |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 10 | 0.481 | 0.231 | 5.9% | 13.9% | −25.6% | 0.516 | 58.6% | 6.0 | 72 | 49.2 | 0.118 |
| **20 (selected)** | **0.617** | **0.450** | **7.6%** | 13.3% | −16.9% | 0.522 | 53.4% | 6.2 | 74 | 43.6 | 0.147 |
| 40 | 0.235 | 0.052 | 2.3% | 13.5% | −44.1% | 0.517 | 54.2% | 5.0 | 60 | 54.6 | 0.065 |
| 60 | 0.539 | 0.310 | 6.8% | 13.9% | −21.8% | 0.526 | 58.4% | 3.3 | 40 | 88.3 | 0.071 |

N = 20 is selected by highest in-sample Sharpe. Its win over N = 60 is real but not dominant
(0.617 vs. 0.539), and a narrow win among economically plausible neighbors is more consistent
with a genuine, moderately robust signal than a single spiking outlier would be.

On the in-sample random-benchmark check, N=20 beat 473 of 500 exposure-matched random draws,
the 94.6th percentile.

### 6.2 Out-of-sample confirmation (January 2017 – December 2025), N = 20 frozen

| Metric | Value |
|---|---|
| Sharpe | 0.656 |
| Calmar | 0.363 |
| Ann. return | 6.8% |
| Ann. vol | 11.0% |
| Max drawdown | −18.8% |
| Hit rate | 0.545 |
| Average exposure | 55.7% |
| Trades | 49 |
| Avg hold (d) | 50.4 |
| Random-benchmark percentile | 36.2nd (beat 181/500; random mean 0.731) |

A Sharpe of 0.656 looks respectable on its own, but it falls below the exposure-matched random
benchmark's own mean. The pooled out-of-sample result doesn't show genuine timing skill once
exposure-driven dilution is controlled for.

### 6.3 Regime split, N = 20 frozen

| Metric | Regime 1 (2008–2021) | Regime 2 (2022–2024) |
|---|---|---|
| Sharpe | 0.607 | −0.026 |
| Calmar | 0.418 | −0.037 |
| Ann. return | 7.2% | −0.7% |
| Ann. vol | 12.8% | 9.5% |
| Max drawdown | −17.2% | −18.8% |
| Hit rate | 0.531 | 0.514 |
| Average exposure | 58.2% | 41.8% |
| Trades | 80 | 20 |
| Random-benchmark percentile | 98.2nd (beat 491/500) | 8.8th (beat 44/500) |
| Random draws' mean Sharpe | 0.248 | 0.571 |

### 6.4 Block bootstrap significance (block = 21 days, 1,000 replicates, seed 42)

| Period | Actual Sharpe | Bootstrap mean | 95% CI | P(Sharpe ≤ 0) |
|---|---|---|---|---|
| IS (2005–2016) | 0.617 | 0.631 | [0.083, 1.187] | 0.010 |
| OOS (2017–2025) | 0.656 | 0.658 | [0.096, 1.265] | 0.011 |
| Regime 1 (2008–2021) | 0.607 | 0.569 | [0.088, 1.100] | 0.011 |
| Regime 2 (2022–2024) | −0.026 | 0.030 | [−0.867, 0.895] | 0.465 |

---

## 7. Discussion

IS, OOS, and Regime 1 are all bootstrap-distinguishable from zero, but OOS's positive result
shouldn't be read as validation of timing skill. Its Sharpe is reliably positive largely
because GLD trended upward over 2017–2025 and the strategy was long roughly half the time, a
beta effect that a randomly-timed strategy with the same exposure captures just as well, and
in fact did slightly better (§6.2). The bootstrap test and the random-timing benchmark answer
different questions and can disagree. Only Regime 1 shows both a reliably positive Sharpe and
genuine outperformance of random timing, which makes it the strongest evidence of real,
mechanism-driven edge in this project.

Regime 2's failure isn't merely worse, it's a different kind of result, and one the mechanism
in §1 predicts. Its Sharpe is negative but not statistically distinguishable from zero given
the regime's short window (36 months, 20 trades), and it underperformed random timing at the
8.8th percentile. Both facts are consistent with the discount-rate channel being overwhelmed
by a separate, non-modeled driver once that driver became dominant. §8 has independent
evidence that this is exactly what happened to gold's real-yield relationship after 2022.

---

## 8. Related research

**Barsky, R.B. and Summers, L.H. (1988).** "Gibson's Paradox and the Gold Standard."
*Journal of Political Economy*, Vol. 96, No. 3, pp. 528–550.
https://www.journals.uchicago.edu/doi/abs/10.1086/261550 (NBER working paper version:
https://www.nber.org/papers/w1680). Explains the historical correlation between interest
rates and the price level under the gold standard through an opportunity-cost mechanism: a
rise in the real rate of return reduces gold's equilibrium relative price, operating through
the allocation of gold between monetary and non-monetary uses. This project's discount-rate
framing draws on this mechanism.

**European Central Bank (2025).** "Gold demand: the role of the official sector and
geopolitics." *In-Focus*, ECB Economic Bulletin.
https://www.ecb.europa.eu/press/other-publications/ire/focus/html/ecb.irebox202506_01~f93400a4aa.en.html.
Documents that gold prices were negatively correlated with real yields from 2008 to early
2022, and that this correlation broke down following Russia's 2022 invasion of Ukraine; cites
research linking the imposition of financial sanctions to central banks increasing the gold
share of their reserves.

**RBC Wealth Management (2025).** "Gold's regime change?"
https://www.rbcwealthmanagement.com/en-asia/insights/golds-regime-change. Reports that the
rolling correlation between gold prices and 10-year TIPS yields ran around 84% from
1997–2004, but fell to approximately 3% in 2022–2023, a direct empirical measure of the
regime break this project's Regime 1 / Regime 2 split is built around.

**World Gold Council.** *Gold Demand Trends*, Central Banks section.
https://www.gold.org/goldhub/research/central-banks. Reports that central banks purchased
over 1,000 tonnes of gold annually in 2022, 2023, and 2024, around a quarter of total gold
demand in 2022–2023, well above the 2010–2021 average of roughly 473 tonnes/year, providing
direct evidence for the competing demand channel named in §1 and §7.

---

## 9. Status and next steps

Completed: data collection, audit, cleaning and merge, signal, costs, backtest engine, IS
parameter selection, OOS confirmation, regime split, block bootstrap significance,
cost-sensitivity testing, the memo (`memo.md`), the source note (`data/source_note.md`), and
the self-contained HTML report (`result/report.html`).

Two open questions are left for future work, not yet tested. One is whether rebalancing more
frequently than monthly, weekly for instance, captures meaningful additional signal value or
mainly adds transaction cost (§2). The other is a continuous-weighting version of the signal,
and generalization to other assets; the engine and evaluation modules were built asset- and
signal-agnostic specifically to support this without rewriting the core pipeline.

The project runs in a Python virtual environment at `.venv`, no credentials required. Both raw
data files are committed to the repo (`data/raw/gld_raw.csv`, `data/raw/DFII10.csv`), so the
core results reproduce with no network access. To refresh them, GLD re-fetches via yfinance
(`loaders.fetch_gld()`) and DFII10 is downloaded manually from FRED (see §3). See `CLAUDE.md`
for the coding-agent working conventions used on this project.
