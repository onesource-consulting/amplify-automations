"""Tests for core utility helper modules.

The utilities rely primarily on :mod:`pandas` for Excel interaction.  The
testing environment used for these exercises does not ship with the optional
``openpyxl`` dependency required for ``DataFrame.to_excel`` / ``read_excel``.
To keep the tests lightweight and independent of external packages we mock the
relevant pandas functions.
"""

from __future__ import annotations

import hashlib
from datetime import datetime
from pathlib import Path

import pytest

pd = pytest.importorskip("pandas")

from src.core.io_utils import expand, file_hash, write_excel
from src.core.logging_utils import append_step_log, now_ts
from src.core.validation_utils import debits_equal_credits, require_columns


def test_expand_basic():
    assert expand("{root}/data/{name}.txt", root="base", name="file") == (
        "base/data/file.txt"
    )


def test_file_hash(tmp_path):
    file = tmp_path / "sample.txt"
    content = b"hello world"
    file.write_bytes(content)

    expected = hashlib.sha256(content).hexdigest()
    assert file_hash(str(file)) == expected


def test_write_excel_creates_parent_and_writes(tmp_path, monkeypatch):
    df = pd.DataFrame({"A": [1], "B": [2]})
    written = {}

    def fake_to_excel(self, path, index=False):
        written["path"] = path
        written["index"] = index
        Path(path).write_text("dummy")

    monkeypatch.setattr(pd.DataFrame, "to_excel", fake_to_excel, raising=False)

    out = tmp_path / "sub" / "file.xlsx"
    write_excel(df, str(out))

    assert written["path"] == str(out)
    assert written["index"] is False
    assert out.exists()


def test_append_step_log_creates_file(tmp_path, monkeypatch):
    log_row = {"Step": "done"}

    def fake_read_excel(path):
        raise FileNotFoundError

    monkeypatch.setattr(pd, "read_excel", fake_read_excel)

    saved = {}

    def fake_to_excel(self, path, index=False):
        saved["df"] = self.copy()
        saved["path"] = path

    monkeypatch.setattr(pd.DataFrame, "to_excel", fake_to_excel, raising=False)

    folder = tmp_path / "logs"
    append_step_log(str(folder), log_row)

    assert saved["path"] == str(folder / "Automation_Log.xlsx")
    assert saved["df"].to_dict(orient="records")[0] == log_row


def test_now_ts_parses():
    ts = now_ts()
    # Should not raise
    datetime.fromisoformat(ts)


def test_require_columns():
    df = pd.DataFrame({"A": [1], "B": [2]})
    assert require_columns(df, ["A", "C"]) == ["C"]


def test_debits_equal_credits():
    df = pd.DataFrame({"Debit": [100, 50], "Credit": [75, 75]})
    assert debits_equal_credits(df)

    df2 = pd.DataFrame({"Debit": [100], "Credit": [50]})
    assert not debits_equal_credits(df2)

