"""Client engagement letter draft generation step."""

from __future__ import annotations

import csv
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional

from ..core.contracts import StepIO, ValidationResult
from ..core.io_utils import expand, read_excel
from ..core.registry import register
from ..core.step_base import Step


@register("ClientEngagementLetterDraft")
class ClientEngagementLetterDraft(Step):
    """Generate draft engagement letters from metadata and templates."""

    name = "ClientEngagementLetterDraft"

    def plan_io(self) -> StepIO:
        params = self.cfg.get("params", {})
        required = ("client_metadata", "service_lines", "template_path")
        missing = [key for key in required if key not in params]
        if missing:
            raise ValueError(f"Missing required params for {self.name}: {missing}")

        inputs: Dict[str, str] = {
            "client_metadata": self._expand(params["client_metadata"]),
            "service_lines": self._expand(params["service_lines"]),
            "template_path": self._expand(params["template_path"]),
        }

        prior_folder = params.get("prior_letters_folder")
        if isinstance(prior_folder, str) and prior_folder:
            inputs["prior_letters_folder"] = self._expand(prior_folder)

        output_folder = params.get("output_folder", "{support}/EngagementLetters/{period}")
        letters_dir = self._expand(output_folder)

        manifest_path = params.get("manifest_path")
        if isinstance(manifest_path, str) and manifest_path:
            manifest = self._expand(manifest_path)
        else:
            manifest = str(Path(letters_dir) / f"draft_manifest_{self.period}.json")

        notification_path = params.get("notification_log")
        if isinstance(notification_path, str) and notification_path:
            notification_log = self._expand(notification_path)
        else:
            notification_log = str(Path(letters_dir) / f"notifications_{self.period}.txt")

        outputs = {
            "letters_dir": letters_dir,
            "manifest": manifest,
            "notification_log": notification_log,
        }

        return StepIO(inputs=inputs, outputs=outputs)

    def run(self, io: StepIO) -> ValidationResult:
        messages: List[str] = []
        metrics: Dict[str, Any] = {}

        metadata_path = Path(io.inputs["client_metadata"])
        service_path = Path(io.inputs["service_lines"])
        template_path = Path(io.inputs["template_path"])
        prior_folder = io.inputs.get("prior_letters_folder")

        try:
            metadata_rows = self._load_client_metadata(metadata_path)
        except FileNotFoundError:
            messages.append(f"Client metadata file not found: {metadata_path}")
            return ValidationResult(ok=False, messages=messages, metrics={})
        except Exception as exc:  # pragma: no cover - defensive
            messages.append(f"Failed to load client metadata: {exc}")
            return ValidationResult(ok=False, messages=messages, metrics={})

        try:
            service_rows = self._load_service_lines(service_path)
        except FileNotFoundError:
            messages.append(f"Service line reference file not found: {service_path}")
            return ValidationResult(ok=False, messages=messages, metrics={})
        except Exception as exc:  # pragma: no cover - defensive
            messages.append(f"Failed to load service line reference data: {exc}")
            return ValidationResult(ok=False, messages=messages, metrics={})

        metrics["clients_processed"] = len(metadata_rows)
        if not metadata_rows:
            messages.append(
                "Client metadata file contained no records → escalate to Manager for delayed export."
            )

        service_index = self._index_service_lines(service_rows)
        metrics["service_lines_available"] = len(service_index)

        try:
            template_text = self._load_template(template_path)
        except FileNotFoundError:
            messages.append(f"Template file not found: {template_path}")
            return ValidationResult(ok=False, messages=messages, metrics=metrics)

        letters_dir = Path(io.outputs["letters_dir"])
        letters_dir.mkdir(parents=True, exist_ok=True)

        manifest: List[Dict[str, Any]] = []
        exceptions: List[Dict[str, Any]] = []
        rolled_forward = 0

        for record in metadata_rows:
            client_name = self._extract_field(record, ["ClientName", "client_name", "Name"])
            client_id = self._extract_field(record, ["ClientID", "client_id", "Id", "ID"])
            fiscal_year = (
                self._extract_field(record, ["FiscalYear", "fiscal_year", "FY"]) or (self.period[:4] if self.period else "")
            )
            service_codes = self._extract_service_codes(record)

            missing_fields: List[str] = []
            if not client_name:
                missing_fields.append("client_name")
            if not client_id:
                missing_fields.append("client_id")
            if not fiscal_year:
                missing_fields.append("fiscal_year")
            if not service_codes:
                missing_fields.append("service_lines")

            if missing_fields:
                msg = f"Record missing required fields {missing_fields}: {record}"
                messages.append(msg)
                exceptions.append({"client_id": client_id or "", "reason": msg})
                continue

            service_details: List[Dict[str, Any]] = []
            invalid_codes: List[str] = []
            for code in service_codes:
                info = service_index.get(code.upper())
                if not info:
                    invalid_codes.append(code)
                    continue
                rate = self._extract_field(info, ["Rate", "BillingRate", "StandardRate", "HourlyRate"])
                if rate in (None, ""):
                    invalid_codes.append(code)
                    continue
                description = self._extract_field(
                    info,
                    ["Description", "ServiceLineDescription", "Name", "Service"],
                    default="",
                )
                service_details.append({"code": code.upper(), "description": description, "rate": rate})

            if invalid_codes:
                msg = (
                    f"Service line validation failed for client {client_name} ({client_id}): "
                    f"invalid or missing rate for {invalid_codes}"
                )
                messages.append(msg)
                exceptions.append({"client_id": client_id, "reason": msg})
                continue

            base_text = template_text
            source = "template"
            if prior_folder:
                prior_letter = self._locate_prior_letter(prior_folder, client_name, fiscal_year)
                if prior_letter and prior_letter.exists():
                    try:
                        prior_text = prior_letter.read_text(encoding="utf-8")
                    except UnicodeDecodeError:
                        prior_text = prior_letter.read_text(encoding="utf-8", errors="ignore")
                    if prior_text:
                        base_text = prior_text
                        source = "rolled_forward"
                        rolled_forward += 1
                else:
                    messages.append(
                        f"Prior year letter not found for {client_name} FY{fiscal_year} → defaulted to template."
                    )

            summary_lines: List[str] = []
            for item in service_details:
                rate_value = item["rate"]
                try:
                    cleaned = str(rate_value).replace("$", "").replace(",", "")
                    rate_float = float(cleaned)  # type: ignore[arg-type]
                    rate_display = f"${rate_float:,.2f}"
                except (TypeError, ValueError):
                    rate_display = str(rate_value)
                summary_lines.append(f"- {item['code']} ({item['description']}) @ {rate_display}")
            service_summary = "\n".join(summary_lines)

            generated_on = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
            context = {
                "ClientName": client_name,
                "ClientID": client_id,
                "FiscalYear": fiscal_year,
                "ServiceSummary": service_summary,
                "GeneratedOn": generated_on,
            }

            letter_text = self._merge_template(base_text, context)
            if "{{ServiceSummary}}" not in base_text:
                letter_text = letter_text.rstrip() + "\n\nService Summary:\n" + service_summary + "\n"
            if f"FY{fiscal_year}" not in letter_text:
                letter_text = letter_text.rstrip() + f"\n\nFiscal Year: FY{fiscal_year}\n"

            filename = f"{self._slugify(client_name)}_EngagementLetter_FY{fiscal_year}.docx"
            output_path = letters_dir / filename
            output_path.write_text(letter_text, encoding="utf-8")

            manifest.append(
                {
                    "client_id": client_id,
                    "client_name": client_name,
                    "fiscal_year": fiscal_year,
                    "service_lines": [item["code"] for item in service_details],
                    "output_path": str(output_path),
                    "source": source,
                    "generated_on": generated_on,
                }
            )

        manifest_path = Path(io.outputs["manifest"])
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_payload = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "letters": manifest,
            "exceptions": exceptions,
        }
        manifest_path.write_text(json.dumps(manifest_payload, indent=2), encoding="utf-8")

        raw_recipients = self.cfg.get("params", {}).get("notification_recipients", [])
        if isinstance(raw_recipients, (list, tuple, set)):
            recipients = [str(value) for value in raw_recipients if str(value).strip()]
        elif raw_recipients:
            recipients = [str(raw_recipients)]
        else:
            recipients = []

        notification_path = Path(io.outputs["notification_log"])
        notification_path.parent.mkdir(parents=True, exist_ok=True)
        if recipients:
            lines = [
                f"{datetime.utcnow().isoformat()}Z | Draft engagement letters ready: {len(manifest)} clients"
            ]
            for entry in manifest:
                lines.append(
                    "Notify "
                    + ", ".join(recipients)
                    + f" → {entry['client_name']} letter saved to {entry['output_path']}"
                )
        else:
            lines = ["No notification recipients configured."]
        notification_path.write_text("\n".join(lines), encoding="utf-8")

        metrics.update(
            {
                "letters_generated": len(manifest),
                "exceptions": len(exceptions),
                "rolled_forward_letters": rolled_forward,
                "notifications_prepared": len(recipients) * len(manifest) if recipients else 0,
            }
        )
        messages.append(f"Generated {len(manifest)} engagement letter drafts.")
        if exceptions:
            messages.append(f"Flagged {len(exceptions)} records for Administrator review.")

        ok = len(exceptions) == 0 and bool(manifest)
        return ValidationResult(ok=ok, messages=messages, metrics=metrics)

    # Helper utilities -----------------------------------------------------

    def _expand(self, value: str) -> str:
        return expand(value, **{**self.folders, **self.naming, "period": self.period})

    def _load_client_metadata(self, path: Path) -> List[Dict[str, Any]]:
        if not path.exists():
            raise FileNotFoundError(path)
        suffix = path.suffix.lower()
        if suffix == ".json":
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return [dict(item) for item in data]
            if isinstance(data, dict):
                if isinstance(data.get("clients"), list):
                    return [dict(item) for item in data["clients"]]
                return [dict(data)]
            raise ValueError("Client metadata JSON must be a list or contain a 'clients' array")
        if suffix == ".csv":
            with path.open(newline="", encoding="utf-8") as handle:
                reader = csv.DictReader(handle)
                return [dict(row) for row in reader]
        table = read_excel(path.as_posix())
        return self._as_records(table)

    def _load_service_lines(self, path: Path) -> List[Dict[str, Any]]:
        if not path.exists():
            raise FileNotFoundError(path)
        if path.suffix.lower() == ".json":
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return [dict(item) for item in data]
            if isinstance(data, dict) and isinstance(data.get("service_lines"), list):
                return [dict(item) for item in data["service_lines"]]
            raise ValueError("Service line JSON must be a list or contain 'service_lines'.")
        table = read_excel(path.as_posix())
        return self._as_records(table)

    def _as_records(self, table: Any) -> List[Dict[str, Any]]:
        if hasattr(table, "to_dict"):
            try:
                records = table.to_dict(orient="records")  # type: ignore[call-arg]
                return [dict(row) for row in records]
            except TypeError:
                pass
        if isinstance(table, list):
            return [dict(row) for row in table]
        if isinstance(table, tuple):
            return [dict(row) for row in table]
        return [dict(row) for row in list(table)]

    def _index_service_lines(self, rows: Iterable[Mapping[str, Any]]) -> Dict[str, Dict[str, Any]]:
        index: Dict[str, Dict[str, Any]] = {}
        for row in rows:
            code = self._extract_field(row, ["ServiceLineCode", "Code", "ServiceLine", "ServiceCode"])
            if not code:
                continue
            index[str(code).strip().upper()] = dict(row)
        return index

    def _load_template(self, path: Path) -> str:
        if not path.exists():
            raise FileNotFoundError(path)
        try:
            return path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return path.read_text(encoding="latin-1")

    def _extract_field(self, data: Mapping[str, Any], keys: Iterable[str], default: Any = None) -> Any:
        for key in keys:
            if key in data:
                value = data[key]
                if value not in (None, "", []):
                    return value
        return default

    def _extract_service_codes(self, record: Mapping[str, Any]) -> List[str]:
        candidates = [
            record.get("service_line_codes"),
            record.get("ServiceLineCodes"),
            record.get("ServiceLines"),
            record.get("services"),
            record.get("ServiceAssignments"),
        ]
        values: Any = None
        for candidate in candidates:
            if candidate not in (None, "", []):
                values = candidate
                break
        codes: List[str] = []
        if isinstance(values, str):
            parts = re.split(r"[;,]", values)
            codes = [part.strip() for part in parts if part.strip()]
        elif isinstance(values, Mapping):
            nested = values.get("codes") or values.get("items") or values.get("service_lines")
            if isinstance(nested, list):
                for item in nested:
                    codes.extend(self._extract_service_codes({"ServiceLines": item}))
        elif isinstance(values, Iterable) and not isinstance(values, (str, bytes)):
            for item in values:
                if isinstance(item, Mapping):
                    code = self._extract_field(item, ["code", "Code", "ServiceLineCode"])
                    if code:
                        codes.append(str(code).strip())
                else:
                    text = str(item).strip()
                    if text:
                        codes.append(text)
        ordered: List[str] = []
        for code in codes:
            uc = code.upper()
            if uc and uc not in ordered:
                ordered.append(uc)
        return ordered

    def _merge_template(self, template: str, context: Mapping[str, Any]) -> str:
        merged = template
        for key, value in context.items():
            merged = merged.replace(f"{{{{{key}}}}}", str(value))
        return merged

    def _slugify(self, name: str) -> str:
        slug = re.sub(r"[^A-Za-z0-9]+", "_", name).strip("_")
        return slug or "client"

    def _locate_prior_letter(self, folder: str, client_name: str, fiscal_year: str) -> Optional[Path]:
        base = Path(folder)
        if not base.exists():
            return None
        try:
            prev_year = str(int(fiscal_year) - 1)
        except (TypeError, ValueError):
            return None
        filename = f"{self._slugify(client_name)}_EngagementLetter_FY{prev_year}.docx"
        candidate = base / filename
        return candidate if candidate.exists() else None
