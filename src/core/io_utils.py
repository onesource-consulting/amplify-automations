"""Utility helpers for common I/O operations.

This module provides small, dependency-light helpers used across the project.
When :mod:`pandas` is available, we write/read real Excel files. In constrained
environments (e.g., kata/tests without pandas), we gracefully fall back to CSV
while keeping the same function signatures.

Functions
~~~~~~~~~
expand(path_tmpl, **kw)
    Simple str.format path expansion.

file_hash(path)
    SHA256 hash (streamed).

write_excel(obj, path, headers=None)
    Write a DataFrame *or* iterable of dicts to an Excel file (if pandas is
    available) or CSV fallback if not.

read_excel(path)
    Read an Excel/CSV file. Returns a pandas DataFrame if pandas is available,
    otherwise returns a list[dict].
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, Sequence, Union
import hashlib
import csv

try:
    import pandas as pd  # type: ignore
    HAS_PANDAS = True
except Exception:  # pragma: no cover
    pd = None  # type: ignore
    HAS_PANDAS = False


def expand(path_tmpl: str, **kw: Any) -> str:
    """Expand a string template representing a path."""
    return path_tmpl.format(**kw)


def file_hash(path: str) -> str:
    """Return the SHA256 hash of a file (streamed)."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def write_excel(
    obj: Union["pd.DataFrame", Iterable[Dict[str, Any]]],
    path: str,
    headers: Sequence[str] | None = None,
) -> None:
    """Write tabular data to ``path``.

    Behavior:
    - If pandas is available:
        * If ``obj`` is a DataFrame → write true Excel (index=False).
        * If ``obj`` is rows of dicts → convert to DataFrame, then write Excel.
    - If pandas is NOT available:
        * Write CSV with the same path (used by kata/tests). The caller treats
          it as a simple table file; downstream tests read it via ``read_excel``.

    Parameters
    ----------
    obj
        pandas DataFrame or iterable of dict rows.
    path
        Destination file path. Parent directories are created automatically.
    headers
        Optional explicit column order when writing rows of dicts (CSV fallback).
    """
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)

    if HAS_PANDAS:
        if isinstance(obj, pd.DataFrame):
            obj.to_excel(path, index=False)
        else:
            rows = list(obj)
            if not rows:
                df = pd.DataFrame()
            else:
                cols = list(headers) if headers else list(rows[0].keys())
                df = pd.DataFrame(rows, columns=cols)
            df.to_excel(path, index=False)
        return

    # Fallback: CSV writer (no pandas)
    rows: list[Dict[str, Any]]
    if isinstance(obj, list):
        rows = obj  # assume list[dict]
    else:
        rows = list(obj)
    cols = list(headers) if headers else (list(rows[0].keys()) if rows else [])
    with p.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow(r)


def read_excel(path: str):
    """Read a table file from ``path``.

    Returns
    -------
    pandas.DataFrame if pandas is available, else list[dict].

    Notes
    -----
    - If pandas is available, we try Excel via ``pd.read_excel``; if that fails
      (or extension is .csv) we fall back to ``pd.read_csv``.
    - Without pandas, we parse CSV to list[dict]. If the file is an Excel file
      written by pandas, tests should run in an environment with pandas.
    """
    if HAS_PANDAS:
        try:
            # Try Excel first (common case in the main project)
            return pd.read_excel(path)
        except Exception:
            # Fall back to CSV if not a real Excel file (e.g., kata fallback)
            return pd.read_csv(path)
    # No pandas: CSV-only fallback to list[dict]
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        return [dict(row) for row in reader]