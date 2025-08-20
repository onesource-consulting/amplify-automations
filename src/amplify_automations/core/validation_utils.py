"""Validation helper functions for tabular finance data.

Works with either:
- pandas.DataFrame (main project), or
- Iterable[Dict[str, object]] (kata/tests without pandas).
"""

from __future__ import annotations

from typing import Iterable, Dict, List, Any

try:
    import pandas as pd  # type: ignore
    HAS_PANDAS = True
except Exception:  # pragma: no cover
    pd = None  # type: ignore
    HAS_PANDAS = False


def _columns_of(obj) -> List[str]:
    """Return column names for DataFrame or rows-of-dicts."""
    if HAS_PANDAS and isinstance(obj, pd.DataFrame):
        return list(obj.columns)
    rows = list(obj)
    return list(rows[0].keys()) if rows else []


def require_columns(obj, cols: List[str]) -> List[str]:
    """Return list of names from `cols` that are missing in `obj`."""
    existing = set(_columns_of(obj))
    return [c for c in cols if c not in existing]


def _sum_numeric(series_or_iter, key: str | None = None) -> float:
    """Sum a numeric column robustly from DF or iterable-of-dicts."""
    total = 0.0
    if HAS_PANDAS and isinstance(series_or_iter, pd.DataFrame):
        s = pd.to_numeric(series_or_iter[key], errors="coerce")  # type: ignore[index]
        return float(s.fillna(0).sum())
    # iterable of dicts
    for row in series_or_iter:
        val = row.get(key, 0) if key is not None else row
        try:
            total += float(val or 0)
        except (TypeError, ValueError):  # defensive
            return float("nan")
    return total


def debits_equal_credits(obj) -> bool:
    """Check that total Debits and Credits balance (to 2 decimals).

    Returns False if required columns are missing or values are not numeric.
    """
    missing = require_columns(obj, ["Debit", "Credit"])
    if missing:
        return False

    # Compute totals with coercion; guard against NaN by treating as 0
    debit_total = _sum_numeric(obj, "Debit")
    credit_total = _sum_numeric(obj, "Credit")

    if debit_total != debit_total or credit_total != credit_total:  # NaN check
        return False

    return round(debit_total - credit_total, 2) == 0.0