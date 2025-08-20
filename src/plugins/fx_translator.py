"""Implementation of the ``FXTranslator`` step.

This step enriches the master trial balance with foreign exchange rates and
produces both an adjusted TB and a separate FX adjustment file.  The
implementation is intentionally lightweight and operates on CSV based pseudo
Excel files to keep the test environment small.
"""

from __future__ import annotations

from typing import Dict, List

from core.registry import register
from core.step_base import Step
from core.contracts import StepIO, ValidationResult
from core.io_utils import expand, read_excel, write_excel


@register("FXTranslator")
class FXTranslator(Step):
    name = "FXTranslator"

    def plan_io(self) -> StepIO:
        tb_dir = self.folders["tb"]
        fx_dir = self.folders["fx"]
        master_in = f"{tb_dir}/" + expand(self.naming["master_tb"], period=self.period)
        fx_rates = expand(self.naming["fx_rates"], period=self.period)
        fx_adj = f"{fx_dir}/" + expand(self.naming["fx_adjustments"], period=self.period)
        master_out = f"{tb_dir}/Master_TB_{self.period}_Adjusted.xlsx"
        return StepIO(
            inputs={"master_tb": master_in, "fx_rates": f"{fx_dir}/{fx_rates}"},
            outputs={"adjusted_tb": master_out, "fx_adjustments": fx_adj},
        )

    def _load_rates(self, fx_source: str, rates_file: str, reporting_currency: str) -> Dict[str, float]:
        """Load FX rates from a file.  External sources are intentionally unsupported."""
        if fx_source != "file":  # pragma: no cover - defensive
            raise ValueError("Only file FX sources are supported in the test implementation")
        rows = read_excel(rates_file)
        if not isinstance(rows, list):
            rows = rows.to_dict(orient="records")
        return {row["CurrencyCode"]: float(row["FXRate"]) for row in rows}

    def run(self, io: StepIO) -> ValidationResult:
        params = self.cfg["params"]
        tol = params.get("tolerance", 5)
        reporting = self.cfg.get("reporting_currency", "USD")

        tb = read_excel(io.inputs["master_tb"])
        if not isinstance(tb, list):
            tb = tb.to_dict(orient="records")
        rates = self._load_rates(params.get("fx_source", "file"), io.inputs["fx_rates"], reporting)

        if tb and "CurrencyCode" not in tb[0]:
            return ValidationResult(False, ["Missing CurrencyCode in TB"])

        missing_codes: List[str] = []
        for row in tb:
            code = row.get("CurrencyCode")
            rate = rates.get(code)
            if rate is None:
                missing_codes.append(code)
                continue
            row["FXRate"] = rate
            row["LocalAmount"] = float(row.get("Debit", 0) or 0) - float(row.get("Credit", 0) or 0)
            row["ReportingCurrencyAmount"] = round(row["LocalAmount"] * rate, 2)

        if missing_codes:
            return ValidationResult(False, [f"Missing FX rates for: {sorted(set(missing_codes))}"])

        fx_adj = [
            {
                "EntityCode": r.get("EntityCode"),
                "AccountCode": r.get("AccountCode"),
                "LocalAmount": r["LocalAmount"],
                "FXRate": r["FXRate"],
                "ReportingCurrencyAmount": r["ReportingCurrencyAmount"],
                "Period": self.period,
            }
            for r in tb
        ]

        write_excel(tb, io.outputs["adjusted_tb"])
        write_excel(fx_adj, io.outputs["fx_adjustments"])
        return ValidationResult(True, [f"Applied FX to {len(tb)} rows"], {"rows": len(tb), "tolerance": tol})
