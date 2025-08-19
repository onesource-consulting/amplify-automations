"""Implementation of the ``TBCollector`` step.

The real project loads a number of trial balance (TB) spreadsheets and merges
them into a master TB.  The simplified implementation operates on small CSV
files with an ``.xlsx`` extension so that the tests can run without heavy
third‑party dependencies.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Dict

from core.registry import register
from core.step_base import Step
from core.contracts import StepIO, ValidationResult
from core.io_utils import expand, read_excel, write_excel
from core.validation_utils import require_columns, debits_equal_credits


@register("TBCollector")
class TBCollector(Step):
    name = "TBCollector"

    def plan_io(self) -> StepIO:
        tb_dir = self.folders["tb"]
        out_master = expand(self.naming["master_tb"], period=self.period)
        return StepIO(inputs={"tb_folder": tb_dir},
                      outputs={"master_tb": f"{tb_dir}/{out_master}"})

    def run(self, io: StepIO) -> ValidationResult:
        req_cols: List[str] = self.cfg["params"]["required_columns"]
        enforce_balanced = self.cfg["params"].get("enforce_balanced", True)

        rows: List[Dict[str, object]] = []
        metrics = {"files": 0, "rows": 0}
        messages: List[str] = []
        for path in Path(io.inputs["tb_folder"]).glob(f"TB_*_{self.period}.xlsx"):
            data = read_excel(path)
            missing = require_columns(data, req_cols)
            if missing:
                messages.append(f"{path.name}: missing {missing}")
                return ValidationResult(False, messages)
            if enforce_balanced and not debits_equal_credits(data):
                messages.append(f"{path.name}: debits != credits")
                return ValidationResult(False, messages)
            rows.extend(data)
            metrics["files"] += 1
            metrics["rows"] += len(data)

        # Always produce a file with the proper header even if no TBs were found
        write_excel(rows, io.outputs["master_tb"], headers=req_cols)
        messages.append(f"Master TB rows={len(rows)} files={metrics['files']}")
        return ValidationResult(True, messages, metrics)
