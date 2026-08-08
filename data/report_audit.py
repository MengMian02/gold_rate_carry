"""Format audit results for human review -- display only, no logic.

Thin companion to audit.py: it takes the dicts returned by ``audit_gld()`` and
``audit_dfii10()`` *together with the source frames that were audited*, and
renders them into human-readable files under ``outputs/``. For every flagged
date it reports the full underlying row (OHLCV for GLD, the value for DFII10),
so each flag can be checked and verified directly against the raw data.

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

# Columns produced by the audit's anomalies DataFrame (kept local to stay
# independent of audit.py). Everything merged in beyond these is source data.
_ANOMALY_COLUMNS = ["date", "issue_type", "value", "detail"]

_GLD_CSV = "audit_flags_gld.csv"
_DFII10_CSV = "audit_flags_dfii10.csv"
_REPORT_MD = "audit_flags.md"

_COL_LABELS = {
    "date": "Date",
    "issue_type": "Issue Type",
    "value": "Value",
    "detail": "Detail",
}


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


def _enrich(anomalies: pd.DataFrame | None, source_df: pd.DataFrame | None) -> pd.DataFrame:
    """Attach the full source row for each flagged date onto the anomalies.

    Left-joins ``source_df`` (indexed by date) onto the anomalies by date, so
    every flagged day carries all of its underlying data. Returns a copy; the
    inputs are not modified.
    """
    if anomalies is None:
        anomalies = pd.DataFrame(columns=_ANOMALY_COLUMNS)
    if source_df is None or len(anomalies) == 0:
        return anomalies.copy()

    src = source_df.copy()
    src.index = pd.to_datetime(src.index)
    # Drop any source column that would collide with an anomaly column.
    src = src[[c for c in src.columns if c not in _ANOMALY_COLUMNS]]
    return anomalies.merge(src, left_on="date", right_index=True, how="left")


def _col_label(col: str) -> str:
    return _COL_LABELS.get(col, col)


def _fmt_cell(col: str, value) -> str:
    if col == "date":
        return _fmt_date(value)
    if col in ("issue_type", "detail"):
        if value is None or (isinstance(value, float) and pd.isna(value)):
            return ""
        return str(value)
    return _fmt_value(value)


def _md_table(df: pd.DataFrame, columns: list[str]) -> list[str]:
    header = "| " + " | ".join(_col_label(c) for c in columns) + " | Classification |"
    sep = "| " + " | ".join("---" for _ in columns) + " | --- |"
    lines = [header, sep]
    for _, r in df.iterrows():
        cells = [_fmt_cell(c, r.get(c)) for c in columns]
        # Classification column intentionally left blank for human review.
        lines.append("| " + " | ".join(cells) + " |  |")
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
        "`audit_dfii10()`, enriched with the full underlying row for each flagged date.\n"
        "It makes **no** judgment about whether a flag is a real market event or a data\n"
        "error; that determination is human-authored in `data/decisions.md`. The blank\n"
        "**Classification** column in each table marks where that review should reference\n"
        "the date."
    )


def _series_section(name: str, result: dict, enriched: pd.DataFrame, csv_name: str) -> str:
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

    n = len(enriched)
    lines.append(f"**Flagged rows: {n}** (full detail in `{csv_name}`)")
    lines.append("")

    if n == 0:
        lines.append("_No anomalies flagged._")
        return "\n".join(lines)

    if n > _MAX_TABLE_ROWS:
        shown = _top_by_magnitude(enriched, _TRUNCATED_ROWS)
        lines.append(
            f"> Showing the {len(shown)} most extreme of {n} flagged rows "
            f"(ranked by magnitude of deviation). See `{csv_name}` for all {n}."
        )
        lines.append("")
    else:
        shown = enriched.sort_values("date") if "date" in enriched else enriched

    # date, issue_type, then all underlying source columns, then flag specifics.
    source_cols = [c for c in enriched.columns if c not in _ANOMALY_COLUMNS]
    display_cols = ["date", "issue_type"] + source_cols + ["value", "detail"]
    lines.extend(_md_table(shown, display_cols))
    return "\n".join(lines)


# --------------------------------------------------------------------------
# public entry point
# --------------------------------------------------------------------------
def write_audit_report(
    gld_result: dict,
    dfii10_result: dict,
    gld_df: pd.DataFrame,
    dfii10_df: pd.DataFrame,
    output_dir: str = "outputs/",
) -> None:
    """Render audit results to ``outputs/audit_flags.md`` (+ per-series CSVs).

    ``gld_df`` and ``dfii10_df`` are the same frames that were passed to
    ``audit_gld()`` / ``audit_dfii10()``; each flagged date is joined back to its
    full row so the report shows all underlying data for that day. All three
    files are overwritten on every run. Never touches ``data/decisions.md``.
    """
    out = _resolve_dir(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    gld_enriched = _enrich(gld_result.get("anomalies"), gld_df)
    dfii_enriched = _enrich(dfii10_result.get("anomalies"), dfii10_df)

    # Full detail (all flagged rows, all columns) always goes to CSV.
    gld_enriched.to_csv(out / _GLD_CSV, index=False)
    dfii_enriched.to_csv(out / _DFII10_CSV, index=False)

    parts = [
        _header(),
        _series_section("GLD", gld_result, gld_enriched, _GLD_CSV),
        _series_section("DFII10", dfii10_result, dfii_enriched, _DFII10_CSV),
    ]
    (out / _REPORT_MD).write_text("\n\n".join(parts) + "\n", encoding="utf-8")
