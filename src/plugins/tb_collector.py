"""Trial Balance collector step with normalisation logic.

This implementation demonstrates how raw client files can be ingested
and converted into the canonical trial balance schema used by the rest
of the pipeline.  The step is intentionally lightweight – it focuses on
normalisation rather than complex business rules.
"""

from __future__ import annotations

from pathlib import Path
from typing import List

import pandas as pd
import numpy as np

from core.contracts import StepIO, ValidationResult
from core.step_base import Step
from core.normalization import (
    COLUMN_ALIASES,
    SCHEMAS,
    coerce_tb_types,
    infer_entity_from_filename,
    infer_period_from_filename,
    resolve_columns,
)


class TBCollector(Step):
    """Normalises a single trial balance Excel file."""

    name = "TBCollector"

    # -- Step interface -------------------------------------------------
    def plan_io(self) -> StepIO:
        inputs = {"tb": self.cfg.get("input")}
        outputs = {"tb": self.cfg.get("output")}
        return StepIO(inputs, outputs)

    # ------------------------------------------------------------------
    def run(self, io: StepIO) -> ValidationResult:  # pragma: no cover - thin wrapper
        messages: List[str] = []
        metrics = {}

        raw_path = io.inputs["tb"]
        raw = pd.read_excel(raw_path)

        # 1) resolve columns
        before_cols = set(raw.columns)
        raw = resolve_columns(raw, SCHEMAS["TB"], COLUMN_ALIASES)
        after_cols = set(raw.columns)
        metrics["aliased_columns"] = len(after_cols - before_cols)

        # 2) coerce types & normalise
        tb = coerce_tb_types(raw)

        # 3) fill EntityCode/Period from filename if missing
        if tb["EntityCode"].isna().all():
            ent = infer_entity_from_filename(raw_path)
            if ent:
                tb["EntityCode"] = ent
                metrics["entity_inferred_from_filename"] = 1

        if tb["Period"].isna().all() or (tb["Period"] == "").all():
            per = infer_period_from_filename(raw_path)
            if per:
                tb["Period"] = per
                metrics["period_inferred_from_filename"] = 1

        # 4) handle single Amount column -> split into Debit/Credit
        if "Amount" in raw.columns and (
            "Debit" not in raw.columns or "Credit" not in raw.columns
        ):
            amt = pd.to_numeric(raw["Amount"], errors="coerce").fillna(0.0)
            tb["Debit"] = np.where(amt > 0, amt, 0.0)
            tb["Credit"] = np.where(amt < 0, -amt, 0.0)
            metrics["coerced_numeric_cells"] = int(amt.notna().sum())

        # 5) validation
        missing = [c for c in SCHEMAS["TB"] if c not in tb.columns]
        if missing:
            messages.append(f"unresolved columns {missing}")
            return ValidationResult(False, messages, metrics)

        # output
        tb.to_excel(io.outputs["tb"], index=False)
        return ValidationResult(True, messages, metrics)

