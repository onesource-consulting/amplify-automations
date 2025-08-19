"""Validation helpers used by the simplified plugins."""

from __future__ import annotations

from typing import Iterable, Dict, Sequence


def require_columns(rows: Iterable[Dict[str, object]], required: Sequence[str]) -> list[str]:
    """Return a list of required columns that are missing from ``rows``."""
    rows = list(rows)
    if not rows:
        return list(required)
    cols = set(rows[0].keys())
    return [c for c in required if c not in cols]


def debits_equal_credits(rows: Iterable[Dict[str, object]]) -> bool:
    """Verify that total debits equal total credits."""
    debit = 0.0
    credit = 0.0
    for row in rows:
        try:
            debit += float(row.get("Debit", 0) or 0)
            credit += float(row.get("Credit", 0) or 0)
        except (TypeError, ValueError):  # pragma: no cover - defensive
            return False
    return abs(debit - credit) < 1e-6
