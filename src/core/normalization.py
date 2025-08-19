"""Utilities for normalising heterogeneous source files.

This module provides a set of helper functions that make it easier to
work with trial balance and foreign exchange data coming from a variety
of accounting systems.  The helpers focus on bringing data into a
canonical shape so downstream steps can rely on consistent schemas.

The implementation follows the guidelines outlined in the user
instruction: column aliasing with optional fuzzy matching, basic type
coercion, period/entity inference from filenames and a small schema
registry used by the pipeline.
"""

from __future__ import annotations

from pathlib import Path
import re
from typing import Dict, List

import numpy as np

try:  # Optional dependencies -------------------------------------------------
    import pandas as pd
except Exception as exc:  # pragma: no cover - handled in tests
    raise ImportError("pandas is required for the normalisation utilities") from exc

try:  # Fuzzy matching is optional; fall back to alias-only mode if missing
    from rapidfuzz import fuzz, process

    USE_FUZZ = True
except Exception:  # pragma: no cover - rapidfuzz is optional
    USE_FUZZ = False

# ---------------------------------------------------------------------------
# 1) Schema registry
# ---------------------------------------------------------------------------
SCHEMAS: Dict[str, List[str]] = {
    "TB": [
        "EntityCode",
        "AccountCode",
        "AccountName",
        "Debit",
        "Credit",
        "Period",
        "CurrencyCode",
    ],
    "FX_RATES": ["CurrencyCode", "FXRate", "Period", "Source"],
    "FX_ADJ": [
        "EntityCode",
        "AccountCode",
        "LocalAmount",
        "FXRate",
        "ReportingCurrencyAmount",
        "Variance",
        "Period",
    ],
}

# ---------------------------------------------------------------------------
# 2) Column aliases
# ---------------------------------------------------------------------------
COLUMN_ALIASES: Dict[str, List[str]] = {
    "EntityCode": [
        "Entity",
        "Company",
        "CompanyCode",
        "CoCode",
        "LegalEntity",
        "LE",
    ],
    "AccountCode": [
        "GL",
        "GLCode",
        "Account",
        "Acct",
        "GL Account",
        "Account Number",
    ],
    "AccountName": ["AccountDesc", "Account Description", "GL Name"],
    "Debit": ["Dr", "Debits", "Debit Amount"],
    "Credit": ["Cr", "Credits", "Credit Amount"],
    "Period": ["FiscalPeriod", "PeriodId", "YYYYMM", "PostingPeriod"],
    "CurrencyCode": ["Currency", "Curr", "ISO Currency", "LCY"],
    "FXRate": ["Rate", "FX", "ExchangeRate"],
    "ReportingCurrencyAmount": [
        "RptAmt",
        "Reporting Amount",
        "TranslatedAmount",
        "USD Amount",
        "Group Currency Amount",
    ],
    "LocalAmount": [
        "LC Amount",
        "Local Amt",
        "Functional Amount",
        "Amt LCY",
        "Amount",
    ],
}

# ---------------------------------------------------------------------------
# 3) Column resolver
# ---------------------------------------------------------------------------

def resolve_columns(df: pd.DataFrame, target: List[str], aliases: Dict[str, List[str]]) -> pd.DataFrame:
    """Rename columns in *df* to match the *target* schema.

    The function first attempts exact matches, then alias lookups and
    finally (optionally) fuzzy matching.  Only columns that can be
    matched are renamed, remaining columns are left untouched.
    """

    # Case-insensitive lookup of existing columns
    cols = {c.lower(): c for c in df.columns}
    new_cols: Dict[str, str] = {}

    for want in target:
        found = None
        lower = want.lower()
        if lower in cols:
            found = cols[lower]
        else:
            for alt in aliases.get(want, []):
                if alt.lower() in cols:
                    found = cols[alt.lower()]
                    break
        if not found and USE_FUZZ:  # Optional fuzzy matching
            choices = list(df.columns)
            best = process.extractOne(want, choices, scorer=fuzz.token_set_ratio)
            if best and best[1] >= 90:  # confidence threshold
                found = best[0]
        if found:
            new_cols[found] = want

    return df.rename(columns=new_cols)


# ---------------------------------------------------------------------------
# 4) Type coercion & safe defaults
# ---------------------------------------------------------------------------

def coerce_tb_types(df: pd.DataFrame) -> pd.DataFrame:
    """Coerce common TB columns to sane types and fill defaults."""

    for col in ["Debit", "Credit"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

    if "Period" in df.columns:
        df["Period"] = (
            df["Period"].astype(str).str.replace(r"[^0-9]", "", regex=True).str.slice(0, 6)
        )

    if "CurrencyCode" in df.columns:
        df["CurrencyCode"] = df["CurrencyCode"].astype(str).str.upper()

    # Ensure required columns exist
    for req in SCHEMAS["TB"]:
        if req not in df.columns:
            df[req] = np.nan if req not in ["Debit", "Credit"] else 0.0

    return df


# ---------------------------------------------------------------------------
# 5) Filename inference helpers
# ---------------------------------------------------------------------------

def infer_period_from_filename(path: str) -> str | None:
    """Extract a YYYYMM period from *path* if present."""

    m = re.search(r"(20\d{2})(0[1-9]|1[0-2])", Path(path).name)
    return f"{m.group(1)}{m.group(2)}" if m else None


def infer_entity_from_filename(path: str) -> str | None:
    """Attempt to infer an entity code from a TB filename."""

    m = re.search(r"TB_([^_\.]+)", Path(path).name, flags=re.IGNORECASE)
    return m.group(1) if m else None


# ---------------------------------------------------------------------------
# 6) FX rate loader with normalisation
# ---------------------------------------------------------------------------

def load_fx_rates(path_or_api: str) -> Dict[str, float]:
    """Load FX rates from a local file or a simple HTTP JSON API."""

    if path_or_api.startswith("http"):
        import json
        from urllib.request import urlopen

        with urlopen(path_or_api) as fh:  # pragma: no cover - network use
            data = json.load(fh)["rates"]
            return {k.upper(): float(v) for k, v in data.items()}

    df = pd.read_excel(path_or_api)
    df = resolve_columns(df, SCHEMAS["FX_RATES"], COLUMN_ALIASES)
    df["FXRate"] = pd.to_numeric(df["FXRate"], errors="coerce")
    df["CurrencyCode"] = df["CurrencyCode"].astype(str).str.upper()
    return dict(zip(df["CurrencyCode"], df["FXRate"]))


__all__ = [
    "SCHEMAS",
    "COLUMN_ALIASES",
    "resolve_columns",
    "coerce_tb_types",
    "infer_period_from_filename",
    "infer_entity_from_filename",
    "load_fx_rates",
]
