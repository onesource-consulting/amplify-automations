"""Implementation of the ``PDFAssembler`` step.

The original project produced rich PDF reports.  To keep this kata light‑weight
we simulate the behaviour by converting tabular data into plain text files with a
``.pdf`` extension and concatenating them.  This is sufficient for unit tests to
exercise the control flow of the step.
"""

from __future__ import annotations

from pathlib import Path
from typing import List

from ..core.registry import register
from ..core.step_base import Step
from ..core.contracts import StepIO, ValidationResult
from ..core.io_utils import expand, read_excel


def excel_to_simple_pdf(excel_path: str, pdf_path: str) -> None:
    """Create a rudimentary PDF (actually a text file) from tabular data."""
    rows = read_excel(excel_path)
    if not isinstance(rows, list):
        rows = rows.to_dict(orient="records")
    with open(pdf_path, "w") as f:
        for row in rows[:1000]:
            f.write(" | ".join(str(v) for v in row.values()))
            f.write("\n")


@register("PDFAssembler")
class PDFAssembler(Step):
    name = "PDFAssembler"

    def plan_io(self) -> StepIO:
        support_pdf = f"{self.folders['support']}/" + expand(self.naming["support_pdf"], period=self.period)
        return StepIO(inputs={}, outputs={"support": support_pdf})

    def run(self, io: StepIO) -> ValidationResult:
        inc: List[str] = self.cfg["params"]["include"]
        pdfs: List[str] = []
        for p in inc:
            path = expand(p, tb=self.folders["tb"], fx=self.folders["fx"], period=self.period)
            pdf_out = Path(path).with_suffix(".pdf").as_posix()
            excel_to_simple_pdf(path, pdf_out)
            pdfs.append(pdf_out)

        Path(io.outputs["support"]).parent.mkdir(parents=True, exist_ok=True)
        with open(io.outputs["support"], "w") as out_f:
            for p in pdfs:
                with open(p) as f:
                    out_f.write(f.read())
                    out_f.write("\n")
        return ValidationResult(True, [f"Merged {len(pdfs)} PDFs → {io.outputs['support']}"] , {"source_pdfs": len(pdfs)})
