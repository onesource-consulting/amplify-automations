"""Utility helpers for common I/O operations.

This module currently provides a small collection of helper functions used
across the project.  They intentionally have **no** third‑party dependencies
other than :mod:`pandas` and standard library modules so that they can be used
from many contexts (tests, plugins, etc.).

Functions
~~~~~~~~~

``expand``
    Perform a simple ``str.format`` expansion on a path template.
``file_hash``
    Compute a SHA256 hash for a file, streaming the contents to avoid loading
    the entire file into memory.
``write_excel``
    Write a :class:`pandas.DataFrame` to an Excel file, creating any parent
    directories as required.
"""

from __future__ import annotations

from pathlib import Path
import hashlib
import pandas as pd


def expand(path_tmpl: str, **kw: str) -> str:
    """Expand a string template representing a path.

    Parameters
    ----------
    path_tmpl:
        The template to expand.  It should use ``str.format`` style
        placeholders.
    **kw:
        Keyword arguments that will be substituted into ``path_tmpl``.

    Returns
    -------
    str
        The expanded path string.
    """

    return path_tmpl.format(**kw)


def file_hash(path: str) -> str:
    """Return the SHA256 hash of a file.

    The file is read in chunks so very large files do not need to be loaded
    entirely into memory.
    """

    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def write_excel(df: pd.DataFrame, path: str) -> None:
    """Write ``df`` to an Excel file located at ``path``.

    Any missing parent directories will be created automatically.  The DataFrame
    is written with ``index=False`` which mirrors the behaviour used throughout
    the project.
    """

    Path(path).parent.mkdir(parents=True, exist_ok=True)
    df.to_excel(path, index=False)

