"""Helper functions for logging progress and producing timestamps."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd


def append_step_log(folder: str, log_row: dict) -> None:
    """Append a row to an automation log stored in ``folder``.

    The log is stored as ``Automation_Log.xlsx``.  If the log does not yet
    exist it will be created.  ``log_row`` is expected to be a mapping of column
    names to values which will become a single row in the resulting file.
    """

    Path(folder).mkdir(parents=True, exist_ok=True)
    log_path = Path(folder) / "Automation_Log.xlsx"
    try:
        df = pd.read_excel(log_path)
        df = pd.concat([df, pd.DataFrame([log_row])], ignore_index=True)
    except FileNotFoundError:
        df = pd.DataFrame([log_row])
    df.to_excel(log_path, index=False)


def now_ts() -> str:
    """Return the current UTC timestamp in ISO format."""

    return datetime.utcnow().isoformat()

