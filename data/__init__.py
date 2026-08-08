"""Data subpackage: retrieval, auditing, and cleaning of raw inputs.

Each responsibility lives in its own module and must not bleed into another:
    loaders.py       -> raw pulls only (no cleaning, no validation)
    audit.py         -> read-only anomaly diagnostics (no fixes, no judgment)
    report_audit.py  -> formats audit results for human review (display only)
    clean.py         -> applies ONLY fixes documented in decisions.md
    decisions.md     -> the human paper trail justifying every data change
"""
