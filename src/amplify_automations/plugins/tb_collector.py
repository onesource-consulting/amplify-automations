"""Trial Balance collector step with normalisation and master merge.

This implementation scans a TB folder for files named `TB_*_{YYYYMM}.xlsx`,
normalises each file into the canonical TB schema, validates it, and merges
all rows into a single Master TB for the given period.

- With pandas installed: full normalisation (aliases, type coercion, filename
  inference, Amount→Debit/Credit split).
- Without pandas: falls back to strict schema checks and simple coercion.

Outputs always conform to the canonical TB header and naming contract.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Dict, Any, Iterable

# Optional pandas import: enables richer normalisation
try:
    import pandas as pd  # type: ignore
    import numpy as np  # type: ignore
    HAS_PANDAS = True
except Exception:  # pragma: no cover
    pd = None  # type: ignore
    np = None  # type: ignore
    HAS_PANDAS = False

from ..core.registry import register
from ..core.step_base import Step
from ..core.contracts import StepIO, ValidationResult
from ..core.io_utils import expand, read_excel, write_excel
from ..core.validation_utils import require_columns, debits_equal_credits

# Try to use a shared normalisation module if present; otherwise provide light defaults.
try:  # pragma: no cover (imported in main project)
    from ..core.normalization import (
        COLUMN_ALIASES,
        SCHEMAS,
        coerce_tb_types,
        infer_entity_from_filename,
        infer_period_from_filename,
        resolve_columns,
    )
except Exception:  # Fallbacks so kata/tests still work without the module
    COLUMN_ALIASES = {
        "EntityCode": ["Entity", "Company", "CompanyCode", "CoCode", "LegalEntity", "LE"],
        "AccountCode": ["GL", "GLCode", "Account", "Acct", "GL Account", "Account Number"],
        "AccountName": ["AccountDesc", "Account Description", "GL Name"],
        "Debit": ["Dr", "Debits", "Debit Amount"],
        "Credit": ["Cr", "Credits", "Credit Amount"],
        "Period": ["FiscalPeriod", "PeriodId", "YYYYMM", "PostingPeriod"],
        "CurrencyCode": ["Currency", "Curr", "ISO Currency", "LCY"],
    }
    SCHEMAS = {
        "TB": ["EntityCode","AccountCode","AccountName","Debit","Credit","Period","CurrencyCode"]
    }

    def infer_period_from_filename(path: str) -> str | None:
        import re
        m = re.search(r"(20\d{2})(0[1-9]|1[0-2])", Path(path).name)
        return f"{m.group(1)}{m.group(2)}" if m else None

    def infer_entity_from_filename(path: str) -> str | None:
        import re
        m = re.search(r"TB_([^_\.]+)", Path(path).name, flags=re.IGNORECASE)
        return m.group(1) if m else None

    def resolve_columns(df: "pd.DataFrame", target: List[str], aliases: Dict[str, List[str]]) -> "pd.DataFrame":
        # Simple alias resolver; no fuzzy matching in fallback.
        cols = {c.lower(): c for c in df.columns}
        ren = {}
        for want in target:
            if want in df.columns:
                continue
            found = None
            for alt in aliases.get(want, []):
                if alt.lower() in cols:
                    found = cols[alt.lower()]
                    break
            if found:
                ren[found] = want
        if ren:
            df = df.rename(columns=ren)
        return df

    def coerce_tb_types(df: "pd.DataFrame") -> "pd.DataFrame":
        if "Debit" in df.columns:
            df["Debit"] = pd.to_numeric(df["Debit"], errors="coerce").fillna(0.0)
        if "Credit" in df.columns:
            df["Credit"] = pd.to_numeric(df["Credit"], errors="coerce").fillna(0.0)
        if "CurrencyCode" in df.columns:
            df["CurrencyCode"] = df["CurrencyCode"].astype(str).str.upper()
        if "Period" in df.columns:
            df["Period"] = (
                df["Period"].astype(str).str.replace(r"[^0-9]", "", regex=True).str.slice(0, 6)
            )
        # Ensure all required columns exist
        for req in SCHEMAS["TB"]:
            if req not in df.columns:
                df[req] = "" if req not in ("Debit", "Credit") else 0.0
        return df


@register("TBCollector")
class TBCollector(Step):
    name = "TBCollector"

    def plan_io(self) -> StepIO:
        tb_dir = self.folders["tb"]
        out_master = expand(self.naming["master_tb"], period=self.period)
        return StepIO(
            inputs={"tb_folder": tb_dir},
            outputs={"master_tb": f"{tb_dir}/{out_master}"},
        )

    def _normalise_with_pandas(self, path: Path, req_cols: List[str], metrics: Dict[str, Any], messages: List[str]) -> List[Dict[str, Any]] | None:
        """Read + normalise a single file using pandas; return records or None on error."""
        df = read_excel(path)
        if not isinstance(df, pd.DataFrame):
            # convert list-of-dicts to DF for normalisation
            df = pd.DataFrame(df)

        before_cols = set(df.columns)
        df = resolve_columns(df, SCHEMAS["TB"], COLUMN_ALIASES)
        after_cols = set(df.columns)
        metrics["aliased_columns"] = metrics.get("aliased_columns", 0) + len(after_cols - before_cols)

        df = coerce_tb_types(df)

        # fill from filename if missing
        if "EntityCode" in df.columns and (df["EntityCode"].isna() | (df["EntityCode"] == "")).all():
            ent = infer_entity_from_filename(path.as_posix())
            if ent:
                df["EntityCode"] = ent
                metrics["entity_inferred_from_filename"] = metrics.get("entity_inferred_from_filename", 0) + 1

        if "Period" in df.columns and (df["Period"].isna() | (df["Period"] == "")).all():
            per = infer_period_from_filename(path.as_posix())
            if per:
                df["Period"] = per
                metrics["period_inferred_from_filename"] = metrics.get("period_inferred_from_filename", 0) + 1

        # If single Amount column exists, split into Debit/Credit
        if "Amount" in df.columns and (("Debit" not in df.columns) or ("Credit" not in df.columns)):
            amt = pd.to_numeric(df["Amount"], errors="coerce").fillna(0.0)
            df["Debit"] = np.where(amt > 0, amt, 0.0)
            df["Credit"] = np.where(amt < 0, -amt, 0.0)
            metrics["coerced_numeric_cells"] = metrics.get("coerced_numeric_cells", 0) + int(amt.notna().sum())

        # validate required columns
        missing = [c for c in req_cols if c not in df.columns]
        if missing:
            messages.append(f"{path.name}: unresolved columns {missing}")
            return None

        # Optional balance check can be applied by caller using validation_utils
        return df.to_dict(orient="records")

    def _normalise_without_pandas(self, path: Path, req_cols: List[str], metrics: Dict[str, Any], messages: List[str]) -> List[Dict[str, Any]] | None:
        """Fallback: operate on list-of-dicts only (no pandas)."""
        data = read_excel(path)  # list[dict]
        # Ensure keys exist; try filename inference
        period_hint = infer_period_from_filename(path.as_posix())
        entity_hint = infer_entity_from_filename(path.as_posix())

        # If Amount present but no Debit/Credit, derive them
        rows_out: List[Dict[str, Any]] = []
        for row in data:
            r = dict(row)
            if "Debit" not in r and "Credit" not in r and "Amount" in r:
                try:
                    val = float(r.get("Amount", 0) or 0)
                except (TypeError, ValueError):
                    val = 0.0
                r["Debit"] = val if val > 0 else 0.0
                r["Credit"] = -val if val < 0 else 0.0
            # basic normalisations
            if "CurrencyCode" in r and isinstance(r["CurrencyCode"], str):
                r["CurrencyCode"] = r["CurrencyCode"].upper()
            if (not r.get("EntityCode")) and entity_hint:
                r["EntityCode"] = entity_hint
            if (not r.get("Period")) and period_hint:
                r["Period"] = period_hint
            rows_out.append(r)

        missing = require_columns(rows_out, req_cols)
        if missing:
            messages.append(f"{path.name}: missing {missing}")
            return None

        return rows_out

    def run(self, io: StepIO) -> ValidationResult:
        req_cols: List[str] = self.cfg["params"]["required_columns"]
        enforce_balanced = self.cfg["params"].get("enforce_balanced", True)

        all_rows: List[Dict[str, Any]] = []
        metrics: Dict[str, Any] = {"files": 0, "rows": 0}
        messages: List[str] = []

        for path in Path(io.inputs["tb_folder"]).glob(f"TB_*_{self.period}.xlsx"):
            if HAS_PANDAS:
                rows = self._normalise_with_pandas(path, req_cols, metrics, messages)
            else:
                rows = self._normalise_without_pandas(path, req_cols, metrics, messages)

            if rows is None:
                return ValidationResult(False, messages, metrics)

            # per-file balance check if requested
            if enforce_balanced:
                if HAS_PANDAS:
                    # Convert to DF for numeric robustness
                    df = pd.DataFrame(rows)
                    if not debits_equal_credits(df):
                        messages.append(f"{path.name}: debits != credits")
                        return ValidationResult(False, messages, metrics)
                else:
                    if not debits_equal_credits(rows):
                        messages.append(f"{path.name}: debits != credits")
                        return ValidationResult(False, messages, metrics)

            all_rows.extend(rows)
            metrics["files"] += 1
            metrics["rows"] += len(rows)

        # Always produce a file with canonical header, even if no TBs found
        write_excel(all_rows, io.outputs["master_tb"], headers=req_cols)
        messages.append(f"Master TB rows={len(all_rows)} files={metrics['files']}")
        return ValidationResult(True, messages, metrics)