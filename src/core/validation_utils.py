"""Validation helper functions for working with :class:`pandas.DataFrame`."""

from __future__ import annotations

import pandas as pd


def require_columns(df: pd.DataFrame, cols: list) -> list:
    """Return a list of column names from ``cols`` that are missing in ``df``."""

    missing = [c for c in cols if c not in df.columns]
    return missing


def debits_equal_credits(df: pd.DataFrame) -> bool:
    """Check that total debits and credits balance to zero.

    Values are rounded to two decimal places to mitigate floating point
    precision issues which often appear in financial data.
    """

    return round(df["Debit"].sum() - df["Credit"].sum(), 2) == 0.0

