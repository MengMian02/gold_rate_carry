# Data Decisions Log

This is the paper trail justifying **every** data change. It is not a Python
file. For each anomaly `audit.py` flags, add an entry below with:

1. **What was flagged** — the date(s) and the anomaly type reported by `audit.py`.
2. **Human determination of cause** — the reasoning, with supporting evidence
   (e.g. corporate action, holiday, source revision, genuine market move).
3. **Action that follows** — the exact transformation `clean.py` will apply, or
   "no action" with justification.

`clean.py` may only implement fixes that appear here. If it is not written down
in this file, it does not happen in the data.

---

## Template

### YYYY-MM-DD — <anomaly type>

- **Flagged:** <what audit.py reported>
- **Cause:** <human determination + supporting reasoning>
- **Action:** <fix applied in clean.py, or "no action" + why>

---

<!-- Entries below, most recent first -->

### 2026-08-08 — Data validation review (GLD + DFII10)

Determinations provided by the repo owner on 2026-08-08, recorded here as the
paper trail. Reviewed against the audit run over **GLD 2004-11-18 → 2026-08-06**
(yfinance, `gld_raw.csv`) and **DFII10 2003-01-02 → 2026-08-06** (manual FRED CSV,
`DFII10.csv`). Full flag lists: `result/audit_flags.md` and the per-series
`audit_flags_gld.csv` / `audit_flags_dfii10.csv` snapshots.

**DFII10 — `stale_value` (131 flags)**
- **Flagged:** runs of 3+ consecutive identical `dfii10_value`.
- **Cause:** normal. The 10-year real yield is quoted to 2 decimals, so genuinely
  unchanged values repeat across low-volatility stretches; these are real
  unchanged observations, not frozen/duplicated data.
- **Action:** none. Values left as-is.

**DFII10 — `mad_outlier_change` (24 flags)**
- **Flagged:** daily changes beyond 4·MAD of the trailing 60-day window.
- **Cause:** reviewed, no problem — genuine large real-yield moves, not data
  errors. (Top flags fall on known events, e.g. the Feb-2021 rate spike,
  Mar-2020, Mar-2009.)
- **Action:** none.

**GLD — `mad_outlier_pct_change` (57 flags)**
- **Flagged:** daily % change in `adj_close` beyond 4·MAD of the trailing 60-day
  window.
- **Cause:** reviewed, no problem — genuine large gold-price moves, not data
  errors.
- **Action:** none.

**Other (noted, nothing to decide):** GLD hard-error checks all passed;
`stale_adj_close`, `zero_volume`, and `close_adj_divergence` were all 0. DFII10
has 253 NaN on non-trading days (holidays), which is expected and only counted
here — any holiday handling / T+1 publication alignment is a later `clean.py`
concern, not a data change.
