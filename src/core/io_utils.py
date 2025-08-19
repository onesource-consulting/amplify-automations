"""Utility helpers for reading and writing simple spreadsheet like files.

The real project uses Excel and pandas, but those heavy dependencies are
unavailable in the execution environment for the kata.  These helpers implement
just enough functionality for the unit tests by storing tabular data as CSV
files.  The helpers intentionally keep the API surface small so that plugins can
rely on them in the same way the real project would rely on more capable
libraries.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Dict, Any, Sequence
import csv
import hashlib


def expand(template: str, **values: Any) -> str:
    """Expand placeholders in ``template`` using ``str.format`` semantics."""
    return template.format(**values)


def read_excel(path: str) -> list[Dict[str, Any]]:
    """Read a pseudo Excel file returning a list of string valued rows."""
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        return [dict(row) for row in reader]


def write_excel(rows: Iterable[Dict[str, Any]], path: str, headers: Sequence[str] | None = None) -> None:
    """Write rows to a pseudo Excel file.

    ``rows`` is an iterable of dictionaries.  ``headers`` can be provided to
    explicitly control column order; when omitted it is derived from the first
    row.  The destination directory is created automatically.
    """
    path_obj = Path(path)
    path_obj.parent.mkdir(parents=True, exist_ok=True)
    rows = list(rows)
    if headers is None:
        headers = list(rows[0].keys()) if rows else []
    with path_obj.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(headers))
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def file_hash(path: str) -> str:
    """Return a SHA256 hash of the file at ``path``."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        h.update(f.read())
    return h.hexdigest()
