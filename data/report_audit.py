"""Format audit results for human review -- display only, no logic.

Thin companion to audit.py: it takes the dicts returned by ``audit_gld()`` and
``audit_dfii10()`` and renders them into human-readable files under ``outputs/``.
It makes NO judgment about whether a flag is a genuine market event or a data
error -- that determination is human-authored in ``data/decisions.md``.

This module never imports from, nor writes to, ``data/decisions.md``. The only
files it writes are ``audit_flags.md``, ``audit_flags_gld.csv`` and
``audit_flags_dfii10.csv``, all fully regenerated (overwritten) on every run.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd

# Relative output paths are anchored to the repo root (parent of data/), so the
# report always lands in the project's outputs/ regardless of the caller's cwd
# -- matching loaders.py's caching convention. Absolute paths are used as given.
_REPO_ROOT = Path(__file__).resolve().parent.parent

_MAX_TABLE_ROWS = 20        # if a series has more flagged rows than this, truncate the table
_TRUNCATED_ROWS = 10        # ...to this many most-extreme rows (full detail stays in the CSV)

# Expected schema of the anomalies DataFrame (kept local to stay independent of audit.py).
_ANOMALY_COLUMNS = ["date", "issue_type", "value", "detail"]

_GLD_CSV = "audit_flags_gld.csv"
_DFII10_CSV = "audit_flags_dfii10.csv"
_REPORT_MD = "audit_flags.md"


# --------------------------------------------------------------------------
# formatting helpers
# --------------------------------------------------------------------------
def _resolve_dir(output_dir: str) -> Path:
    p = Path(output_dir)
    return p if p.is_absolute() else _REPO_ROOT / p


def _fmt_date(value) -> str:
    try:
        return pd.Timestamp(value).strftime("%Y-%m-%d")
    except (ValueError, TypeError):
        return str(value)


def _fmt_value(value) -> str:
    if value is None:
        return ""
    try:
        f = float(value)
    except (TypeError, ValueError):
        return str(value)
    if pd.isna(f):
        return ""
    return f"{f:.6g}"


def _magnitude(row) -> float:
    """A single 'magnitude of deviation' per row, used only to rank the table.

    Uses the audit's own deviation measure when present in ``detail``
    (``mod_z=`` for MAD outliers, ``rel=`` for close/adj_close divergence);
    otherwise falls back to |value|. This is display-ordering only -- it makes
    no real-vs-error judgment.
    """
    detail = str(row.get("detail", "") or "")
    for prefix in ("mod_z=", "rel="):
        if detail.startswith(prefix):
            try:
                return abs(float(detail[len(prefix):]))
            except ValueError:
                return float("nan")
    try:
        return abs(float(row["value"]))
    except (TypeError, ValueError):
        return float("nan")


def _top_by_magnitude(anomalies: pd.DataFrame, k: int) -> pd.DataFrame:
    mag = anomalies.apply(_magnitude, axis=1)
    order = mag.sort_values(ascending=False, na_position="last").index
    return anomalies.loc[order].head(k)


def _md_table(anomalies: pd.DataFrame) -> list[str]:
    lines = [
        "| Date | Issue Type | Value | Detail | Classification |",
        "| --- | --- | --- | --- | --- |",
    ]
    for _, r in anomalies.iterrows():
        date = _fmt_date(r.get("date"))
        issue = str(r.get("issue_type", ""))
        value = _fmt_value(r.get("value"))
        detail = str(r.get("detail", "") or "")
        # Classification column intentionally left blank for human review.
        lines.append(f"| {date} | {issue} | {value} | {detail} | |")
    return lines


def _header() -> str:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return (
        "# Audit Flags — AUTO-GENERATED\n\n"
        f"_Generated: {ts}_\n\n"
        "> **Do not hand-edit this file.** It is fully regenerated (overwritten) every\n"
        "> time `data/report_audit.py::write_audit_report()` runs. Manual review notes,\n"
        "> anomaly classifications, and the decisions that follow belong in\n"
        "> `data/decisions.md` — never here.\n\n"
        "This report only formats and displays the output of `audit_gld()` and\n"
        "`audit_dfii10()`. It makes **no** judgment about whether a flag is a real\n"
        "market event or a data error; that determination is human-authored in\n"
        "`data/decisions.md`. The blank **Classification** column in each table marks\n"
        "where that review should reference the date."
    )


def _series_section(name: str, result: dict, csv_name: str) -> str:
    lines: list[str] = [f"## {name}", ""]

    checks = result.get("hard_errors_checked", []) or []
    lines.append(f"**Hard-error checks passed ({len(checks)}):**")
    if checks:
        lines.extend(f"- `{c}`" for c in checks)
    else:
        lines.append("- _(none recorded)_")
    lines.append("")

    summary = result.get("summary", {}) or {}
    lines.append("**Anomaly summary:**")
    if summary:
        lines.extend(f"- {k}: {v}" for k, v in summary.items())
    else:
        lines.append("- _(no summary)_")
    lines.append("")

    anomalies = result.get("anomalies")
    n = 0 if anomalies is None else len(anomalies)
    lines.append(f"**Flagged rows: {n}** (full detail in `{csv_name}`)")
    lines.append("")

    if n == 0:
        lines.append("_No anomalies flagged._")
        return "\n".join(lines)

    if n > _MAX_TABLE_ROWS:
        shown = _top_by_magnitude(anomalies, _TRUNCATED_ROWS)
        lines.append(
            f"> Showing the {len(shown)} most extreme of {n} flagged rows "
            f"(ranked by magnitude of deviation). See `{csv_name}` for all {n}."
        )
        lines.append("")
    else:
        shown = anomalies.sort_values("date") if "date" in anomalies else anomalies

    lines.extend(_md_table(shown))
    return "\n".join(lines)


# --------------------------------------------------------------------------
# public entry point
# --------------------------------------------------------------------------
def write_audit_report(
    gld_result: dict,
    dfii10_result: dict,
    output_dir: str = "outputs/",
) -> None:
    """Render audit results to ``outputs/audit_flags.md`` (+ per-series CSVs).

    All three files are overwritten on every run. Never touches
    ``data/decisions.md``. See module docstring.
    """
    out = _resolve_dir(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    # Full detail always goes to CSV, regardless of the markdown table cap.
    gld_anom = gld_result.get("anomalies")
    dfii_anom = dfii10_result.get("anomalies")
    if gld_anom is None:
        gld_anom = pd.DataFrame(columns=_ANOMALY_COLUMNS)
    if dfii_anom is None:
        dfii_anom = pd.DataFrame(columns=_ANOMALY_COLUMNS)
    gld_anom.to_csv(out / _GLD_CSV, index=False)
    dfii_anom.to_csv(out / _DFII10_CSV, index=False)

    parts = [
        _header(),
        _series_section("GLD", gld_result, _GLD_CSV),
        _series_section("DFII10", dfii10_result, _DFII10_CSV),
    ]
    (out / _REPORT_MD).write_text("\n\n".join(parts) + "\n", encoding="utf-8")
