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
